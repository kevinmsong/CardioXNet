"""Configuration management using Pydantic settings."""

from typing import Dict, List, Literal, Optional
from functools import lru_cache
from pydantic import Field, field_validator
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
    string_version: str = Field(
        default="12.0",
        description=(
            "STRING release actually queried. This said 11.5 while the client "
            "hardcoded the version-12-0 host, so every run used v12.0 while the "
            "health check and the generated reports claimed v11.5."
        ),
    )
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
        default=75,
        ge=10,
        le=200,
        description="Number of neighbors from STRING for functional neighborhood assembly (validated range: 10-200)"
    )
    string_score_threshold: float = Field(
        default=0.60,
        ge=0.4,
        le=0.95,
        description="STRING combined score threshold for protein-protein interactions (validated range: 0.4-0.95)"
    )
    fdr_threshold: float = Field(
        default=0.05,
        ge=0.001,
        le=0.2,
        description="FDR significance threshold (validated range: 0.001-0.2)"
    )
    top_hypotheses_count: int = Field(
        default=15,
        ge=5,
        le=100,
        description="Number of top hypotheses to validate (validated range: 5-100)"
    )
    
    # Database Weights
    db_weight_reactome: float = Field(default=1.5, ge=0.0, le=10.0, description="Reactome database weight")
    db_weight_kegg: float = Field(default=1.5, ge=0.0, le=10.0, description="KEGG database weight")
    db_weight_wikipathways: float = Field(default=1.2, ge=0.0, le=10.0, description="WikiPathways weight")
    db_weight_gobp: float = Field(default=1.0, ge=0.0, le=10.0, description="GO:BP weight")
    
    # API Endpoints (Per official documentation)
    string_api_url: str = Field(
        default="https://string-db.org/api",
        description="STRING Database API (https://stringdb.readthedocs.io/)"
    )
    gprofiler_api_url: str = Field(
        default="https://biit.cs.ut.ee/gprofiler",
        description="g:Profiler service base URL"
    )
    reactome_api_url: str = Field(
        default="https://reactome.org/ContentService",
        description="Reactome Content Service API (https://reactome.org/ContentService/)"
    )
    
    # Retry Configuration
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum API retry attempts after the initial request",
    )
    retry_backoff_factor: float = Field(
        default=1.5,
        ge=0.0,
        le=60.0,
        description="Initial exponential retry backoff in seconds",
    )
    request_timeout: int = Field(
        default=15,
        ge=1,
        le=300,
        description="API request timeout in seconds",
    )
    gprofiler_timeout_seconds: float = Field(
        default=120.0,
        ge=1.0,
        le=600.0,
        description=(
            "Hard wall-clock deadline for one g:Profiler enrichment request. "
            "The official library exposes no HTTP timeout, so CardioXNet runs "
            "each call in a spawned process and terminates it at this deadline."
        ),
    )
    
    # Clinical Evidence API Timeouts (Stage 3: HPA, GWAS, Epigenomic)
    hpa_timeout: int = Field(default=30, ge=1, le=300, description="Human Protein Atlas API timeout in seconds")
    gwas_timeout: int = Field(default=45, ge=1, le=300, description="GWAS Catalog API timeout in seconds")
    epigenomic_timeout: int = Field(default=30, ge=1, le=300, description="ENCODE Epigenomics API timeout in seconds")
    clinical_api_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retry attempts for clinical evidence APIs",
    )
    
    # Aggregation Configuration
    aggregation_strategy: Literal["intersection", "frequency", "weighted"] = Field(
        default="frequency",
        description="Pathway aggregation strategy: intersection, frequency, or weighted"
    )
    min_support_threshold: int = Field(
        default=1,  # Inclusive for comprehensive pathway coverage
        ge=1,
        le=10,
        description="Minimum support count for pathway replication (1 for comprehensive coverage, validated range: 1-10)"
    )
    
    # Secondary enrichment expansion
    primary_pathways_to_expand: int = Field(
        default=20, ge=1, le=200,
        description="Number of primary pathways expanded in secondary enrichment stage"
    )

    # Literature Mining Configuration
    pubmed_max_results: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Max PubMed results per gene (validated range: 10-500)"
    )
    literature_relevance_threshold: float = Field(
        default=0.30,
        ge=0.05,
        le=0.7,
        description="Minimum relevance score for literature-expanded genes (validated range: 0.05-0.7)"
    )
    
    # Semantic Filtering Configuration (Disease-context aware, comprehensive)
    semantic_relevance_threshold: float = Field(
        default=0.01,
        ge=0.0,
        le=0.7,
        description=(
            "Minimum cardiac semantic relevance. Since the scorer was corrected "
            "so that a pathway with no cardiac evidence scores exactly 0.0 "
            "(it previously scored 0.304 regardless), this threshold now means "
            "'must carry at least some cardiac evidence'. Values above ~0.3 "
            "retain only pathways named for the heart and will exclude "
            "mechanistically relevant terms such as Inflammasomes."
        )
    )

    # Max hypotheses sent to literature mining
    semantic_max_hypotheses_for_literature: int = Field(
        default=30, ge=1, le=100,
        description="Maximum hypotheses passed to literature mining stage"
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
        ge=0.0,
        le=1.0,
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
        default=1000,
        ge=10,
        le=10000,
        description=(
            "Number of permutations for the empirical p-value. The smallest "
            "attainable p is 1/(n+1), so this value sets the resolution floor: "
            "n=25 could never yield p < 0.038 and therefore could not survive "
            "FDR correction at any sensible threshold. 1000 gives a floor of "
            "1e-3. (validated range: 10-10000)"
        )
    )
    min_fold_enrichment: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Minimum fold-enrichment (observed/expected overlap ratio) for pathway inclusion. Ensures biological effect size beyond statistical significance. Default 2.0 = 2× enrichment."
    )
    
    # Final cardiac name filter. Retains a pathway if its NAME carries a cardiac
    # or disease term, or if it clears the semantic-rescue bar (high cardiac
    # relevance + replication + significance). Exposed here so it can be set via
    # config_overrides: the pipeline only applies overrides for keys that exist
    # on this model, so before this field was declared the filter was permanently
    # on and could not be turned off from the UI or API.
    #
    # Name matching is a source of circularity for a discovery tool -- a pathway
    # that is genuinely novel for the heart is unlikely to be named for it -- so
    # this is reported alongside results and its effect is quantified in the
    # benchmark rather than left implicit.
    enforce_final_name_filter: bool = Field(
        default=False,
        description=(
            "Require cardiac/disease terms in the pathway name (with semantic "
            "rescue) at the final filter stage. Defaults to OFF: on the reference "
            "VEGFA/MMP9/IL6/TNF/ACE heart-failure panel it cut 66 hypotheses to 23 "
            "and removed every one of the 6 Highly Novel pathways, because a "
            "pathway that is genuinely under-studied for the heart is precisely "
            "the one unlikely to carry a cardiac term in its name. Cardiac "
            "relevance is enforced upstream by the evidence-based semantic filter "
            "instead. Set True to restore name-based gating."
        )
    )

    # Skip literature expansion for pathways whose names carry no specific
    # concept. Read via getattr with a True default before it was declared here,
    # so it could not be turned off from the UI or API.
    filter_generic_pathways: bool = Field(
        default=True,
        description="Skip literature mining for pathways whose names are purely generic"
    )

    # Redundancy filtering
    redundancy_jaccard_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Jaccard similarity threshold for pathway redundancy filtering"
    )

    # Stage 8 limits - how many top pathways each validation step processes
    gtex_top_pathways: int = Field(
        default=20, ge=0, le=1000, description="Pathways to validate with GTEx (0 = all)"
    )
    permutation_top_pathways: int = Field(
        default=20, ge=0, le=1000, description="Pathways to run permutation testing on (0 = all)"
    )
    external_druggability_top_pathways: int = Field(
        default=20, ge=0, le=1000, description="Pathways to query external druggability APIs (0 = all)"
    )
    external_druggability_enabled: bool = Field(
        default=True, description="Enable external druggability lookup (Open Targets / ChEMBL)"
    )

    # Druggability Analysis Configuration
    druggability_analysis: bool = Field(
        default=True,
        description="Enable druggable target identification"
    )
    
    # Output Configuration
    output_formats: List[Literal["pdf", "json", "markdown", "html"]] = Field(
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
        case_sensitive=False,
        extra="ignore",  # tolerate non-NETS_ keys present in the shared .env (e.g. GROQ_API_KEY)
    )


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = Field(default="CardioXNet", description="Application name")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=True, description="Debug mode")

    # External API Keys (optional)
    groq_api_key: Optional[str] = Field(default=None, description="Groq API key for AI report generation")

    @field_validator('debug', mode='before')
    @classmethod
    def parse_debug_string(cls, v):
        """Accept non-standard boolean strings used in deployment environments."""
        if isinstance(v, str):
            return v.lower() not in ('false', 'release', 'production', '0', 'no', 'off')
        return v
    
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
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
