"""Temporal-holdout validation of the CardioXNet Discovery Score.

The question
------------
The Discovery Score is intended to surface supported pathway intersections that
are under-examined for a given seed set and disease. This retrospective analysis
freezes literature at a cutoff year and tests whether the resulting ranking is
positively associated with subsequent publication activity. A null result
bounds the score as a gap-triage measure rather than a forecast.

Design
------
For each analysis in the input set, and for every ranked pathway:

  1. ``hits_pre``  = PubMed records at the (pathway x seed genes x disease)
     intersection published on or before ``--cutoff``.
  2. ``hits_post`` = records at the same intersection published after the cutoff,
     up to ``--through``.
  3. Literature novelty is recomputed from ``hits_pre``. The pathway's static
     gene-novelty component is recovered from the live score components, then
     combined at the same 2:1 literature-to-gene ratio used by the deployed
     validator. This reproduces the score CardioXNet would have assigned at the
     cutoff.
  4. Growth is ``hits_post / (hits_pre + 1)`` -- the post-cutoff publication rate
     normalized for how large the field already was. Without that normalization
     the measure would simply rediscover that big fields publish more.

Read-out
--------
Spearman correlation between the retrospective Discovery Score and subsequent
growth, the same for the composite novelty term and for the enrichment score
alone (as baselines), plus growth stratified by the novelty tier assigned at the
cutoff. A positive correlation for Discovery but not for the enrichment
baseline would support prospective utility. A negative result is reported as a
validity boundary.

Every PubMed count is cached on disk, so a rerun costs no API calls.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import GeneInfo
from app.services.hypothesis_validator import HypothesisValidator
from app.services.literature_miner import LiteratureMiner

CACHE_PATH = Path(__file__).resolve().parent / "out" / "pubmed_counts.json"


class CountCache:
    """On-disk memo for PubMed counts, keyed by query and date window."""

    def __init__(self, path: Path):
        self.path = path
        self.data: Dict[str, int] = {}
        if path.exists():
            self.data = json.loads(path.read_text(encoding="utf-8"))
        self._dirty = 0

    def get(self, client, query: str, mindate: Optional[str], maxdate: Optional[str]) -> int:
        key = f"{mindate or ''}|{maxdate or ''}|{query}"
        if key in self.data:
            return self.data[key]
        value = client.count_hits(query, mindate=mindate, maxdate=maxdate)
        # A failed lookup is never cached, so a later run retries it.
        if value >= 0:
            self.data[key] = value
            self._dirty += 1
            if self._dirty % 20 == 0:
                self.flush()
        return value

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=0), encoding="utf-8")


def saturation(hits: int, ceiling: int = HypothesisValidator.SATURATION_CEILING) -> float:
    """The same transform the live validator applies."""
    return max(0.0, min(math.log10(hits + 1) / math.log10(ceiling + 1), 1.0))


def gene_novelty_from_report(hypothesis: Dict) -> float:
    """Recover the deployed gene-novelty term from a persisted report row.

    New reports store this component directly. Earlier reports retain the
    full-precision weighted novelty contribution and exact PubMed count, which
    together identify gene novelty through the deployed 2:1 composite.
    """
    components = hypothesis.get("score_components") or {}
    direct = components.get("gene_novelty")
    if direct is not None:
        return max(0.0, min(float(direct), 1.0))

    weighted = components.get("novelty_score")
    hits = components.get("pubmed_hit_count")
    if weighted is None or not isinstance(hits, int) or hits < 0:
        raise ValueError(
            "Cannot reconstruct gene novelty for "
            f"{hypothesis.get('pathway_name', 'pathway')}"
        )
    live_composite = float(weighted) / 0.15
    live_literature_novelty = 1.0 - saturation(hits)
    recovered = 3.0 * live_composite - 2.0 * live_literature_novelty
    return max(0.0, min(recovered, 1.0))


def composite_novelty(literature_novelty: float, gene_novelty: float) -> float:
    """Use the same 2:1 novelty weighting as HypothesisValidator."""
    return (2.0 * literature_novelty + gene_novelty) / 3.0


def persisted_query_provenance(hypothesis: Dict) -> Dict[str, object]:
    """Read the exact deployed query inputs; never silently reconstruct them."""
    components = hypothesis.get("score_components") or {}
    query = hypothesis.get("literature_query") or components.get("literature_query")
    query_genes = (
        hypothesis.get("literature_query_genes")
        or components.get("literature_query_genes")
    )
    query_tier = hypothesis.get("query_tier") or components.get("query_tier")
    concept_query = (
        hypothesis.get("literature_concept_query")
        or components.get("literature_concept_query")
    )
    missing = [
        name
        for name, value in (
            ("literature_query", query),
            ("literature_query_genes", query_genes),
            ("query_tier", query_tier),
            ("literature_concept_query", concept_query),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            "Temporal holdout requires exact persisted query provenance for "
            f"{hypothesis.get('pathway_name', 'pathway')}: missing "
            + ", ".join(missing)
        )
    if query_tier != "strict":
        raise ValueError(
            "Temporal holdout accepts only strict deployed queries; "
            f"got {query_tier!r} for {hypothesis.get('pathway_name', 'pathway')}"
        )
    return {
        "query": str(query),
        "query_genes": list(query_genes),
        "query_tier": str(query_tier),
        "concept_query": str(concept_query),
    }


def spearman(xs: List[float], ys: List[float]) -> Optional[float]:
    """Spearman rho using average ranks for ties. None when undefined."""
    n = len(xs)
    if n < 3:
        return None

    def ranks(values: List[float]) -> List[float]:
        order = sorted(range(n), key=lambda i: values[i])
        out = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and values[order[j + 1]] == values[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return round(num / den, 4) if den else None


def tier(novelty: float, novelty_confidence: Optional[str] = None) -> str:
    if novelty_confidence == "ungrounded_seeds":
        return "Ungrounded"
    if novelty_confidence and novelty_confidence.startswith("unverified"):
        return "Unverified"
    if novelty >= 0.80:
        return "Highly Novel"
    if novelty >= 0.55:
        return "Novel"
    if novelty >= 0.30:
        return "Emerging"
    return "Established"


def novelty_gate_state(
    hits_pre: int,
    seed_disease_pre: int,
    concept_hits_pre: Optional[int] = None,
) -> Dict[str, object]:
    """Reproduce the validator's grounding and zero-query confidence gates."""
    state: Dict[str, object] = {
        "saturation_hits_pre": hits_pre,
        "saturation_basis": "pubmed_corpus",
        "novelty_confidence": None,
    }
    if seed_disease_pre < HypothesisValidator.MIN_SEED_DISEASE_CORPUS:
        state.update({
            "saturation_hits_pre": max(
                hits_pre, HypothesisValidator.UNVERIFIED_CORPUS_PROXY
            ),
            "saturation_basis": "ungrounded_seeds",
            "novelty_confidence": "ungrounded_seeds",
        })
    elif hits_pre == 0:
        if concept_hits_pre is None or concept_hits_pre < 0:
            raise ValueError("A grounded zero-count query requires a concept count")
        if concept_hits_pre < HypothesisValidator.MIN_CONCEPT_CORPUS:
            state.update({
                "saturation_hits_pre": HypothesisValidator.UNVERIFIED_CORPUS_PROXY,
                "saturation_basis": "unverified_concept",
                "novelty_confidence": "unverified_concept",
            })
        else:
            state["novelty_confidence"] = "verified_gap"
    return state


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="analysis JSON files")
    ap.add_argument("--cutoff", default="2020", help="literature frozen at end of this year")
    ap.add_argument("--through", default="2026", help="upper bound of the follow-up window")
    ap.add_argument(
        "--retrieved-on",
        default=None,
        help="date on which the live PubMed counts were retrieved (YYYY-MM-DD)",
    )
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--cache",
        default=str(CACHE_PATH),
        help="path to the PubMed count cache",
    )
    ap.add_argument(
        "--max-pathways",
        type=int,
        default=None,
        help="optional per-panel cap; by default every ranked pathway is evaluated",
    )
    args = ap.parse_args()

    miner = LiteratureMiner()
    cache = CountCache(Path(args.cache))
    records: List[Dict] = []

    for run_path in args.runs:
        run = json.loads(Path(run_path).read_text(encoding="utf-8"))
        # A bench run JSON records where the report was written; the ranked
        # hypotheses live in that report, not in the run wrapper.
        report_path = (run.get("report_files") or {}).get("json")
        if report_path and Path(report_path).exists():
            report = json.loads(Path(report_path).read_text(encoding="utf-8"))
            report["_bench"] = run.get("_bench", {})
            run = report
        bench = run.get("_bench", {})
        disease = bench.get("disease") or run.get("disease_context") or "heart_failure"
        seed_symbols = bench.get("seed_genes") or [
            g.get("symbol") for g in (run.get("seed_genes") or []) if isinstance(g, dict)
        ]
        seeds = [GeneInfo(input_id=s, entrez_id="0", symbol=s) for s in seed_symbols if s]
        hypotheses = run.get("ranked_hypotheses") or []
        print(f"\n{Path(run_path).name}: {len(hypotheses)} pathways, seeds={seed_symbols}")

        # Reuse the deployed run-level grounding query exactly. Reconstructing
        # it from a manifest can diverge when input validation drops a seed.
        grounding = (run.get("run_metadata") or {}).get("literature_grounding") or {}
        seed_query = grounding.get("query")
        if not seed_query:
            raise ValueError(
                f"Missing persisted literature grounding query for {Path(run_path).name}"
            )
        seed_disease_pre = cache.get(
            miner.pubmed_client, seed_query, None, args.cutoff
        )
        if seed_disease_pre < 0:
            raise RuntimeError(
                f"Seed-disease corpus lookup failed for {Path(run_path).name}"
            )
        selected_hypotheses = (
            hypotheses if args.max_pathways is None
            else hypotheses[: args.max_pathways]
        )

        for h in selected_hypotheses:
            name = h.get("pathway_name", "")
            provenance = persisted_query_provenance(h)
            query = provenance["query"]

            hits_pre = cache.get(miner.pubmed_client, query, None, args.cutoff)
            hits_post = cache.get(
                miner.pubmed_client, query, str(int(args.cutoff) + 1), args.through
            )
            if hits_pre < 0 or hits_post < 0:
                print(f"  ! count lookup failed, skipping: {name[:50]}")
                continue

            # Match HypothesisValidator's confidence gates exactly. A raw zero
            # becomes a verified gap only when the pathway concept itself had a
            # searchable pre-cutoff corpus; otherwise a conservative proxy is
            # used. An ungrounded seed panel receives the same proxy and an
            # explicit undefined tier.
            concept_hits_pre: Optional[int] = None
            if (
                seed_disease_pre >= HypothesisValidator.MIN_SEED_DISEASE_CORPUS
                and hits_pre == 0
            ):
                concept_hits_pre = (
                    cache.get(
                        miner.pubmed_client,
                        provenance["concept_query"],
                        None,
                        args.cutoff,
                    )
                    if concept_clause else 0
                )
                if concept_hits_pre < 0:
                    raise RuntimeError(f"Concept corpus lookup failed for {name}")

            gate = novelty_gate_state(
                hits_pre, seed_disease_pre, concept_hits_pre
            )
            saturation_hits_pre = int(gate["saturation_hits_pre"])
            saturation_basis = str(gate["saturation_basis"])
            novelty_confidence = gate["novelty_confidence"]

            literature_novelty_pre = 1.0 - saturation(saturation_hits_pre)
            gene_novelty = gene_novelty_from_report(h)
            novelty_pre = composite_novelty(literature_novelty_pre, gene_novelty)
            pps = float(h.get("nes_score") or 0.0)
            records.append({
                "run": Path(run_path).stem,
                "pathway_id": h.get("pathway_id"),
                "pathway_name": name,
                "source_db": h.get("source_db"),
                "pps": pps,
                "hits_pre": hits_pre,
                "hits_post": hits_post,
                "saturation_hits_pre": saturation_hits_pre,
                "saturation_basis": saturation_basis,
                "novelty_confidence": novelty_confidence,
                "concept_hits_pre": concept_hits_pre,
                "seed_disease_pre": seed_disease_pre,
                "literature_novelty_pre": round(literature_novelty_pre, 4),
                "gene_novelty": round(gene_novelty, 4),
                "novelty_pre": round(novelty_pre, 4),
                "tier_pre": tier(novelty_pre, novelty_confidence),
                "discovery_pre": round(pps * novelty_pre, 4),
                "growth": round(hits_post / (hits_pre + 1), 4),
            })
            print(f"  {hits_pre:>6} -> +{hits_post:<5} growth={records[-1]['growth']:6.2f} "
                  f"{records[-1]['tier_pre']:<13} {name[:46]}")

    cache.flush()

    summary: Dict = {
        "cutoff": args.cutoff,
        "through": args.through,
        "retrieved_on": args.retrieved_on,
        "cache": str(Path(args.cache)),
        "n_pathways": len(records),
        "n_runs": len(args.runs),
        "analysis_unit_note": (
            "Pathways within a panel overlap and are not independent biological "
            "replicates; correlations are descriptive."
        ),
    }
    if records:
        summary["spearman_discovery_vs_growth"] = spearman(
            [r["discovery_pre"] for r in records], [r["growth"] for r in records]
        )
        summary["spearman_novelty_vs_growth"] = spearman(
            [r["novelty_pre"] for r in records], [r["growth"] for r in records]
        )
        # Baseline: does the enrichment score on its own predict growth?
        # Absolute post-cutoff volume, not a rate. The rate normalizes away the
        # very effect being tested when hits_pre is small, so both are reported.
        summary["spearman_novelty_vs_absolute"] = spearman(
            [r["novelty_pre"] for r in records], [r["hits_post"] for r in records]
        )
        summary["n_measurable"] = sum(1 for r in records if r["hits_pre"] > 0)
        measurable = [r for r in records if r["hits_pre"] > 0]
        if len(measurable) >= 3:
            summary["spearman_discovery_vs_growth_measurable"] = spearman(
                [r["discovery_pre"] for r in measurable], [r["growth"] for r in measurable]
            )
        summary["spearman_pps_vs_growth"] = spearman(
            [r["pps"] for r in records], [r["growth"] for r in records]
        )
        summary["spearman_discovery_vs_growth_by_run"] = {
            run: spearman(
                [r["discovery_pre"] for r in records if r["run"] == run],
                [r["growth"] for r in records if r["run"] == run],
            )
            for run in sorted({r["run"] for r in records})
        }
        summary["novelty_confidence_counts"] = {
            str(confidence or "not_applicable_nonzero"): sum(
                1 for r in records if r["novelty_confidence"] == confidence
            )
            for confidence in sorted(
                {r["novelty_confidence"] for r in records},
                key=lambda value: str(value),
            )
        }
        by_tier: Dict[str, List[float]] = {}
        for r in records:
            by_tier.setdefault(r["tier_pre"], []).append(r["growth"])
        summary["growth_by_tier"] = {
            t: {
                "n": len(v),
                "mean_growth": round(sum(v) / len(v), 4),
                "median_growth": round(statistics.median(v), 4),
            }
            for t, v in sorted(by_tier.items())
        }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"summary": summary, "records": records}, indent=1), encoding="utf-8"
    )
    print("\n" + json.dumps(summary, indent=1))
    print(f"\nWROTE {out}")


if __name__ == "__main__":
    main()
