"""View-model helpers that turn normalized analysis results into template context.

These functions consume the dict produced by ``AnalysisResultsResponse.model_dump()``
(the same payload the JSON API returns) so the HTML and JSON views never diverge.
All derived metrics are computed here to keep templates declarative.
"""

from typing import Any, Dict, List, Optional


_INTERPRETABLE_NOVELTY_CONFIDENCE = {"verified", "verified_gap"}

_NOVELTY_CONFIDENCE_LABELS = {
    "verified": "Verified measurement",
    "verified_gap": "Verified zero-record gap",
    "unverified_measurement": "Unverified: count not measured",
    "unverified_query_scope": "Unverified: strict query not established",
    "unverified_seed_corpus": "Unverified: seed corpus unavailable",
    "unverified_concept": "Unverified: pathway concept prerequisite",
    "ungrounded_seeds": "Unverified: seed corpus too sparse",
    # Backward-compatible label for saved results produced before the
    # prerequisite-specific confidence values were introduced.
    "unverified": "Unverified: incomplete literature prerequisites",
}


def _novelty_evidence_state(sc: Dict[str, Any]) -> tuple[bool, str]:
    """Return whether a literature-novelty call is interpretable and its label.

    An explicit strict query tier and a completed prerequisite chain are both
    required.  Missing confidence provenance is therefore unverified rather
    than being treated as a legacy success.
    """
    confidence = str(sc.get("novelty_confidence") or "")
    query_tier = str(sc.get("query_tier") or "unknown")
    interpretable = (
        query_tier == "strict"
        and confidence in _INTERPRETABLE_NOVELTY_CONFIDENCE
    )
    if confidence:
        label = _NOVELTY_CONFIDENCE_LABELS.get(
            confidence, f"Unverified: {confidence.replace('_', ' ')}"
        )
    else:
        label = "Unverified: evidence provenance unavailable"
    if query_tier != "strict" and confidence not in {"unverified_query_scope"}:
        label = "Unverified: strict query not established"
    return interpretable, label


def _sc(hyp: Dict[str, Any]) -> Dict[str, Any]:
    """Return a hypothesis' score_components dict (always a dict)."""
    sc = hyp.get("score_components")
    return sc if isinstance(sc, dict) else {}


def _citation_count(hyp: Dict[str, Any]) -> int:
    cits = hyp.get("citations")
    return len(cits) if isinstance(cits, list) else 0


def _discovery_method(hyp: Dict[str, Any]) -> str:
    lineage = hyp.get("lineage") or {}
    method = lineage.get("discovery_method")
    if method:
        return method
    support = (hyp.get("aggregated_pathway") or {}).get("support_count", 0)
    return "aggregated" if (support or 0) > 1 else "primary"


def _is_seed_independent(hyp: Dict[str, Any], seed_symbols: set) -> bool:
    """True when the pathway is reached by network expansion rather than being
    carried by the seed genes themselves: the traced seed genes are a minority of
    the pathway's evidence genes.

    This is a *structural* property and deliberately not called "novel" -- it
    says nothing about the literature. Literature novelty is the separate
    ``novelty_tier`` / ``discovery_score`` pair computed in Stage 8. Presenting
    this flag under the label "novel" conflated the two.
    """
    evidence = hyp.get("evidence_genes") or []
    traced = set(hyp.get("traced_seed_genes") or [])
    if not evidence:
        return True
    seed_in_pathway = len([g for g in evidence if g in seed_symbols or g in traced])
    return (seed_in_pathway / len(evidence)) < 0.5


def _cardiac_expression(sc: Dict[str, Any]) -> float:
    """Bounded 0–1 cardiac-expression value for the results meter.

    ``cardiac_expression_ratio`` is the fraction of a pathway's genes expressed
    in cardiac tissue (GTEx Heart LV + Atrial Appendage, median TPM ≥ 1; curated
    estimate when live validation is off). Already 0–1.
    """
    expr = sc.get("cardiac_expression_ratio")
    try:
        return max(0.0, min(float(expr), 1.0))
    except (TypeError, ValueError):
        return 0.0


def format_p(value: Optional[float]) -> str:
    """Format a p-value compactly (scientific for small numbers)."""
    if value is None:
        return "-"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "-"
    if v <= 0:
        return "<1e-300"
    if v < 0.001:
        return f"{v:.1e}"
    return f"{v:.3f}"


def hypothesis_rows(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build sortable table rows with derived metrics, ranked by NES descending."""
    hyps = ((resp.get("hypotheses") or {}).get("hypotheses")) or []
    seed_symbols = {g.get("symbol") for g in (resp.get("seed_genes") or []) if g.get("symbol")}
    rows: List[Dict[str, Any]] = []
    for hyp in hyps:
        sc = _sc(hyp)
        novelty_interpretable, novelty_evidence_label = _novelty_evidence_state(sc)
        rows.append({
            "pathway_id": hyp.get("pathway_id", ""),
            "pathway_name": hyp.get("pathway_name", "(unnamed pathway)"),
            "source_db": hyp.get("source_db", ""),
            "pps_score": float(hyp.get("nes_score") or 0.0),
            "p_adj": hyp.get("p_adj"),
            "p_adj_fmt": format_p(hyp.get("p_adj")),
            "fold_enrichment": sc.get("fold_enrichment"),
            "term_size": sc.get("term_size"),
            "evidence_count": int(hyp.get("evidence_count") or len(hyp.get("evidence_genes") or [])),
            "cardiac_relevance": float(sc.get("cardiac_relevance") or 0.0),
            "cardiac_expression": _cardiac_expression(sc),
            "druggability_tier": sc.get("druggability_tier") or "-",
            "druggability_source": sc.get("druggability_source") or "",
            "external_lookup_complete": sc.get("external_lookup_complete"),
            "external_lookup_failures": sc.get("external_lookup_failures"),
            "empirical_pvalue": sc.get("empirical_pvalue"),
            "empirical_qvalue": sc.get("empirical_qvalue"),
            "empirical_q_fmt": format_p(sc.get("empirical_qvalue")),
            "permutation_testable": sc.get("permutation_testable"),
            # Literature novelty / discovery (Stage 8)
            "pubmed_hit_count": sc.get("pubmed_hit_count"),
            "saturation_corpus_size": sc.get("saturation_corpus_size"),
            "query_tier": sc.get("query_tier") or "unknown",
            "literature_query": sc.get("literature_query") or "",
            "literature_saturation": sc.get("literature_saturation"),
            "literature_novelty": sc.get("literature_novelty"),
            "gene_novelty": sc.get("gene_novelty"),
            "composite_novelty": sc.get("composite_novelty"),
            "novelty_tier": sc.get("novelty_tier") or "-",
            "novelty_confidence": sc.get("novelty_confidence"),
            "novelty_interpretable": novelty_interpretable,
            "novelty_evidence_label": novelty_evidence_label,
            "discovery_score": sc.get("discovery_score"),
            "literature_count": _citation_count(hyp),
            "traced_seed_genes": hyp.get("traced_seed_genes") or [],
            "support_count": (hyp.get("aggregated_pathway") or {}).get("support_count", 0),
            "discovery_method": _discovery_method(hyp),
            "seed_independent": _is_seed_independent(hyp, seed_symbols),
        })
    # Discovery Score is the primary ranking: enriched and literature-sparse
    # under the prespecified query.
    # Pathways without a discovery score (Stage 8 skipped) fall back to PPS.
    rows.sort(
        key=lambda r: (
            r["discovery_score"] if r["discovery_score"] is not None else -1.0,
            r["pps_score"],
        ),
        reverse=True,
    )
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows


def summary_stats(resp: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """High-level numbers for the results header."""
    total_citations = sum(r["literature_count"] for r in rows)
    seed_independent = sum(1 for r in rows if r["seed_independent"])
    expanded = sum(1 for r in rows if r["discovery_method"] == "aggregated")
    nt = resp.get("network_topology") or {}
    hub_genes = nt.get("hub_genes") or (resp.get("topology") or {}).get("hub_genes") or []
    novel_tiers = {"Highly Novel", "Novel"}
    return {
        "pathway_count": len(rows),
        # Literature-sparse under the pathway x seeds x disease query. Distinct
        # from seed_independent_count, which is structural.
        "novel_count": sum(
            1 for r in rows
            if r.get("novelty_interpretable")
            and r.get("novelty_tier") in novel_tiers
        ),
        "seed_independent_count": seed_independent,
        "expanded_count": expanded,
        "citation_count": total_citations,
        "seed_count": len(resp.get("seed_genes") or []),
        "hub_count": len(hub_genes),
        "with_literature": sum(1 for r in rows if r["literature_count"] > 0),
        "fdr_significant": sum(
            1 for r in rows
            if r.get("empirical_qvalue") is not None and r["empirical_qvalue"] <= 0.05
        ),
    }


def find_hypothesis(resp: Dict[str, Any], pathway_id: str) -> Optional[Dict[str, Any]]:
    """Locate a full hypothesis dict by pathway_id for the detail page."""
    hyps = ((resp.get("hypotheses") or {}).get("hypotheses")) or []
    for hyp in hyps:
        if hyp.get("pathway_id") == pathway_id:
            return hyp
    return None


def cytoscape_elements(resp: Dict[str, Any], max_nodes: int = 30) -> Dict[str, Any]:
    """Build cytoscape elements (nodes + edges) from network topology.

    Nodes are the top hub genes; edges connect genes that co-occur in a shared
    pathway. Seed genes are flagged so the template can colour them distinctly.
    """
    nt = resp.get("network_topology") or {}
    hub_genes = nt.get("hub_genes") or []
    seed_symbols = {g.get("symbol") for g in (resp.get("seed_genes") or []) if g.get("symbol")}

    if not hub_genes:
        return {"nodes": [], "edges": []}

    hub_genes = hub_genes[:max_nodes]
    gene_pathways: Dict[str, set] = {}
    nodes = []
    for h in hub_genes:
        gene = h.get("gene_symbol") or h.get("gene")
        if not gene:
            continue
        score = float(h.get("hub_score") or h.get("pagerank") or h.get("degree_centrality") or 0.0)
        gene_pathways[gene] = set(h.get("pathways") or [])
        nodes.append({
            "data": {
                "id": gene,
                "label": gene,
                "score": round(score, 4),
                "size": 18 + round(score * 42, 1),
                "is_seed": gene in seed_symbols,
            }
        })

    genes = list(gene_pathways.keys())
    edges = []
    seen = set()
    for i in range(len(genes)):
        for j in range(i + 1, len(genes)):
            a, b = genes[i], genes[j]
            shared = gene_pathways[a] & gene_pathways[b]
            if shared:
                key = (a, b)
                if key not in seen:
                    seen.add(key)
                    edges.append({"data": {"id": f"{a}__{b}", "source": a, "target": b,
                                           "weight": len(shared)}})
    return {"nodes": nodes, "edges": edges}


def csv_rows(resp: Dict[str, Any]) -> List[List[str]]:
    """Build CSV (header + rows) for the results export.

    Column names state what each number is. ``pps_score`` is the Pathway
    Prioritization Score, not a GSEA normalized enrichment score; ``p_adj`` is
    the Fisher-combined probability from per-query g:Profiler adjusted values;
    ``perm_q_value`` is the BH-corrected permutation p-value;
    ``discovery_score`` is PPS x composite novelty, with
    exact-query literature novelty weighted 2:1 over low seed-gene overlap.
    """
    header = [
        "rank", "pathway_name", "pathway_id", "source_db",
        "discovery_score", "novelty_tier", "novelty_confidence",
        "literature_saturation", "literature_novelty", "gene_novelty",
        "composite_novelty", "pubmed_hit_count", "saturation_corpus_size",
        "query_tier", "literature_query",
        "pps_score", "p_adj", "fold_enrichment", "term_size", "evidence_genes",
        "perm_p_value", "perm_q_value",
        "cardiac_relevance_pct", "cardiac_expression_pct",
        "druggability_tier", "druggability_source", "external_lookup_complete",
        "external_lookup_failures", "retrieved_citations", "discovery_method",
        "seed_independent", "traced_seed_genes",
    ]

    def num(value, fmt="{:.4f}"):
        return "" if value is None else fmt.format(value)

    out = [header]
    for r in hypothesis_rows(resp):
        out.append([
            str(r["rank"]),
            r["pathway_name"].replace(",", ";"),
            r["pathway_id"],
            r["source_db"],
            num(r["discovery_score"]),
            r["novelty_tier"],
            r["novelty_confidence"] or "",
            num(r["literature_saturation"]),
            num(r["literature_novelty"]),
            num(r["gene_novelty"]),
            num(r["composite_novelty"]),
            "" if r["pubmed_hit_count"] is None else str(r["pubmed_hit_count"]),
            "" if r["saturation_corpus_size"] is None else str(r["saturation_corpus_size"]),
            r["query_tier"],
            r["literature_query"],
            f'{r["pps_score"]:.4f}',
            format_p(r["p_adj"]),
            num(r["fold_enrichment"], "{:.2f}"),
            "" if r["term_size"] is None else str(r["term_size"]),
            str(r["evidence_count"]),
            format_p(r["empirical_pvalue"]),
            format_p(r["empirical_qvalue"]),
            f'{r["cardiac_relevance"] * 100:.1f}',
            f'{r["cardiac_expression"] * 100:.1f}',
            r["druggability_tier"],
            r["druggability_source"],
            ("" if r["external_lookup_complete"] is None
             else "yes" if r["external_lookup_complete"] else "no"),
            ("" if r["external_lookup_failures"] is None
             else str(r["external_lookup_failures"])),
            str(r["literature_count"]),
            r["discovery_method"],
            "yes" if r["seed_independent"] else "no",
            " ".join(r["traced_seed_genes"]),
        ])
    return out
