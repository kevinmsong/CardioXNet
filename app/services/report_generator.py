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
        
        # Generate reports in requested formats
        output_files = {}
        
        if "pdf" in output_formats:
            output_files["pdf"] = self._generate_pdf(
                analysis_id,
                report_data
            )
        
        if "markdown" in output_formats:
            output_files["markdown"] = self._generate_markdown(
                analysis_id,
                report_data
            )
        
        if "html" in output_formats:
            output_files["html"] = self._generate_html(
                analysis_id,
                report_data
            )
        
        if "json" in output_formats:
            output_files["json"] = self._generate_json(
                analysis_id,
                report_data
            )
        
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
                    "year": c.year,
                    "relevance": c.relevance_score
                }
                for c in citations[:3]  # Top 3 citations
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
            
            table_rows.append({
                "rank": h.rank,
                "pathway_id": pathway_id,
                "pathway_name": h.aggregated_pathway.pathway.pathway_name,
                "source_db": h.aggregated_pathway.pathway.source_db,
                "nes_score": h.nes_score,
                "p_adj": h.aggregated_pathway.pathway.p_adj,
                "evidence_count": h.aggregated_pathway.pathway.evidence_count,
                "support_count": h.aggregated_pathway.support_count,
                "seed_genes": seed_genes,
                "literature_support": lit_support,
                "citations": citation_summaries,
                "citation_count": len(citations),
                "key_nodes": key_nodes,
                "source_primaries": h.aggregated_pathway.source_primary_pathways
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
        
        return (
            f"Analysis identified {scored_hypotheses.total_count} novel pathway hypotheses. "
            f"The top-ranked hypothesis is '{top_hypothesis.aggregated_pathway.pathway.pathway_name}' "
            f"(NES: {top_hypothesis.nes_score:.2f}), which shows strong evidence for involvement in "
            f"cardiovascular disease and phenotype processes based on functional network analysis and literature mining."
        )
    
    def _generate_markdown(self, analysis_id: str, report_data: Dict) -> str:
        """Generate Markdown report."""
        template_str = """# CardioXNet Analysis Report

**Analysis ID:** {{ analysis_id }}  
**Generated:** {{ timestamp }}

## Input Summary

- **Seed Genes:** {{ input_summary.total_seed_genes }}
- **Valid Genes:** {{ input_summary.valid_genes }}
- **Gene List:** {{ input_summary.gene_list | join(', ') }}

## Pipeline Results

### Stage 1: Functional Neighborhood Assembly
- **F_N Size:** {{ stage_1.fn_size }} genes
- **Neighbors Added:** {{ stage_1.neighbor_count }}

### Stage 2a: Primary Pathway Enrichment
- **Primary Pathways:** {{ stage_2a.primary_pathways_count }}
- **Known Pathways Filtered:** {{ stage_2a.known_pathways_filtered }}

### Stage 2b: Secondary Pathway Discovery
- **Secondary Pathways:** {{ stage_2b.total_secondary_pathways }}
- **Genes Added via Literature:** {{ stage_2b.literature_stats.total_genes_added }}

### Stage 2c: Pathway Aggregation
- **Final Pathways:** {{ stage_2c.final_pathways_count }}
- **Strategy:** {{ stage_2c.aggregation_strategy }}

### Stage 3a: Final NES Scoring
- **Total Hypotheses:** {{ stage_3.total_hypotheses }}

## Ranked Hypotheses

| Rank | Pathway | NES Score | P-adj | Evidence | Seed Genes | Literature Support | Citations | Key Nodes |
|------|---------|-----------|-------|----------|------------|-------------------|-----------|-----------|
{% for h in ranked_hypotheses[:10] -%}
| {{ h.rank }} | {{ h.pathway_name }} | {{ "%.2f"|format(h.nes_score) }} | {{ "%.2e"|format(h.p_adj) }} | {{ h.evidence_count }} | {{ h.seed_genes | join(', ') if h.seed_genes else 'N/A' }} | {{ 'Yes' if h.literature_support else 'No' }} | {{ h.citation_count }} | {{ h.key_nodes | length if h.key_nodes else 0 }} |
{% endfor %}

## Conclusion

{{ conclusion }}
"""
        
        template = Template(template_str)
        markdown = template.render(**report_data)
        
        # Save to file
        output_dir = Path(self.settings.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"{analysis_id}_report.md"
        output_file.write_text(markdown)
        
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
            <th>NES Score</th>
            <th>P-adj</th>
            <th>Evidence</th>
            <th>Seed Genes</th>
            <th>Literature Support</th>
            <th>Citations</th>
            <th>Key Nodes</th>
        </tr>
        {% for h in ranked_hypotheses[:10] %}
        <tr>
            <td>{{ h.rank }}</td>
            <td>{{ h.pathway_name }}</td>
            <td>{{ "%.2f"|format(h.nes_score) }}</td>
            <td>{{ "%.2e"|format(h.p_adj) }}</td>
            <td>{{ h.evidence_count }}</td>
            <td>{{ h.seed_genes | join(', ') if h.seed_genes else 'N/A' }}</td>
            <td>{{ 'Yes' if h.literature_support else 'No' }}</td>
            <td>{{ h.citation_count }}</td>
            <td>{{ h.key_nodes | length if h.key_nodes else 0 }}</td>
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
        """Generate professional scientific PDF report."""
        if not REPORTLAB_AVAILABLE:
            logger.error("ReportLab not available - cannot generate PDF")
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")
        
        output_dir = Path(self.settings.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"{analysis_id}_report.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1976d2'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1976d2'),
            spaceAfter=12,
            spaceBefore=12
        )
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#424242'),
            spaceAfter=10
        )
        
        # Title Page
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("CardioXNet Analysis Report", title_style))
        elements.append(Paragraph("NETS Pipeline for Cardiovascular Disease and Phenotype-Aware Pathway Discovery", styles['Normal']))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"Analysis ID: {analysis_id}", styles['Normal']))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(PageBreak())
        
        # Executive Summary
        elements.append(Paragraph("AI-Powered Cardiovascular Discovery Report", heading_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1976d2')))
        elements.append(Spacer(1, 12))
        
        input_summary = report_data.get('input_summary', {})
        stage_3 = report_data.get('stage_3', {})
        
        # Add AI-powered discovery summary
        ai_summary_text = """
        <b>7-Stage AI Pipeline Overview:</b><br/>
        This report presents results from CardioXNet's AI-powered multi-dimensional pathway discovery system, 
        integrating 6 AI/ML techniques: (1) Semantic NLP filtering, (2) Graph ML topology analysis, 
        (3) Multi-modal clinical fusion, (4) Composite scoring, (5) Literature NLP mining, and 
        (6) Intelligent pathway aggregation. Clinical evidence from HPA and druggability databases 
        provides up to 2× scoring boost for validated pathways.
        """
        elements.append(Paragraph(ai_summary_text, styles['Normal']))
        elements.append(Spacer(1, 15))
        
        summary_data = [
            ['Metric', 'Value'],
            ['Seed Genes', str(input_summary.get('total_seed_genes', input_summary.get('seed_gene_count', 0)))],
            ['Functional Neighborhood Size', str(report_data.get('stage_1', {}).get('fn_size', 0))],
            ['Primary Pathways (Stage 2)', str(report_data.get('stage_2a', {}).get('primary_pathways_count', report_data.get('stage_2a', {}).get('primary_count', 0)))],
            ['Clinical Evidence Validated (Stage 3)', str(stage_3.get('clinically_validated_count', 'N/A'))],
            ['Final Hypotheses (NES Scored)', str(stage_3.get('total_hypotheses', 0))],
            ['High Confidence (NES > 50)', str(stage_3.get('high_confidence_count', 0))],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Top Hypotheses (Extended to show more pathways)
        elements.append(PageBreak())
        elements.append(Paragraph("Pathway Hypotheses", heading_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1976d2')))
        elements.append(Spacer(1, 12))
        
        elements.append(Paragraph(
            "The following table presents the top cardiovascular pathway hypotheses ranked by NES (Novelty and Evidence Score), "
            "which integrates statistical significance, evidence strength, and cardiac relevance.",
            styles['Normal']
        ))
        elements.append(Spacer(1, 12))
        
        hypotheses = report_data.get('ranked_hypotheses', [])[:50]  # Top 50 for comprehensive report
        
        if hypotheses:
            hyp_data = [['Pathway Name', 'NES', 'P-adj', 'Clinical', 'Cardiac', 'Evidence', 'Lit', 'Citations', 'Database']]
            for hyp in hypotheses:
                seed_genes_str = ', '.join(hyp.get('seed_genes', [])) if hyp.get('seed_genes') else 'N/A'
                lit_support = 'Yes' if hyp.get('literature_support') else 'No'
                citations = str(hyp.get('citation_count', 0))
                cardiac_rel = f"{(hyp.get('cardiac_relevance', 0) * 100):.0f}%"
                database = hyp.get('source_db', hyp.get('database', 'Unknown'))
                
                # Get clinical evidence if available (Stage 3)
                clinical_score = 'N/A'
                if hyp.get('stage_3_clinical_evidence'):
                    clinical_score = f"{(hyp['stage_3_clinical_evidence'].get('clinical_score', 0) * 100):.0f}%"
                elif hyp.get('score_components', {}).get('clinical_score') is not None:
                    clinical_score = f"{(hyp['score_components']['clinical_score'] * 100):.0f}%"
                
                hyp_data.append([
                    hyp.get('pathway_name', '')[:45],  # Truncate long names
                    f"{hyp.get('nes_score', 0):.2f}",
                    f"{hyp.get('p_adj', 0):.2e}",
                    clinical_score,
                    cardiac_rel,
                    str(hyp.get('evidence_count', 0)),
                    lit_support,
                    citations,
                    database[:12]  # Truncate database name
                ])
            
            hyp_table = Table(hyp_data, colWidths=[2.2*inch, 0.6*inch, 0.7*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.4*inch, 0.5*inch, 0.7*inch])
            hyp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 6.5),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            elements.append(hyp_table)
        else:
            elements.append(Paragraph("No pathway hypotheses generated.", styles['Normal']))
        
        # Add Key Genes Section
        elements.append(PageBreak())
        elements.append(Paragraph("Key Genes and Evidence", heading_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1976d2')))
        elements.append(Spacer(1, 12))
        
        if hypotheses:
            elements.append(Paragraph(
                "The following genes appear most frequently across top-ranked pathways and represent key nodes in the cardiovascular network:",
                styles['Normal']
            ))
            elements.append(Spacer(1, 12))
            
            # Collect gene frequencies across top pathways
            gene_freq = {}
            for hyp in hypotheses[:20]:  # Top 20 for gene analysis
                evidence_genes = hyp.get('evidence_genes', [])
                for gene in evidence_genes:
                    gene_freq[gene] = gene_freq.get(gene, 0) + 1
            
            # Sort by frequency and take top 30
            top_genes = sorted(gene_freq.items(), key=lambda x: x[1], reverse=True)[:30]
            
            if top_genes:
                gene_data = [['Gene Symbol', 'Pathway Frequency', 'Evidence Strength']]
                for gene, freq in top_genes:
                    strength = 'High' if freq >= 5 else 'Medium' if freq >= 3 else 'Moderate'
                    gene_data.append([gene, str(freq), strength])
                
                gene_table = Table(gene_data, colWidths=[2*inch, 2*inch, 2*inch])
                gene_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(gene_table)
        
        # Add Literature Evidence Section
        elements.append(PageBreak())
        elements.append(Paragraph("Literature Support and Citations", heading_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1976d2')))
        elements.append(Spacer(1, 12))
        
        total_citations = sum(hyp.get('citation_count', 0) for hyp in hypotheses)
        pathways_with_lit = sum(1 for hyp in hypotheses if hyp.get('literature_support'))
        
        lit_summary_text = f"""
        <b>Literature Mining Summary:</b><br/>
        • Total PubMed citations analyzed: {total_citations}<br/>
        • Pathways with literature support: {pathways_with_lit} / {len(hypotheses)} ({(pathways_with_lit/len(hypotheses)*100):.1f}%)<br/>
        • Average citations per pathway: {(total_citations/len(hypotheses)):.1f}<br/><br/>
        
        Literature evidence was systematically mined from PubMed to validate pathway-disease associations. 
        Pathways with direct literature support demonstrate established connections to cardiovascular biology.
        """
        elements.append(Paragraph(lit_summary_text, styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # Add Stage 4c Network Topology Section (Enhanced)
        topology_summary = report_data.get('topology_summary', {})
        if topology_summary:
            elements.append(PageBreak())
            elements.append(Paragraph("Stage 4c: Comprehensive Network Topology Analysis", heading_style))
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1976d2')))
            elements.append(Spacer(1, 12))
            
            elements.append(Paragraph("Network Overview", subheading_style))
            topology_text = f"""
            <b>STRING Protein-Protein Interaction Network Characteristics:</b><br/>
            • Total nodes (proteins): {topology_summary.get('total_genes', 'N/A')} genes<br/>
            • Total edges (interactions): {topology_summary.get('total_interactions', 'N/A')} interactions<br/>
            • Network density: {topology_summary.get('density', 0):.4f}<br/>
            • Average clustering coefficient: {topology_summary.get('avg_clustering', 0):.4f}<br/>
            • Network diameter: {topology_summary.get('diameter', 'N/A')}<br/>
            • Hub genes identified (top 1% by centrality): {topology_summary.get('hub_count', 0)}<br/><br/>
            
            Network topology analysis reveals the structural organization of protein-protein interactions 
            underlying the discovered pathways. Hub genes represent critical nodes with high connectivity 
            and betweenness centrality, often serving as key regulators or therapeutic targets.
            """
            elements.append(Paragraph(topology_text, styles['Normal']))
            elements.append(Spacer(1, 15))
            
            # Hub Genes Table
            hub_genes = topology_summary.get('hub_genes', [])
            if hub_genes:
                elements.append(Paragraph("Top Hub Genes", subheading_style))
                elements.append(Spacer(1, 8))
                
                hub_data = [['Gene', 'Hub Score', 'Betweenness', 'PageRank', 'Degree', 'Pathways', 'Druggable']]
                for hub in hub_genes[:25]:  # Top 25 hub genes
                    centrality = hub.get('centrality_scores', {})
                    hub_data.append([
                        hub.get('gene_symbol', '')[:15],
                        f"{hub.get('hub_score', 0):.3f}",
                        f"{centrality.get('betweenness', 0):.4f}",
                        f"{centrality.get('pagerank', 0):.4f}",
                        str(centrality.get('degree', 0)),
                        str(hub.get('pathway_count', 0)),
                        'Yes' if hub.get('is_druggable', False) else 'No'
                    ])
                
                hub_table = Table(hub_data, colWidths=[1.2*inch, 0.8*inch, 1*inch, 0.8*inch, 0.7*inch, 0.8*inch, 0.8*inch])
                hub_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
                ]))
                elements.append(hub_table)
                elements.append(Spacer(1, 10))
                
                # Hub gene explanation
                hub_explanation = """
                <b>Hub Score Calculation:</b> Composite metric combining multiple centrality measures weighted by 
                importance: Betweenness (35%), PageRank (25%), Degree (20%), Closeness (15%), Eigenvector (5%). 
                Hub genes with high scores are critical network nodes that may serve as key regulators or 
                therapeutic intervention points.
                """
                elements.append(Paragraph(hub_explanation, styles['Normal']))
            
            elements.append(Spacer(1, 15))
            
            # Therapeutic Targets Table
            therapeutic_targets = topology_summary.get('therapeutic_targets', [])
            if therapeutic_targets:
                elements.append(Paragraph("Top Therapeutic Target Candidates", subheading_style))
                elements.append(Spacer(1, 8))
                
                target_data = [['Gene', 'Therapeutic Score', 'Centrality', 'Druggability', 'Evidence', 'Pathway Diversity']]
                for target in therapeutic_targets[:20]:  # Top 20 targets
                    scores = target.get('scores', {})
                    target_data.append([
                        target.get('gene_symbol', '')[:15],
                        f"{target.get('therapeutic_score', 0):.3f}",
                        f"{scores.get('centrality_component', 0):.2f}",
                        f"{scores.get('druggability_component', 0):.2f}",
                        f"{scores.get('evidence_component', 0):.2f}",
                        f"{scores.get('pathway_diversity_component', 0):.2f}"
                    ])
                
                target_table = Table(target_data, colWidths=[1.1*inch, 1.2*inch, 1*inch, 1*inch, 0.9*inch, 1.2*inch])
                target_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
                ]))
                elements.append(target_table)
                elements.append(Spacer(1, 10))
                
                # Therapeutic scoring explanation
                therapeutic_explanation = """
                <b>Therapeutic Score Formula:</b> Prioritizes genes for therapeutic targeting using weighted 
                components: Centrality (40%), Druggability (30%), Evidence Strength (20%), Pathway Diversity (10%). 
                This integrative score identifies hub genes that are both biologically critical and pharmacologically 
                actionable, with strong supporting evidence across multiple pathways.
                """
                elements.append(Paragraph(therapeutic_explanation, styles['Normal']))
        
        # Add Stage 3 Clinical Evidence Section (NEW)
        elements.append(PageBreak())
        elements.append(Paragraph("🆕 Stage 3: Multi-Modal Clinical Evidence Validation", heading_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#FF5722')))
        elements.append(Spacer(1, 12))
        
        # Count pathways with clinical evidence
        clinically_validated = sum(1 for hyp in hypotheses if hyp.get('stage_3_clinical_evidence', {}).get('clinical_score', 0) > 0.3)
        strong_clinical = sum(1 for hyp in hypotheses if hyp.get('stage_3_clinical_evidence', {}).get('clinical_score', 0) > 0.5)
        
        clinical_intro_text = f"""
        <b>Novel Clinical Validation Framework:</b><br/>
        Stage 3 validates pathway genes using <b>three independent clinical evidence sources</b> queried in parallel:<br/><br/>
        
        • <b>Human Protein Atlas (HPA):</b> Tissue-specific RNA expression in cardiac tissues<br/>
        • <b>DrugBank:</b> FDA-approved and investigational drugs<br/>
        • <b>Epigenomics Roadmap:</b> H3K27ac enhancer marks indicating regulatory activity<br/><br/>
        
        <b>Clinical Validation Statistics:</b><br/>
        • Pathways with clinical evidence (&gt;30%): {clinically_validated} / {len(hypotheses)} ({(clinically_validated/len(hypotheses)*100):.1f}%)<br/>
        • Strong clinical support (&gt;50%): {strong_clinical} / {len(hypotheses)} ({(strong_clinical/len(hypotheses)*100):.1f}%)<br/>
        • Clinical weight multiplier range: 1.0× - 2.0× (applied to NES score)<br/><br/>
        
        <b>Impact on Discovery:</b><br/>
        Clinical evidence integration ensures discovered pathways are not just statistically significant but also 
        biologically validated in cardiac tissues. The multi-modal approach (combining expression + genetics + regulation) 
        provides orthogonal validation that pathways are mechanistically relevant to cardiovascular disease.
        """
        elements.append(Paragraph(clinical_intro_text, styles['Normal']))
        elements.append(Spacer(1, 15))
        
        # Clinical Evidence Distribution Table
        if any(hyp.get('stage_3_clinical_evidence') for hyp in hypotheses):
            elements.append(Paragraph("Clinical Evidence Score Distribution", subheading_style))
            elements.append(Spacer(1, 8))
            
            clinical_data = [['Pathway Name', 'HPA Score', 'Druggability', 'Combined', 'Weight']]
            for hyp in hypotheses[:20]:  # Top 20 pathways
                clinical_ev = hyp.get('stage_3_clinical_evidence', {})
                if clinical_ev:
                    clinical_data.append([
                        hyp.get('pathway_name', '')[:40],
                        f"{(clinical_ev.get('hpa_score', 0) * 100):.0f}%",
                        f"{(clinical_ev.get('gwas_score', 0) * 100):.0f}%",
                        f"{(clinical_ev.get('epigenomic_score', 0) * 100):.0f}%",
                        f"{(clinical_ev.get('clinical_score', 0) * 100):.0f}%",
                        f"{clinical_ev.get('clinical_weight', 1.0):.2f}×"
                    ])
            
            if len(clinical_data) > 1:
                clinical_table = Table(clinical_data, colWidths=[2.5*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.9*inch, 0.7*inch])
                clinical_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF5722')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
                ]))
                elements.append(clinical_table)
                elements.append(Spacer(1, 12))
                
                clinical_explanation = """
                <b>Clinical Score Calculation:</b> Combined Score = (HPA + Druggability) / 2.
                The clinical weight multiplier (1.0-2.0×) is then applied to the pathway's NES score.
                Pathways with strong clinical validation (score &gt; 0.5) receive significant boost,
                prioritizing clinically relevant mechanisms over purely statistical associations.
                """
                elements.append(Paragraph(clinical_explanation, styles['Normal']))
        
        elements.append(Spacer(1, 15))
        
        # Add GTEx Validation Section (Legacy but complementary)
        elements.append(Paragraph("Tissue Expression Validation (GTEx - Complementary)", subheading_style))
        elements.append(Spacer(1, 8))
        
        cardiac_validated = sum(1 for hyp in hypotheses if hyp.get('score_components', {}).get('cardiac_specificity_ratio', 0) > 0.5)
        
        gtex_text = f"""
        <b>GTEx Expression Validation (Legacy System):</b><br/>
        • Pathways with cardiac expression evidence: {cardiac_validated} / {len(hypotheses)} ({(cardiac_validated/len(hypotheses)*100):.1f}%)<br/>
        • Threshold for cardiac specificity: &gt;0.50 (heart/median tissue ratio)<br/><br/>
        
        GTEx (Genotype-Tissue Expression) data provides complementary validation to Stage 3 HPA evidence, 
        confirming that genes in identified pathways show preferential expression in cardiac tissues. 
        Both HPA (Stage 3) and GTEx use different methodologies and sample sets, providing robust orthogonal validation.
        """
        elements.append(Paragraph(gtex_text, styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # Add Druggability Section
        elements.append(Paragraph("Druggability Assessment", subheading_style))
        elements.append(Spacer(1, 8))
        
        druggable_count = sum(1 for hyp in hypotheses if hyp.get('druggability', {}).get('has_druggable_targets', False))
        
        drug_text = f"""
        <b>Therapeutic Potential Analysis:</b><br/>
        • Pathways with druggable targets: {druggable_count} / {len(hypotheses)} ({(druggable_count/len(hypotheses)*100):.1f}%)<br/>
        • Sources: DrugBank, Therapeutic Target Database (TTD)<br/><br/>
        
        Druggability annotation identifies pathways containing genes that are known drug targets or have 
        drug-like properties. These represent potential therapeutic intervention points for cardiovascular diseases.
        Note: Druggability is added post-discovery to avoid biasing pathway identification.
        """
        elements.append(Paragraph(drug_text, styles['Normal']))
        
        # Methodology
        elements.append(PageBreak())
        elements.append(Paragraph("Methodology", heading_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1976d2')))
        elements.append(Spacer(1, 12))
        
        methodology_text = """
        <b>🤖 AI-Powered NETS Pipeline (7-Stage Multi-Dimensional Discovery):</b><br/><br/>
        
        <b>Stage 0: Input Validation</b><br/>
        Validates seed genes against HGNC (HUGO Gene Nomenclature Committee) to ensure standardized gene symbols. 
        Invalid or ambiguous gene symbols are flagged for manual review.<br/><br/>
        
        <b>Stage 1: Functional Neighborhood Assembly (Graph ML)</b><br/>
        Expands seed genes using STRING protein-protein interaction network (v12.0) to identify functionally 
        related genes. Network expansion uses combined confidence scores (&gt;0.60) incorporating experimental, database, 
        text-mining, and co-expression evidence. Typical expansion: 100 high-confidence interactors per seed gene.<br/><br/>
        
        <b>Stage 2: Pathway Enrichment & Intelligent Aggregation</b><br/>
        Performs multi-database pathway enrichment using g:Profiler (integrating Reactome, KEGG, WikiPathways, GO:BP) 
        with FDR correction (Benjamini-Hochberg, threshold ≤ 0.05). Primary pathways are discovered from functional 
        neighborhood, then literature mining (PubMed) expands gene sets to discover secondary pathways. Fisher's method 
        combines evidence across databases with consistency scoring requiring ≥2 primary pathway support.<br/><br/>
        
        <b>Stage 3: Clinical Evidence Integration (Multi-Modal Fusion) 🆕</b><br/>
        <b>Novel multi-modal validation</b> using three independent clinical evidence sources queried in parallel:<br/>
        • <b>HPA (Human Protein Atlas):</b> Validates tissue-specific RNA expression in cardiac tissues (heart muscle, atrium, ventricle)<br/>
        • <b>DrugBank:</b> Identifies FDA-approved and investigational drugs<br/>
        • <b>Epigenomics Roadmap:</b> Detects H3K27ac enhancer marks indicating regulatory activity in cardiac tissues<br/>
        Combined clinical score (0-1) provides <b>clinical weight multiplier (1.0-2.0×)</b> applied to NES score. 
        This ensures pathways are not just statistically significant but also biologically validated in cardiac tissues.<br/><br/>
        
        <b>Stage 5: NES Composite Scoring (6-Dimensional Optimization)</b><br/>
        Calculates Novelty and Evidence Score (NES) integrating 6 dimensions:<br/>
        1. <b>Statistical Significance:</b> -log₁₀(P_adj) from FDR correction<br/>
        2. <b>Evidence Count:</b> Number of pathway genes from functional neighborhood<br/>
        3. <b>Database Quality:</b> Weighting by curation level (Reactome/KEGG 1.5×, WikiPathways 1.2×, GO:BP 1.0×)<br/>
        4. <b>Cardiac Relevance:</b> Semantic NLP matching (700+ terms, +30% disease-context boost)<br/>
        5. <b>Literature Score:</b> PubMed co-citation network analysis (0.8-1.2×)<br/>
        6. <b>Clinical Weight:</b> Multi-modal validation multiplier (1.0-2.0×) from Stage 3<br/>
        Formula: NES = Base_Score × DB_Weight × Cardiac_Relevance × Lit_Score × Clinical_Weight × Network_Weight<br/><br/>
        
        <b>Stage 4: Semantic Filtering (NLP with 700+ Cardiovascular Terms)</b><br/>
        AI-powered semantic matching using 700+ cardiovascular terms across 8 categories: anatomical (heart, ventricle, atrium), 
        physiological (contraction, conduction), disease (cardiomyopathy, arrhythmia, infarction), molecular (calcium, ion channel), 
        cellular (cardiomyocyte, endothelial), metabolic (energy, oxidative), inflammatory (cytokine, immune), and pharmacological 
        (drug, therapy). Pathways matching selected disease context receive <b>+30% relevance boost</b> with 75% semantic weight. 
        Minimum cardiac relevance threshold (0.01) ensures cardiovascular specificity.<br/><br/>
        
        <b>Stage 6: Literature Mining & Validation (NLP)</b><br/>
        PubMed literature mining with cardiovascular keyword matching and co-citation network analysis. Discovers literature-supported 
        pathways (100 secondary pathways) and validates primary findings with publication evidence. Citation networks reveal 
        mechanistic connections not evident from gene-level analysis.<br/><br/>
        
        <b>Stage 7: Network Topology Analysis (Graph ML)</b><br/>
        Advanced graph machine learning using <b>PageRank, betweenness centrality, and community detection</b> algorithms 
        to identify:<br/>
        • <b>Hub genes:</b> Critical network nodes with high connectivity and centrality<br/>
        • <b>Therapeutic targets:</b> Druggable hub genes prioritized by centrality (40%), druggability (30%), evidence (20%), pathway diversity (10%)<br/>
        • <b>Functional modules:</b> Community detection reveals pathway crosstalk and mechanistic relationships<br/>
        Top 20 genes ranked by multi-factor importance score: Importance = (Frequency^1.2) × (Avg NES) × (1 + Cardiac Relevance)<br/><br/>
        
        <b>Report Generation and Druggability Annotation</b><br/>
        Generates comprehensive reports with druggability annotations from DrugBank and TTD (4-tier classification: FDA Approved, 
        Clinical Trial, Druggable protein family, Research-stage). Druggability annotation occurs post-discovery to avoid 
        selection bias while providing translational context for therapeutic target identification.
        """
        elements.append(Paragraph(methodology_text, styles['Normal']))
        
        # Statistical Parameters
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Statistical Parameters", subheading_style))
        
        params_data = [
            ['Parameter', 'Value'],
            ['FDR Threshold', str(self.settings.nets.fdr_threshold)],
            ['STRING Score Threshold', str(self.settings.nets.string_score_threshold)],
            ['Minimum Support Count', str(self.settings.nets.min_support_threshold)],
            ['Semantic Relevance Threshold', str(self.settings.nets.semantic_relevance_threshold)],
        ]
        
        params_table = Table(params_data, colWidths=[3*inch, 2*inch])
        params_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(params_table)
        
        # Statistical Summary
        elements.append(PageBreak())
        elements.append(Paragraph("Statistical Summary", heading_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1976d2')))
        elements.append(Spacer(1, 12))
        
        if hypotheses:
            avg_nes = sum(hyp.get('nes_score', 0) for hyp in hypotheses) / len(hypotheses)
            avg_padj = sum(hyp.get('p_adj', 1.0) for hyp in hypotheses) / len(hypotheses)
            avg_cardiac = sum(hyp.get('cardiac_relevance', 0) for hyp in hypotheses) / len(hypotheses)
            avg_evidence = sum(hyp.get('evidence_count', 0) for hyp in hypotheses) / len(hypotheses)
            
            stats_text = f"""
            <b>Aggregate Statistics Across Top Pathways:</b><br/><br/>
            
            • <b>Mean NES Score:</b> {avg_nes:.3f} (higher indicates stronger novelty and evidence)<br/>
            • <b>Mean Adjusted P-value:</b> {avg_padj:.2e} (FDR-corrected statistical significance)<br/>
            • <b>Mean Cardiac Relevance:</b> {(avg_cardiac*100):.1f}% (semantic cardiac specificity)<br/>
            • <b>Mean Evidence Genes:</b> {avg_evidence:.1f} genes per pathway<br/><br/>
            
            <b>Distribution Characteristics:</b><br/>
            • NES Range: {min(hyp.get('nes_score', 0) for hyp in hypotheses):.3f} - {max(hyp.get('nes_score', 0) for hyp in hypotheses):.3f}<br/>
            • P-value Range: {min(hyp.get('p_adj', 1.0) for hyp in hypotheses):.2e} - {max(hyp.get('p_adj', 1.0) for hyp in hypotheses):.2e}<br/>
            • Evidence Count Range: {min(hyp.get('evidence_count', 0) for hyp in hypotheses)} - {max(hyp.get('evidence_count', 0) for hyp in hypotheses)} genes<br/><br/>
            
            All statistics are calculated from enrichment analysis with FDR correction (Benjamini-Hochberg method) 
            and validated through multiple independent evidence sources.
            """
            elements.append(Paragraph(stats_text, styles['Normal']))
        
        # Conclusion
        elements.append(PageBreak())
        elements.append(Paragraph("Conclusion", heading_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1976d2')))
        elements.append(Spacer(1, 12))
        
        conclusion = report_data.get('conclusion', 'Analysis completed successfully.')
        if isinstance(conclusion, dict):
            conclusion_text = conclusion.get('summary', 'Analysis completed successfully.')
        else:
            conclusion_text = str(conclusion) if conclusion else 'Analysis completed successfully.'
        
        elements.append(Paragraph(conclusion_text, styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Add interpretation guidance
        interpretation_text = """
        <b>Interpreting Results:</b><br/><br/>
        
        The NETS pipeline systematically expands beyond seed genes to discover novel cardiovascular pathways through 
        multi-database integration and statistical aggregation. High-ranking pathways represent robust hypotheses 
        supported by multiple lines of evidence including enrichment statistics, literature validation, tissue expression, 
        and network topology.<br/><br/>
        
        <b>Quality Indicators:</b><br/>
        • <b>High NES scores</b> (>2.0): Strong novelty and evidence support<br/>
        • <b>Low adjusted p-values</b> (<0.01): High statistical significance<br/>
        • <b>High cardiac relevance</b> (>50%): Strong cardiovascular specificity<br/>
        • <b>Literature support</b>: Direct validation from published research<br/>
        • <b>GTEx validation</b>: Preferential cardiac expression patterns<br/><br/>
        
        Pathways should be evaluated holistically considering all evidence dimensions rather than single metrics.
        """
        elements.append(Paragraph(interpretation_text, styles['Normal']))
        
        # Data Sources and References
        elements.append(PageBreak())
        elements.append(Paragraph("Data Sources and References", heading_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1976d2')))
        elements.append(Spacer(1, 12))
        
        references_text = """
        <b>Primary Data Sources (9 Databases):</b><br/><br/>
        
        • <b>STRING v12.0</b> - Protein-protein interaction networks (Stage 1)<br/>
          Szklarczyk D, et al. (2023) Nucleic Acids Res. 51(D1):D638-D646<br/><br/>
        
        • <b>g:Profiler</b> - Functional enrichment analysis (Stage 2)<br/>
          Raudvere U, et al. (2019) Nucleic Acids Res. 47(W1):W191-W198<br/><br/>
        
        • <b>Reactome</b> - Pathway database (Stage 2)<br/>
          Gillespie M, et al. (2022) Nucleic Acids Res. 50(D1):D687-D692<br/><br/>
        
        • <b>KEGG</b> - Kyoto Encyclopedia of Genes and Genomes (Stage 2)<br/>
          Kanehisa M, et al. (2023) Nucleic Acids Res. 51(D1):D587-D592<br/><br/>
        
        • <b>🆕 Human Protein Atlas (HPA)</b> - Tissue expression validation (Stage 3)<br/>
          Uhlén M, et al. (2015) Science. 347(6220):1260419<br/><br/>
        
        • <b>🆕 DrugBank</b> - Therapeutic target database (Stage 3)<br/>
          Sollis E, et al. (2023) Nucleic Acids Res. 51(D1):D1019-D1028<br/><br/>
        
        • <b>🆕 Epigenomics Roadmap</b> - Regulatory element maps (Stage 3)<br/>
          Roadmap Epigenomics Consortium (2015) Nature. 518(7539):317-330<br/><br/>
        
        • <b>GTEx v8</b> - Genotype-Tissue Expression Project (Complementary)<br/>
          GTEx Consortium (2020) Science. 369(6509):1318-1330<br/><br/>
        
        • <b>DrugBank 5.1</b> - Drug and drug target database (Post-discovery annotation)<br/>
          Wishart DS, et al. (2018) Nucleic Acids Res. 46(D1):D1074-D1082<br/><br/>
        
        • <b>PubMed/NCBI</b> - Biomedical literature database (Stage 2 & 6)<br/>
          National Center for Biotechnology Information<br/><br/>
        
        <b>Statistical Methods:</b><br/><br/>
        
        • <b>Fisher's Method</b> - Meta-analysis of p-values<br/>
          Fisher RA (1932) Statistical Methods for Research Workers<br/><br/>
        
        • <b>Benjamini-Hochberg FDR</b> - Multiple testing correction<br/>
          Benjamini Y, Hochberg Y (1995) J R Stat Soc Series B. 57(1):289-300<br/><br/>
        
        <b>Analysis Framework:</b><br/><br/>
        
        CardioXNet implements the NETS (Neighborhood Enrichment Triage and Scoring) pipeline, a systematic 
        approach to cardiovascular pathway discovery through functional neighborhood expansion, 
        multi-database integration, and rigorous statistical validation.
        """
        elements.append(Paragraph(references_text, styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        
        logger.info(f"PDF report saved to {output_file}")
        
        return str(output_file)
