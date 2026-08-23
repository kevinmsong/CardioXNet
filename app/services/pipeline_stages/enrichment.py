"""Enrichment stages: validation, neighbourhood, primary/secondary discovery,
aggregation, prioritization scoring and the semantic cardiac filter.

Mixed into :class:`app.services.pipeline.Pipeline`. Split out of a 1,756-line
module so the orchestration in ``run()`` can be read on its own; every method body
is unchanged and still uses the services ``Pipeline.__init__`` builds.
"""

import logging
import time
from typing import Dict, List, Optional

from app.models import (
    FinalPathwayResult,
    FunctionalNeighborhood,
    GeneInfo,
    PrimaryTriageResult,
    ScoredHypotheses,
    SecondaryTriageResult,
    ValidationResult,
)

from app.services.pipeline_errors import PipelineError

logger = logging.getLogger(__name__)


class EnrichmentStagesMixin:
    """Stages 0 through the semantic cardiac filter."""

    async def _run_stage_0(self, seed_genes: List[str]) -> ValidationResult:
        """Run Stage 0: Input Validation."""
        logger.info("Running Stage 0: Input Validation")
        
        try:
            validation_result = self.input_validator.validate_input(
                seed_genes,
                check_api_connectivity=True
            )
            
            # Store full validation result for API response
            self.results["stage_0"] = validation_result.model_dump()
            
            self.warnings.extend(validation_result.warnings)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Stage 0 failed: {str(e)}")
            raise PipelineError(f"Input validation failed: {str(e)}")
    
    async def _run_stage_1(self, seed_genes: List[GeneInfo]) -> FunctionalNeighborhood:
        """Run Stage 1: Functional Neighborhood Assembly."""
        logger.info("Running Stage 1: Functional Neighborhood Assembly")
        
        try:
            fn_result = self.fn_builder.build_neighborhood(seed_genes)
            
            self.results["stage_1"] = {
                "fn_size": fn_result.size,
                "neighbor_count": len(fn_result.neighbors),
                "interaction_count": len(fn_result.interactions),
                "contributions": fn_result.contributions
            }
            
            return fn_result
            
        except Exception as e:
            logger.error(f"Stage 1 failed: {str(e)}")
            raise PipelineError(f"Functional neighborhood assembly failed: {str(e)}")
    
    async def _run_stage_2a(self, fn: FunctionalNeighborhood) -> PrimaryTriageResult:
        """Run Stage 2a: Primary Pathway Enrichment."""
        logger.info("Running Stage 2a: Primary Pathway Enrichment")
        
        try:
            primary_result = self.primary_analyzer.analyze(fn)
            
            self.results["stage_2a"] = {
                "primary_pathways": len(primary_result.primary_pathways),
                "known_pathways_filtered": primary_result.filtered_count,
                "pathway_details": [
                    {
                        "pathway_id": p.pathway_id,
                        "pathway_name": p.pathway_name,
                        "source_db": p.source_db,
                        "p_value": p.p_value,
                        "p_adj": p.p_adj,
                        "evidence_count": len(p.evidence_genes),
                        "contributing_seed_genes": getattr(p, 'contributing_seed_genes', [])
                    }
                    for p in primary_result.primary_pathways[:50]  # Store top 50 for lineage visualization
                ]
            }
            
            return primary_result
            
        except Exception as e:
            logger.error(f"Stage 2a failed: {str(e)}")
            raise PipelineError(f"Primary pathway enrichment failed: {str(e)}")
    
    async def _run_stage_2b(
        self,
        primary_result: PrimaryTriageResult,
        seed_genes: List[GeneInfo]
    ) -> SecondaryTriageResult:
        """Run Stage 2b: Secondary Pathway Discovery (REQUIRED)."""
        logger.info("Running Stage 2b: Secondary Pathway Discovery")
        
        try:
            secondary_result = self.secondary_analyzer.analyze(
                primary_result,
                seed_genes
            )
            
            self.results["stage_2b"] = {
                "secondary_pathways": secondary_result.total_secondary_count,
                "literature_stats": secondary_result.literature_expansion_stats
            }
            
            # Secondary pathways are required - warn if none found
            if secondary_result.total_secondary_count == 0:
                logger.warning(
                    "Stage 2b produced 0 secondary pathways. "
                    "This may indicate issues with literature mining or enrichment."
                )
                self.warnings.append(
                    "No secondary pathways discovered. Results based on primary pathways only."
                )
            
            return secondary_result
            
        except Exception as e:
            logger.error(f"Stage 2b failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise PipelineError(f"Secondary pathway discovery failed: {str(e)}")
    
    async def _run_stage_2c(
        self,
        secondary_result: SecondaryTriageResult,
        primary_result = None
    ) -> FinalPathwayResult:
        """Run Stage 2c: Pathway Aggregation."""
        logger.info("Running Stage 2c: Pathway Aggregation")
        
        try:
            final_result = self.aggregator.aggregate(secondary_result, primary_result=primary_result)
            
            self.results["stage_2c"] = {
                "final_pathways": final_result.total_count,
                "aggregation_strategy": final_result.aggregation_strategy
            }
            
            if final_result.total_count == 0:
                logger.warning("Stage 2c produced 0 final pathways")
                self.warnings.append("No final pathways after aggregation")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Stage 2c failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Don't fail pipeline - return empty result
            logger.warning("Continuing pipeline with empty final pathways")
            self.warnings.append(f"Stage 2c failed: {str(e)}")
            
            from app.models import FinalPathwayResult
            return FinalPathwayResult(
                final_pathways=[],
                total_count=0,
                aggregation_strategy=self.settings.nets.aggregation_strategy,
                min_support_threshold=self.settings.nets.min_support_threshold
            )
    

    async def _run_stage_5_scoring(
        self,
        final_result: FinalPathwayResult,
        fn_result: Optional[FunctionalNeighborhood] = None,
    ) -> ScoredHypotheses:
        """Run Stage 3: Pathway Prioritization Scoring.

        ``fn_result`` supplies the seed-proximity term of the centrality weight.
        It was previously not passed, so the weight was pinned at 1.0 for every
        pathway and contributed nothing to the ranking.
        """
        logger.info("Running Stage 3: Pathway Prioritization Scoring")

        try:
            scored_hypotheses = self.nes_scorer.score(final_result, fn_result=fn_result)
            
            # Note: Stage 5a results will be stored AFTER Stage 4a semantic filtering
            # to include cardiac_relevance scores in the final output
            
            if scored_hypotheses.total_count == 0:
                logger.warning("Stage 5a produced 0 scored hypotheses")
                self.warnings.append("No hypotheses after NES scoring")
            
            return scored_hypotheses
            
        except Exception as e:
            logger.error(f"Stage 5a failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Don't fail pipeline - return empty result
            logger.warning("Continuing pipeline with empty hypotheses")
            self.warnings.append(f"Stage 5a failed: {str(e)}")
            
            from app.models import ScoredHypotheses
            return ScoredHypotheses(
                hypotheses=[],
                total_count=0
            )
    
    async def _run_stage_4_semantic(self, scored_hypotheses: ScoredHypotheses) -> ScoredHypotheses:
        """
        Run Stage 4a: Semantic Cardiac Relevance Filtering.
        
        SCIENTIFIC RIGOR:
        - Validates input hypotheses before processing
        - Applies consistent semantic scoring across all pathways
        - Maintains statistical ordering while prioritizing cardiac relevance
        - Logs comprehensive statistics for reproducibility
        - Gracefully handles failures without compromising pipeline integrity
        - Preserves original NES scores for transparency
        
        This stage applies semantic cardiac relevance scoring to prioritize
        pathways with strong cardiac context while maintaining broad discovery
        potential through permissive thresholds.
        """
        logger.info("Running Stage 4a: Semantic Cardiac Relevance Filtering")
        
        try:
            # Validate input
            if scored_hypotheses.total_count == 0:
                logger.warning("No hypotheses to filter - skipping semantic stage")
                self.results["stage_3_5_semantic"] = {
                    "hypotheses_after_filtering": 0,
                    "semantic_statistics": {},
                    "threshold_used": self.settings.nets.semantic_relevance_threshold,
                    "status": "skipped_no_input"
                }
                return scored_hypotheses
            
            if not scored_hypotheses.hypotheses:
                logger.error("Hypotheses list is None or empty despite non-zero count")
                raise ValueError("Invalid hypotheses structure")
            
            # Get threshold with validation
            min_threshold = self.settings.nets.semantic_relevance_threshold
            if not 0 <= min_threshold <= 1:
                logger.warning(f"Invalid threshold {min_threshold}, using default 0.1")
                min_threshold = 0.1
            
            logger.info(
                f"Applying semantic filtering: {scored_hypotheses.total_count} hypotheses, "
                f"threshold={min_threshold}"
            )
            
            # Store pre-filtering count for comparison
            pre_filter_count = scored_hypotheses.total_count
            
            # Apply semantic boost with permissive threshold (parallel processing)
            max_workers = getattr(self.settings, 'max_workers_semantic', 4)
            boosted_hypotheses_list = self.semantic_filter.apply_semantic_boost_parallel(
                scored_hypotheses.hypotheses,
                min_threshold=min_threshold,
                disease_context=self.disease_context,
                disease_synonyms=self.disease_synonyms,
                max_workers=max_workers
            )
            
            # Validate output
            if not isinstance(boosted_hypotheses_list, list):
                raise ValueError("Semantic filter returned invalid type")
            
            # Get comprehensive semantic statistics
            semantic_stats = self.semantic_filter.get_semantic_statistics(boosted_hypotheses_list)
            
            # Update scored hypotheses
            scored_hypotheses.hypotheses = boosted_hypotheses_list
            scored_hypotheses.total_count = len(boosted_hypotheses_list)
            
            # Calculate filtering metrics
            filtered_count = pre_filter_count - scored_hypotheses.total_count
            retention_rate = (scored_hypotheses.total_count / pre_filter_count * 100) if pre_filter_count > 0 else 0
            
            # Store comprehensive semantic filtering results
            self.results["stage_3_5_semantic"] = {
                "hypotheses_before_filtering": pre_filter_count,
                "hypotheses_after_filtering": scored_hypotheses.total_count,
                "filtered_count": filtered_count,
                "retention_rate_percent": round(retention_rate, 2),
                "semantic_statistics": semantic_stats,
                "threshold_used": min_threshold,
                "status": "completed"
            }
            
            logger.info(
                f"Semantic filtering complete: {scored_hypotheses.total_count}/{pre_filter_count} hypotheses retained "
                f"({retention_rate:.1f}%), mean relevance: {semantic_stats.get('mean_relevance', 0):.3f}, "
                f"high relevance: {semantic_stats.get('high_relevance_count', 0)}"
            )
            
            # Warn if excessive filtering occurred
            if retention_rate < 50:
                warning_msg = f"Semantic filtering removed {filtered_count} hypotheses ({100-retention_rate:.1f}%)"
                logger.warning(warning_msg)
                self.warnings.append(warning_msg)
            
            # Stage 3.5b: Pathway Redundancy Detection (optional)
            if getattr(self.settings.nets, 'enable_redundancy_detection', True):
                logger.info("Running Stage 3.5b: Pathway Redundancy Detection")
                pre_redundancy_count = scored_hypotheses.total_count
                
                try:
                    # Remove redundant pathways
                    non_redundant_hypotheses = self.redundancy_detector.remove_redundant_pathways(
                        scored_hypotheses.hypotheses,
                        keep_best_scored=True
                    )
                    
                    # Get redundancy statistics
                    redundancy_stats = self.redundancy_detector.get_redundancy_statistics(
                        scored_hypotheses.hypotheses
                    )
                    
                    # Update hypotheses
                    scored_hypotheses.hypotheses = non_redundant_hypotheses
                    scored_hypotheses.total_count = len(non_redundant_hypotheses)
                    
                    removed_count = pre_redundancy_count - scored_hypotheses.total_count
                    
                    self.results["stage_3_5b_redundancy"] = {
                        "hypotheses_before": pre_redundancy_count,
                        "hypotheses_after": scored_hypotheses.total_count,
                        "removed_count": removed_count,
                        "redundancy_statistics": redundancy_stats,
                        "jaccard_threshold": self.redundancy_detector.similarity_threshold
                    }
                    
                    logger.info(
                        f"Redundancy detection complete: {pre_redundancy_count} → {scored_hypotheses.total_count} "
                        f"({removed_count} redundant pathways removed)"
                    )
                    
                except Exception as e:
                    logger.warning(f"Redundancy detection failed: {str(e)}, continuing without it")
                    self.warnings.append(f"Redundancy detection failed: {str(e)}")
            
            # stage_3 is NOT snapshotted here. It used to be written at this
            # point and again after seed tracing, but both were frozen
            # model_dump()s taken before the discovery stage runs, so the copy
            # that reached results.json carried none of the Discovery Score,
            # novelty tier or permutation q. Stage 8 writes the one that counts.
            
            return scored_hypotheses
            
        except Exception as e:
            logger.error(f"Stage 3b semantic filtering failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Don't fail pipeline - return original hypotheses with warning
            logger.warning("Continuing pipeline without semantic filtering")
            error_msg = f"Semantic filtering failed: {str(e)}"
            self.warnings.append(error_msg)
            
            # Store failure information
            self.results["stage_3_5_semantic"] = {
                "hypotheses_after_filtering": scored_hypotheses.total_count,
                "semantic_statistics": {},
                "threshold_used": self.settings.nets.semantic_relevance_threshold,
                "status": "failed",
                "error": str(e)
            }
            
            return scored_hypotheses
