"""Modular CardioXNet pipeline orchestrator."""

import logging
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from collections import defaultdict

from app.core.pipeline_stage import PipelineStage, ParallelStageGroup
from app.core.service_registry import get_service, register_service
from app.services.pipeline_stages import (
    InputValidationStage,
    FunctionalNeighborhoodStage,
    PrimaryPathwayStage,
    SecondaryPathwayStage,
    PathwayAggregationStage,
    ScoringStage,
    SemanticFilteringStage,
    LiteratureMiningStage,
    TopologyAnalysisStage,
    NESSrescoringStage,
    DruggabilityAnalysisStage,
    PermutationTestingStage,
    TissueExpressionStage,
    ReportGenerationStage
)

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when pipeline execution fails."""
    pass


class ModularCardioXNetPipeline:
    """
    Modular pipeline orchestrator using composable stages.
    
    This replaces the monolithic CardioXNetPipeline with a flexible,
    stage-based architecture that supports:
    - Lazy loading of services
    - All stages are required (no optional stages)
    - Parallel execution where possible
    - Easy extension and customization
    """
    
    def __init__(self, analysis_id: Optional[str] = None, config_overrides: Optional[Dict] = None):
        """
        Initialize modular pipeline.
        
        Args:
            analysis_id: Unique analysis identifier (auto-generated if not provided)
            config_overrides: Configuration parameter overrides
        """
        self.analysis_id = analysis_id or self._generate_analysis_id()
        self.config_overrides = config_overrides or {}
        self.progress_callback = None
        
        # Initialize stage registry
        self._stages = self._create_stages()
        self._stage_dependencies = self._build_dependency_graph()
        
        # Pipeline state
        self.results = {}
        self.warnings = []
        
        logger.info(f"Modular CardioXNetPipeline initialized (ID: {self.analysis_id})")
    
    def _create_stages(self) -> Dict[str, PipelineStage]:
        """Create and configure all pipeline stages."""
        stages = {}
        
        # Core stages
        stages["input_validation"] = InputValidationStage()
        stages["functional_neighborhood"] = FunctionalNeighborhoodStage()
        stages["primary_pathway"] = PrimaryPathwayStage()
        stages["secondary_pathway"] = SecondaryPathwayStage()
        stages["pathway_aggregation"] = PathwayAggregationStage()
        stages["nes_scoring"] = ScoringStage()
        stages["semantic_filtering"] = SemanticFilteringStage()
        stages["literature_mining"] = LiteratureMiningStage()
        stages["topology_analysis"] = TopologyAnalysisStage()
        stages["nes_rescoring"] = NESSrescoringStage()
        stages["druggability_analysis"] = DruggabilityAnalysisStage()
        stages["permutation_testing"] = PermutationTestingStage()
        stages["tissue_expression"] = TissueExpressionStage()
        stages["report_generation"] = ReportGenerationStage()
        
        # Configure stages with overrides
        for stage in stages.values():
            if hasattr(stage, 'config'):
                stage.config.update(self.config_overrides)
        
        return stages
    
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph for stage execution ordering."""
        graph = defaultdict(list)
        for stage_name, stage in self._stages.items():
            for dep in stage.dependencies:
                graph[dep].append(stage_name)
        return dict(graph)
    
    def _get_execution_order(self) -> List[str]:
        """Get stages in topological execution order."""
        # Simple topological sort for now
        # In a more complex implementation, we'd use a proper topological sort
        return [
            "input_validation",
            "functional_neighborhood", 
            "primary_pathway",
            "secondary_pathway",
            "pathway_aggregation",
            "nes_scoring",
            "semantic_filtering",
            "literature_mining",
            "topology_analysis",
            "nes_rescoring",
            "druggability_analysis",
            "permutation_testing",
            "tissue_expression",
            "report_generation"
        ]
    
    async def run(
        self,
        seed_genes: List[str],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Run complete modular pipeline.
        
        Args:
            seed_genes: List of seed gene identifiers
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with all pipeline results
        """
        self.progress_callback = progress_callback
        
        # Start timing
        import time
        pipeline_start_time = time.time()
        
        logger.info(
            f"Starting modular NETS pipeline analysis (ID: {self.analysis_id}) "
            f"with {len(seed_genes)} seed genes"
        )
        print(f"\n🚀 [TIMING] Modular Pipeline START at {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # Initialize context with input
            context = {
                "seed_genes": seed_genes,
                "analysis_id": self.analysis_id,
                "config": self.config_overrides
            }
            
            # Execute stages in order
            execution_order = self._get_execution_order()
            total_stages = len(execution_order)
            
            for i, stage_name in enumerate(execution_order):
                stage = self._stages[stage_name]
                progress = int((i / total_stages) * 100)
                
                await self._update_progress(
                    f"Stage {stage_name}", 
                    progress, 
                    f"Executing {stage_name}"
                )
                
                stage_start_time = time.time()
                result = await stage.run(context)
                elapsed = time.time() - stage_start_time
                
                # Store result in context
                context[stage_name] = {
                    "status": result.status.value,
                    "data": result.data,
                    "metadata": result.metadata,
                    "error": result.error
                }
                
                if result.status == "failed":
                    raise PipelineError(f"Required stage {stage_name} failed: {result.error}")
                
                print(f"⏱️  [TIMING] {stage_name} completed in {elapsed:.2f}s")
            
            # Collect final results
            final_results = {
                "analysis_id": self.analysis_id,
                "stages": context,
                "warnings": self.warnings,
                "total_time": time.time() - pipeline_start_time
            }
            
            logger.info(f"Modular pipeline completed successfully in {final_results['total_time']:.2f}s")
            return final_results
            
        except Exception as e:
            logger.error(f"Modular pipeline failed: {str(e)}", exc_info=True)
            raise PipelineError(f"Pipeline execution failed: {str(e)}")
    
    async def _update_progress(self, stage: str, progress: float, message: str):
        """Update progress if callback provided."""
        if self.progress_callback:
            await self.progress_callback(stage, progress, message)
    
    def _generate_analysis_id(self) -> str:
        """Generate unique analysis identifier."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"analysis_{timestamp}"
    
    def get_available_stages(self) -> List[str]:
        """Get list of available stage names."""
        return list(self._stages.keys())
    
    def enable_stage(self, stage_name: str):
        """Enable a specific stage."""
        if stage_name not in self._stages:
            raise ValueError(f"Unknown stage: {stage_name}")
        # Implementation for enabling/disabling stages
        pass
    
    def disable_stage(self, stage_name: str):
        """Disable a specific stage."""
        if stage_name not in self._stages:
            raise ValueError(f"Unknown stage: {stage_name}")
        # Implementation for enabling/disabling stages
        pass


# Register the modular pipeline as the default
def create_modular_pipeline(analysis_id: Optional[str] = None, config_overrides: Optional[Dict] = None):
    """Factory function for creating modular pipeline."""
    return ModularCardioXNetPipeline(analysis_id, config_overrides)

register_service("pipeline", create_modular_pipeline)
