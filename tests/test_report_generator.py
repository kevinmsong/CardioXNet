import json
from pathlib import Path

import pytest

from app.models import (
    AggregatedPathway,
    FinalPathwayResult,
    FunctionalNeighborhood,
    GeneInfo,
    LiteratureEvidence,
    PathwayEntry,
    PrimaryTriageResult,
    ScoredHypotheses,
    ScoredPathway,
    ScoredPathwayEntry,
    SecondaryTriageResult,
    TopologyResult,
    ValidationResult,
)
from app.services import report_generator as report_module
from app.services.report_generator import ReportGenerator


def _gene(symbol: str) -> GeneInfo:
    return GeneInfo(input_id=symbol, entrez_id="1", hgnc_id=None, symbol=symbol)


def test_generate_report_keeps_json_when_pdf_unavailable(tmp_path, monkeypatch):
    seed_gene = _gene("SRC")
    pathway = PathwayEntry(
        pathway_id="REAC:R-HSA-1",
        pathway_name="Cardiac signaling",
        source_db="REAC",
        p_value=0.001,
        p_adj=0.01,
        evidence_count=1,
        evidence_genes=["SRC"],
    )
    aggregated = AggregatedPathway(
        pathway=pathway,
        support_count=1,
        source_primary_pathways=["primary-1"],
        aggregation_score=1.0,
    )
    scored_pathway = ScoredPathway(
        aggregated_pathway=aggregated,
        nes_score=2.5,
        rank=1,
        traced_seed_genes=["SRC"],
    )

    generator = ReportGenerator()
    generator.settings.output_dir = str(tmp_path)
    monkeypatch.setattr(report_module, "REPORTLAB_AVAILABLE", False)

    output_files = generator.generate_report(
        analysis_id="analysis_test",
        seed_genes=[seed_gene],
        validation_result=ValidationResult(valid_genes=[seed_gene], invalid_genes=[], warnings=[]),
        fn_result=FunctionalNeighborhood(
            seed_genes=[seed_gene],
            neighbors=[],
            interactions=[],
            size=1,
            contributions={"SRC": 1},
            sources={"SRC": ["test"]},
        ),
        primary_result=PrimaryTriageResult(
            primary_pathways=[
                ScoredPathwayEntry(
                    pathway_id="REAC:R-HSA-1",
                    pathway_name="Cardiac signaling",
                    source_db="REAC",
                    p_value=0.001,
                    p_adj=0.01,
                    evidence_count=1,
                    evidence_genes=["SRC"],
                    preliminary_nes=1.5,
                )
            ],
            known_pathways=[],
            filtered_count=0,
            filtering_contributions={},
        ),
        secondary_result=SecondaryTriageResult(
            union_genes=["SRC"],
            gene_triage_results=[],
            aggregated_pathways=[],
            pathway_support={},
            pathway_frequency={},
            total_secondary_count=0,
            literature_expansion_stats={"total_genes_added": 0},
        ),
        final_result=FinalPathwayResult(
            final_pathways=[aggregated],
            aggregation_strategy="weighted",
            total_count=1,
            min_support_threshold=1,
        ),
        scored_hypotheses=ScoredHypotheses(hypotheses=[scored_pathway], total_count=1),
        topology_result=TopologyResult(hypothesis_networks={}),
        literature_evidence=LiteratureEvidence(hypothesis_citations={}),
        output_formats=["pdf", "json"],
        run_metadata={
            "resource_identifiers": {
                "string": {
                    "configured_endpoint": "https://string-db.org/api",
                    "effective_endpoint": "https://version-12-0.string-db.org/api",
                }
            }
        },
    )

    assert "json" in output_files
    assert "pdf" not in output_files
    assert Path(output_files["json"]).exists()
    report_data = json.loads(Path(output_files["json"]).read_text(encoding="utf-8"))
    assert report_data["run_metadata"]["resource_identifiers"]["string"][
        "effective_endpoint"
    ] == "https://version-12-0.string-db.org/api"


def test_build_conclusion_avoids_claiming_novelty_without_literature_support():
    generator = ReportGenerator()
    pathway = PathwayEntry(
        pathway_id="KEGG:05415",
        pathway_name="Diabetic cardiomyopathy",
        source_db="KEGG",
        p_value=1e-6,
        p_adj=1e-5,
        evidence_count=5,
        evidence_genes=["PIK3R1"],
    )
    aggregated = AggregatedPathway(
        pathway=pathway,
        support_count=2,
        source_primary_pathways=["primary-1", "primary-2"],
        aggregation_score=1.0,
    )
    scored = ScoredPathway(
        aggregated_pathway=aggregated,
        nes_score=3.2,
        rank=1,
        traced_seed_genes=["PIK3R1"],
        literature_associations={
            "has_literature_support": False,
            "total_citations": 0,
            "associations": [],
        },
    )

    conclusion = generator._build_conclusion(
        ScoredHypotheses(hypotheses=[scored], total_count=1)
    )

    assert "novel pathway hypotheses" not in conclusion
    assert "not proof of novelty" in conclusion


def test_build_conclusion_reports_supported_final_pathways():
    generator = ReportGenerator()
    pathway = PathwayEntry(
        pathway_id="KEGG:04151",
        pathway_name="PI3K-Akt signaling pathway",
        source_db="KEGG",
        p_value=1e-8,
        p_adj=1e-7,
        evidence_count=8,
        evidence_genes=["PIK3R1", "AKT1"],
    )
    aggregated = AggregatedPathway(
        pathway=pathway,
        support_count=3,
        source_primary_pathways=["primary-1", "primary-2", "primary-3"],
        aggregation_score=1.0,
    )
    scored = ScoredPathway(
        aggregated_pathway=aggregated,
        nes_score=3.8,
        rank=1,
        traced_seed_genes=["PIK3R1"],
        literature_associations={
            "has_literature_support": True,
            "total_citations": 4,
            "associations": [{"seed_gene": "PIK3R1", "citation_count": 4, "has_support": True}],
        },
    )

    conclusion = generator._build_conclusion(
        ScoredHypotheses(hypotheses=[scored], total_count=1)
    )

    assert "co-mention support for 1 of 1 final pathways" in conclusion


@pytest.mark.skipif(
    not report_module.REPORTLAB_AVAILABLE,
    reason="ReportLab is not installed",
)
def test_pdf_escapes_unbalanced_pubmed_markup(tmp_path):
    generator = ReportGenerator()
    generator.settings.output_dir = str(tmp_path)
    report_data = {
        "seed_genes": ["CACNA1C"],
        "stage_3": {"total_hypotheses": 1},
        "conclusion": "Computational hypothesis for review.",
        "ranked_hypotheses": [
            {
                "rank": 1,
                "pathway_name": "Calcium <super>2+ signaling",
                "source_db": "TEST",
                "discovery_score": 1.0,
                "novelty_tier": "Novel",
                "nes_score": 1.1,
                "p_adj": 0.01,
                "empirical_qvalue": 0.02,
                "evidence_count": 1,
                "pubmed_hit_count": 1,
                "citation_count": 1,
                "literature_support": True,
                "citations": [
                    {
                        "title": "An unclosed <super> tag from an external abstract",
                        "pmid": "12345",
                        "year": 2026,
                    }
                ],
            }
        ],
    }

    output = generator._generate_pdf("analysis_markup", report_data)

    assert Path(output).exists()
    assert Path(output).stat().st_size > 0
