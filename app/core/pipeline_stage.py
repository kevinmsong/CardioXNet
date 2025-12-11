"""Base classes for modular pipeline stages."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class StageStatus(Enum):
    """Pipeline stage execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    """Result of a pipeline stage execution."""
    stage_name: str
    status: StageStatus
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage_name": self.stage_name,
            "status": self.status.value,
            "data": self.data,
            "metadata": self.metadata,
            "error": self.error
        }


class PipelineStage(ABC):
    """
    Abstract base class for pipeline stages.
    
    Each stage is a self-contained unit that:
    - Has a unique name
    - Declares its dependencies
    - Can validate inputs
    - Executes its logic
    - Returns structured results
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the stage.
        
        Args:
            config: Stage-specific configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Stage identifier."""
        pass
    
    @property
    def dependencies(self) -> List[str]:
        """
        List of stage names this stage depends on.
        
        Returns:
            List of stage names
        """
        return []
    
    @property
    def optional(self) -> bool:
        """
        Whether this stage is optional.
        
        All stages are now required - no optional stages.
        """
        return False
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        """
        Validate input data before execution.
        
        Args:
            context: Pipeline context with results from previous stages
            
        Returns:
            True if input is valid
            
        Raises:
            ValueError: If validation fails
        """
        # Check dependencies are available
        for dep in self.dependencies:
            if dep not in context:
                raise ValueError(f"Missing required dependency: {dep}")
        return True
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        """
        Execute the stage logic.
        
        Args:
            context: Pipeline context with results from previous stages
            
        Returns:
            Stage execution result
        """
        pass
    
    async def run(self, context: Dict[str, Any]) -> StageResult:
        """
        Run the stage with validation and error handling.
        
        Args:
            context: Pipeline context
            
        Returns:
            Stage result
        """
        self.logger.info(f"Starting stage: {self.name}")
        
        try:
            # Validate input
            self.validate_input(context)
            
            # Execute stage
            result = await self.execute(context)
            
            # Log completion
            self.logger.info(f"Completed stage: {self.name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Stage {self.name} failed: {str(e)}", exc_info=True)
            
            if self.optional:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SKIPPED,
                    error=str(e)
                )
            else:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.FAILED,
                    error=str(e)
                )


class ConditionalStage(PipelineStage):
    """
    Stage that only executes if a condition is met.
    """
    
    @abstractmethod
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """
        Determine if the stage should execute.
        
        Args:
            context: Pipeline context
            
        Returns:
            True if stage should execute
        """
        pass
    
    async def run(self, context: Dict[str, Any]) -> StageResult:
        """Run with condition check."""
        if not self.should_execute(context):
            self.logger.info(f"Skipping conditional stage: {self.name}")
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED
            )
        
        return await super().run(context)


class ParallelStageGroup:
    """
    Group of stages that can execute in parallel.
    """
    
    def __init__(self, name: str, stages: List[PipelineStage]):
        """
        Initialize parallel stage group.
        
        Args:
            name: Group identifier
            stages: List of stages to execute in parallel
        """
        self.name = name
        self.stages = stages
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    async def run(self, context: Dict[str, Any]) -> Dict[str, StageResult]:
        """
        Execute all stages in parallel.
        
        Args:
            context: Pipeline context
            
        Returns:
            Dictionary of stage results
        """
        import asyncio
        
        self.logger.info(f"Starting parallel stage group: {self.name}")
        
        # Execute all stages concurrently
        tasks = [stage.run(context) for stage in self.stages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build results dictionary
        stage_results = {}
        for stage, result in zip(self.stages, results):
            if isinstance(result, Exception):
                self.logger.error(f"Stage {stage.name} failed: {str(result)}")
                stage_results[stage.name] = StageResult(
                    stage_name=stage.name,
                    status=StageStatus.FAILED,
                    error=str(result)
                )
            else:
                stage_results[stage.name] = result
        
        self.logger.info(f"Completed parallel stage group: {self.name}")
        return stage_results
