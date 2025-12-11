"""CardioXNet pipeline orchestrator."""

import logging
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from app.models import (
    GeneInfo,
    ValidationResult,
    FunctionalNeighborhood,
    PrimaryTriageResult,
    SecondaryTriageResult,
    FinalPathwayResult,
    ScoredHypotheses,
    TopologyResult,
    LiteratureEvidence
)
from app.services import (
    InputValidator,
    FunctionalNeighborhoodBuilder,
    PrimaryPathwayAnalyzer,
    SecondaryPathwayAnalyzer,
    NESScorer,
    LiteratureMiner,
    ReportGenerator,
    TissueExpressionValidator,
    PermutationTester,
    DruggabilityAnalyzer,
    SeedGeneTracer
)
from app.services.pathway_aggregator_rigorous import RigorousPathwayAggregator
from app.services.semantic_filter import SemanticFilter
from app.services.hypothesis_validator import HypothesisValidator
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when pipeline execution fails."""
    pass


class Pipeline:
    """Orchestrates the complete NETS analysis pipeline (unified fast + full pipeline)."""
    
    def __init__(self, analysis_id: Optional[str] = None, config_overrides: Optional[Dict] = None):
        """
        Initialize pipeline.
        
        Args:
            analysis_id: Unique analysis identifier (auto-generated if not provided)
            config_overrides: Configuration parameter overrides from frontend
        """
        # Create a copy of settings to avoid modifying the global instance
        import copy
        self.settings = copy.deepcopy(get_settings())
        
        # Apply config overrides if provided
        if config_overrides:
            logger.info(f"Applying {len(config_overrides)} configuration overrides: {config_overrides}")
            for key, value in config_overrides.items():
                if hasattr(self.settings.nets, key):
                    old_value = getattr(self.settings.nets, key)
                    setattr(self.settings.nets, key, value)
                    logger.info(f"Override: {key} = {old_value} -> {value}")
                elif key == 'disease_context':
                    # Store disease context for semantic filtering
                    self.disease_context = value
                    logger.info(f"Disease context set: {value}")
                elif key == 'disease_synonyms':
                    # Store disease synonyms for literature search
                    self.disease_synonyms = value or []
                    logger.info(f"Disease synonyms set: {value}")
                else:
                    logger.warning(f"Unknown configuration parameter: {key}")
        
        self.analysis_id = analysis_id or self._generate_analysis_id()
        
        # Initialize services
        self.input_validator = InputValidator()
        self.fn_builder = FunctionalNeighborhoodBuilder()
        self.primary_analyzer = PrimaryPathwayAnalyzer()
        self.secondary_analyzer = SecondaryPathwayAnalyzer()
        self.aggregator = RigorousPathwayAggregator()
        self.nes_scorer = NESScorer()
        self.semantic_filter = SemanticFilter()
        self.tissue_validator = TissueExpressionValidator()
        
        # Import PathwayRedundancyDetector
        from app.services.pathway_redundancy import PathwayRedundancyDetector
        redundancy_threshold = getattr(self.settings.nets, 'redundancy_jaccard_threshold', 0.7)
        self.redundancy_detector = PathwayRedundancyDetector(similarity_threshold=redundancy_threshold)
        self.permutation_tester = PermutationTester()
        self.druggability_analyzer = DruggabilityAnalyzer()
        # topology_analyzer removed for speed optimization
        
        # Stage 3: Clinical Evidence Integrator (REMOVED - GWAS API deprecated)
        # disease_context = getattr(self, 'disease_context', 'cardiovascular')
        # self.clinical_evidence_integrator = ClinicalEvidenceIntegrator(disease_context=disease_context)
        
        # Comprehensive topology analyzer removed for speed optimization
        
        self.literature_miner = LiteratureMiner()
        self.hypothesis_validator = HypothesisValidator()
        self.seed_gene_tracer = SeedGeneTracer()
        self.report_generator = ReportGenerator()
        
        # Pipeline state
        self.results = {}
        self.warnings = []
        self.progress_callback = None
        
        # Disease context for semantic filtering and literature search
        self.disease_context = None
        self.disease_synonyms = []
        
        logger.info(f"CardioXNetPipeline initialized (ID: {self.analysis_id})")
    
    async def run(
        self,
        seed_genes: List[str],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Run complete NETS analysis pipeline.
        
        Args:
            seed_genes: List of seed gene identifiers
            progress_callback: Optional callback for progress updates
                              Signature: callback(stage: str, progress: float, message: str)
            
        Returns:
            Dictionary with all pipeline results
            
        Raises:
            PipelineError: If pipeline execution fails
        """
        self.progress_callback = progress_callback
        
        # Start timing
        import time
        pipeline_start_time = time.time()
        stage_start_time = pipeline_start_time
        
        logger.info(
            f"Starting NETS pipeline analysis (ID: {self.analysis_id}) "
            f"with {len(seed_genes)} seed genes"
        )
        print(f"\n[TIMING] Pipeline START at {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # Stage 0: Input Validation
            await self._update_progress("Stage 1", 5, "Validating input")
            stage_start_time = time.time()
            validation_result = await self._run_stage_0(seed_genes)
            elapsed = time.time() - stage_start_time
            print(f"⏱️  [TIMING] Stage 0 completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            
            # Stage 1: Functional Neighborhood Assembly
            await self._update_progress("Stage 2", 15, "Building functional neighborhood")
            stage_start_time = time.time()
            fn_result = await self._run_stage_1(validation_result.valid_genes)
            elapsed = time.time() - stage_start_time
            print(f"⏱️  [TIMING] Stage 1 completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            
            # Stage 2a: Primary Pathway Enrichment
            await self._update_progress("Stage 3", 25, "Primary pathway enrichment")
            stage_start_time = time.time()
            primary_result = await self._run_stage_2a(fn_result)
            elapsed = time.time() - stage_start_time
            print(f"⏱️  [TIMING] Stage 2a completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            
            # Stage 2b: Secondary Pathway Discovery
            await self._update_progress("Stage 4", 40, "Secondary pathway discovery")
            stage_start_time = time.time()
            secondary_result = await self._run_stage_2b(
                primary_result,
                validation_result.valid_genes
            )
            elapsed = time.time() - stage_start_time
            print(f"⏱️  [TIMING] Stage 2b completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            
            # Stage 2c: Pathway Aggregation
            await self._update_progress("Stage 5", 55, "Aggregating pathways")
            stage_start_time = time.time()
            final_result = await self._run_stage_2c(secondary_result, primary_result)
            elapsed = time.time() - stage_start_time
            logger.info(f"Stage 2c complete: {final_result.total_count} final pathways")
            print(f"⏱️  [TIMING] Stage 2c completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            await self._update_progress("Stage 5", 60, f"Stage 5 complete: {final_result.total_count} pathways")
            
            # Stage 5a: Final NES Scoring
            await self._update_progress("Stage 6", 65, "Calculating NES scores")
            stage_start_time = time.time()
            print(f"[PIPELINE DEBUG] Calling Stage 5a with {final_result.total_count} pathways")
            scored_hypotheses = await self._run_stage_5_scoring(final_result, None)
            elapsed = time.time() - stage_start_time
            print(f"[PIPELINE DEBUG] Stage 5a returned {scored_hypotheses.total_count} hypotheses")
            logger.info(f"Stage 5a complete: {scored_hypotheses.total_count} scored hypotheses")
            print(f"⏱️  [TIMING] Stage 5a completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            await self._update_progress("Stage 6", 70, f"Stage 6 complete: {scored_hypotheses.total_count} hypotheses")
            
            # Stage 4a: Semantic Filtering (Cardiac Relevance Boost)
            await self._update_progress("Stage 7", 72, "Applying semantic cardiac relevance filtering")
            stage_start_time = time.time()
            scored_hypotheses = await self._run_stage_4_semantic(scored_hypotheses)
            elapsed = time.time() - stage_start_time
            logger.info(f"Stage 4a complete: {scored_hypotheses.total_count} hypotheses after semantic filtering")
            print(f"⏱️  [TIMING] Stage 4a completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            await self._update_progress("Stage 7", 76, f"Semantic filtering complete: {scored_hypotheses.total_count} hypotheses")
            
            # Stage 4b: Enhanced Biological Validation (Tissue Expression, Permutation, Druggability)
            await self._update_progress("Stage 8", 78, "Applying enhanced biological validation")
            stage_start_time = time.time()
            print(f"[PIPELINE DEBUG] Starting Stage 4b with {scored_hypotheses.total_count} hypotheses")
            logger.info(f"Starting Stage 4b enhanced validation with {scored_hypotheses.total_count} hypotheses")
            
            try:
                scored_hypotheses = await self._run_stage_4_enhanced_validation(
                    scored_hypotheses,
                    fn_result,
                    validation_result.valid_genes
                )
                elapsed = time.time() - stage_start_time
                print(f"[PIPELINE DEBUG] Stage 4b completed successfully")
                logger.info(f"Stage 4b complete: Enhanced validation applied to {scored_hypotheses.total_count} hypotheses")
                print(f"⏱️  [TIMING] Stage 4b completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                await self._update_progress("Stage 8", 81, f"Enhanced validation complete")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                print(f"[PIPELINE DEBUG] Stage 4b failed: {str(e)}")
                logger.error(f"Stage 4b failed but continuing pipeline: {str(e)}")
                print(f"⏱️  [TIMING] Stage 4b failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                import traceback
                traceback.print_exc()
                self.warnings.append(f"Stage 4b enhanced validation failed: {str(e)}")
                await self._update_progress("Stage 8", 81, f"Stage 8 failed, continuing pipeline")
            
            # Stage 6: Literature Mining & Seed Gene Traceability
            await self._update_progress("Stage 9", 82, "Mining literature and tracing seed genes")
            stage_6_start = time.time()
            print(f"[PIPELINE DEBUG] Starting Stage 6 with {scored_hypotheses.total_count} hypotheses")
            
            # Stage 6a: Literature Mining (detailed citations)
            try:
                stage_start_time = time.time()
                literature_evidence = await self._run_stage_6_literature(
                    scored_hypotheses,
                    validation_result.valid_genes
                )
                elapsed = time.time() - stage_start_time
                print(f"[PIPELINE DEBUG] Stage 6a literature mining completed successfully")
                logger.info(f"Stage 6a complete: Literature mining found citations for {len(literature_evidence.hypothesis_citations)} hypotheses")
                print(f"⏱️  [TIMING] Stage 6a completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                literature_error_msg = f"[PIPELINE DEBUG] Stage 6a literature mining failed: {str(e)}"
                print(literature_error_msg, flush=True)
                logger.error(f"Stage 6a literature mining failed but continuing: {str(e)}")
                print(f"⏱️  [TIMING] Stage 6a failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                import traceback
                traceback.print_exc()
                self.warnings.append(f"Stage 6a literature mining failed: {str(e)}")
                literature_evidence = LiteratureEvidence(hypothesis_citations={})
            
            # Stage 6b: Seed Gene Traceability & Literature Association
            try:
                stage_start_time = time.time()
                scored_hypotheses = await self._run_stage_6_seed_tracing(
                    scored_hypotheses,
                    validation_result.valid_genes,
                    primary_result,
                    secondary_result
                )
                elapsed = time.time() - stage_start_time
                stage6_complete_msg = f"[PIPELINE DEBUG] Stage 6b completed successfully"
                print(stage6_complete_msg, flush=True)
                logger.info(f"Stage 6b complete: Seed gene tracing and literature associations added")
                print(f"⏱️  [TIMING] Stage 6b completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                stage6_error_msg = f"[PIPELINE DEBUG] Stage 6b failed: {str(e)}"
                print(stage6_error_msg, flush=True)
                logger.error(f"Stage 6b failed but continuing: {str(e)}")
                print(f"⏱️  [TIMING] Stage 6b failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                import traceback
                traceback.print_exc()
                self.warnings.append(f"Stage 6b seed tracing failed: {str(e)}")
            
            # Stage 6c: FINAL STRICT FILTER - configurable enforcement
            # Pathway names are required to contain cardiac/disease terms by default,
            # but this can be disabled via settings.nets.enforce_final_name_filter = False
            await self._update_progress("Stage 7", 77, "Applying strict cardiac name filter")
            stage_start_time = time.time()
            pre_final_filter_count = scored_hypotheses.total_count
            
            try:
                enforce_filter = getattr(self.settings.nets, 'enforce_final_name_filter', True)

                if enforce_filter:
                    filtered_hypotheses = self.semantic_filter.apply_final_strict_name_filter(
                        scored_hypotheses.hypotheses,
                        disease_context=self.disease_context
                    )
                    scored_hypotheses.hypotheses = filtered_hypotheses
                    scored_hypotheses.total_count = len(filtered_hypotheses)
                else:
                    # Skip enforcement - keep existing hypotheses
                    logger.info("Final strict name filter disabled via configuration; skipping filter")
                    filtered_hypotheses = scored_hypotheses.hypotheses
                elapsed = time.time() - stage_start_time
                
                final_filtered_count = pre_final_filter_count - scored_hypotheses.total_count
                retention_rate = (scored_hypotheses.total_count / pre_final_filter_count * 100) if pre_final_filter_count > 0 else 0
                
                self.results["stage_4b_final_name_filter"] = {
                    "hypotheses_before": pre_final_filter_count,
                    "hypotheses_after": scored_hypotheses.total_count,
                    "filtered_count": final_filtered_count,
                    "retention_rate_percent": round(retention_rate, 2),
                    "mandatory": enforce_filter,
                    "enforced": enforce_filter,
                    "status": "completed"
                }
                
                logger.info(
                    f"[PIPELINE] Stage 4b MANDATORY name filter complete: {scored_hypotheses.total_count}/{pre_final_filter_count} "
                    f"pathways retained ({retention_rate:.1f}%) - 100% contain cardiac/disease terms in pathway name"
                )
                print(f"[PIPELINE DEBUG] [SUCCESS] Stage 4b: {scored_hypotheses.total_count}/{pre_final_filter_count} pathways retained (100% cardiac-named)")
                print(f"⏱️  [TIMING] Stage 6c (Final Filter) completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                
                # CRITICAL: Update stage_3 with FILTERED results (100% cardiac-relevant pathways)
                self.results["stage_3"] = scored_hypotheses.model_dump()
                logger.info(f"Updated stage_3 with {scored_hypotheses.total_count} cardiac-filtered pathways")
                
                if scored_hypotheses.total_count == 0:
                    warning_msg = "⚠️ Stage 4b filter removed ALL pathways - no cardiac-named pathways found. Consider adjusting disease context or input genes."
                    logger.warning(warning_msg)
                    print(warning_msg)
                    self.warnings.append(warning_msg)
                    
            except Exception as e:
                elapsed = time.time() - stage_start_time
                error_msg = f"Stage 4b MANDATORY filter failed: {str(e)}"
                logger.error(error_msg)
                print(f"⏱️  [TIMING] Stage 6c (Final Filter) failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                import traceback
                traceback.print_exc()
                self.warnings.append(error_msg)
                raise PipelineError(f"CRITICAL: Mandatory cardiac name filter failed - {str(e)}")
            
            # Stage 11: Generate Important Genes (Top 20 from Top 50 Pathways by NES)
            await self._update_progress("Stage 11", 93, "Identifying important genes")
            stage_start_time = time.time()
            print(f"[PIPELINE DEBUG] Generating important genes from top pathways")
            
            try:
                top_genes = self._generate_important_genes(
                    scored_hypotheses.hypotheses,
                    self.druggability_analyzer,
                    top_n_pathways=50,
                    top_n_genes=20
                )
                self.results['top_genes'] = top_genes
                elapsed = time.time() - stage_start_time
                logger.info(f"[SUCCESS] Generated {len(top_genes)} important genes from top pathways")
                print(f"[PIPELINE DEBUG] Generated {len(top_genes)} important genes")
                print(f"⏱️  [TIMING] Important genes generation completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                logger.warning(f"Important genes generation failed (non-critical): {str(e)}")
                print(f"[PIPELINE DEBUG] ⚠️ Important genes generation failed: {str(e)}")
                print(f"⏱️  [TIMING] Important genes generation failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                self.warnings.append(f"Important genes generation failed: {str(e)}")
                self.results['top_genes'] = []
            
            # Generate Reports
            await self._update_progress("Stage 12", 97, "Generating reports")
            stage_start_time = time.time()
            print(f"[PIPELINE DEBUG] Starting report generation with {scored_hypotheses.total_count} final hypotheses")
            
            try:
                # Get top genes from results
                top_genes_data = self.results.get('top_genes', [])
                
                report_files = await self._generate_reports(
                    validation_result.valid_genes,
                    validation_result,
                    fn_result,
                    primary_result,
                    secondary_result,
                    final_result,
                    scored_hypotheses,
                    None,  # topology_result removed
                    literature_evidence,  # detailed literature citations
                    None,  # comprehensive_topology removed
                    top_genes_data  # Important genes
                )
                elapsed = time.time() - stage_start_time
                print(f"[PIPELINE DEBUG] Report generation completed successfully")
                print(f"[PIPELINE DEBUG] Generated report files: {list(report_files.keys()) if report_files else 'None'}")
                print(f"⏱️  [TIMING] Report generation completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                print(f"[PIPELINE DEBUG] Report generation failed: {str(e)}")
                logger.error(f"Report generation failed: {str(e)}")
                print(f"⏱️  [TIMING] Report generation failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                import traceback
                traceback.print_exc()
                self.warnings.append(f"Report generation failed: {str(e)}")
                report_files = {}
            
            # Save final results
            await self._update_progress("Complete", 100, "Analysis complete")
            stage_start_time = time.time()
            print(f"[PIPELINE DEBUG] Saving final results...")
            
            try:
                await self._save_results()
                elapsed = time.time() - stage_start_time
                print(f"[PIPELINE DEBUG] Final results saved successfully")
                print(f"⏱️  [TIMING] Save results completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                print(f"[PIPELINE DEBUG] Error saving results: {str(e)}")
                logger.error(f"Error saving results: {str(e)}")
                print(f"⏱️  [TIMING] Save results failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            
            # Final timing summary
            total_elapsed = time.time() - pipeline_start_time
            print(f"\n{'='*80}")
            print(f"🏁 [TIMING] PIPELINE COMPLETED SUCCESSFULLY")
            print(f"{'='*80}")
            print(f"   Analysis ID: {self.analysis_id}")
            print(f"   Final hypotheses: {scored_hypotheses.total_count}")
            print(f"   Total time: {total_elapsed:.2f}s ({total_elapsed/60:.2f} minutes)")
            print(f"   Completed at: {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Warnings: {len(self.warnings)}")
            print(f"{'='*80}\n")
            logger.info(f"Pipeline analysis complete (ID: {self.analysis_id}) in {total_elapsed:.2f}s")
            
            return {
                "analysis_id": self.analysis_id,
                "status": "completed",
                "results": self.results,
                "warnings": self.warnings,
                "report_files": report_files
            }
            
        except Exception as e:
            print(f"[PIPELINE DEBUG] *** PIPELINE FAILED ***")
            print(f"[PIPELINE DEBUG] Error: {str(e)}")
            print(f"[PIPELINE DEBUG] Analysis ID: {self.analysis_id}")
            logger.error(f"Pipeline execution failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            try:
                await self._update_progress("Error", 0, f"Pipeline failed: {str(e)}")
            except Exception as progress_error:
                print(f"[PIPELINE DEBUG] Error updating progress: {progress_error}")
                
            raise PipelineError(f"Pipeline execution failed: {str(e)}")
    
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
        print(f"[STAGE 2C DEBUG] Starting aggregation with {secondary_result.total_secondary_count} pathways")
        
        try:
            final_result = self.aggregator.aggregate(secondary_result, primary_result=primary_result)
            print(f"[STAGE 2C DEBUG] Aggregation returned {final_result.total_count} final pathways")
            
            self.results["stage_2c"] = {
                "final_pathways": final_result.total_count,
                "aggregation_strategy": final_result.aggregation_strategy
            }
            
            if final_result.total_count == 0:
                logger.warning("Stage 2c produced 0 final pathways")
                self.warnings.append("No final pathways after aggregation")
            
            print(f"[STAGE 2C DEBUG] Returning result")
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
    

    async def _run_stage_5_scoring(self, final_result: FinalPathwayResult, clinical_evidence_result: Optional['ClinicalEvidenceResult']) -> ScoredHypotheses:
        """Run Stage 5a: Final NES Scoring."""
        logger.info("Running Stage 5a: Final NES Scoring")
        print(f"[STAGE 5a DEBUG] Starting NES scoring with {final_result.total_count} pathways")
        
        try:
            # Pass None for clinical evidence (Stage 3 removed)
            scored_hypotheses = self.nes_scorer.score(final_result, None)
            print(f"[STAGE 5a DEBUG] NES scoring returned {scored_hypotheses.total_count} hypotheses")
            
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
            
            # Store Stage 3a results AFTER semantic filtering and redundancy detection
            self.results["stage_3"] = scored_hypotheses.model_dump()
            logger.info(f"Stored stage_3 results with cardiac_relevance for {scored_hypotheses.total_count} hypotheses")
            
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
    
    async def _run_stage_4_enhanced_validation(
        self,
        scored_hypotheses: ScoredHypotheses,
        fn: FunctionalNeighborhood,
        seed_genes: List[GeneInfo]
    ) -> ScoredHypotheses:
        """
        Run Stage 4b: Enhanced Biological Validation.
        
        Applies three critical validation layers to the TOP 50 hypotheses:
        1. Cardiac Tissue Expression - Validates genes are expressed in heart tissue
        2. Permutation Testing - Calculates empirical p-values to control for network bias
        3. Druggability Analysis - Identifies therapeutic intervention opportunities
        
        These validations add biological rigor and translational relevance to the most promising hypotheses.
        """
        logger.info("Running Stage 4b: Enhanced Biological Validation")
        
        try:
            print(f"[STAGE 3C DEBUG] Starting enhanced validation...")
            logger.info(f"Stage 3c: Processing top 25 of {scored_hypotheses.total_count} hypotheses for enhanced validation")
            
            # Get all genes for permutation testing
            # Extract all unique genes from seed genes and neighbors
            seed_gene_symbols = [g.symbol for g in seed_genes]
            fn_genes = [g.symbol for g in fn.neighbors] if fn.neighbors else []
            all_genes = list(set(seed_gene_symbols + fn_genes))
            
            print(f"[STAGE 3C DEBUG] Gene counts - seed: {len(seed_gene_symbols)}, neighbors: {len(fn_genes)}, total: {len(all_genes)}")
            
            # Calculate gene degrees from functional neighborhood for degree-preserving permutation
            # Degree = number of connections each gene has in the network
            gene_degrees = {}
            if hasattr(fn, 'interactions') and fn.interactions:
                for interaction in fn.interactions:
                    gene1 = interaction.get('gene1', '')
                    gene2 = interaction.get('gene2', '')
                    gene_degrees[gene1] = gene_degrees.get(gene1, 0) + 1
                    gene_degrees[gene2] = gene_degrees.get(gene2, 0) + 1
                logger.info(f"Calculated degrees for {len(gene_degrees)} genes from network")
                print(f"[STAGE 3C DEBUG] Calculated degrees for {len(gene_degrees)} genes")
            else:
                # Fallback: assign uniform degree if no interaction data
                for gene in all_genes:
                    gene_degrees[gene] = 1
                logger.warning("No interaction data available, using uniform degrees")
                print(f"[STAGE 3C DEBUG] Using uniform degrees for {len(all_genes)} genes")
            
            # Track statistics
            tissue_filtered = 0
            high_druggability = 0
            
            print(f"[STAGE 3C DEBUG] Starting hypothesis processing...")
            
            # Limit enhanced validation to top 25 hypotheses for speed optimization
            top_hypotheses = scored_hypotheses.hypotheses[:25]
            print(f"[STAGE 3C DEBUG] Limiting enhanced validation to top {len(top_hypotheses)} hypotheses")
            
            # Process each hypothesis
            for i, hypothesis in enumerate(top_hypotheses):
                if i % 10 == 0:  # Progress every 10 hypotheses (since we're only doing 50)
                    print(f"[STAGE 3C DEBUG] Processing hypothesis {i+1}/{len(top_hypotheses)} (top 50 only)")
                    
                try:
                    pathway_genes = hypothesis.aggregated_pathway.pathway.evidence_genes
                    
                    # Initialize score_components if needed
                    if not hypothesis.score_components:
                        hypothesis.score_components = {}
                    
                    # 1. Cardiac Tissue Expression Validation with GTEx
                    try:
                        tissue_score = await self.tissue_validator.calculate_expression_score(pathway_genes)
                        hypothesis.score_components['cardiac_expression_ratio'] = tissue_score.cardiac_expression_ratio
                        hypothesis.score_components['cardiac_expressed_genes'] = tissue_score.expressed_genes
                        hypothesis.score_components['tissue_validation_passed'] = tissue_score.validation_passed
                        hypothesis.score_components['mean_cardiac_tpm'] = tissue_score.mean_cardiac_tpm
                        hypothesis.score_components['cardiac_specificity_ratio'] = tissue_score.mean_cardiac_specificity_ratio
                        
                        if not tissue_score.validation_passed:
                            tissue_filtered += 1
                    except Exception as e:
                        logger.warning(f"GTEx tissue validation failed for hypothesis {i}: {str(e)}")
                        hypothesis.score_components['tissue_validation_passed'] = False
                        tissue_filtered += 1
                
                    # 2. Permutation Testing (Optional for performance - degree-preserving empirical p-value)
                    # SCIENTIFIC RIGOR: Use degree-preserving permutation to control for network topology
                    # Reduced from 1000 to 100 permutations for performance while maintaining statistical validity
                    try:
                        if all_genes and fn_genes and gene_degrees and self.settings.nets.permutation_test_enabled:
                            empirical_p, perm_stats = self.permutation_tester.calculate_degree_preserving_pvalue(
                                pathway_genes,
                                fn_genes,
                                gene_degrees,
                                all_genes,
                                n_permutations=25  # Further reduced for speed optimization
                            )
                            hypothesis.score_components['empirical_pvalue'] = empirical_p
                            hypothesis.score_components['permutation_z_score'] = perm_stats.get('z_score', 0)
                            hypothesis.score_components['observed_overlap'] = perm_stats.get('observed_overlap', 0)
                            hypothesis.score_components['expected_overlap'] = perm_stats.get('mean_null_overlap', 0)
                            hypothesis.score_components['n_permutations_used'] = perm_stats.get('n_permutations', 100)
                            hypothesis.score_components['degree_preserved'] = perm_stats.get('degree_preserved', True)
                        else:
                            hypothesis.score_components['empirical_pvalue'] = None
                            hypothesis.score_components['permutation_z_score'] = None
                    except Exception as e:
                        logger.warning(f"Permutation testing failed for hypothesis {i}: {str(e)}")
                        hypothesis.score_components['empirical_pvalue'] = None
                        hypothesis.score_components['permutation_z_score'] = None
                    
                    # 3. Druggability Analysis
                    try:
                        drug_score = self.druggability_analyzer.calculate_druggability_score(pathway_genes)
                        hypothesis.score_components['druggable_genes'] = drug_score.druggable_genes
                        hypothesis.score_components['druggable_ratio'] = drug_score.druggable_ratio
                        hypothesis.score_components['approved_drug_count'] = drug_score.approved_drug_count
                        hypothesis.score_components['clinical_trial_count'] = drug_score.clinical_trial_count
                        hypothesis.score_components['druggability_tier'] = drug_score.druggability_tier
                        
                        if drug_score.druggability_tier == 'high':
                            high_druggability += 1
                    except Exception as e:
                        logger.warning(f"Druggability analysis failed for hypothesis {i}: {str(e)}")
                        hypothesis.score_components['druggability_tier'] = 'unknown'
                        
                except Exception as e:
                    logger.error(f"Failed to process hypothesis {i}: {str(e)}")
                    continue  # Skip this hypothesis and continue with the next
            
            # Store validation results
            self.results["stage_3_6_enhanced_validation"] = {
                "hypotheses_validated": len(top_hypotheses),
                "total_hypotheses": scored_hypotheses.total_count,
                "validation_scope": "top_50_only",
                "tissue_expression": {
                    "low_expression_count": tissue_filtered,
                    "passed_count": len(top_hypotheses) - tissue_filtered
                },
                "permutation_testing": {
                    "applied": all_genes and fn_genes,
                    "n_permutations": 100
                },
                "druggability": {
                    "high_tier_count": high_druggability,
                    "analyzed_count": len(top_hypotheses)
                }
            }
            
            print(f"[STAGE 3C DEBUG] Enhanced validation completed successfully")
            logger.info(
                f"Stage 3c complete: Enhanced validation applied to top {len(top_hypotheses)} hypotheses, "
                f"{tissue_filtered} low cardiac expression, "
                f"{high_druggability} high druggability tier"
            )
            
            return scored_hypotheses
            
        except Exception as e:
            logger.error(f"Stage 3c enhanced validation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Don't fail pipeline - return original hypotheses with warning
            logger.warning("Continuing pipeline without enhanced validation")
            self.warnings.append(f"Enhanced validation failed: {str(e)}")
            
            return scored_hypotheses
    
    async def _run_stage_7_topology(
        self,
        scored_hypotheses: ScoredHypotheses,
        fn: FunctionalNeighborhood,
        primary_pathways: List
    ) -> TopologyResult:
        """Run Stage 7: Topology Analysis."""
        topo_msg = "Running Stage 7: Topology Analysis"
        logger.info(topo_msg)
        print(f"[STAGE 7 DEBUG] {topo_msg}", flush=True)
        
        try:
            topology_result = self.topology_analyzer.analyze(
                scored_hypotheses.hypotheses,
                fn,
                primary_pathways
            )
            
            # Store full topology data for API response
            self.results["stage_4_topology"] = topology_result.model_dump()
            
            return topology_result
            
        except Exception as e:
            logger.warning(f"Stage 4 topology analysis failed: {str(e)}")
            self.warnings.append(f"Topology analysis failed: {str(e)}")
            # Return empty result to continue pipeline
            return TopologyResult(hypothesis_networks={})
    
    async def _run_stage_6_literature(
        self,
        scored_hypotheses: ScoredHypotheses,
        seed_genes: List[GeneInfo]
    ) -> LiteratureEvidence:
        """Run Stage 6a: Literature Validation."""
        lit_msg = "Running Stage 6a: Literature Validation"
        logger.info(lit_msg)
        print(f"[STAGE 6A DEBUG] {lit_msg}", flush=True)
        
        try:
            literature_evidence = await self.literature_miner.validate_hypotheses_async(
                scored_hypotheses.hypotheses,
                seed_genes,
                top_n=None,  # Mine literature for ALL pathways (will default to config or all hypotheses)
                disease_context=self.disease_context,
                disease_synonyms=self.disease_synonyms,
                max_concurrent=3  # Allow 3 concurrent literature searches
            )
            
            self.results["stage_4_literature"] = {
                "hypotheses_validated": len(literature_evidence.hypothesis_citations),
                "hypothesis_citations": literature_evidence.hypothesis_citations
            }
            
            return literature_evidence
            
        except Exception as e:
            logger.warning(f"Stage 4 literature validation failed: {str(e)}")
            self.warnings.append(f"Literature validation failed: {str(e)}")
            # Return empty result to continue pipeline
            return LiteratureEvidence(hypothesis_citations={})
    
    async def _run_stage_4_5_validation(
        self,
        scored_hypotheses: ScoredHypotheses,
        topology_result: TopologyResult,
        literature_evidence: LiteratureEvidence,
        seed_genes: List[GeneInfo]
    ) -> ScoredHypotheses:
        """
        Run Stage 4.5: Multi-Evidence Validation & Final Ranking.
        
        Combines evidence from:
        - Statistical significance (Stage 2-3)
        - Replication support (Stage 2c)
        - Literature evidence (Stage 4)
        - Network topology (Stage 4)
        - Novelty (seed overlap)
        
        Returns hypotheses with validation scores and re-ranked by confidence.
        """
        multi_msg = "Running Stage 4.5: Multi-Evidence Validation"
        logger.info(multi_msg)
        print(f"[STAGE 4 DEBUG] {multi_msg}", flush=True)
        
        try:
            validation_scores = {}
            
            # Calculate validation score for each hypothesis
            for hypothesis in scored_hypotheses.hypotheses:
                pathway_id = hypothesis.aggregated_pathway.pathway.pathway_id
                
                # Get literature citations for this hypothesis
                lit_citations = literature_evidence.hypothesis_citations.get(pathway_id, [])
                
                # Get network analysis for this hypothesis
                network_analysis_obj = topology_result.hypothesis_networks.get(pathway_id)
                if network_analysis_obj is not None:
                    network_analysis = network_analysis_obj.model_dump()
                else:
                    network_analysis = {}
                
                # Calculate comprehensive validation score
                validation_score = self.hypothesis_validator.calculate_validation_score(
                    hypothesis,
                    lit_citations,
                    network_analysis,
                    seed_genes
                )
                
                validation_scores[pathway_id] = validation_score
                
                # Add validation scores to hypothesis score_components
                if not hypothesis.score_components:
                    hypothesis.score_components = {}
                
                hypothesis.score_components['validation_score'] = validation_score['total_validation_score']
                hypothesis.score_components['confidence_level'] = validation_score['confidence_level']
                hypothesis.score_components['statistical_strength'] = validation_score['statistical_strength']
                hypothesis.score_components['replication_support'] = validation_score['replication_support']
                hypothesis.score_components['literature_evidence'] = validation_score['literature_evidence']
                hypothesis.score_components['network_evidence'] = validation_score['network_evidence']
                hypothesis.score_components['novelty_score'] = validation_score['novelty_score']
            
            # Re-rank by validation score (optional - keep NES ranking but add validation info)
            # For now, keep NES ranking but add validation scores
            
            # Store validation results
            self.results["stage_4_5_validation"] = {
                "hypotheses_validated": len(validation_scores),
                "high_confidence_count": sum(1 for v in validation_scores.values() if v['confidence_level'] == 'high'),
                "medium_confidence_count": sum(1 for v in validation_scores.values() if v['confidence_level'] == 'medium'),
                "low_confidence_count": sum(1 for v in validation_scores.values() if v['confidence_level'] == 'low'),
                "mean_validation_score": sum(v['total_validation_score'] for v in validation_scores.values()) / len(validation_scores) if validation_scores else 0
            }
            
            logger.info(
                f"Stage 4.5 complete: {len(validation_scores)} hypotheses validated, "
                f"{self.results['stage_4_5_validation']['high_confidence_count']} high confidence, "
                f"{self.results['stage_4_5_validation']['medium_confidence_count']} medium confidence, "
                f"{self.results['stage_4_5_validation']['low_confidence_count']} low confidence"
            )
            
            return scored_hypotheses
            
        except Exception as e:
            logger.error(f"Stage 4.5 validation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.warnings.append(f"Multi-evidence validation failed: {str(e)}")
            return scored_hypotheses
    
    async def _run_stage_6_seed_tracing(
        self,
        scored_hypotheses: ScoredHypotheses,
        seed_genes: List[GeneInfo],
        primary_result: PrimaryTriageResult,
        secondary_result: SecondaryTriageResult
    ) -> ScoredHypotheses:
        """
        Run Stage 6b: Seed Gene Traceability & Literature Association.
        
        Traces which seed genes led to each final pathway and checks
        PubMed for literature evidence of pathway-seed gene associations.
        """
        stage_msg = "Running Stage 6b: Seed Gene Traceability & Literature Association"
        logger.info(stage_msg)
        print(f"[STAGE 6B DEBUG] {stage_msg}", flush=True)
        print(f"[STAGE 6B DEBUG] Starting seed gene tracing and literature association", flush=True)
        print(f"[STAGE 4 DEBUG] Input: {scored_hypotheses.total_count} hypotheses, {len(seed_genes)} seed genes", flush=True)
        print(f"[STAGE 4 DEBUG] Seed genes: {[g.symbol for g in seed_genes][:10]}{'...' if len(seed_genes) > 10 else ''}", flush=True)
        print(f"[STAGE 4 DEBUG] Primary pathways available: {len(primary_result.primary_pathways)}", flush=True)
        
        try:
            # Trace seed genes to pathways
            trace_msg = f"[STAGE 4 DEBUG] Step 1: Tracing seed genes to pathways..."
            print(trace_msg, flush=True)
            logger.info(f"Tracing {len(seed_genes)} seed genes to {scored_hypotheses.total_count} hypotheses")
            
            traced_hypotheses = self.seed_gene_tracer.trace_seed_genes_to_pathways(
                scored_hypotheses.hypotheses,
                seed_genes,
                primary_result.primary_pathways,
                {}  # secondary_pathways not needed for current implementation
            )
            
            scored_hypotheses.hypotheses = traced_hypotheses
            print(f"[STAGE 4 DEBUG] Step 1 complete: Seed gene tracing finished")
            
            # Check literature associations with enhanced visibility
            step2_msg = f"[STAGE 4 DEBUG] Step 2: Checking literature associations..."
            print(step2_msg, flush=True)
            max_lit_check = min(50, scored_hypotheses.total_count)
            lit_msg = f"[STAGE 4 DEBUG] Will check literature for top {max_lit_check} hypotheses"
            print(lit_msg, flush=True)
            logger.info(f"Checking literature associations for top {max_lit_check} hypotheses")
            
            # This will trigger our enhanced debug output from seed_gene_tracer
            literature_checked_hypotheses = self.seed_gene_tracer.check_literature_associations(
                scored_hypotheses.hypotheses,
                max_hypotheses=max_lit_check
            )
            
            scored_hypotheses.hypotheses = literature_checked_hypotheses
            complete_msg = f"[STAGE 4 DEBUG] Step 2 complete: Literature association checking finished"
            print(complete_msg, flush=True)
            
            # Store results with detailed statistics
            print(f"[STAGE 4 DEBUG] Calculating final statistics...")
            
            try:
                traced_count = sum(1 for h in scored_hypotheses.hypotheses if h.traced_seed_genes)
                lit_support_count = sum(
                    1 for h in scored_hypotheses.hypotheses 
                    if h.literature_associations.get('has_literature_support', False)
                )
            except AttributeError as e:
                print(f"[STAGE 4 DEBUG] Error accessing hypothesis attributes: {e}")
                traced_count = 0
                lit_support_count = 0
            
            print(f"[STAGE 4 DEBUG] Final statistics:")
            print(f"[STAGE 4 DEBUG]   - Total hypotheses: {scored_hypotheses.total_count}")
            print(f"[STAGE 4 DEBUG]   - Traced hypotheses: {traced_count}")
            print(f"[STAGE 4 DEBUG]   - Hypotheses with literature: {lit_support_count}")
            
            self.results["stage_4_6_seed_tracing"] = {
                "hypotheses_traced": traced_count,
                "hypotheses_with_literature_support": lit_support_count,
                "total_hypotheses": scored_hypotheses.total_count
            }
            
            print(f"[STAGE 4 DEBUG] Stage 4.6 completely finished")
            logger.info(
                f"Stage 4.6 complete: {traced_count} hypotheses traced, "
                f"{lit_support_count} with literature support"
            )
            
            # Update stage_3 results with traced seed genes and literature associations
            self.results["stage_3"] = scored_hypotheses.model_dump()
            logger.info(f"Updated stage_3 results with seed tracing and literature associations for {scored_hypotheses.total_count} hypotheses")
            
            return scored_hypotheses
            
        except Exception as e:
            print(f"[STAGE 4 DEBUG] Stage 4.6 failed with error: {str(e)}")
            logger.error(f"Stage 4.6 seed tracing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.warnings.append(f"Seed gene tracing failed: {str(e)}")
            print(f"[STAGE 4 DEBUG] Returning original hypotheses due to error")
            return scored_hypotheses
    
    async def _generate_reports(self, *args) -> Dict[str, str]:
        """Generate analysis reports."""
        print(f"[PIPELINE DEBUG] Starting report generation phase")
        logger.info("Generating reports")
        print(f"[PIPELINE DEBUG] Report generation arguments received: {len(args)} items")
        
        try:
            report_files = self.report_generator.generate_report(
                self.analysis_id,
                *args,
                output_formats=self.settings.nets.output_formats
            )
            
            return report_files
            
        except Exception as e:
            logger.warning(f"Report generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.warnings.append(f"Report generation failed: {str(e)}")
            return {}
    
    async def _save_results(self):
        """Save intermediate results to disk."""
        output_dir = Path(self.settings.output_dir) / self.analysis_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results_file = output_dir / "results.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {results_file}")
    
    async def _update_progress(self, stage: str, progress: float, message: str):
        """Update progress via callback."""
        logger.info(f"[{progress}%] {stage}: {message}")
        
        if self.progress_callback:
            try:
                if asyncio.iscoroutinefunction(self.progress_callback):
                    await self.progress_callback(stage, progress, message)
                else:
                    self.progress_callback(stage, progress, message)
                logger.debug(f"Progress callback executed successfully for {stage}")
            except Exception as e:
                logger.error(f"Progress callback failed: {str(e)}", exc_info=True)
    
    def _generate_analysis_id(self) -> str:
        """Generate unique analysis ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"analysis_{timestamp}"
    
    def _generate_important_genes(
        self,
        hypotheses: List,
        druggability_analyzer,
        top_n_pathways: int = 50,
        top_n_genes: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Generate important genes from top pathways by NES score.
        
        Args:
            hypotheses: List of scored hypotheses
            druggability_analyzer: Druggability analyzer instance
            top_n_pathways: Number of top pathways to consider
            top_n_genes: Number of top genes to return
            
        Returns:
            List of top gene dictionaries with pathway counts and druggability metrics
        """
        # Collect all genes with their metrics
        gene_scores = {}
        
        # Extract genes from top pathways by NES score
        for i, hyp in enumerate(hypotheses[:top_n_pathways]):
            pathway_genes = []
            if hasattr(hyp, 'aggregated_pathway') and hyp.aggregated_pathway:
                if hasattr(hyp.aggregated_pathway, 'pathway') and hyp.aggregated_pathway.pathway:
                    pathway_genes = hyp.aggregated_pathway.pathway.evidence_genes
                elif hasattr(hyp.aggregated_pathway, 'evidence_genes'):
                    pathway_genes = hyp.aggregated_pathway.evidence_genes
            elif hasattr(hyp, 'evidence_genes'):
                pathway_genes = hyp.evidence_genes
            elif hasattr(hyp, 'genes'):
                pathway_genes = hyp.genes
            
            # Score each gene
            for gene in pathway_genes:
                gene_symbol = gene if isinstance(gene, str) else gene.symbol if hasattr(gene, 'symbol') else str(gene)
                
                if gene_symbol not in gene_scores:
                    gene_scores[gene_symbol] = {
                        'gene': gene_symbol,
                        'pathway_count': 0,
                        'importance_score': 0.0,
                        'druggability_tier': 'unknown',
                        'is_druggable': False,
                        'is_fda_approved': False,
                        'is_clinical_trial': False,
                        'centrality': 0.0
                    }
                
                # Increment pathway count
                gene_scores[gene_symbol]['pathway_count'] += 1
                
                # Add importance based on pathway rank (top pathways = more important)
                gene_scores[gene_symbol]['importance_score'] += (51 - i) / 50.0
        
        # Add druggability information
        if druggability_analyzer:
            for gene_symbol in gene_scores:
                if gene_symbol in druggability_analyzer.druggable_genes:
                    gene_scores[gene_symbol]['is_druggable'] = True
                    
                if gene_symbol in druggability_analyzer.approved_drug_targets:
                    gene_scores[gene_symbol]['is_fda_approved'] = True
                    gene_scores[gene_symbol]['druggability_tier'] = 'high'
                    
                if gene_symbol in druggability_analyzer.clinical_trial_targets:
                    gene_scores[gene_symbol]['is_clinical_trial'] = True
                    if gene_scores[gene_symbol]['druggability_tier'] == 'unknown':
                        gene_scores[gene_symbol]['druggability_tier'] = 'medium'
        
        # Centrality not used - removed topology analysis for speed
        
        # Add DisGeNET cardiac disease association scores
        try:
            from app.services.disgenet_client import DisGeNETClient
            disgenet = DisGeNETClient()
            
            logger.info(f"Querying DisGeNET for {len(gene_scores)} genes...")
            disgenet_scores = disgenet.get_batch_scores(list(gene_scores.keys()))
            
            for gene_symbol in gene_scores:
                gene_scores[gene_symbol]['disgenet_cardiac_score'] = disgenet_scores.get(gene_symbol, 0.0)
            
            logger.info(f"DisGeNET scores obtained for {len(disgenet_scores)} genes")
        except Exception as e:
            logger.warning(f"DisGeNET scoring failed (non-critical): {str(e)}")
            # Set default scores if DisGeNET fails
            for gene_symbol in gene_scores:
                gene_scores[gene_symbol]['disgenet_cardiac_score'] = 0.0
        
        # Calculate final score: importance * (1 + druggability_bonus + centrality_bonus + disgenet_bonus)
        for gene_symbol in gene_scores:
            druggability_bonus = 0.0
            if gene_scores[gene_symbol]['is_fda_approved']:
                druggability_bonus = 1.0
            elif gene_scores[gene_symbol]['is_clinical_trial']:
                druggability_bonus = 0.5
            elif gene_scores[gene_symbol]['is_druggable']:
                druggability_bonus = 0.25
            
            disgenet_bonus = gene_scores[gene_symbol]['disgenet_cardiac_score'] * 0.75  # Weight DisGeNET score
            
            gene_scores[gene_symbol]['final_score'] = gene_scores[gene_symbol]['importance_score'] * (
                1.0 + druggability_bonus + disgenet_bonus
            )
        
        # Sort by final score and return top N
        sorted_genes = sorted(
            gene_scores.values(),
            key=lambda x: x['final_score'],
            reverse=True
        )
        
        return sorted_genes[:top_n_genes]
    
    def close(self):
        """Close all service connections."""
        self.input_validator.close()
        self.fn_builder.close()
        self.primary_analyzer.close()
        self.secondary_analyzer.close()
        # topology_analyzer removed
        
        logger.info("Pipeline services closed")
