"""Result data models for pipeline stages."""

from typing import List, Dict, Optional, Set
from pydantic import BaseModel, Field
from .gene import GeneInfo
from .pathway import PathwayEntry, ScoredPathwayEntry, AggregatedPathway, ScoredPathway


class ValidationResult(BaseModel):
    """Result of gene validation."""
    
    valid_genes: List[GeneInfo] = Field(default_factory=list, description="Successfully validated genes")
    invalid_genes: List[str] = Field(default_factory=list, description="Failed validation")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid_genes": [
                    {
                        "input_id": "TP53",
                        "entrez_id": "7157",
                        "hgnc_id": "HGNC:11998",
                        "symbol": "TP53",
                        "species": "Homo sapiens"
                    }
                ],
                "invalid_genes": ["INVALID123"],
                "warnings": ["Gene XYZ has multiple mappings"]
            }
        }


class FunctionalNeighborhood(BaseModel):
    """Functional neighborhood assembly result."""
    
    seed_genes: List[GeneInfo] = Field(default_factory=list, description="Original seed genes")
    neighbors: List[GeneInfo] = Field(default_factory=list, description="Neighbor genes")
    interactions: List[Dict] = Field(default_factory=list, description="Protein-protein interactions")
    size: int = Field(..., description="Total size of F_N")
    contributions: Dict[str, int] = Field(
        default_factory=dict,
        description="Contribution count per seed gene"
    )
    sources: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Source databases per gene"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "seed_genes": [{"input_id": "TP53", "entrez_id": "7157", "symbol": "TP53"}],
                "neighbors": [{"input_id": "MDM2", "entrez_id": "4193", "symbol": "MDM2"}],
                "size": 75,
                "contributions": {"7157": 50, "4193": 25},
                "sources": {"7157": ["GeneMANIA", "STRING"]}
            }
        }


class EnrichmentResult(BaseModel):
    """Pathway enrichment result."""
    
    pathways: List[PathwayEntry] = Field(default_factory=list, description="Enriched pathways")
    total_count: int = Field(..., description="Total number of pathways")
    databases_queried: List[str] = Field(default_factory=list, description="Databases queried")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pathways": [
                    {
                        "pathway_id": "REAC:R-HSA-5663202",
                        "pathway_name": "Signal transduction",
                        "source_db": "REAC",
                        "p_value": 0.0001,
                        "p_adj": 0.005,
                        "evidence_count": 15,
                        "evidence_genes": ["TP53"]
                    }
                ],
                "total_count": 1,
                "databases_queried": ["REAC", "KEGG", "WP", "GO:BP"]
            }
        }


class PrimaryTriageResult(BaseModel):
    """Primary pathway triage result with NES scoring."""
    
    primary_pathways: List[ScoredPathwayEntry] = Field(
        default_factory=list,
        description="Novel candidate pathways with NES scores"
    )
    known_pathways: List[PathwayEntry] = Field(
        default_factory=list,
        description="Filtered out known pathways"
    )
    filtered_count: int = Field(..., description="Number of pathways filtered")
    filtering_contributions: Dict[str, int] = Field(
        default_factory=dict,
        description="Filtering contribution per seed gene"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "primary_pathways": [
                    {
                        "pathway_id": "REAC:R-HSA-5663202",
                        "pathway_name": "Novel pathway",
                        "source_db": "REAC",
                        "p_value": 0.0001,
                        "p_adj": 0.005,
                        "evidence_count": 15,
                        "evidence_genes": ["TP53"],
                        "preliminary_nes": 4.52
                    }
                ],
                "known_pathways": [],
                "filtered_count": 5,
                "filtering_contributions": {"7157": 3, "4193": 2}
            }
        }


class LiteratureExpansion(BaseModel):
    """Literature-based gene expansion result."""
    
    original_genes: List[str] = Field(default_factory=list, description="Original pathway genes")
    expanded_genes: List[str] = Field(default_factory=list, description="Literature-expanded genes")
    literature_evidence: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="PMIDs per gene"
    )
    cardiac_relevance_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Relevance score per gene"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "original_genes": ["TP53", "MDM2"],
                "expanded_genes": ["CDKN1A", "BAX"],
                "literature_evidence": {
                    "CDKN1A": ["12345678", "23456789"]
                },
                "cardiac_relevance_scores": {
                    "CDKN1A": 0.85,
                    "BAX": 0.72
                }
            }
        }


class SecondaryPathwaySet(BaseModel):
    """Secondary pathways discovered from a primary pathway."""
    
    primary_pathway_id: str = Field(..., description="Source primary pathway ID")
    primary_pathway_name: str = Field(..., description="Source primary pathway name")
    secondary_pathways: List[ScoredPathwayEntry] = Field(
        default_factory=list,
        description="Scored secondary pathways"
    )
    member_genes_used: List[str] = Field(default_factory=list, description="Member genes used")
    literature_expanded_genes: List[str] = Field(
        default_factory=list,
        description="Genes added via literature"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "primary_pathway_id": "REAC:R-HSA-5663202",
                "primary_pathway_name": "Signal transduction",
                "secondary_pathways": [],
                "member_genes_used": ["TP53", "MDM2"],
                "literature_expanded_genes": ["CDKN1A"]
            }
        }


class GeneTriageResult(BaseModel):
    """Result from running triage module for a single gene."""
    
    gene_id: str = Field(..., description="Gene identifier")
    gene_symbol: str = Field(..., description="Gene symbol")
    literature_expanded_genes: List[str] = Field(
        default_factory=list,
        description="Genes added through literature expansion"
    )
    enriched_pathways: List[ScoredPathwayEntry] = Field(
        default_factory=list,
        description="Pathways discovered for this gene"
    )
    literature_evidence: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Literature evidence (gene -> PMIDs)"
    )
    pmid_count: int = Field(default=0, description="Number of literature citations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gene_id": "TP53",
                "gene_symbol": "TP53",
                "literature_expanded_genes": ["MDM2", "CDKN1A", "BAX"],
                "enriched_pathways": [],
                "literature_evidence": {"MDM2": ["12345678", "23456789"]},
                "pmid_count": 2
            }
        }


class SecondaryTriageResult(BaseModel):
    """Secondary pathway discovery result using gene union approach."""
    
    union_genes: List[str] = Field(
        default_factory=list,
        description="All unique genes from union across primaries"
    )
    gene_triage_results: List[GeneTriageResult] = Field(
        default_factory=list,
        description="Triage result per union gene"
    )
    aggregated_pathways: List[ScoredPathwayEntry] = Field(
        default_factory=list,
        description="All pathways aggregated across genes"
    )
    pathway_support: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Pathway ID to supporting gene IDs"
    )
    pathway_frequency: Dict[str, int] = Field(
        default_factory=dict,
        description="Pathway ID to count of genes that found it"
    )
    total_secondary_count: int = Field(..., description="Total secondary pathways")
    literature_expansion_stats: Dict[str, int] = Field(
        default_factory=dict,
        description="Statistics on literature expansion"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "union_genes": ["TP53", "NKX2-5", "GATA4"],
                "gene_triage_results": [],
                "aggregated_pathways": [],
                "pathway_support": {"REAC:R-HSA-1234": ["TP53", "NKX2-5"]},
                "pathway_frequency": {"REAC:R-HSA-1234": 2},
                "total_secondary_count": 0,
                "literature_expansion_stats": {
                    "total_genes_added": 25,
                    "total_pmids": 150,
                    "genes_processed": 3
                }
            }
        }


class FinalPathwayResult(BaseModel):
    """Final aggregated pathway result."""
    
    final_pathways: List[AggregatedPathway] = Field(
        default_factory=list,
        description="Aggregated final pathways"
    )
    aggregation_strategy: str = Field(..., description="Strategy used for aggregation")
    total_count: int = Field(..., description="Total final pathways")
    min_support_threshold: int = Field(..., description="Minimum support threshold used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "final_pathways": [],
                "aggregation_strategy": "intersection",
                "total_count": 0,
                "min_support_threshold": 2
            }
        }


class ScoredHypotheses(BaseModel):
    """Final scored hypotheses."""
    
    hypotheses: List[ScoredPathway] = Field(default_factory=list, description="Ranked hypotheses")
    total_count: int = Field(..., description="Total number of hypotheses")
    
    class Config:
        json_schema_extra = {
            "example": {
                "hypotheses": [],
                "total_count": 0
            }
        }


class Citation(BaseModel):
    """Literature citation."""
    
    pmid: str = Field(..., description="PubMed ID")
    title: str = Field(..., description="Paper title")
    authors: str = Field(..., description="Author list")
    year: int = Field(..., description="Publication year")
    relevance_score: float = Field(..., description="Relevance score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pmid": "12345678",
                "title": "Cardiovascular disease mechanisms",
                "authors": "Smith J, Doe J",
                "year": 2023,
                "relevance_score": 0.85
            }
        }


class LiteratureEvidence(BaseModel):
    """Literature evidence for hypotheses."""
    
    hypothesis_citations: Dict[str, List[Citation]] = Field(
        default_factory=dict,
        description="Citations per pathway ID"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "hypothesis_citations": {
                    "REAC:R-HSA-5663202": [
                        {
                            "pmid": "12345678",
                            "title": "Cardiovascular disease",
                            "authors": "Smith J",
                            "year": 2023,
                            "relevance_score": 0.85
                        }
                    ]
                }
            }
        }


class KeyNode(BaseModel):
    """Key mediating node in network."""
    
    gene_id: str = Field(..., description="Gene identifier")
    gene_symbol: str = Field(..., description="Gene symbol")
    betweenness_centrality: float = Field(..., description="Betweenness centrality score")
    connects_to_seeds: List[str] = Field(default_factory=list, description="Connected seed genes")
    connects_to_pathway: List[str] = Field(default_factory=list, description="Connected pathway genes")
    role: str = Field(..., description="Node role: mediator, hub, or bridge")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gene_id": "4193",
                "gene_symbol": "MDM2",
                "betweenness_centrality": 0.45,
                "connects_to_seeds": ["TP53"],
                "connects_to_pathway": ["CDKN1A", "BAX"],
                "role": "mediator"
            }
        }


class PathwayLineage(BaseModel):
    """Pathway discovery lineage."""
    
    seed_genes: List[str] = Field(default_factory=list, description="Seed genes")
    fn_genes: List[str] = Field(default_factory=list, description="Functional neighborhood genes")
    primary_pathways: List[str] = Field(default_factory=list, description="Primary pathway IDs")
    primary_pathway_genes: List[str] = Field(default_factory=list, description="Primary pathway genes")
    final_pathway_genes: List[str] = Field(default_factory=list, description="Final pathway genes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "seed_genes": ["TP53"],
                "fn_genes": ["MDM2", "CDKN1A"],
                "primary_pathways": ["REAC:R-HSA-5663202"],
                "primary_pathway_genes": ["TP53", "MDM2"],
                "final_pathway_genes": ["CDKN1A", "BAX"]
            }
        }


class NetworkAnalysis(BaseModel):
    """Network topology analysis result."""
    
    lineage: PathwayLineage = Field(..., description="Pathway lineage")
    key_nodes: List[KeyNode] = Field(default_factory=list, description="Key mediating nodes")
    seed_specific_connections: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Seed-specific connections"
    )
    shared_connections: List[str] = Field(default_factory=list, description="Shared connections")
    network_data: Dict = Field(default_factory=dict, description="Network visualization data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "lineage": {
                    "seed_genes": ["TP53"],
                    "fn_genes": ["MDM2"],
                    "primary_pathways": ["REAC:R-HSA-5663202"],
                    "primary_pathway_genes": ["TP53"],
                    "final_pathway_genes": ["CDKN1A"]
                },
                "key_nodes": [],
                "seed_specific_connections": {"TP53": ["MDM2"]},
                "shared_connections": [],
                "network_data": {}
            }
        }


class TopologyResult(BaseModel):
    """Topology analysis for multiple hypotheses."""
    
    hypothesis_networks: Dict[str, NetworkAnalysis] = Field(
        default_factory=dict,
        description="Network analysis per pathway ID"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "hypothesis_networks": {
                    "REAC:R-HSA-5663202": {
                        "lineage": {
                            "seed_genes": ["TP53"],
                            "fn_genes": ["MDM2"],
                            "primary_pathways": [],
                            "primary_pathway_genes": [],
                            "final_pathway_genes": []
                        },
                        "key_nodes": [],
                        "seed_specific_connections": {},
                        "shared_connections": [],
                        "network_data": {}
                    }
                }
            }
        }
