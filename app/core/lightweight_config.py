"""Lightweight, fast configuration - all features required, no fallbacks."""

from typing import Dict, List
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FastNETSConfig(BaseSettings):
    """
    Lightweight NETS configuration - optimized for speed.
    ALL features are required, no optional analyses, no fallbacks.
    """
    
    # API Configuration
    string_version: str = Field(default="11.5")
    gprofiler_version: str = Field(default="e104_eg51_p15")
    reactome_version: str = Field(default="79")
    
    # Core Analysis Parameters - Optimized for speed
    string_neighbor_count: int = Field(default=50, ge=10, le=200)  # Reduced for speed
    string_score_threshold: float = Field(default=0.70, ge=0.4, le=0.95)
    fdr_threshold: float = Field(default=0.05, ge=0.001, le=0.2)
    top_hypotheses_count: int = Field(default=15, ge=5, le=100)  # Reduced for speed
    
    # Database Weights
    db_weight_reactome: float = Field(default=2.0)
    db_weight_kegg: float = Field(default=1.8)
    db_weight_wikipathways: float = Field(default=1.5)
    db_weight_gobp: float = Field(default=1.3)
    
    # API Endpoints
    string_api_url: str = Field(default="https://string-db.org/api")
    gprofiler_api_url: str = Field(default="https://biit.cs.ut.ee/gprofiler/api")
    reactome_api_url: str = Field(default="https://reactome.org/ContentService")
    
    # Fast Retry Configuration - Fail fast
    max_retries: int = Field(default=2)  # Reduced retries
    retry_backoff_factor: float = Field(default=1.5)  # Faster backoff
    request_timeout: int = Field(default=15)  # Shorter timeout
    
    # Clinical Evidence API Timeouts - Optimized
    hpa_timeout: int = Field(default=20)  # Reduced
    gwas_timeout: int = Field(default=30)  # Reduced
    epigenomic_timeout: int = Field(default=20)  # Reduced
    clinical_api_max_retries: int = Field(default=1)  # Fail faster
    
    # Aggregation
    aggregation_strategy: str = Field(default="weighted")
    min_support_threshold: int = Field(default=1, ge=1, le=10)
    
    # Literature Mining - Optimized
    pubmed_max_results: int = Field(default=30, ge=10, le=500)  # Reduced for speed
    literature_relevance_threshold: float = Field(default=0.40, ge=0.05, le=0.7)
    
    # Semantic Filtering - Optimized
    semantic_relevance_threshold: float = Field(default=0.15, ge=0.001, le=0.7)
    semantic_max_results: int = Field(default=50, ge=15, le=1000)  # Reduced for speed
    semantic_progressive_thresholds: Dict[str, float] = Field(
        default={
            'high_disease': 0.60,
            'medium_disease': 0.40,
            'low_disease': 0.15
        }
    )
    
    # Novelty Filtering
    seed_overlap_threshold: float = Field(default=0.5)
    
    # ALL features are REQUIRED - no optional flags
    min_cardiac_expression_ratio: float = Field(default=0.30, ge=0.1, le=0.8)
    n_permutations: int = Field(default=50, ge=25, le=1000)  # Reduced for speed
    
    # Output
    output_formats: List[str] = Field(default=["json"])  # JSON only for speed
    
    @property
    def db_weights(self) -> Dict[str, float]:
        """Get database weights."""
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


class FastSettings(BaseSettings):
    """Lightweight application settings - optimized for speed."""
    
    # Application
    app_name: str = Field(default="CardioXNet")
    environment: str = Field(default="production")  # Production mode
    debug: bool = Field(default=False)  # No debug overhead
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )
    
    # Logging - Minimal
    log_level: str = Field(default="WARNING")  # Less logging overhead
    log_format: str = Field(
        default="%(levelname)s - %(message)s"  # Minimal format
    )
    
    # Paths
    data_dir: str = Field(default="data")
    output_dir: str = Field(default="outputs")
    config_dir: str = Field(default="config")
    
    # Performance - Optimized for speed
    max_concurrent_requests: int = Field(default=30)  # Increased parallelism
    batch_size: int = Field(default=100)  # Larger batches
    cache_ttl: int = Field(default=3600)  # Shorter cache for freshness
    
    # Parallel Processing - Max performance
    max_workers_semantic: int = Field(default=12)  # Increased
    max_workers_literature: int = Field(default=10)  # Increased
    max_concurrent_pubmed: int = Field(default=15)  # Increased
    
    # NETS Pipeline
    nets: FastNETSConfig = Field(default_factory=FastNETSConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


@lru_cache()
def get_fast_settings() -> FastSettings:
    """Get cached fast settings instance."""
    return FastSettings()
