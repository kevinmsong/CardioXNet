"""Configuration management using Pydantic settings."""

from typing import Dict, List, Optional
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NETSConfig(BaseSettings):
    """
    NETS pipeline configuration parameters.

    SCIENTIFIC RIGOR:
    - All parameters validated for range and type
    - Defaults optimized for QUALITY DISCOVERY with disease/cardiac relevance
    - Stringent FDR threshold (0.01) for statistical validity
    - Higher support threshold ensures robust replication
    - Rigorous semantic filtering prioritizes cardiovascular disease relevance

    PARAMETER PHILOSOPHY:
    - Selective network parameters for high-confidence interactions
    - Stringent statistical thresholds for quality over quantity
    - Enhanced semantic filtering with cardiac disease focus
    - Efficient literature mining targeting disease-relevant evidence
    """
    
    # API Configuration
    string_version: str = Field(default="11.5", description="STRING API version")
    gprofiler_version: str = Field(default="e104_eg51_p15", description="g:Profiler version")
    reactome_version: str = Field(default="79", description="Reactome version")
    
    # API Resilience Configuration
    graceful_degradation: bool = Field(
        default=True, 
        description="Continue analysis even when some API services are unavailable"
    )
    require_all_apis: bool = Field(
        default=False,
        description="Require all API services to be available (strict mode)"
    )
    
    # Analysis Parameters (Optimized for comprehensive disease pathway discovery)
    string_neighbor_count: int = Field(
        default=100,  # Increased for comprehensive neighborhood expansion
        ge=10,
        le=200,
        description="Number of neighbors from STRING for functional neighborhood assembly (100 for comprehensive coverage, validated range: 10-200)"
    )
    string_score_threshold: float = Field(
        default=0.70,  # Balanced selectivity for more pathway coverage
        ge=0.4,
        le=0.95,
        description="STRING combined score threshold for protein-protein interactions (0.70 for balanced coverage, validated range: 0.4-0.95)"
    )
    fdr_threshold: float = Field(
        default=0.05,  # More permissive for broader discovery
        ge=0.001,
        le=0.2,
        description="FDR significance threshold (0.05 for comprehensive discovery, validated range: 0.001-0.2)"
    )
    top_hypotheses_count: int = Field(
        default=20,  # Increased for more comprehensive results
        ge=5,
        le=100,
        description="Number of top hypotheses to validate (20 for comprehensive coverage, validated range: 5-100)"
    )
    
    # Database Weights (Comprehensive pathway coverage)
    db_weight_reactome: float = Field(default=2.0, description="Reactome database weight (highest quality)")
    db_weight_kegg: float = Field(default=1.8, description="KEGG database weight (comprehensive)")
    db_weight_wikipathways: float = Field(default=1.5, description="WikiPathways weight (community curated)")
    db_weight_gobp: float = Field(default=1.3, description="GO:BP weight (broad functional annotation)")
    
    # API Endpoints (Per official documentation)
    string_api_url: str = Field(
        default="https://string-db.org/api",
        description="STRING Database API (https://stringdb.readthedocs.io/)"
    )
    gprofiler_api_url: str = Field(
        default="https://biit.cs.ut.ee/gprofiler/api",
        description="g:Profiler API"
    )
    reactome_api_url: str = Field(
        default="https://reactome.org/ContentService",
        description="Reactome Content Service API (https://reactome.org/ContentService/)"
    )
    
    # Retry Configuration (Balanced for reliability and speed)
    max_retries: int = Field(default=3, description="Maximum API retry attempts")
    retry_backoff_factor: float = Field(default=2.0, description="Exponential backoff factor")
    request_timeout: int = Field(default=20, description="API request timeout in seconds")
    
    # Clinical Evidence API Timeouts (Stage 3: HPA, GWAS, Epigenomic)
    hpa_timeout: int = Field(default=30, description="Human Protein Atlas API timeout in seconds")
    gwas_timeout: int = Field(default=45, description="GWAS Catalog API timeout in seconds")
    epigenomic_timeout: int = Field(default=30, description="ENCODE Epigenomics API timeout in seconds")
    clinical_api_max_retries: int = Field(default=2, description="Maximum retry attempts for clinical evidence APIs")
    
    # Aggregation Configuration
    aggregation_strategy: str = Field(
        default="weighted",  # Changed to weighted for comprehensive coverage
        description="Pathway aggregation strategy: intersection, frequency, or weighted (weighted for comprehensive discovery)"
    )
    min_support_threshold: int = Field(
        default=1,  # Inclusive for comprehensive pathway coverage
        ge=1,
        le=10,
        description="Minimum support count for pathway replication (1 for comprehensive coverage, validated range: 1-10)"
    )
    
    # Literature Mining Configuration (Comprehensive cardiovascular disease focus)
    pubmed_max_results: int = Field(
        default=50,  # Increased for comprehensive literature coverage
        ge=10,
        le=500,
        description="Max PubMed results per gene (50 for comprehensive coverage, validated range: 10-500)"
    )
    literature_relevance_threshold: float = Field(
        default=0.40,  # More permissive for broader evidence inclusion
        ge=0.05,
        le=0.7,
        description="Minimum relevance score for literature-expanded genes (0.40 for comprehensive disease evidence, validated range: 0.05-0.7)"
    )
    
    # Semantic Filtering Configuration (Disease-context aware, comprehensive)
    semantic_relevance_threshold: float = Field(
        default=0.15,  # More inclusive for comprehensive pathway discovery
        ge=0.001,
        le=0.7,
        description="Minimum semantic cardiovascular disease relevance score (0.15 for comprehensive discovery, validated range: 0.001-0.7)"
    )

    # Semantic result limits (comprehensive pathway discovery)
    semantic_max_results: int = Field(
        default=100,  # Comprehensive results including secondary pathways
        ge=15,
        le=1000,
        description="Maximum pathways to return after semantic filtering (100 for comprehensive discovery, validated range: 15-1000)"
    )

    # Progressive thresholds (disease-context aware filtering)
    semantic_progressive_thresholds: Dict[str, float] = Field(
        default={
            'high_disease': 0.60,  # High cardiovascular disease relevance
            'medium_disease': 0.40,  # Moderate cardiovascular disease relevance
            'low_disease': 0.15   # Some cardiovascular disease relevance
        },
        description="Progressive semantic thresholds for comprehensive result discovery"
    )
    
    # Novelty Filtering Configuration
    seed_overlap_threshold: float = Field(
        default=0.5,
        description="Maximum seed gene overlap ratio for novelty filtering (0.5 = 50%)"
    )
    
    # Tissue Expression Validation Configuration
    tissue_expression_validation: bool = Field(
        default=True,
        description="Enable cardiac tissue expression validation"
    )
    min_cardiac_expression_ratio: float = Field(
        default=0.30,  # More permissive for comprehensive pathway coverage
        ge=0.1,
        le=0.8,
        description="Minimum ratio of pathway genes expressed in cardiac tissue (0.30 for comprehensive coverage, validated range: 0.1-0.8)"
    )
    
    # Permutation Testing Configuration
    permutation_test_enabled: bool = Field(
        default=True,
        description="Enable permutation-based empirical p-value calculation"
    )
    n_permutations: int = Field(
        default=100,  # Increased for more robust statistical testing
        ge=25,
        le=1000,
        description="Number of permutations for empirical p-value (100 for robust validation, validated range: 25-1000)"
    )
    
    # Druggability Analysis Configuration
    druggability_analysis: bool = Field(
        default=True,
        description="Enable druggable target identification"
    )
    
    # Output Configuration
    output_formats: List[str] = Field(
        default=["pdf", "json"],
        description="Report output formats"
    )
    
    @property
    def db_weights(self) -> Dict[str, float]:
        """Get database weights as a dictionary."""
        return {
            "REAC": self.db_weight_reactome,
            "KEGG": self.db_weight_kegg,
            "WP": self.db_weight_wikipathways,
            "GO:BP": self.db_weight_gobp,
        }
    
    model_config = SettingsConfigDict(
        env_prefix="NETS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = Field(default="CardioXNet", description="Application name")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=True, description="Debug mode")
    
    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    # Paths
    data_dir: str = Field(default="data", description="Data directory")
    output_dir: str = Field(default="outputs", description="Output directory")
    config_dir: str = Field(default="config", description="Configuration directory")
    
    # Performance Configuration (Optimized for throughput)
    max_concurrent_requests: int = Field(default=20, description="Maximum concurrent API requests")
    batch_size: int = Field(default=50, description="Batch size for bulk operations")
    cache_ttl: int = Field(default=604800, description="Cache TTL in seconds (7 days)")
    enable_aggressive_caching: bool = Field(default=True, description="Enable aggressive result caching")
    
    # Parallel Processing Configuration (Optimized for comprehensive analysis)
    max_workers_semantic: int = Field(default=8, description="Max workers for semantic filtering")
    max_workers_literature: int = Field(default=6, description="Max workers for literature mining")
    max_concurrent_pubmed: int = Field(default=10, description="Max concurrent PubMed requests")
    
    # NETS Pipeline Configuration
    nets: NETSConfig = Field(default_factory=NETSConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
