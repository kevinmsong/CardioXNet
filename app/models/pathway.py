"""Pathway-related data models."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class PathwayEntry(BaseModel):
    """Basic pathway enrichment entry."""
    
    pathway_id: str = Field(..., description="Pathway identifier")
    pathway_name: str = Field(..., description="Pathway name")
    source_db: str = Field(..., description="Source database (REAC, KEGG, WP, GO:BP)")
    p_value: float = Field(..., description="Raw p-value")
    p_adj: float = Field(..., description="FDR-adjusted p-value")
    evidence_count: int = Field(..., description="Number of genes from input in pathway")
    evidence_genes: List[str] = Field(default_factory=list, description="Gene IDs in pathway")

    # Effect-size inputs from the enrichment test. Without these only the
    # p-value is available, and p-value alone systematically favours very large,
    # generic gene sets because significance grows with set size independently
    # of how concentrated the query genes actually are.
    term_size: Optional[int] = Field(
        None, description="Total number of genes annotated to this term in the source database"
    )
    query_size: Optional[int] = Field(
        None, description="Number of query genes tested against this term"
    )
    effective_domain_size: Optional[int] = Field(
        None, description="Size of the annotation universe used by the enrichment test"
    )

    @property
    def fold_enrichment(self) -> Optional[float]:
        """Observed/expected overlap ratio.

        expected = term_size * query_size / effective_domain_size
        Returns None when the enrichment test did not report the sizes needed.
        """
        if not (self.term_size and self.query_size and self.effective_domain_size):
            return None
        expected = (self.term_size * self.query_size) / self.effective_domain_size
        if expected <= 0:
            return None
        return self.evidence_count / expected

    @property
    def gene_set_specificity(self) -> float:
        """1.0 for a tightly-scoped term, falling to 0.0 for very broad ones.

        Log-scaled against a 500-gene reference: a 10-gene term scores 0.63, a
        100-gene term 0.26, a 500-gene term 0.0. Used to stop maximally generic
        GO terms ("developmental process", 200+ genes) from dominating the
        ranking purely on set size.
        """
        import math as _m
        size = self.term_size or max(self.evidence_count, 1)
        if size <= 1:
            return 1.0
        return max(0.0, 1.0 - _m.log10(size) / _m.log10(500))
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pathway_id": "REAC:R-HSA-5663202",
                "pathway_name": "Cardiac muscle contraction",
                "source_db": "REAC",
                "p_value": 0.0001,
                "p_adj": 0.005,
                "evidence_count": 15,
                "evidence_genes": ["NKX2-5", "GATA4", "MEF2C"]
            }
        }
    )


class ScoredPathwayEntry(PathwayEntry):
    """Pathway entry carrying the preliminary screening score."""
    
    preliminary_nes: float = Field(
        ...,
        description=(
            "Expansion screening score: min(-log10(p_adj), 20) * sqrt(evidence_count) "
            "* db_weight. Recall-oriented and deliberately different from the final "
            "Pathway Prioritization Score."
        ),
    )
    literature_support: Optional[Dict] = Field(None, description="Literature expansion metadata")
    contributing_seed_genes: List[str] = Field(
        default_factory=list,
        description="Seed genes that contributed to this pathway discovery"
    )
    source_primary_pathway: Optional[str] = Field(
        None,
        description="ID of the primary pathway that led to this secondary pathway discovery"
    )


class AggregatedPathway(BaseModel):
    """Pathway with aggregation metadata and statistical rigor."""
    
    pathway: PathwayEntry = Field(..., description="Base pathway information")
    support_count: int = Field(..., description="Number of primary pathways supporting this")
    source_primary_pathways: List[str] = Field(
        default_factory=list,
        description="IDs of primary pathways that led to this"
    )
    source_secondary_pathways: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Secondary pathway instances that were aggregated into this final pathway"
    )
    aggregation_score: float = Field(..., description="Aggregation-based score")
    
    # Statistical rigor fields
    combined_p_value: Optional[float] = Field(None, description="Fisher's combined p-value across primaries")
    aggregated_nes: Optional[float] = Field(None, description="Weighted average NES across primaries")
    consistency_score: Optional[float] = Field(None, description="Consistency of evidence across primaries (0-1)")
    confidence_score: Optional[float] = Field(None, description="Overall confidence score (0-1)")
    support_fraction: Optional[float] = Field(None, description="Fraction of primaries that support this (0-1)")
    
    # Seed gene tracking
    contributing_seed_genes: List[str] = Field(
        default_factory=list,
        description="Seed genes that contributed to this aggregated pathway"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pathway": {
                    "pathway_id": "REAC:R-HSA-5663202",
                    "pathway_name": "Cardiac development",
                    "source_db": "REAC",
                    "p_value": 0.0001,
                    "p_adj": 0.005,
                    "evidence_count": 15,
                    "evidence_genes": ["NKX2-5"]
                },
                "support_count": 3,
                "source_primary_pathways": ["primary_1", "primary_2"],
                "aggregation_score": 0.85
            }
        }
    )


class ScoredPathway(BaseModel):
    """Final scored pathway hypothesis."""
    
    aggregated_pathway: AggregatedPathway = Field(..., description="Aggregated pathway data")
    nes_score: float = Field(
        ...,
        description=(
            "Final Pathway Prioritization Score, including the bounded semantic "
            "cardiovascular-relevance multiplier when that stage has run. Field "
            "name retained for backwards compatibility with persisted reports; "
            "this is NOT a GSEA normalized enrichment score."
        ),
    )
    rank: int = Field(..., description="Rank by Discovery Score after Stage 8, else by PPS")
    score_components: Dict[str, Any] = Field(
        default_factory=dict,
        description="Breakdown of score calculation (can contain floats or nested dicts)"
    )
    
    # Seed gene traceability
    traced_seed_genes: List[str] = Field(
        default_factory=list,
        description="Seed genes that trace back to this pathway"
    )
    literature_associations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Literature evidence for pathway-seed gene associations"
    )
    cardiac_disease_score: Optional[float] = Field(
        None,
        description="Cardiac disease association score (0-1) based on evidence genes from curated database"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "aggregated_pathway": {
                    "pathway": {
                        "pathway_id": "REAC:R-HSA-5663202",
                        "pathway_name": "Cardiac muscle development",
                        "source_db": "REAC",
                        "p_value": 0.0001,
                        "p_adj": 0.005,
                        "evidence_count": 15,
                        "evidence_genes": ["GATA4"]
                    },
                    "support_count": 3,
                    "source_primary_pathways": ["primary_1"],
                    "aggregation_score": 0.85
                },
                "nes_score": 5.67,
                "rank": 1,
                "score_components": {
                    "p_adj_component": 0.995,
                    "evidence_component": 4.0,
                    "db_weight": 1.5,
                    "agg_weight": 1.2
                }
            }
        }
    )
