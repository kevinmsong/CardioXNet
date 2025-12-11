"""Gene-related data models."""

from typing import Optional
from pydantic import BaseModel, Field


class GeneInfo(BaseModel):
    """Information about a validated gene."""
    
    input_id: str = Field(..., description="Original input identifier")
    entrez_id: str = Field(..., description="NCBI Entrez Gene ID")
    hgnc_id: Optional[str] = Field(None, description="HGNC ID")
    symbol: str = Field(..., description="Official gene symbol")
    species: str = Field(default="Homo sapiens", description="Species name")
    
    class Config:
        json_schema_extra = {
            "example": {
                "input_id": "TP53",
                "entrez_id": "7157",
                "hgnc_id": "HGNC:11998",
                "symbol": "TP53",
                "species": "Homo sapiens"
            }
        }
