"""Pipeline configuration management for performance tuning."""

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


class PipelineMode(str, Enum):
    """Pipeline execution modes balancing speed vs accuracy."""
    
    ULTRA_FAST = "ultra_fast"  # <30s for 5 genes, minimal depth
    FAST = "fast"              # Quick results, lower precision
    BALANCED = "balanced"      # Default, good balance
    RIGOROUS = "rigorous"      # Maximum accuracy, slower


@dataclass
class PipelineConfig:
    """
    Configuration for pipeline execution.
    
    Controls performance/accuracy tradeoffs across all stages.
    """
    
    # Execution mode
    mode: PipelineMode = PipelineMode.BALANCED
    
    # Permutation testing settings
    min_permutations: int = 100
    max_permutations: int = 500
    adaptive_permutation: bool = True
    
    # Caching settings
    enable_cache: bool = True
    cache_ttl_hours: int = 24
    cache_max_size_mb: int = 500
    
    # Parallel execution settings
    enable_parallel: bool = True
    max_workers: int = 4
    task_timeout_seconds: int = 300
    
    # Filtering settings
    min_pathway_size: int = 5
    max_pathway_size: int = 500
    fdr_threshold: float = 0.01
    min_cardiac_expression_ratio: float = 0.3
    
    # Performance monitoring
    enable_profiling: bool = True
    log_cache_stats: bool = True
    
    @classmethod
    def from_mode(cls, mode: PipelineMode) -> 'PipelineConfig':
        """
        Create configuration from mode preset.
        
        Args:
            mode: Pipeline execution mode
            
        Returns:
            PipelineConfig with mode-specific settings
        """
        if mode == PipelineMode.ULTRA_FAST:
            return cls(
                mode=mode,
                min_permutations=25,
                max_permutations=50,
                adaptive_permutation=False,
                enable_cache=True,
                cache_ttl_hours=24,
                enable_parallel=True,
                max_workers=12,  # Maximum parallelization
                fdr_threshold=0.10,  # Very permissive
                min_cardiac_expression_ratio=0.1  # Minimal threshold for speed
            )
        
        elif mode == PipelineMode.FAST:
            return cls(
                mode=mode,
                min_permutations=50,
                max_permutations=100,
                adaptive_permutation=True,
                enable_cache=True,
                cache_ttl_hours=24,
                enable_parallel=True,
                max_workers=8,
                fdr_threshold=0.05,
                min_cardiac_expression_ratio=0.2
            )
        
        elif mode == PipelineMode.BALANCED:
            return cls(
                mode=mode,
                min_permutations=100,
                max_permutations=500,
                adaptive_permutation=True,
                enable_cache=True,
                cache_ttl_hours=24,
                enable_parallel=True,
                max_workers=6,  # Increased for comprehensive coverage
                fdr_threshold=0.05,  # More inclusive for broader discovery
                min_cardiac_expression_ratio=0.30  # More permissive
            )
        
        elif mode == PipelineMode.RIGOROUS:
            return cls(
                mode=mode,
                min_permutations=500,
                max_permutations=1000,
                adaptive_permutation=False,  # Use fixed permutations for rigor
                enable_cache=True,
                cache_ttl_hours=24,
                enable_parallel=True,
                max_workers=4,  # Parallel but stable
                fdr_threshold=0.01,  # Stringent but not overly restrictive
                min_cardiac_expression_ratio=0.30  # Comprehensive coverage
            )
        
        else:
            logger.warning(f"Unknown mode: {mode}, using BALANCED")
            return cls.from_mode(PipelineMode.BALANCED)
    
    def validate(self) -> bool:
        """
        Validate configuration parameters.
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        if self.min_permutations < 10:
            raise ValueError("min_permutations must be >= 10")
        
        if self.max_permutations < self.min_permutations:
            raise ValueError("max_permutations must be >= min_permutations")
        
        if self.max_permutations > 10000:
            raise ValueError("max_permutations must be <= 10000")
        
        if self.max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        
        if self.max_workers > 16:
            raise ValueError("max_workers must be <= 16")
        
        if not 0 < self.fdr_threshold < 1:
            raise ValueError("fdr_threshold must be between 0 and 1")
        
        if not 0 < self.min_cardiac_expression_ratio <= 1:
            raise ValueError("min_cardiac_expression_ratio must be between 0 and 1")
        
        if self.cache_ttl_hours < 1:
            raise ValueError("cache_ttl_hours must be >= 1")
        
        if self.cache_max_size_mb < 10:
            raise ValueError("cache_max_size_mb must be >= 10")
        
        return True
    
    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'mode': self.mode.value,
            'permutation': {
                'min': self.min_permutations,
                'max': self.max_permutations,
                'adaptive': self.adaptive_permutation
            },
            'caching': {
                'enabled': self.enable_cache,
                'ttl_hours': self.cache_ttl_hours,
                'max_size_mb': self.cache_max_size_mb
            },
            'parallel': {
                'enabled': self.enable_parallel,
                'max_workers': self.max_workers,
                'timeout_seconds': self.task_timeout_seconds
            },
            'filtering': {
                'min_pathway_size': self.min_pathway_size,
                'max_pathway_size': self.max_pathway_size,
                'fdr_threshold': self.fdr_threshold,
                'min_cardiac_expression_ratio': self.min_cardiac_expression_ratio
            },
            'monitoring': {
                'profiling_enabled': self.enable_profiling,
                'log_cache_stats': self.log_cache_stats
            }
        }
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"PipelineConfig(mode={self.mode.value}, "
            f"permutations={self.min_permutations}-{self.max_permutations}, "
            f"cache={self.enable_cache}, "
            f"parallel={self.enable_parallel})"
        )


def get_default_config() -> PipelineConfig:
    """
    Get default pipeline configuration (BALANCED mode).
    
    Returns:
        Default PipelineConfig
    """
    return PipelineConfig.from_mode(PipelineMode.BALANCED)
