"""API request and response models."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from .gene import GeneInfo
from .results import ValidationResult, ScoredHypotheses


class GeneValidationRequest(BaseModel):
    """Request to validate gene identifiers."""
    
    gene_ids: List[str] = Field(..., description="List of gene identifiers to validate")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gene_ids": ["NKX2-5", "GATA4", "MEF2C"]
            }
        }


class GeneValidationResponse(BaseModel):
    """Response from gene validation."""
    
    result: ValidationResult = Field(..., description="Validation result")
    
    class Config:
        json_schema_extra = {
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


class AnalysisRequest(BaseModel):
    """Request to start a new analysis."""
    
    seed_genes: List[str] = Field(..., description="Seed gene identifiers")
    disease_context: Optional[str] = Field(None, description="Optional disease context for analysis")
    config_overrides: Optional[Dict] = Field(None, description="Configuration overrides")
    
    class Config:
        json_schema_extra = {
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


class AnalysisResponse(BaseModel):
    """Response after starting analysis."""
    
    analysis_id: str = Field(..., description="Unique analysis identifier")
    status: str = Field(..., description="Analysis status")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "abc123",
                "status": "started",
                "message": "Analysis started successfully"
            }
        }


class AnalysisStatusResponse(BaseModel):
    """Response for analysis status check."""
    
    analysis_id: str = Field(..., description="Analysis identifier")
    status: str = Field(..., description="Current status: pending, running, completed, failed")
    current_stage: Optional[str] = Field(None, description="Current pipeline stage")
    progress_percentage: Optional[float] = Field(None, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "abc123",
                "status": "running",
                "current_stage": "Stage 2a: Primary Enrichment",
                "progress_percentage": 45.0,
                "message": "Performing pathway enrichment"
            }
        }


class AnalysisResultsResponse(BaseModel):
    """Response containing analysis results."""
    
    analysis_id: str = Field(..., description="Analysis identifier")
    status: str = Field(..., description="Analysis status")
    seed_genes: List[GeneInfo] = Field(default_factory=list, description="Validated seed genes")
    hypotheses: Optional[Dict] = Field(None, description="Scored hypotheses (flexible format for frontend)")
    topology: Optional[Dict] = Field(None, description="Network topology analysis results")
    top_genes: Optional[List[Dict]] = Field(None, description="Top genes aggregated across pathways")
    report_urls: Optional[Dict[str, str]] = Field(None, description="URLs to download reports")
    
    class Config:
        json_schema_extra = {
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


class StageResultResponse(BaseModel):
    """Response for specific stage results."""
    
    analysis_id: str = Field(..., description="Analysis identifier")
    stage_id: str = Field(..., description="Stage identifier")
    stage_name: str = Field(..., description="Stage name")
    status: str = Field(..., description="Stage status")
    data: Dict = Field(default_factory=dict, description="Stage-specific data")
    
    class Config:
        json_schema_extra = {
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


class ConfigDefaultsResponse(BaseModel):
    """Response containing default configuration."""
    
    config: Dict = Field(..., description="Default configuration parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "config": {
                    "string_score_threshold": 0.7,
                    "fdr_threshold": 0.05
                }
            }
        }


class ProgressMessage(BaseModel):
    """WebSocket progress message."""
    
    analysis_id: str = Field(..., description="Analysis identifier")
    stage: str = Field(..., description="Current stage")
    progress: float = Field(..., description="Progress percentage (0-100)")
    message: str = Field(..., description="Progress message")
    timestamp: str = Field(..., description="ISO timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis_id": "abc123",
                "stage": "Stage 1",
                "progress": 25.0,
                "message": "Building functional neighborhood",
                "timestamp": "2024-10-02T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict] = Field(None, description="Additional error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid gene identifier",
                "details": {
                    "invalid_genes": ["INVALID123"]
                }
            }
        }
