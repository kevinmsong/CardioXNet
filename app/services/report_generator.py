"""Report generation service for NETS pipeline results."""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader, Template

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.platypus.flowables import HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available - PDF generation will be disabled")

from app.models import (
    GeneInfo,
    ValidationResult,
    FunctionalNeighborhood,
    PrimaryTriageResult,
    SecondaryTriageResult,
    FinalPathwayResult,
    ScoredHypotheses,
    TopologyResult,
    LiteratureEvidence
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates analysis reports in multiple formats."""

    def __init__(self):
        """Initialize report generator."""
        self.settings = get_settings()

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        template_dir.mkdir(exist_ok=True)
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

        # AI narrative generator (gracefully disabled if Groq unavailable)
        try:
            from app.services.groq_report_enhancer import GroqReportEnhancer
            self.groq = GroqReportEnhancer()
        except Exception:
            self.groq = None

        logger.info("ReportGenerator initialized")
    
    def generate_report(
        self,
        analysis_id: str,
        seed_genes: List[GeneInfo],
        validation_result: ValidationResult,
        fn_result: FunctionalNeighborhood,
        primary_result: PrimaryTriageResult,
        secondary_result: SecondaryTriageResult,
        final_result: FinalPathwayResult,
        scored_hypotheses: ScoredHypotheses,
        topology_result: TopologyResult,
        literature_evidence: LiteratureEvidence,
        comprehensive_topology: Any = None,
        top_genes: List[Dict[str, Any]] = None,
        output_formats: List[str] = None
    ) -> Dict[str, str]:
        """
        Generate comprehensive analysis report.
        
        Args:
            analysis_id: Unique analysis identifier
            seed_genes: Original seed genes
            validation_result: Validation result
            fn_result: Functional neighborhood result
            primary_result: Primary triage result
            secondary_result: Secondary triage result
            final_result: Final pathway result
            scored_hypotheses: Scored hypotheses
            topology_result: Topology analysis result
            literature_evidence: Literature evidence
            comprehensive_topology: Comprehensive topology result from Stage 7
            top_genes: Top therapeutic target candidates
            output_formats: Output formats (default: markdown, html, json)
            
        Returns:
            Dictionary mapping format to file path
        """
        output_formats = output_formats or ["markdown", "html", "json"]
        
        logger.info(
            f"Generating report for analysis {analysis_id} "
            f"in formats: {output_formats}"
        )
        
        # Build report data
        report_data = self._build_report_data(
            analysis_id,
            seed_genes,
            validation_result,
            fn_result,
            primary_result,
            secondary_result,
            final_result,
            scored_hypotheses,
            topology_result,
            literature_evidence,
            comprehensive_topology,
            top_genes
        )
        
        # Generate reports per format so one failing renderer does not discard all output.
        output_files = {}
        generators = []

        if "pdf" in output_formats:
            generators.append(("pdf", lambda: self._generate_pdf(analysis_id, report_data)))

        if "markdown" in output_formats:
            generators.append(("markdown", lambda: self._generate_markdown(analysis_id, report_data)))

        if "html" in output_formats:
            generators.append(("html", lambda: self._generate_html(analysis_id, report_data)))

        if "json" in output_formats:
            generators.append(("json", lambda: self._generate_json(analysis_id, report_data)))

        for fmt, generate in generators:
            try:
                output_files[fmt] = generate()
            except Exception as exc:
                logger.warning(f"{fmt.upper()} report generation failed: {exc}")

        logger.info(f"Report generation complete: {list(output_files.keys())}")
        
        return output_files
    
    def _build_report_data(
        self,
        analysis_id: str,
        seed_genes: List[GeneInfo],
        validation_result: ValidationResult,
        fn_result: FunctionalNeighborhood,
        primary_result: PrimaryTriageResult,
        secondary_result: SecondaryTriageResult,
        final_result: FinalPathwayResult,
        scored_hypotheses: ScoredHypotheses,
        topology_result: TopologyResult,
        literature_evidence: LiteratureEvidence,
        comprehensive_topology: Any = None,
        top_genes: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build comprehensive report data structure."""
        
        report_dict = {
            "analysis_id": analysis_id,
            "timestamp": datetime.now().isoformat(),
            "input_summary": self._build_input_summary(seed_genes, validation_result),
            "stage_1": self._build_stage_1_summary(fn_result),
            "stage_2a": self._build_stage_2a_summary(primary_result),
            "stage_2b": self._build_stage_2b_summary(secondary_result),
            "stage_2c": self._build_stage_2c_summary(final_result),
            "stage_3": self._build_stage_3_summary(scored_hypotheses),
            "stage_4_topology": self._build_topology_summary(topology_result),
            "stage_4_literature": self._build_literature_summary(literature_evidence),
            "ranked_hypotheses": self._build_hypotheses_table(scored_hypotheses, topology_result, literature_evidence),
            "testable_hypotheses": self._build_testable_hypotheses(scored_hypotheses),
            "conclusion": self._build_conclusion(scored_hypotheses)
        }
        
        # Add Stage 7 comprehensive topology if available
        if comprehensive_topology is not None:
            if hasattr(comprehensive_topology, 'to_dict'):
                report_dict["stage_7_topology"] = comprehensive_topology.to_dict()
            else:
                report_dict["stage_7_topology"] = comprehensive_topology
        
        # Add top genes if available
        if top_genes is not None:
            report_dict["top_genes"] = top_genes

        # Build Groq-compatible pathway list
        report_dict["top_pathways"] = [
            {
                "name": h.get("pathway_name", ""),
                "nes_score": h.get("nes_score", 0),
                "p_value": h.get("p_adj", 1.0),
                "evidence_genes": h.get("seed_genes", []),
                "database": h.get("source_db", ""),
                "cardiac_disease_score": h.get("cardiac_relevance", 0),
                "citation_count": h.get("citation_count", 0),
                "citations": h.get("citations", []),
                "key_nodes": h.get("key_nodes", []),
            }
            for h in report_dict.get("ranked_hypotheses", [])[:15]
        ]
        report_dict["seed_genes"] = report_dict.get("input_summary", {}).get("gene_list", [])
        report_dict["disease_context"] = "cardiovascular disease"

        # AI-enhanced narrative sections (falls back to rule-based if Groq unavailable)
        if self.groq:
            try:
                report_dict = self.groq.enhance_report_data(report_dict)
            except Exception as e:
                logger.warning(f"Groq enhancement failed: {e}")

        return report_dict
    
    def _build_input_summary(
        self,
        seed_genes: List[GeneInfo],
        validation_result: ValidationResult
    ) -> Dict:
        """Build input summary section."""
        return {
            "total_seed_genes": len(seed_genes),
            "valid_genes": len(validation_result.valid_genes),
            "invalid_genes": len(validation_result.invalid_genes),
            "gene_list": [gene.symbol for gene in seed_genes],
            "warnings": validation_result.warnings
        }
    
    def _build_stage_1_summary(self, fn_result: FunctionalNeighborhood) -> Dict:
        """Build Stage 1 summary."""
        return {
            "fn_size": fn_result.size,
            "seed_count": len(fn_result.seed_genes),
            "neighbor_count": len(fn_result.neighbors),
            "contributions": fn_result.contributions
        }
    
    def _build_stage_2a_summary(self, primary_result: PrimaryTriageResult) -> Dict:
        """Build Stage 2a summary."""
        return {
            "primary_pathways_count": len(primary_result.primary_pathways),
            "known_pathways_filtered": primary_result.filtered_count,
            "top_pathways": [
                {
                    "name": p.pathway_name,
                    "nes": p.preliminary_nes,
                    "p_adj": p.p_adj
                }
                for p in primary_result.primary_pathways[:5]
            ]
        }
    
    def _build_stage_2b_summary(self, secondary_result: SecondaryTriageResult) -> Dict:
        """Build Stage 2b summary."""
        return {
            "total_secondary_pathways": secondary_result.total_secondary_count,
            "union_genes_processed": len(secondary_result.union_genes),
            "genes_successfully_processed": len(secondary_result.gene_triage_results),
            "literature_stats": secondary_result.literature_expansion_stats
        }
    
    def _build_stage_2c_summary(self, final_result: FinalPathwayResult) -> Dict:
        """Build Stage 2c summary."""
        return {
            "final_pathways_count": final_result.total_count,
            "aggregation_strategy": final_result.aggregation_strategy,
            "min_support_threshold": final_result.min_support_threshold
        }
    
    def _build_stage_3_summary(self, scored_hypotheses: ScoredHypotheses) -> Dict:
        """Build Stage 3a summary."""
        return {
            "total_hypotheses": scored_hypotheses.total_count,
            "top_nes_score": scored_hypotheses.hypotheses[0].nes_score if scored_hypotheses.hypotheses else 0
        }
    
    def _build_topology_summary(self, topology_result: TopologyResult) -> Dict:
        """Build topology analysis summary."""
        summaries = {}
        
        if topology_result and hasattr(topology_result, 'hypothesis_networks'):
            for pathway_id, network in topology_result.hypothesis_networks.items():
                summaries[pathway_id] = {
                    "key_nodes_count": len(network.key_nodes) if hasattr(network, 'key_nodes') else 0,
                    "top_key_nodes": [
                        {
                            "gene": node.gene_symbol,
                            "centrality": node.betweenness_centrality,
                            "role": node.role
                        }
                        for node in network.key_nodes[:5]
                    ] if hasattr(network, 'key_nodes') else []
                }
        
        return summaries
    
    def _build_literature_summary(self, literature_evidence: LiteratureEvidence) -> Dict:
        """Build literature validation summary."""
        summaries = {}
        
        if literature_evidence and hasattr(literature_evidence, 'hypothesis_citations'):
            for pathway_id, citations in literature_evidence.hypothesis_citations.items():
                summaries[pathway_id] = {
                    "citation_count": len(citations),
                    "top_citations": [
                        {
                            "pmid": c.pmid,
                            "title": c.title,
                            "year": c.year,
                            "relevance": c.relevance_score
                        }
                        for c in citations[:3]
                    ]
                }
        
        return summaries
    
    def _build_hypotheses_table(
        self, 
        scored_hypotheses: ScoredHypotheses,
        topology_result: TopologyResult,
        literature_evidence: LiteratureEvidence
    ) -> List[Dict]:
        """Build ranked hypotheses table with detailed evidence."""
        table_rows = []
        
        for h in scored_hypotheses.hypotheses:
            pathway_id = h.aggregated_pathway.pathway.pathway_id
            
            # Get literature citations for this pathway
            citations = []
            if literature_evidence and hasattr(literature_evidence, 'hypothesis_citations'):
                citations = literature_evidence.hypothesis_citations.get(pathway_id, [])
            citation_summaries = [
                {
                    "pmid": c.pmid,
                    "title": c.title,
                    "journal": getattr(c, 'journal', ''),
                    "year": c.year,
                    "abstract": getattr(c, 'abstract', ''),
                    "relevance": c.relevance_score
                }
                for c in citations
            ]
            
            # Get key nodes from topology analysis
            network = None
            if topology_result and hasattr(topology_result, 'hypothesis_networks'):
                network = topology_result.hypothesis_networks.get(pathway_id, None)
            key_nodes = []
            if network and hasattr(network, 'key_nodes'):
                key_nodes = [
                    {
                        "gene": node.gene_symbol,
                        "centrality": node.betweenness_centrality,
                        "role": node.role
                    }
                    for node in network.key_nodes[:3]  # Top 3 key nodes
                ]
            
            # Get traced seed genes
            seed_genes = h.traced_seed_genes if h.traced_seed_genes else []

            # Get literature associations
            lit_support = h.literature_associations.get('has_literature_support', False) if h.literature_associations else False

            # Pull novelty / discovery data from score_components (set by HypothesisValidator)
            sc = h.score_components or {}
            novelty_tier     = sc.get('novelty_tier', '')
            literature_sat   = sc.get('literature_saturation', None)
            n_relevant_cits  = sc.get('n_relevant_citations', len(citation_summaries))
            discovery_score  = sc.get('discovery_score', None)

            pathway_obj = h.aggregated_pathway.pathway
            table_rows.append({
                "rank": h.rank,
                "pathway_id": pathway_id,
                "pathway_name": pathway_obj.pathway_name,
                "source_db": pathway_obj.source_db,
                # Retained under the historical key for API/report compatibility.
                # This is the Pathway Prioritization Score, not a GSEA NES.
                "nes_score": h.nes_score,
                "pps_score": h.nes_score,
                "p_adj": pathway_obj.p_adj,
                "fold_enrichment": pathway_obj.fold_enrichment,
                "term_size": pathway_obj.term_size,
                "empirical_pvalue": sc.get('empirical_pvalue'),
                "empirical_qvalue": sc.get('empirical_qvalue'),
                "permutation_testable": sc.get('permutation_testable'),
                "pubmed_hit_count": sc.get('pubmed_hit_count'),
                "evidence_count": pathway_obj.evidence_count,
                "support_count": h.aggregated_pathway.support_count,
                "seed_genes": seed_genes,
                "literature_support": lit_support,
                "citations": citation_summaries,
                "citation_count": len(citations),
                "n_relevant_citations": n_relevant_cits,
                "key_nodes": key_nodes,
                "source_primaries": h.aggregated_pathway.source_primary_pathways,
                # Novelty / discovery fields
                "novelty_tier": novelty_tier,
                "literature_saturation": literature_sat,
                "discovery_score": discovery_score,
                "score_components": {
                    k: v for k, v in sc.items()
                    if not isinstance(v, (dict, list))
                },
            })
        
        return table_rows
    
    def _build_testable_hypotheses(self, scored_hypotheses: ScoredHypotheses) -> List[Dict]:
        """Build testable hypotheses section."""
        return [
            {
                "hypothesis": f"Pathway '{h.aggregated_pathway.pathway.pathway_name}' is involved in cardiovascular disease and phenotype processes",
                "pathway_id": h.aggregated_pathway.pathway.pathway_id,
                "nes_score": h.nes_score,
                "experimental_approaches": [
                    "Functional enrichment analysis in cardiac tissue",
                    "Gene expression profiling",
                    "Pathway perturbation studies"
                ]
            }
            for h in scored_hypotheses.hypotheses[:5]
        ]
    
    def _build_conclusion(self, scored_hypotheses: ScoredHypotheses) -> str:
        """Build conclusion section."""
        if not scored_hypotheses.hypotheses:
            return "No significant pathway hypotheses were identified."
        
        top_hypothesis = scored_hypotheses.hypotheses[0]
        supported_hypotheses = sum(
            1
            for hypothesis in scored_hypotheses.hypotheses
            if hypothesis.literature_associations
            and hypothesis.literature_associations.get("has_literature_support", False)
        )

        total_hypotheses = scored_hypotheses.total_count
        top_name = top_hypothesis.aggregated_pathway.pathway.pathway_name
        top_nes = top_hypothesis.nes_score

        if supported_hypotheses > 0:
            return (
                f"Analysis prioritized {total_hypotheses} cardiac-relevant pathway hypotheses. "
                f"The top-ranked pathway is '{top_name}' (PPS: {top_nes:.3f}). "
                f"Automated PubMed co-mention searches found direct support for "
                f"{supported_hypotheses} of {total_hypotheses} final pathways. "
                f"These results should be treated as candidate associations pending expert review."
            )
        
        return (
            f"Analysis prioritized {total_hypotheses} cardiac-relevant pathway hypotheses. "
            f"The top-ranked pathway is '{top_name}' (PPS: {top_nes:.3f}). "
            f"Automated PubMed co-mention searches did not retrieve direct support for the final ranked pathways; "
            f"that should be interpreted as an unresolved literature gap in this query strategy, not proof of novelty "
            f"or absence from the literature."
        )
    
    def _generate_markdown(self, analysis_id: str, report_data: Dict) -> str:
        """Generate Markdown report focused on analysis findings."""
        template_str = """# CardioXNet Cardiovascular Pathway Analysis Report

**Analysis ID:** {{ analysis_id }}
**Generated:** {{ timestamp }}
**Gene Set:** {{ input_summary.gene_list | join(', ') }}
**Pathways Identified:** {{ stage_3.total_hypotheses }}

---

## Executive Summary

{{ ai_executive_summary if ai_executive_summary else conclusion }}

---

## Top Pathway Discoveries

Ranked by Discovery Score. Column definitions are given in the Methods note below.

| Rank | Pathway | Source | Discovery | Novelty | PPS | Enrich. p<sub>adj</sub> | Fold | Perm. q | Genes | PubMed hits |
|------|---------|--------|-----------|---------|-----|--------------|------|---------|-------|-------------|
{% for h in ranked_hypotheses[:20] -%}
| {{ h.rank }} | {{ h.pathway_name }} | {{ h.source_db }} | {{ "%.3f"|format(h.discovery_score) if h.discovery_score is not none else "—" }} | {{ h.novelty_tier or "—" }} | {{ "%.3f"|format(h.nes_score) }} | {{ "%.2e"|format(h.p_adj) }} | {{ "%.1f"|format(h.fold_enrichment) if h.fold_enrichment is not none else "—" }} | {{ "%.3g"|format(h.empirical_qvalue) if h.empirical_qvalue is not none else "n/t" }} | {{ h.evidence_count }} | {{ h.pubmed_hit_count if h.pubmed_hit_count is not none and h.pubmed_hit_count >= 0 else "—" }} |
{% endfor %}

**Column definitions.**
`Discovery` = PPS x literature novelty; the primary ranking metric, high for pathways
that are both well supported and under-reported.
`Novelty` = literature tier derived from `PubMed hits`.
`PPS` = Pathway Prioritization Score, a weighted composite of significance (0.30),
fold enrichment (0.30), gene-set specificity (0.25) and cross-source replication
(0.15), scaled by database weight and seed proximity. **This is not a GSEA
normalized enrichment score.**
`Enrich. p_adj` = FDR-adjusted enrichment p-value from g:Profiler.
`Fold` = observed / expected overlap.
`Perm. q` = Benjamini-Hochberg corrected empirical p-value from a degree-matched
permutation null over the annotated background; `n/t` means the test was not run.
`PubMed hits` = total records at the pathway x seed genes x disease intersection.

---

## Pathway Details

{% for item in ai_pathway_interpretations[:5] %}
### {{ loop.index }}. {{ item.pathway.name }}

**PPS:** {{ "%.3f"|format(item.pathway.nes_score) }} | **Enrichment p:** {{ "%.2e"|format(item.pathway.p_value) }} | **Database:** {{ item.pathway.database }}

{{ item.interpretation }}

{% if item.pathway.evidence_genes %}
**Key Evidence Genes:** {{ item.pathway.evidence_genes | join(', ') }}
{% endif %}
{% if item.pathway.citations %}
**Supporting Literature:**
{% for c in item.pathway.citations[:3] %}
- {{ c.title }} (PMID: {{ c.pmid }}, {{ c.year }})
{% endfor %}
{% endif %}

---
{% endfor %}

## Therapeutic Targets

{{ ai_therapeutic_discussion if ai_therapeutic_discussion else '' }}

{% if top_genes %}
### Druggable Gene Summary

| Gene | Druggability Tier | Pathways |
|------|------------------|---------|
{% for g in top_genes[:15] -%}
| {{ g.gene_symbol if g.gene_symbol else g.symbol }} | {{ g.druggability_tier | default('unknown') }} | {{ g.pathway_count | default(1) }} |
{% endfor %}
{% endif %}

---

## Literature Evidence

- **Total citations analyzed:** {{ ranked_hypotheses | sum(attribute='citation_count') }}
- **Pathways with literature support:** {{ ranked_hypotheses | selectattr('literature_support') | list | length }} / {{ ranked_hypotheses | length }}

{% for h in ranked_hypotheses[:10] if h.citations %}
### {{ h.pathway_name }}
{% for c in h.citations[:3] %}
- **{{ c.title }}** — PMID: {{ c.pmid }} ({{ c.year }})
{% endfor %}
{% endfor %}

---

## Conclusion

{{ conclusion }}

---

*Generated by CardioXNet NETS Pipeline · University of Alabama at Birmingham*
"""
        template = Template(template_str)
        # Ensure ai fields have defaults
        report_data.setdefault("ai_executive_summary", "")
        report_data.setdefault("ai_pathway_interpretations", [])
        report_data.setdefault("ai_therapeutic_discussion", "")
        report_data.setdefault("top_genes", [])
        markdown = template.render(**report_data)

        output_dir = Path(self.settings.output_dir)
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{analysis_id}_report.md"
        output_file.write_text(markdown, encoding="utf-8")
        logger.info(f"Markdown report saved to {output_file}")
        return str(output_file)
    
    def _generate_html(self, analysis_id: str, report_data: Dict) -> str:
        """Generate HTML report."""
        template_str = """<!DOCTYPE html>
<html>
<head>
    <title>CardioXNet Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #2c3e50; }
        h2 { color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #3498db; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .metric { background-color: #ecf0f1; padding: 10px; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>CardioXNet Analysis Report</h1>
    <p><strong>Analysis ID:</strong> {{ analysis_id }}</p>
    <p><strong>Generated:</strong> {{ timestamp }}</p>
    
    <h2>Input Summary</h2>
    <div class="metric">
        <p><strong>Seed Genes:</strong> {{ input_summary.total_seed_genes }}</p>
        <p><strong>Gene List:</strong> {{ input_summary.gene_list | join(', ') }}</p>
    </div>
    
    <h2>Ranked Hypotheses</h2>
    <table>
        <tr>
            <th>Rank</th>
            <th>Pathway</th>
            <th title="PPS x literature novelty">Discovery</th>
            <th>Novelty</th>
            <th title="Pathway Prioritization Score - not a GSEA NES">PPS</th>
            <th title="FDR-adjusted enrichment p-value (g:Profiler)">Enrich. p-adj</th>
            <th title="Benjamini-Hochberg corrected permutation p-value">Perm. q</th>
            <th>Evidence</th>
            <th>Seed Genes</th>
            <th title="PubMed records at pathway x seeds x disease">PubMed hits</th>
        </tr>
        {% for h in ranked_hypotheses[:10] %}
        <tr>
            <td>{{ h.rank }}</td>
            <td>{{ h.pathway_name }}</td>
            <td><strong>{{ "%.3f"|format(h.discovery_score) if h.discovery_score is not none else "—" }}</strong></td>
            <td>{{ h.novelty_tier or "—" }}</td>
            <td>{{ "%.3f"|format(h.nes_score) }}</td>
            <td>{{ "%.2e"|format(h.p_adj) }}</td>
            <td>{{ "%.3g"|format(h.empirical_qvalue) if h.empirical_qvalue is not none else "n/t" }}</td>
            <td>{{ h.evidence_count }}</td>
            <td>{{ h.seed_genes | join(', ') if h.seed_genes else 'N/A' }}</td>
            <td>{{ h.pubmed_hit_count if h.pubmed_hit_count is not none and h.pubmed_hit_count >= 0 else "—" }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>Conclusion</h2>
    <p>{{ conclusion }}</p>
</body>
</html>
"""
        
        template = Template(template_str)
        html = template.render(**report_data)
        
        # Save to file
        output_dir = Path(self.settings.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"{analysis_id}_report.html"
        output_file.write_text(html)
        
        logger.info(f"HTML report saved to {output_file}")
        
        return str(output_file)
    
    def _generate_json(self, analysis_id: str, report_data: Dict) -> str:
        """Generate JSON report."""
        # Save to file
        output_dir = Path(self.settings.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"{analysis_id}_report.json"
        
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"JSON report saved to {output_file}")
        
        return str(output_file)
    
    def _generate_pdf(self, analysis_id: str, report_data: Dict) -> str:
        """Generate professional results-focused PDF report."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation.")

        output_dir = Path(self.settings.output_dir)
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{analysis_id}_report.pdf"

        doc = SimpleDocTemplate(
            str(output_file), pagesize=A4,
            rightMargin=56, leftMargin=56, topMargin=56, bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        UAB_GREEN   = colors.HexColor("#1E6B52")
        UAB_GOLD    = colors.HexColor("#FFB81C")
        LIGHT_GREEN = colors.HexColor("#E8F5E9")

        title_style = ParagraphStyle("Title", parent=styles["Title"],
            fontSize=20, textColor=UAB_GREEN, spaceAfter=6, alignment=TA_CENTER)
        h1_style = ParagraphStyle("H1", parent=styles["Heading1"],
            fontSize=14, textColor=UAB_GREEN, spaceBefore=14, spaceAfter=6, leading=18)
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"],
            fontSize=11, textColor=colors.HexColor("#145A43"), spaceBefore=10, spaceAfter=4)
        body_style = ParagraphStyle("Body", parent=styles["Normal"],
            fontSize=9, leading=14, spaceAfter=6)
        small_style = ParagraphStyle("Small", parent=styles["Normal"],
            fontSize=8, leading=12, textColor=colors.HexColor("#444444"))
        caption_style = ParagraphStyle("Caption", parent=styles["Normal"],
            fontSize=7.5, leading=11, textColor=colors.HexColor("#666666"))

        def hr():
            return HRFlowable(width="100%", thickness=1, color=UAB_GOLD, spaceAfter=8)
        def sp(h=8):
            return Spacer(1, h)

        def base_tbl_style():
            return TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), UAB_GREEN),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",   (0, 0), (-1, 0), 8),
                ("FONTSIZE",   (0, 1), (-1, -1), 7.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREEN]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ])

        els = []

        # ── Title page ──────────────────────────────────────────────────
        els.append(sp(40))
        els.append(Paragraph("CardioXNet Cardiovascular Pathway Analysis", title_style))
        els.append(Paragraph("NETS Pipeline Report",
            ParagraphStyle("Sub", parent=styles["Normal"],
                fontSize=12, textColor=colors.HexColor("#4A9B7F"),
                alignment=TA_CENTER, spaceAfter=20)))
        els.append(hr())
        seed_genes = report_data.get("seed_genes", [])
        gene_display = ", ".join(seed_genes[:12])
        if len(seed_genes) > 12:
            gene_display += f" (+{len(seed_genes)-12} more)"
        meta_rows = [
            ["Analysis ID", analysis_id],
            ["Generated",   datetime.now().strftime("%Y-%m-%d %H:%M")],
            ["Gene Set",    gene_display],
            ["Pathways Identified", str(report_data.get("stage_3", {}).get("total_hypotheses", 0))],
        ]
        meta_tbl = Table(
            [[Paragraph(f"<b>{k}</b>", small_style), Paragraph(v, small_style)]
             for k, v in meta_rows],
            colWidths=[1.6*inch, 4.5*inch])
        meta_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREEN),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C8E6C9")),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        els.append(meta_tbl)
        els.append(PageBreak())

        # ── Executive Summary ────────────────────────────────────────────
        els.append(Paragraph("Executive Summary", h1_style))
        els.append(hr())
        summary = (report_data.get("ai_executive_summary") or
                   report_data.get("conclusion") or "No summary available.")
        for para in summary.split("\n\n"):
            if para.strip():
                els.append(Paragraph(para.strip(), body_style))
        els.append(sp())

        # ── Ranked Pathways Table ────────────────────────────────────────
        els.append(PageBreak())
        els.append(Paragraph("Ranked Pathway Discoveries", h1_style))
        els.append(hr())
        hypotheses = report_data.get("ranked_hypotheses", [])
        if hypotheses:
            def _fmt(value, spec, blank="-"):
                return format(value, spec) if isinstance(value, (int, float)) else blank

            tbl_data = [["Rank", "Pathway Name", "DB", "Disc.", "Novelty",
                         "PPS", "Enr. p", "Perm. q", "Genes", "PubMed"]]
            for h in hypotheses[:30]:
                tbl_data.append([
                    str(h.get("rank", "")),
                    Paragraph(str(h.get("pathway_name", ""))[:60], small_style),
                    str(h.get("source_db", ""))[:6],
                    _fmt(h.get("discovery_score"), ".3f"),
                    Paragraph(str(h.get("novelty_tier") or "-"), small_style),
                    _fmt(h.get("nes_score"), ".3f"),
                    _fmt(h.get("p_adj"), ".0e"),
                    _fmt(h.get("empirical_qvalue"), ".2g", blank="n/t"),
                    str(h.get("evidence_count", 0)),
                    str(h["pubmed_hit_count"]) if isinstance(h.get("pubmed_hit_count"), int)
                        and h["pubmed_hit_count"] >= 0 else "-",
                ])
            t = Table(tbl_data,
                      colWidths=[0.35*inch, 2.15*inch, 0.42*inch, 0.48*inch, 0.68*inch,
                                 0.42*inch, 0.48*inch, 0.48*inch, 0.42*inch, 0.52*inch])
            t.setStyle(base_tbl_style())
            els.append(t)
            els.append(sp(6))
            els.append(Paragraph(
                "<b>Disc.</b> Discovery Score = PPS x literature novelty (primary ranking). "
                "<b>PPS</b> Pathway Prioritization Score: weighted composite of significance (0.30), "
                "fold enrichment (0.30), gene-set specificity (0.25) and replication (0.15) - "
                "not a GSEA normalized enrichment score. "
                "<b>Enr. p</b> FDR-adjusted enrichment p-value (g:Profiler). "
                "<b>Perm. q</b> Benjamini-Hochberg corrected empirical p-value from a "
                "degree-matched permutation null; n/t = not tested. "
                "<b>PubMed</b> records at the pathway x seed genes x disease intersection.",
                caption_style))
        else:
            els.append(Paragraph("No pathway hypotheses available.", body_style))

        # ── Per-Pathway Interpretations ──────────────────────────────────
        ai_interps = report_data.get("ai_pathway_interpretations", [])
        if ai_interps:
            els.append(PageBreak())
            els.append(Paragraph("Pathway Interpretations", h1_style))
            els.append(hr())
            for i, item in enumerate(ai_interps[:5], 1):
                pw    = item.get("pathway", {})
                interp = item.get("interpretation", "")
                els.append(Paragraph(f"{i}. {pw.get('name', 'Unknown')}", h2_style))
                stats = (f"PPS = {pw.get('nes_score', 0):.3f}  |  "
                         f"p = {pw.get('p_value', 1):.2e}  |  "
                         f"DB: {pw.get('database', '')}  |  "
                         f"Citations: {pw.get('citation_count', 0)}")
                els.append(Paragraph(stats, caption_style))
                if interp:
                    els.append(Paragraph(interp, body_style))
                genes = pw.get("evidence_genes", [])
                if genes:
                    els.append(Paragraph(
                        "<b>Evidence genes:</b> " + ", ".join(genes[:12]),
                        small_style))
                for c in pw.get("citations", [])[:3]:
                    els.append(Paragraph(
                        f"• {c.get('title','')[:90]} — PMID {c.get('pmid','')} ({c.get('year','')})",
                        caption_style))
                els.append(sp(6))

        # ── Therapeutic Targets ──────────────────────────────────────────
        top_genes = report_data.get("top_genes", [])
        if top_genes:
            els.append(PageBreak())
            els.append(Paragraph("Therapeutic Target Genes", h1_style))
            els.append(hr())
            ai_ther = report_data.get("ai_therapeutic_discussion", "")
            if ai_ther:
                for para in ai_ther.split("\n\n"):
                    if para.strip():
                        els.append(Paragraph(para.strip(), body_style))
                els.append(sp())
            gene_data = [["Gene", "Druggability", "PPS", "Pathways"]]
            for g in top_genes[:20]:
                gene_data.append([
                    str(g.get("gene_symbol", g.get("symbol", ""))),
                    str(g.get("druggability_tier", "unknown")).capitalize(),
                    f"{g.get('nes_score', 0):.2f}" if g.get("nes_score") else "—",
                    str(g.get("pathway_count", "—")),
                ])
            gt = Table(gene_data,
                       colWidths=[1.5*inch, 1.4*inch, 1.2*inch, 1.2*inch])
            gt.setStyle(base_tbl_style())
            els.append(gt)

        # ── Literature Summary ───────────────────────────────────────────
        if hypotheses:
            els.append(PageBreak())
            els.append(Paragraph("Literature Evidence", h1_style))
            els.append(hr())
            total_cit = sum(h.get("citation_count", 0) for h in hypotheses)
            lit_n = sum(1 for h in hypotheses if h.get("literature_support"))
            pct = lit_n / max(len(hypotheses), 1) * 100
            els.append(Paragraph(
                f"<b>{total_cit}</b> PubMed citations analyzed across "
                f"<b>{len(hypotheses)}</b> pathways. "
                f"<b>{lit_n}</b> pathways ({pct:.0f}%) have direct literature support.",
                body_style))
            els.append(sp())
            for h in hypotheses[:10]:
                cits = h.get("citations", [])
                if not cits:
                    continue
                els.append(Paragraph(f"<b>{h.get('pathway_name','')}</b>", small_style))
                for c in cits[:3]:
                    els.append(Paragraph(
                        f"• {c.get('title','')}. PMID: {c.get('pmid','')} ({c.get('year','')})",
                        caption_style))
                els.append(sp(4))

        # ── Conclusion ───────────────────────────────────────────────────
        els.append(PageBreak())
        els.append(Paragraph("Conclusion", h1_style))
        els.append(hr())
        conclusion = report_data.get("conclusion", "")
        if conclusion:
            els.append(Paragraph(conclusion, body_style))
        els.append(sp(20))
        els.append(Paragraph(
            "Generated by CardioXNet NETS Pipeline \u00b7 "
            "University of Alabama at Birmingham \u00b7 "
            f"{datetime.now().strftime('%Y-%m-%d')}",
            caption_style))

        doc.build(els)
        logger.info(f"PDF report saved to {output_file}")
        return str(output_file)

