"""API request and response models."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from .gene import GeneInfo
from .results import ValidationResult, ScoredHypotheses


class GeneValidationRequest(BaseModel):
    """Request to validate gene identifiers."""
    
    gene_ids: List[str] = Field(..., description="List of gene identifiers to validate")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "gene_ids": ["NKX2-5", "GATA4", "MEF2C"]
            }
        }
    )


class GeneValidationResponse(BaseModel):
    """Response from gene validation."""
    
    result: ValidationResult = Field(..., description="Validation result")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "result": {
                    "valid_genes": [
                        {
                            "input_id": "TP53",
                            "entrez_id": "7157",
                            "symbol": "TP53",
                            "species": "Homo sapiens"
                        }
                    ],
                    "invalid_genes": [],
                    "warnings": []
                }
            }
        }
    )


class AnalysisConfigOverrides(BaseModel):
    """Bounded per-analysis settings accepted by the public API.

    Service endpoints and resource-version identifiers are intentionally not
    request-configurable. Operators can still configure those trusted values
    through ``NETS_*`` environment variables, while an API caller is limited to
    analysis behavior and bounded resilience settings.
    """

    graceful_degradation: Optional[bool] = None
    require_all_apis: Optional[bool] = None

    string_neighbor_count: Optional[int] = Field(None, ge=10, le=200)
    string_score_threshold: Optional[float] = Field(None, ge=0.4, le=0.95)
    fdr_threshold: Optional[float] = Field(None, ge=0.001, le=0.2)
    top_hypotheses_count: Optional[int] = Field(None, ge=5, le=100)

    db_weight_reactome: Optional[float] = Field(None, ge=0.0, le=10.0)
    db_weight_kegg: Optional[float] = Field(None, ge=0.0, le=10.0)
    db_weight_wikipathways: Optional[float] = Field(None, ge=0.0, le=10.0)
    db_weight_gobp: Optional[float] = Field(None, ge=0.0, le=10.0)

    max_retries: Optional[int] = Field(None, ge=0, le=5)
    retry_backoff_factor: Optional[float] = Field(None, ge=0.0, le=60.0)
    request_timeout: Optional[int] = Field(None, ge=1, le=300)
    gprofiler_timeout_seconds: Optional[float] = Field(None, ge=1.0, le=600.0)
    hpa_timeout: Optional[int] = Field(None, ge=1, le=300)
    gwas_timeout: Optional[int] = Field(None, ge=1, le=300)
    epigenomic_timeout: Optional[int] = Field(None, ge=1, le=300)
    clinical_api_max_retries: Optional[int] = Field(None, ge=0, le=5)

    aggregation_strategy: Optional[Literal["intersection", "frequency", "weighted"]] = None
    min_support_threshold: Optional[int] = Field(None, ge=1, le=10)
    primary_pathways_to_expand: Optional[int] = Field(None, ge=1, le=200)
    pubmed_max_results: Optional[int] = Field(None, ge=10, le=500)
    literature_relevance_threshold: Optional[float] = Field(None, ge=0.05, le=0.7)

    semantic_relevance_threshold: Optional[float] = Field(None, ge=0.0, le=0.7)
    semantic_max_hypotheses_for_literature: Optional[int] = Field(None, ge=1, le=100)
    semantic_max_results: Optional[int] = Field(None, ge=15, le=1000)
    seed_overlap_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)

    tissue_expression_validation: Optional[bool] = None
    min_cardiac_expression_ratio: Optional[float] = Field(None, ge=0.1, le=0.8)
    permutation_test_enabled: Optional[bool] = None
    n_permutations: Optional[int] = Field(None, ge=10, le=10000)
    min_fold_enrichment: Optional[float] = Field(None, ge=1.0, le=10.0)

    enforce_final_name_filter: Optional[bool] = None
    filter_generic_pathways: Optional[bool] = None
    redundancy_jaccard_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    gtex_top_pathways: Optional[int] = Field(None, ge=0, le=1000)
    permutation_top_pathways: Optional[int] = Field(None, ge=0, le=1000)
    external_druggability_top_pathways: Optional[int] = Field(None, ge=0, le=1000)
    external_druggability_enabled: Optional[bool] = None
    druggability_analysis: Optional[bool] = None
    output_formats: Optional[
        List[Literal["pdf", "json", "markdown", "html"]]
    ] = Field(None, min_length=1, max_length=4)

    # These two values are run context, not service configuration. They remain
    # accepted here for compatibility with older clients that supplied them in
    # config_overrides rather than using AnalysisRequest.disease_context.
    disease_context: Optional[str] = Field(None, min_length=1, max_length=120)
    disease_synonyms: Optional[List[str]] = Field(None, max_length=20)

    @field_validator("disease_synonyms")
    @classmethod
    def validate_disease_synonyms(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        if values is not None and any(not value.strip() or len(value) > 120 for value in values):
            raise ValueError("disease synonyms must contain 1 to 120 characters")
        return values

    model_config = ConfigDict(extra="forbid")


class AnalysisRequest(BaseModel):
    """Request to start a new analysis."""
    
    seed_genes: List[str] = Field(..., description="Seed gene identifiers")
    disease_context: Optional[str] = Field(None, description="Optional disease context for analysis")
    config_overrides: Optional[AnalysisConfigOverrides] = Field(
        None,
        description=(
            "Bounded analysis overrides. Service endpoints and resource-version "
            "identifiers are operator-controlled and cannot be overridden per request."
        ),
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "seed_genes": ["TP53", "EGFR"],
                "disease_context": "hypertensive_remodeling",
                "config_overrides": {
                    "string_neighbor_count": 100,
                    "fdr_threshold": 0.01,
                    "top_hypotheses_count": 20
                }
            }
        }
    )


class AnalysisResponse(BaseModel):
    """Response after starting analysis."""
    
    analysis_id: str = Field(..., description="Unique analysis identifier")
    status: str = Field(..., description="Analysis status")
    message: str = Field(..., description="Status message")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_id": "abc123",
                "status": "started",
                "message": "Analysis started successfully"
            }
        }
    )


class AnalysisStatusResponse(BaseModel):
    """Response for analysis status check."""
    
    analysis_id: str = Field(..., description="Analysis identifier")
    status: str = Field(..., description="Current status: pending, running, completed, failed")
    current_stage: Optional[str] = Field(None, description="Current pipeline stage")
    progress_percentage: Optional[float] = Field(None, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_id": "abc123",
                "status": "running",
                "current_stage": "Stage 2a: Primary Enrichment",
                "progress_percentage": 45.0,
                "message": "Performing pathway enrichment"
            }
        }
    )


class AnalysisResultsResponse(BaseModel):
    """Response containing analysis results."""
    
    analysis_id: str = Field(..., description="Analysis identifier")
    status: str = Field(..., description="Analysis status")
    seed_genes: List[GeneInfo] = Field(default_factory=list, description="Validated seed genes")
    hypotheses: Optional[Dict] = Field(None, description="Scored hypotheses (flexible format for frontend)")
    topology: Optional[Dict] = Field(None, description="Network topology analysis results")
    network_topology: Optional[Dict] = Field(None, description="Comprehensive network topology (hub genes, centrality, network summary)")
    top_genes: Optional[List[Dict]] = Field(None, description="Top genes aggregated across pathways")
    run_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional reproducibility and configured-resource metadata for the run",
    )
    report_urls: Optional[Dict[str, str]] = Field(None, description="URLs to download reports")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_id": "abc123",
                "status": "completed",
                "seed_genes": [
                    {
                        "input_id": "TP53",
                        "entrez_id": "7157",
                        "symbol": "TP53",
                        "species": "Homo sapiens"
                    }
                ],
                "hypotheses": {
                    "hypotheses": [],
                    "total_count": 0
                },
                "report_urls": {
                    "markdown": "/api/v1/analysis/abc123/report/markdown",
                    "json": "/api/v1/analysis/abc123/report/json",
                    "html": "/api/v1/analysis/abc123/report/html"
                }
            }
        }
    )


class StageResultResponse(BaseModel):
    """Response for specific stage results."""
    
    analysis_id: str = Field(..., description="Analysis identifier")
    stage_id: str = Field(..., description="Stage identifier")
    stage_name: str = Field(..., description="Stage name")
    status: str = Field(..., description="Stage status")
    data: Dict = Field(default_factory=dict, description="Stage-specific data")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_id": "abc123",
                "stage_id": "stage_1",
                "stage_name": "Functional Neighborhood Assembly",
                "status": "completed",
                "data": {
                    "fn_size": 75,
                    "contributions": {"7157": 50}
                }
            }
        }
    )


class ConfigDefaultsResponse(BaseModel):
    """Response containing default configuration."""
    
    config: Dict = Field(..., description="Default configuration parameters")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "config": {
                    "string_score_threshold": 0.7,
                    "fdr_threshold": 0.05
                }
            }
        }
    )


class ProgressMessage(BaseModel):
    """WebSocket progress message."""
    
    analysis_id: str = Field(..., description="Analysis identifier")
    stage: str = Field(..., description="Current stage")
    progress: float = Field(..., description="Progress percentage (0-100)")
    message: str = Field(..., description="Progress message")
    timestamp: str = Field(..., description="ISO timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "analysis_id": "abc123",
                "stage": "Stage 1",
                "progress": 25.0,
                "message": "Building functional neighborhood",
                "timestamp": "2024-10-02T10:30:00Z"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict] = Field(None, description="Additional error details")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "message": "Invalid gene identifier",
                "details": {
                    "invalid_genes": ["INVALID123"]
                }
            }
        }
    )
