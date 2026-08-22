"""Temporal-holdout validation of the CardioXNet Discovery Score.

The question
------------
The Discovery Score claims to surface pathways that are genuinely under-studied
for a given seed set. A purely descriptive metric would only restate what has
already been written. To show the score is *predictive*, we freeze the
literature at a cutoff year, rank pathways using only what was known then, and
ask whether the pathways it called novel subsequently accumulated publications.

Design
------
For each analysis in the input set, and for every ranked pathway:

  1. ``hits_pre``  = PubMed records at the (pathway x seed genes x disease)
     intersection published on or before ``--cutoff``.
  2. ``hits_post`` = records at the same intersection published after the cutoff,
     up to ``--through``.
  3. The retrospective Discovery Score is recomputed from ``hits_pre`` alone,
     using the same saturation transform the live validator applies, so the
     ranking is the one CardioXNet would have produced at the cutoff.
  4. Growth is ``hits_post / (hits_pre + 1)`` -- the post-cutoff publication rate
     normalised for how large the field already was. Without that normalisation
     the measure would simply rediscover that big fields publish more.

Read-out
--------
Spearman correlation between the retrospective Discovery Score and subsequent
growth, the same for the novelty term alone and for the enrichment score alone
(as baselines), plus growth stratified by the novelty tier assigned at the
cutoff. A positive correlation for Discovery but not for the enrichment
baseline is the result that would support the tool's central claim.

Every PubMed count is cached on disk, so a rerun costs no API calls.
"""

from __future__ import annotations

import argparse
import json
import math
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


def tier(novelty: float) -> str:
    if novelty >= 0.80:
        return "Highly Novel"
    if novelty >= 0.55:
        return "Novel"
    if novelty >= 0.30:
        return "Emerging"
    return "Established"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="analysis JSON files")
    ap.add_argument("--cutoff", default="2020", help="literature frozen at end of this year")
    ap.add_argument("--through", default="2026", help="upper bound of the follow-up window")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-pathways", type=int, default=40)
    args = ap.parse_args()

    miner = LiteratureMiner()
    cache = CountCache(CACHE_PATH)
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

        for h in hypotheses[: args.max_pathways]:
            name = h.get("pathway_name", "")
            traced = h.get("seed_genes") or seed_symbols
            contributing = [g for g in seeds if g.symbol in traced] or seeds
            query = miner._construct_hypothesis_query(name, contributing, disease_context=disease)

            hits_pre = cache.get(miner.pubmed_client, query, None, args.cutoff)
            hits_post = cache.get(
                miner.pubmed_client, query, str(int(args.cutoff) + 1), args.through
            )
            if hits_pre < 0 or hits_post < 0:
                print(f"  ! count lookup failed, skipping: {name[:50]}")
                continue

            novelty_pre = 1.0 - saturation(hits_pre)
            pps = float(h.get("nes_score") or 0.0)
            records.append({
                "run": Path(run_path).stem,
                "pathway_id": h.get("pathway_id"),
                "pathway_name": name,
                "source_db": h.get("source_db"),
                "pps": pps,
                "hits_pre": hits_pre,
                "hits_post": hits_post,
                "novelty_pre": round(novelty_pre, 4),
                "tier_pre": tier(novelty_pre),
                "discovery_pre": round(pps * novelty_pre, 4),
                "growth": round(hits_post / (hits_pre + 1), 4),
            })
            print(f"  {hits_pre:>6} -> +{hits_post:<5} growth={records[-1]['growth']:6.2f} "
                  f"{records[-1]['tier_pre']:<13} {name[:46]}")

    cache.flush()

    summary: Dict = {
        "cutoff": args.cutoff,
        "through": args.through,
        "n_pathways": len(records),
        "n_runs": len(args.runs),
    }
    if records:
        summary["spearman_discovery_vs_growth"] = spearman(
            [r["discovery_pre"] for r in records], [r["growth"] for r in records]
        )
        summary["spearman_novelty_vs_growth"] = spearman(
            [r["novelty_pre"] for r in records], [r["growth"] for r in records]
        )
        # Baseline: does the enrichment score on its own predict growth?
        # Absolute post-cutoff volume, not a rate. The rate normalises away the
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
        by_tier: Dict[str, List[float]] = {}
        for r in records:
            by_tier.setdefault(r["tier_pre"], []).append(r["growth"])
        summary["growth_by_tier"] = {
            t: {
                "n": len(v),
                "mean_growth": round(sum(v) / len(v), 4),
                "median_growth": round(sorted(v)[len(v) // 2], 4),
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
