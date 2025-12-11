"""Pipeline stages for CardioXNet analysis."""

from app.core.pipeline_stage import PipelineStage, StageResult, StageStatus
from app.core.service_registry import get_service
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class InputValidationStage(PipelineStage):
    """Stage 0: Input validation and gene processing."""
    
    @property
    def name(self) -> str:
        return "input_validation"
    
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        seed_genes = context.get("seed_genes", [])
        
        validator = get_service("input_validator")
        result = validator.validate_input(seed_genes)
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={
                "validation_result": result,
                "valid_genes": result.valid_genes,
                "invalid_genes": result.invalid_genes,
                "warnings": result.warnings
            }
        )


class FunctionalNeighborhoodStage(PipelineStage):
    """Stage 1: Functional neighborhood assembly."""
    
    @property
    def name(self) -> str:
        return "functional_neighborhood"
    
    @property
    def dependencies(self) -> List[str]:
        return ["input_validation"]
    
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        valid_genes = context["input_validation"]["data"]["valid_genes"]
        
        fn_builder = get_service("functional_neighborhood_builder")
        result = fn_builder.build_neighborhood(valid_genes)
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"neighborhood": result}
        )


class PrimaryPathwayStage(PipelineStage):
    """Stage 2a: Primary pathway enrichment."""
    
    @property
    def name(self) -> str:
        return "primary_pathway"
    
    @property
    def dependencies(self) -> List[str]:
        return ["functional_neighborhood"]
    
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        neighborhood = context["functional_neighborhood"]["data"]["neighborhood"]
        
        analyzer = get_service("primary_pathway_analyzer")
        result = analyzer.analyze(neighborhood)
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"pathways": result}
        )


class SecondaryPathwayStage(PipelineStage):
    """Stage 2b: Secondary pathway discovery."""
    
    @property
    def name(self) -> str:
        return "secondary_pathway"
    
    @property
    def dependencies(self) -> List[str]:
        return ["primary_pathway", "input_validation"]
    
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        primary_result = context["primary_pathway"]["data"]["pathways"]
        seed_genes = context["input_validation"]["data"]["valid_genes"]
        
        analyzer = get_service("secondary_pathway_analyzer")
        result = analyzer.analyze(primary_result, seed_genes)
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"pathways": result}
        )


class PathwayAggregationStage(PipelineStage):
    """Stage 2c: Pathway aggregation."""
    
    @property
    def name(self) -> str:
        return "pathway_aggregation"
    
    @property
    def dependencies(self) -> List[str]:
        return ["secondary_pathway", "primary_pathway"]
    
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        secondary_result = context["secondary_pathway"]["data"]["pathways"]
        primary_result = context["primary_pathway"]["data"]["pathways"]
        
        aggregator = get_service("pathway_aggregator")
        result = aggregator.aggregate(secondary_result, primary_result=primary_result)
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"final_pathways": result}
        )


class ScoringStage(PipelineStage):
    """Stage 5a: NES scoring."""
    
    @property
    def name(self) -> str:
        return "nes_scoring"
    
    @property
    def dependencies(self) -> List[str]:
        return ["pathway_aggregation", "functional_neighborhood"]
    
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        pathways = context["pathway_aggregation"]["data"]["final_pathways"]
        fn_result = context["functional_neighborhood"]["data"]["neighborhood"]
        
        scorer = get_service("nes_scorer")
        result = scorer.score(pathways, fn_result=fn_result, topology_result=None)
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"scored_hypotheses": result}
        )


class SemanticFilteringStage(PipelineStage):
    """Stage 4a: Semantic filtering."""
    
    @property
    def name(self) -> str:
        return "semantic_filtering"
    
    @property
    def dependencies(self) -> List[str]:
        return ["nes_scoring"]
    
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        scored_hypotheses = context["nes_scoring"]["data"]["scored_hypotheses"]
        hypotheses = scored_hypotheses.hypotheses
        
        filter_service = get_service("semantic_filter")
        result = filter_service.apply_semantic_boost(hypotheses)
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"filtered_hypotheses": result}
        )


class LiteratureMiningStage(PipelineStage):
    """Stage 6a: Literature mining."""
    
    @property
    def name(self) -> str:
        return "literature_mining"
    
    @property
    def dependencies(self) -> List[str]:
        return ["semantic_filtering", "input_validation"]
    
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        hypotheses = context["semantic_filtering"]["data"]["filtered_hypotheses"]
        seed_genes = context["input_validation"]["data"]["valid_genes"]
        
        miner = get_service("literature_miner")
        result = miner.validate_hypotheses(hypotheses, seed_genes)
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"literature_evidence": result}
        )


class TopologyAnalysisStage(PipelineStage):
    """Stage 7: Network topology analysis."""
    
    @property
    def name(self) -> str:
        return "topology_analysis"
    
    @property
    def dependencies(self) -> List[str]:
        return ["semantic_filtering", "functional_neighborhood", "primary_pathway"]
    
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        hypotheses = context["semantic_filtering"]["data"]["filtered_hypotheses"]
        fn = context["functional_neighborhood"]["data"]["neighborhood"]
        primary_result = context["primary_pathway"]["data"]["pathways"]
        
        analyzer = get_service("topology_analyzer")
        result = analyzer.analyze(hypotheses, fn, primary_result.primary_pathways)
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"topology": result}
        )


class ReportGenerationStage(PipelineStage):
    """Final stage: Report generation."""
    
    @property
    def name(self) -> str:
        return "report_generation"
    
    @property
    def dependencies(self) -> List[str]:
        return ["tissue_expression", "permutation_testing", "druggability_analysis", "nes_rescoring", "topology_analysis", "literature_mining", "input_validation", "functional_neighborhood", "primary_pathway", "secondary_pathway", "pathway_aggregation", "nes_scoring"]
    
    async def execute(self, context: Dict[str, Any]) -> StageResult:
        # Collect all required data from pipeline context
        analysis_id = context.get("analysis_id", "unknown")
        seed_genes = context["input_validation"]["data"]["valid_genes"]
        validation_result = context["input_validation"]["data"]["validation_result"]
        fn_result = context["functional_neighborhood"]["data"]["neighborhood"]
        primary_result = context["primary_pathway"]["data"]["pathways"]
        secondary_result = context["secondary_pathway"]["data"]["pathways"]
        final_result = context["pathway_aggregation"]["data"]["final_pathways"]
        scored_hypotheses = context["nes_rescoring"]["data"]["rescored_hypotheses"]
        
        # Wrap the rescored hypotheses in ScoredHypotheses object for report generator
        from app.models.results import ScoredHypotheses
        scored_hypotheses_obj = ScoredHypotheses(
            hypotheses=scored_hypotheses,
            total_count=len(scored_hypotheses)
        )
        topology_result = context["topology_analysis"]["data"]["topology"]
        literature_evidence = context["literature_mining"]["data"]["literature_evidence"]
        
        generator = get_service("report_generator")
        result = generator.generate_report(
            analysis_id=analysis_id,
            seed_genes=seed_genes,
            validation_result=validation_result,
            fn_result=fn_result,
            primary_result=primary_result,
            secondary_result=secondary_result,
            final_result=final_result,
            scored_hypotheses=scored_hypotheses_obj,
            topology_result=topology_result,
            literature_evidence=literature_evidence
        )
        
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"report": result}
        )


class NESSrescoringStage(PipelineStage):
    """Stage 7b: Re-score hypotheses with network centrality."""

    @property
    def name(self) -> str:
        return "nes_rescoring"

    @property
    def dependencies(self) -> List[str]:
        return ["topology_analysis", "nes_scoring", "functional_neighborhood"]

    async def execute(self, context: Dict[str, Any]) -> StageResult:
        filtered_hypotheses = context["semantic_filtering"]["data"]["filtered_hypotheses"]
        topology_result = context["topology_analysis"]["data"]["topology"]
        fn_result = context["functional_neighborhood"]["data"]["neighborhood"]

        # Re-score with network centrality
        scorer = get_service("nes_scorer")
        seed_neighbors_1hop = scorer._get_seed_neighbors_1hop(fn_result) if fn_result else None

        for hypothesis in filtered_hypotheses:
            if hasattr(hypothesis, 'aggregated_pathway'):
                # Recalculate NES with topology data
                new_nes, new_components = scorer._calculate_nes(
                    hypothesis.aggregated_pathway,
                    fn_result=fn_result,
                    topology_result=topology_result,
                    seed_neighbors_1hop=seed_neighbors_1hop
                )
                hypothesis.nes_score = new_nes
                if hypothesis.score_components:
                    hypothesis.score_components.update(new_components)
                else:
                    hypothesis.score_components = new_components

        # Re-sort by updated NES scores
        filtered_hypotheses.sort(key=lambda h: h.nes_score, reverse=True)
        for i, hyp in enumerate(filtered_hypotheses, 1):
            hyp.rank = i

        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"rescored_hypotheses": filtered_hypotheses}
        )


class DruggabilityAnalysisStage(PipelineStage):
    """Stage 8: Druggability analysis."""

    @property
    def name(self) -> str:
        return "druggability_analysis"

    @property
    def dependencies(self) -> List[str]:
        return ["nes_rescoring"]

    async def execute(self, context: Dict[str, Any]) -> StageResult:
        filtered_hypotheses = context["nes_rescoring"]["data"]["rescored_hypotheses"]

        druggability_analyzer = get_service("druggability_analyzer")
        result = druggability_analyzer.annotate_pathways_with_druggability(filtered_hypotheses)

        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"druggability_result": result}
        )


class PermutationTestingStage(PipelineStage):
    """Stage 9: Permutation testing for statistical validation."""

    @property
    def name(self) -> str:
        return "permutation_testing"

    @property
    def dependencies(self) -> List[str]:
        return ["druggability_analysis", "functional_neighborhood"]

    async def execute(self, context: Dict[str, Any]) -> StageResult:
        filtered_hypotheses = context["nes_rescoring"]["data"]["rescored_hypotheses"]
        fn_result = context["functional_neighborhood"]["data"]["neighborhood"]

        # Extract all genes from functional neighborhood
        all_fn_genes = [g.symbol for g in fn_result.seed_genes] + [g.symbol for g in fn_result.neighbors]

        permutation_tester = get_service("permutation_tester")
        result = permutation_tester.adjust_pvalues_with_permutation(
            filtered_hypotheses,
            all_fn_genes,
            all_fn_genes  # all_genes is the functional neighborhood
        )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"permutation_result": result}
        )


class TissueExpressionStage(PipelineStage):
    """Stage 10: Tissue expression validation."""

    @property
    def name(self) -> str:
        return "tissue_expression"

    @property
    def dependencies(self) -> List[str]:
        return ["permutation_testing"]

    async def execute(self, context: Dict[str, Any]) -> StageResult:
        filtered_hypotheses = context["nes_rescoring"]["data"]["rescored_hypotheses"]

        tissue_validator = get_service("tissue_expression_validator")
        result = await tissue_validator.annotate_pathways_with_expression(filtered_hypotheses)

        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            data={"tissue_result": result}
        )
