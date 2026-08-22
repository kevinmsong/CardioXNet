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
from app.services.gene_background import background_with, BACKGROUND_SOURCE, BACKGROUND_RETRIEVED
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Raised when pipeline execution fails."""


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

        # Disease context for semantic filtering and literature search
        # (must be initialized before config_overrides so overrides can set them)
        self.disease_context = None
        self.disease_synonyms = []

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
        
        # Stage 3: Clinical Evidence Integrator (REMOVED - GWAS API deprecated)
        # disease_context = getattr(self, 'disease_context', 'cardiovascular')
        # self.clinical_evidence_integrator = ClinicalEvidenceIntegrator(disease_context=disease_context)
        
        # Stage 7: Comprehensive Network Topology Analyzer
        from app.services.comprehensive_topology import ComprehensiveTopologyAnalyzer
        self.comprehensive_topology = ComprehensiveTopologyAnalyzer()
        
        self.literature_miner = LiteratureMiner()
        self.hypothesis_validator = HypothesisValidator()
        self.seed_gene_tracer = SeedGeneTracer()
        self.report_generator = ReportGenerator()

        # Sync any config overrides into sub-services that hold their own settings copy
        if config_overrides:
            self._sync_settings_to_services()

        # Pipeline state
        self.results = {}
        self.warnings = []
        self.progress_callback = None

        logger.info(f"CardioXNetPipeline initialized (ID: {self.analysis_id})")

    def _sync_settings_to_services(self) -> None:
        """Push pipeline-level settings overrides into sub-services."""
        nets = self.settings.nets

        # Literature miner and its PubMed client
        self.literature_miner.settings = self.settings
        if hasattr(self.literature_miner, 'pubmed_client'):
            self.literature_miner.pubmed_client.max_results = nets.pubmed_max_results

        # Seed gene tracer PubMed client
        if hasattr(self.seed_gene_tracer, 'pubmed_client'):
            self.seed_gene_tracer.pubmed_client.max_results = nets.pubmed_max_results

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
        
        try:
            # Stage 0: Input Validation
            await self._update_progress("input_validation", 5, "Validating input")
            stage_start_time = time.time()
            validation_result = await self._run_stage_0(seed_genes)
            elapsed = time.time() - stage_start_time
            logger.info(f"[TIMING] Stage 0 completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            
            # Stage 1: Functional Neighborhood Assembly
            await self._update_progress("functional_neighborhood", 15, "Building functional neighborhood")
            stage_start_time = time.time()
            fn_result = await self._run_stage_1(validation_result.valid_genes)
            elapsed = time.time() - stage_start_time
            logger.info(f"[TIMING] Stage 1 completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            
            # Stage 2a: Primary Pathway Enrichment
            await self._update_progress("primary_pathway", 25, "Primary pathway enrichment")
            stage_start_time = time.time()
            primary_result = await self._run_stage_2a(fn_result)
            elapsed = time.time() - stage_start_time
            logger.info(f"[TIMING] Stage 2a completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            
            # Stage 2b: Secondary Pathway Discovery
            await self._update_progress("secondary_pathway", 40, "Secondary pathway discovery")
            stage_start_time = time.time()
            secondary_result = await self._run_stage_2b(
                primary_result,
                validation_result.valid_genes
            )
            elapsed = time.time() - stage_start_time
            logger.info(f"[TIMING] Stage 2b completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            
            # Stage 2c: Pathway Aggregation
            await self._update_progress("pathway_aggregation", 55, "Aggregating pathways")
            stage_start_time = time.time()
            final_result = await self._run_stage_2c(secondary_result, primary_result)
            elapsed = time.time() - stage_start_time
            logger.info(f"Stage 2c complete: {final_result.total_count} final pathways")
            logger.info(f"[TIMING] Stage 2c completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            await self._update_progress("pathway_aggregation", 60, f"Pathway aggregation complete: {final_result.total_count} pathways")
            
            # Stage 5a: Final NES Scoring
            await self._update_progress("nes_scoring", 65, "Calculating NES scores")
            stage_start_time = time.time()
            logger.info(f"[PIPELINE] Calling Stage 5a with {final_result.total_count} pathways")
            scored_hypotheses = await self._run_stage_5_scoring(final_result, None, fn_result=fn_result)
            elapsed = time.time() - stage_start_time
            logger.info(f"Stage 5a complete: {scored_hypotheses.total_count} scored hypotheses")
            logger.info(f"[TIMING] Stage 5a completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            await self._update_progress("nes_scoring", 70, f"NES scoring complete: {scored_hypotheses.total_count} hypotheses")
            
            # Stage 4a: Semantic Filtering (Cardiac Relevance Boost)
            await self._update_progress("semantic_filtering", 72, "Applying semantic cardiac relevance filtering")
            stage_start_time = time.time()
            scored_hypotheses = await self._run_stage_4_semantic(scored_hypotheses)
            elapsed = time.time() - stage_start_time
            logger.info(f"Stage 4a complete: {scored_hypotheses.total_count} hypotheses after semantic filtering")
            logger.info(f"[TIMING] Stage 4a completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            await self._update_progress("semantic_filtering", 76, f"Semantic filtering complete: {scored_hypotheses.total_count} hypotheses")
            
            # Stage 4b: Enhanced Biological Validation (Tissue Expression, Permutation, Druggability)
            await self._update_progress("enhanced_validation", 78, "Applying enhanced biological validation")
            stage_start_time = time.time()
            logger.info(f"Starting Stage 8 enhanced validation with {scored_hypotheses.total_count} hypotheses")
            
            try:
                scored_hypotheses = await self._run_stage_4_enhanced_validation(
                    scored_hypotheses,
                    fn_result,
                    validation_result.valid_genes
                )
                elapsed = time.time() - stage_start_time
                logger.info(f"Stage 8 complete: Enhanced validation applied to {scored_hypotheses.total_count} hypotheses")
                logger.info(f"[TIMING] Stage 8 completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                await self._update_progress("enhanced_validation", 84, f"Enhanced validation complete")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                logger.info(f"[PIPELINE] Stage 8 failed: {str(e)}")
                logger.error(f"Stage 8 failed but continuing pipeline: {str(e)}")
                logger.info(f"[TIMING] Stage 8 failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                import traceback
                traceback.print_exc()
                self.warnings.append(f"Stage 8 enhanced validation failed: {str(e)}")
                await self._update_progress("enhanced_validation", 84, f"Enhanced validation failed, continuing")
            
            # Stage 6: Literature Mining & Seed Gene Traceability
            await self._update_progress("literature_mining", 85, "Mining literature and tracing seed genes")
            stage_6_start = time.time()
            
            # Stage 6a: Literature Mining (detailed citations)
            try:
                stage_start_time = time.time()
                literature_evidence = await self._run_stage_6_literature(
                    scored_hypotheses,
                    validation_result.valid_genes
                )
                elapsed = time.time() - stage_start_time
                logger.info(f"Stage 6a complete: Literature mining found citations for {len(literature_evidence.hypothesis_citations)} hypotheses")
                logger.info(f"[TIMING] Stage 6a completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                literature_error_msg = f"[PIPELINE DEBUG] Stage 6a literature mining failed: {str(e)}"
                logger.error(f"Stage 6a literature mining failed but continuing: {str(e)}")
                logger.info(f"[TIMING] Stage 6a failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
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
                logger.info(f"Stage 6b complete: Seed gene tracing and literature associations added")
                logger.info(f"[TIMING] Stage 6b completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                stage6_error_msg = f"[PIPELINE DEBUG] Stage 6b failed: {str(e)}"
                logger.error(f"Stage 6b failed but continuing: {str(e)}")
                logger.info(f"[TIMING] Stage 6b failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                import traceback
                traceback.print_exc()
                self.warnings.append(f"Stage 6b seed tracing failed: {str(e)}")
            
            # Stage 6c: FINAL STRICT FILTER - configurable enforcement
            # Pathway names are required to contain cardiac/disease terms by default,
            # but this can be disabled via settings.nets.enforce_final_name_filter = False
            # NOTE: This is part of literature_mining stage (already at 85%), no need to update progress
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
                
                # Not all retained pathways are cardiac-named: the filter also
                # keeps pathways that clear the semantic-rescue bar. The previous
                # log line asserted "100% cardiac-named", which was false whenever
                # a rescue fired.
                logger.info(
                    f"[PIPELINE] Final name filter complete: {scored_hypotheses.total_count}/{pre_final_filter_count} "
                    f"pathways retained ({retention_rate:.1f}%) via cardiac name match or semantic rescue"
                )
                logger.info(f"[TIMING] Stage 6c (Final Filter) completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                
                if scored_hypotheses.total_count == 0:
                    warning_msg = "⚠️ Stage 4b filter removed ALL pathways - no cardiac-named pathways found. Consider adjusting disease context or input genes."
                    logger.warning(warning_msg)
                    self.warnings.append(warning_msg)
                    
            except Exception as e:
                elapsed = time.time() - stage_start_time
                error_msg = f"Stage 4b MANDATORY filter failed: {str(e)}"
                logger.error(error_msg)
                logger.info(f"[TIMING] Stage 6c (Final Filter) failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                import traceback
                traceback.print_exc()
                self.warnings.append(error_msg)
                raise PipelineError(f"CRITICAL: Mandatory cardiac name filter failed - {str(e)}")
            
            # Stage 7: Comprehensive Network Topology Analysis
            await self._update_progress("topology_analysis", 91, "Analyzing network topology")
            stage_start_time = time.time()
            
            comprehensive_topology_result = None
            try:
                # Prepare druggability data for topology analysis
                druggability_data = {
                    'druggable_genes': self.druggability_analyzer.druggable_genes,
                    'approved_drug_targets': self.druggability_analyzer.approved_drug_targets,
                    'clinical_trial_targets': self.druggability_analyzer.clinical_trial_targets,
                    'gene_to_drugs': {}  # Could be populated from druggability analyzer if available
                }
                
                # Run comprehensive topology analysis on top 50 pathways
                comprehensive_topology_result = self.comprehensive_topology.analyze(
                    top_pathways=scored_hypotheses.hypotheses,
                    string_network=fn_result.model_dump(),
                    druggability_data=druggability_data,
                    top_n=50
                )
                
                # Store results
                self.results['stage_7_topology'] = comprehensive_topology_result.to_dict()
                elapsed = time.time() - stage_start_time
                
                logger.info(f"[SUCCESS] Stage 7 complete: {len(comprehensive_topology_result.hub_genes)} hubs, "
                           f"{len(comprehensive_topology_result.therapeutic_targets)} therapeutic targets identified")
                logger.info(f"[PIPELINE DEBUG] [SUCCESS] Stage 7: Identified {len(comprehensive_topology_result.hub_genes)} hub genes, "
                      f"{len(comprehensive_topology_result.therapeutic_targets)} therapeutic targets")
                logger.info(f"[TIMING] Stage 7 completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                
                # Stage 11: Therapeutic Targets Generation
                await self._update_progress("therapeutic_targets", 95, "Identifying therapeutic target candidates")
                try:
                    top_genes = self._generate_top_genes(
                        scored_hypotheses.hypotheses,
                        self.druggability_analyzer,
                        comprehensive_topology_result,
                        fn_result,
                        top_n=20  # Top 20 genes by count across ALL final pathways
                    )
                    self.results['top_genes'] = top_genes
                    logger.info(f"[SUCCESS] Generated {len(top_genes)} top therapeutic target candidates")
                    logger.info(f"[PIPELINE DEBUG] Generated {len(top_genes)} top genes")
                except Exception as top_genes_error:
                    logger.warning(f"Top genes generation failed (non-critical): {str(top_genes_error)}")
                    self.results['top_genes'] = []
                
            except Exception as e:
                elapsed = time.time() - stage_start_time
                logger.warning(f"Stage 7 topology analysis failed (non-critical): {str(e)}")
                logger.info(f"[PIPELINE DEBUG] Stage 7 failed: {str(e)}")
                logger.info(f"[TIMING] Stage 7 failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                self.warnings.append(f"Stage 7 topology analysis failed: {str(e)}")
                # Non-critical failure - continue pipeline
            
            # Stage 8: Multi-Evidence Validation, Novelty and Discovery Scoring.
            #
            # This stage computes the Discovery Score -- the primary output of the
            # tool -- and was previously defined but never invoked, so every run
            # emitted discovery_score = null, novelty_tier = "" and
            # literature_saturation = null. It runs here because it consumes both
            # the literature evidence (Stage 6a) and the network topology
            # (Stage 7).
            await self._update_progress("discovery_scoring", 96, "Scoring novelty and discovery")
            stage_start_time = time.time()
            try:
                scored_hypotheses = await self._run_stage_4_5_validation(
                    scored_hypotheses,
                    comprehensive_topology_result,
                    literature_evidence,
                    validation_result.valid_genes,
                    fn_result=fn_result,
                )
                elapsed = time.time() - stage_start_time
                logger.info(
                    f"[TIMING] Stage 8 discovery scoring completed in {elapsed:.2f}s "
                    f"(Total: {time.time() - pipeline_start_time:.2f}s)"
                )
            except Exception as e:
                logger.error(f"Stage 8 discovery scoring failed but continuing: {str(e)}")
                import traceback
                traceback.print_exc()
                self.warnings.append(f"Stage 8 discovery scoring failed: {str(e)}")

            # Generate Reports
            await self._update_progress("report_generation", 97, "Generating reports")
            stage_start_time = time.time()
            
            try:
                # Get comprehensive topology and top genes from results
                comprehensive_topology_data = self.results.get('stage_7_topology')
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
                    comprehensive_topology_data,  # Stage 7 comprehensive topology
                    top_genes_data  # Top therapeutic target candidates
                )
                elapsed = time.time() - stage_start_time
                logger.info(f"[PIPELINE DEBUG] Generated report files: {list(report_files.keys()) if report_files else 'None'}")
                logger.info("  [TIMING] Report generation completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                logger.info(f"[PIPELINE DEBUG] Report generation failed: {str(e)}")
                logger.error(f"Report generation failed: {str(e)}")
                logger.info("  [TIMING] Report generation failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
                import traceback
                traceback.print_exc()
                self.warnings.append(f"Report generation failed: {str(e)}")
                report_files = {}
            
            # Save final results
            await self._update_progress("complete", 100, "Analysis complete")
            stage_start_time = time.time()
            
            try:
                await self._save_results()
                elapsed = time.time() - stage_start_time
                logger.info("  [TIMING] Save results completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            except Exception as e:
                elapsed = time.time() - stage_start_time
                logger.info(f"[PIPELINE DEBUG] Error saving results: {str(e)}")
                logger.error(f"Error saving results: {str(e)}")
                logger.info("  [TIMING] Save results failed after {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            
            # Final timing summary
            total_elapsed = time.time() - pipeline_start_time
            logger.info("[TIMING] PIPELINE COMPLETED SUCCESSFULLY")
            logger.info(f"Pipeline analysis complete (ID: {self.analysis_id}) in {total_elapsed:.2f}s")
            
            return {
                "analysis_id": self.analysis_id,
                "status": "completed",
                "results": self.results,
                "warnings": self.warnings,
                "report_files": report_files
            }
            
        except Exception as e:
            pass
            logger.info(f"[PIPELINE DEBUG] Error: {str(e)}")
            logger.error(f"Pipeline execution failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            try:
                await self._update_progress("Error", 0, f"Pipeline failed: {str(e)}")
            except Exception as progress_error:
                pass
                
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
        clinical_evidence_result: Optional['ClinicalEvidenceResult'],
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
            pass
            logger.info(f"Stage 3c: Processing top 25 of {scored_hypotheses.total_count} hypotheses for enhanced validation")
            
            # Background gene pool for the permutation null.
            #
            # This MUST be drawn from outside the analysis. Two earlier attempts
            # failed for the same underlying reason:
            #   * the functional neighbourhood itself -- every "permuted"
            #     neighbourhood was the neighbourhood again (measured: null mean
            #     11.2 against an observed 12, p ~ 1 for every pathway);
            #   * the neighbourhood plus the genes annotated to the returned
            #     pathways -- g:Profiler reports *intersections*, so those genes
            #     are already inside the neighbourhood by construction (measured:
            #     307 background genes for a 302-gene neighbourhood, ratio 1.0x).
            #
            # The pool is therefore the HGNC protein-coding genome, unioned with
            # any analysis gene missing from that snapshot so the observed
            # overlap is always drawable from the null.
            seed_gene_symbols = [g.symbol for g in seed_genes]
            fn_genes = [g.symbol for g in fn.neighbors] if fn.neighbors else []
            analysis_genes = set(seed_gene_symbols) | set(fn_genes)
            for _hyp in scored_hypotheses.hypotheses:
                analysis_genes.update(_hyp.aggregated_pathway.pathway.evidence_genes or [])
            all_genes = background_with(analysis_genes)
            logger.info(
                f"Permutation background pool: {len(all_genes)} genes "
                f"for a {len(set(fn_genes))}-gene neighbourhood "
                f"(ratio {len(all_genes) / max(len(set(fn_genes)), 1):.1f}x)"
            )

            # Per-gene STRING degrees are no longer computed here. They existed
            # only to feed the degree-preserving permutation variant, which drew
            # replacements from within the neighbourhood and has been removed.

            # Track statistics
            tissue_filtered = 0
            high_druggability = 0
            
            
            # Limit enhanced validation to top 50 hypotheses for speed optimization
            top_hypotheses = scored_hypotheses.hypotheses[:50]
            
            # Process each hypothesis
            for i, hypothesis in enumerate(top_hypotheses):
                try:
                    pathway_genes = hypothesis.aggregated_pathway.pathway.evidence_genes
                    
                    # Initialize score_components if needed
                    if not hypothesis.score_components:
                        hypothesis.score_components = {}
                    
                    # 1. Cardiac Tissue Expression Validation.
                    #    Live GTEx lookups when enabled; otherwise a fast offline
                    #    curated-gene estimate so the tissue-specificity column is
                    #    always populated (the fast preset disables the live calls).
                    try:
                        if self.settings.nets.tissue_expression_validation:
                            tissue_score = await self.tissue_validator.calculate_expression_score(pathway_genes)
                        else:
                            tissue_score = self.tissue_validator.calculate_offline_expression_score(pathway_genes)
                        hypothesis.score_components['cardiac_expression_ratio'] = tissue_score.cardiac_expression_ratio
                        hypothesis.score_components['cardiac_expressed_genes'] = tissue_score.expressed_genes
                        hypothesis.score_components['tissue_validation_passed'] = tissue_score.validation_passed
                        hypothesis.score_components['mean_cardiac_tpm'] = tissue_score.mean_cardiac_tpm
                        hypothesis.score_components['cardiac_specificity_ratio'] = tissue_score.mean_cardiac_specificity_ratio

                        if not tissue_score.validation_passed:
                            tissue_filtered += 1
                    except Exception as e:
                        logger.warning(f"Tissue expression validation failed for hypothesis {i}: {str(e)}")
                        hypothesis.score_components['tissue_validation_passed'] = False
                        tissue_filtered += 1
                
                    # 2. Permutation Testing (Optional for performance - degree-preserving empirical p-value)
                    # SCIENTIFIC RIGOR: Use degree-preserving permutation to control for network topology
                    # Reduced from 1000 to 100 permutations for performance while maintaining statistical validity
                    try:
                        if all_genes and fn_genes and self.settings.nets.permutation_test_enabled:
                            # Size-matched uniform null over the protein-coding
                            # genome. Degree-matched sampling is deliberately NOT
                            # used here: STRING degrees are known only for genes
                            # inside the neighbourhood, so degree bins would draw
                            # replacements almost exclusively from the
                            # neighbourhood itself and reintroduce the degenerate
                            # null this background was introduced to fix. The
                            # statistics dict records degree_preserved=False so
                            # the report does not claim a control that was not
                            # applied.
                            empirical_p, perm_stats = self.permutation_tester.calculate_empirical_pvalue(
                                pathway_genes,
                                fn_genes,
                                all_genes,
                                n_permutations=None,
                            )
                            hypothesis.score_components['empirical_pvalue'] = empirical_p
                            hypothesis.score_components['permutation_z_score'] = perm_stats.get('z_score')
                            hypothesis.score_components['observed_overlap'] = perm_stats.get('observed_overlap', 0)
                            hypothesis.score_components['expected_overlap'] = perm_stats.get('mean_null_overlap')
                            hypothesis.score_components['n_permutations_used'] = perm_stats.get('n_permutations', 0)
                            hypothesis.score_components['degree_preserved'] = perm_stats.get('degree_preserved', True)
                            hypothesis.score_components['permutation_testable'] = perm_stats.get('testable', False)
                            hypothesis.score_components['p_resolution_floor'] = perm_stats.get('p_resolution_floor')
                            if not perm_stats.get('testable', False):
                                hypothesis.score_components['permutation_skip_reason'] = perm_stats.get('reason')
                        else:
                            hypothesis.score_components['empirical_pvalue'] = None
                            hypothesis.score_components['permutation_z_score'] = None
                    except Exception as e:
                        logger.warning(f"Permutation testing failed for hypothesis {i}: {str(e)}")
                        hypothesis.score_components['empirical_pvalue'] = None
                        hypothesis.score_components['permutation_z_score'] = None
                    
                    # 3. Druggability Analysis. The curated tier is computed offline
                    #    and always runs; the live Open Targets lookup is added only
                    #    when external druggability is enabled (skipped by fast preset).
                    if self.settings.nets.druggability_analysis:
                        try:
                            drug_score = self.druggability_analyzer.calculate_druggability_score(
                                pathway_genes,
                                use_external=self.settings.nets.external_druggability_enabled,
                            )
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
            
            # ---- Multiple-testing correction on the empirical p-values -------
            # The permutation test is run once per hypothesis, so the raw
            # empirical p-values are a family and need FDR control before any of
            # them is called significant. Untestable hypotheses carry p = None
            # and are excluded from the correction rather than counted in m.
            raw_p = [h.score_components.get('empirical_pvalue') for h in top_hypotheses]
            q_values = self.permutation_tester.benjamini_hochberg(raw_p)
            n_tested = sum(1 for v in raw_p if v is not None)
            n_sig = 0
            for hypothesis, q in zip(top_hypotheses, q_values):
                hypothesis.score_components['empirical_qvalue'] = q
                if q is not None and q <= self.settings.nets.fdr_threshold:
                    hypothesis.score_components['empirical_significant'] = True
                    n_sig += 1
                elif q is not None:
                    hypothesis.score_components['empirical_significant'] = False
            logger.info(
                f"Permutation FDR: {n_sig}/{n_tested} hypotheses with q <= "
                f"{self.settings.nets.fdr_threshold} (BH across {n_tested} tests)"
            )

            # Store validation results
            self.results["stage_3_6_enhanced_validation"] = {
                "hypotheses_validated": len(top_hypotheses),
                "total_hypotheses": scored_hypotheses.total_count,
                "validation_scope": f"top_{len(top_hypotheses)}",
                "tissue_expression": {
                    "low_expression_count": tissue_filtered,
                    "passed_count": len(top_hypotheses) - tissue_filtered
                },
                "permutation_testing": {
                    "applied": bool(all_genes and fn_genes),
                    "n_permutations": self.permutation_tester.n_permutations,
                    "random_seed": self.permutation_tester.random_seed,
                    "background_pool_size": len(all_genes),
                    "p_resolution_floor": 1.0 / (self.permutation_tester.n_permutations + 1),
                    "n_tested": n_tested,
                    "n_significant_bh": n_sig,
                    "multiple_testing_correction": "benjamini_hochberg",
                },
                "druggability": {
                    "high_tier_count": high_druggability,
                    "analyzed_count": len(top_hypotheses)
                }
            }
            
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
    
    # NOTE: the TopologyAnalyzer stage that used to live here has been removed.
    # It was never called by run() -- the comprehensive topology analyzer covers
    # the same ground and is the one actually wired in -- so its TopologyResult
    # was always empty, which is why the multi-evidence validator's network term
    # scored zero for every pathway until it was re-pointed at the hub genes.

    async def _run_stage_6_literature(
        self,
        scored_hypotheses: ScoredHypotheses,
        seed_genes: List[GeneInfo]
    ) -> LiteratureEvidence:
        """Run Stage 6a: Literature Validation."""
        lit_msg = "Running Stage 6a: Literature Validation"
        logger.info(lit_msg)
        
        try:
            literature_evidence = await self.literature_miner.validate_hypotheses_async(
                scored_hypotheses.hypotheses,
                seed_genes,
                top_n=None,  # Mine literature for ALL pathways (will default to config or all hypotheses)
                disease_context=self.disease_context,
                disease_synonyms=self.disease_synonyms,
                max_concurrent=3  # Allow 3 concurrent literature searches
            )
            
            # Serialize Citation objects to dicts so they survive json.dump(default=str)
            # as structured objects (otherwise they become repr strings and the results
            # API/UI cannot read citation fields). See endpoints._extract_hypotheses.
            self.results["stage_4_literature"] = {
                "hypotheses_validated": len(literature_evidence.hypothesis_citations),
                "hypothesis_citations": {
                    pid: [c.model_dump() if hasattr(c, "model_dump") else c for c in cits]
                    for pid, cits in literature_evidence.hypothesis_citations.items()
                }
            }
            
            return literature_evidence
            
        except Exception as e:
            logger.warning(f"Stage 4 literature validation failed: {str(e)}")
            self.warnings.append(f"Literature validation failed: {str(e)}")
            # Return empty result to continue pipeline
            return LiteratureEvidence(hypothesis_citations={})
    
    def _seed_disease_corpus(self, seed_genes: List[GeneInfo]) -> Optional[int]:
        """PubMed records matching (seed genes AND disease context).

        One query per run. Returns None if the lookup fails, in which case
        novelty is scored without the grounding check rather than being
        wrongly suppressed.
        """
        try:
            miner = self.literature_miner
            gene_clause = miner._gene_clause(seed_genes)
            disease_clause = miner._disease_clause(
                self.disease_context, self.disease_synonyms
            )
            query = f"({gene_clause}) AND ({disease_clause})"
            count = miner.pubmed_client.count_hits(query)
            if count < 0:
                logger.warning("Seed-disease corpus lookup failed; novelty ungated")
                return None
            logger.info(
                f"Seed-disease literature corpus: {count} records "
                f"(threshold for grounded novelty: "
                f"{self.hypothesis_validator.MIN_SEED_DISEASE_CORPUS})"
            )
            self.results['seed_disease_corpus'] = count
            return count
        except Exception as e:
            logger.warning(f"Seed-disease corpus lookup failed: {str(e)}")
            return None

    def _backfill_corpus_counts(
        self,
        scored_hypotheses: ScoredHypotheses,
        hit_counts: Dict[str, int],
        concept_counts: Dict[str, int],
        seed_genes: List[GeneInfo],
    ) -> None:
        """Measure the PubMed corpus for reported pathways literature mining skipped."""
        # None means the pathway was never mined; a negative value means the
        # count lookup was attempted and failed. Both need measuring.
        missing = [
            h for h in scored_hypotheses.hypotheses
            if (hit_counts.get(h.aggregated_pathway.pathway.pathway_id) or -1) < 0
        ]
        if not missing:
            return

        logger.info(f"Backfilling PubMed corpus size for {len(missing)} hypotheses")
        miner = self.literature_miner
        n_ok = 0
        for hypothesis in missing:
            pathway = hypothesis.aggregated_pathway.pathway
            traced = getattr(hypothesis, 'traced_seed_genes', None) or []
            contributing = [g for g in seed_genes if g.symbol in traced] or seed_genes
            try:
                query = miner._construct_hypothesis_query(
                    pathway.pathway_name, contributing,
                    self.disease_context, self.disease_synonyms,
                )
                count = miner.pubmed_client.count_hits(query)
                if count < 0:
                    continue
                hit_counts[pathway.pathway_id] = count
                n_ok += 1
                if count == 0:
                    concept_clause = miner._pathway_clause(pathway.pathway_name)
                    concept = (
                        miner.pubmed_client.count_hits(f"({concept_clause})")
                        if concept_clause else 0
                    )
                    if concept >= 0:
                        concept_counts[pathway.pathway_id] = concept
            except Exception as e:
                logger.warning(f"Corpus backfill failed for {pathway.pathway_id}: {str(e)}")
        logger.info(f"Corpus backfill measured {n_ok}/{len(missing)} hypotheses")

    def _backfill_permutation_tests(
        self,
        scored_hypotheses: ScoredHypotheses,
        fn_result: FunctionalNeighborhood,
        seed_genes: List[GeneInfo],
    ) -> None:
        """Ensure every surviving hypothesis carries an empirical p and BH q.

        Stage 4b tests only the top N hypotheses by the ranking in force at that
        point. Later stages filter and re-rank, so the reported set and the
        tested set can diverge. This tests whatever is missing and then applies
        Benjamini-Hochberg across the whole reported set.
        """
        if not self.settings.nets.permutation_test_enabled:
            return
        if not scored_hypotheses.hypotheses:
            return

        fn_genes = [g.symbol for g in fn_result.neighbors] if fn_result.neighbors else []
        if not fn_genes:
            return

        analysis_genes = {g.symbol for g in seed_genes} | set(fn_genes)
        for hyp in scored_hypotheses.hypotheses:
            analysis_genes.update(hyp.aggregated_pathway.pathway.evidence_genes or [])
        background = background_with(analysis_genes)

        n_backfilled = 0
        for hyp in scored_hypotheses.hypotheses:
            if not hyp.score_components:
                hyp.score_components = {}
            if hyp.score_components.get('empirical_pvalue') is not None:
                continue
            if hyp.score_components.get('permutation_skip_reason'):
                continue
            try:
                empirical_p, stats = self.permutation_tester.calculate_empirical_pvalue(
                    hyp.aggregated_pathway.pathway.evidence_genes,
                    fn_genes,
                    background,
                    n_permutations=None,
                )
                hyp.score_components['empirical_pvalue'] = empirical_p
                hyp.score_components['permutation_z_score'] = stats.get('z_score')
                hyp.score_components['observed_overlap'] = stats.get('observed_overlap', 0)
                hyp.score_components['expected_overlap'] = stats.get('mean_null_overlap')
                hyp.score_components['n_permutations_used'] = stats.get('n_permutations', 0)
                hyp.score_components['permutation_testable'] = stats.get('testable', False)
                hyp.score_components['p_resolution_floor'] = stats.get('p_resolution_floor')
                if not stats.get('testable', False):
                    hyp.score_components['permutation_skip_reason'] = stats.get('reason')
                n_backfilled += 1
            except Exception as e:
                logger.warning(f"Backfill permutation test failed: {str(e)}")

        # Re-apply BH across every reported hypothesis that has a p-value.
        raw_p = [h.score_components.get('empirical_pvalue') for h in scored_hypotheses.hypotheses]
        q_values = self.permutation_tester.benjamini_hochberg(raw_p)
        n_sig = 0
        for hyp, q in zip(scored_hypotheses.hypotheses, q_values):
            hyp.score_components['empirical_qvalue'] = q
            if q is not None:
                hyp.score_components['empirical_significant'] = q <= self.settings.nets.fdr_threshold
                n_sig += int(q <= self.settings.nets.fdr_threshold)

        n_tested = sum(1 for v in raw_p if v is not None)
        self.results['permutation_final'] = {
            'n_backfilled': n_backfilled,
            'n_tested': n_tested,
            'n_reported': len(scored_hypotheses.hypotheses),
            'n_significant_bh': n_sig,
            'fdr_threshold': self.settings.nets.fdr_threshold,
            'correction_family': 'all reported hypotheses',
            'null_model': 'size-matched uniform sampling from the protein-coding genome',
            'background_source': BACKGROUND_SOURCE,
            'background_retrieved': BACKGROUND_RETRIEVED,
            'background_size': len(background),
            'n_permutations': self.permutation_tester.n_permutations,
            'random_seed': self.permutation_tester.random_seed,
        }
        logger.info(
            f"Permutation (final set): {n_backfilled} backfilled, "
            f"{n_sig}/{n_tested} with q <= {self.settings.nets.fdr_threshold}"
        )

    @staticmethod
    def _network_evidence_for_pathway(pathway_genes, hub_index) -> Dict:
        """Per-pathway network evidence derived from the comprehensive topology.

        The validator expects a ``key_nodes`` list. The earlier revision sourced
        this from ``TopologyAnalyzer.hypothesis_networks``, but that analyzer is
        never run by :meth:`run`, so the network term was always zero. Hub genes
        from the comprehensive topology stage carry the same information and are
        actually computed.
        """
        key_nodes = []
        for gene in pathway_genes or []:
            hub = hub_index.get(gene)
            if hub is None:
                continue
            key_nodes.append({
                'gene': gene,
                # A hub that sits on many shortest paths between pathway members
                # is acting as a mediator in the sense the validator scores.
                'role': 'mediator' if hub.get('betweenness_centrality', 0) > 0 else 'member',
                'betweenness_centrality': hub.get('betweenness_centrality', 0.0),
                'hub_score': hub.get('hub_score', 0.0),
            })
        return {'key_nodes': key_nodes}

    async def _run_stage_4_5_validation(
        self,
        scored_hypotheses: ScoredHypotheses,
        comprehensive_topology_result,
        literature_evidence: LiteratureEvidence,
        seed_genes: List[GeneInfo],
        fn_result: Optional[FunctionalNeighborhood] = None,
    ) -> ScoredHypotheses:
        """
        Run Stage 8: Multi-Evidence Validation, Novelty and Discovery Scoring.

        Combines statistical strength, replication, literature evidence, network
        topology and literature novelty into a validation score, and computes the
        Discovery Score = PPS x novelty, which surfaces pathways that are both
        well supported by the enrichment evidence and under-reported in the
        literature at the (pathway x seed genes x disease) intersection.

        Hypotheses are re-ranked by Discovery Score and their ``rank`` fields are
        renumbered contiguously from 1.
        """
        logger.info("Running Stage 8: Multi-Evidence Validation and Discovery Scoring")

        try:
            # Index hub genes once so the per-pathway lookup is O(1).
            hub_index = {}
            if comprehensive_topology_result is not None:
                for hub in getattr(comprehensive_topology_result, 'hub_genes', []) or []:
                    entry = hub if isinstance(hub, dict) else hub.__dict__
                    symbol = entry.get('gene_symbol') or entry.get('gene')
                    if symbol:
                        hub_index[symbol] = entry

            hit_counts = getattr(literature_evidence, 'hypothesis_hit_counts', {}) or {}
            concept_counts = getattr(literature_evidence, 'concept_hit_counts', {}) or {}

            # Literature mining runs on a capped window of hypotheses, but more
            # than that can survive to the report. Any pathway without a measured
            # corpus would be scored 'not_measured' and pushed down the ranking,
            # so measure the missing ones here. This is one cached esearch per
            # pathway -- far cheaper than the abstract retrieval mining does.
            self._backfill_corpus_counts(
                scored_hypotheses, hit_counts, concept_counts, seed_genes
            )

            # Literature footprint of the seed genes themselves in this disease.
            # Novelty is expressed relative to it: if the seeds have no presence
            # in the disease literature, a zero-record pathway intersection is a
            # statement about the seeds, not a discovery.
            seed_disease_corpus = self._seed_disease_corpus(seed_genes)
            validation_scores = {}

            # Backfill permutation tests for surviving hypotheses that were not
            # inside the top-N window at Stage 4b. Without this, a pathway can
            # reach the final report with no q-value purely because of where it
            # sat in an earlier, differently-ordered ranking. Re-running BH over
            # the full tested set afterwards also makes the correction family
            # match the set actually reported.
            if fn_result is not None:
                self._backfill_permutation_tests(scored_hypotheses, fn_result, seed_genes)

            for hypothesis in scored_hypotheses.hypotheses:
                pathway = hypothesis.aggregated_pathway.pathway
                pathway_id = pathway.pathway_id

                lit_citations = literature_evidence.hypothesis_citations.get(pathway_id, [])
                network_analysis = self._network_evidence_for_pathway(
                    pathway.evidence_genes, hub_index
                )

                validation_score = self.hypothesis_validator.calculate_validation_score(
                    hypothesis,
                    lit_citations,
                    network_analysis,
                    seed_genes,
                    pubmed_hit_count=hit_counts.get(pathway_id),
                    concept_hit_count=concept_counts.get(pathway_id),
                    seed_disease_corpus=seed_disease_corpus,
                )

                validation_scores[pathway_id] = validation_score

                if not hypothesis.score_components:
                    hypothesis.score_components = {}

                # Propagate every field the validator produced. The earlier
                # revision copied only five of them and silently dropped
                # discovery_score, novelty_tier and literature_saturation --
                # the three the report and UI actually read.
                for key in (
                    'total_validation_score', 'confidence_level',
                    'statistical_strength', 'replication_support',
                    'literature_evidence', 'network_evidence', 'novelty_score',
                    'novelty_tier', 'literature_saturation', 'discovery_score',
                    'pubmed_hit_count', 'saturation_basis', 'n_relevant_citations',
                    'novelty_confidence', 'concept_hit_count', 'seed_disease_corpus',
                ):
                    if key in validation_score:
                        hypothesis.score_components[key] = validation_score[key]
                hypothesis.score_components['validation_score'] =                     validation_score['total_validation_score']

            # Re-rank by Discovery Score and renumber contiguously. Ranks were
            # previously carried over from the pre-filter ordering, so a surviving
            # set of 32 pathways displayed ranks such as 1, 14, 19 ... 4649.
            scored_hypotheses.hypotheses.sort(
                key=lambda h: (h.score_components or {}).get('discovery_score', 0.0),
                reverse=True,
            )
            for i, hypothesis in enumerate(scored_hypotheses.hypotheses, start=1):
                hypothesis.rank = i

            tier_counts: Dict[str, int] = {}
            for v in validation_scores.values():
                tier = v.get('novelty_tier', 'Unknown')
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

            self.results["stage_8_discovery"] = {
                "hypotheses_validated": len(validation_scores),
                "high_confidence_count": sum(1 for v in validation_scores.values() if v['confidence_level'] == 'high'),
                "medium_confidence_count": sum(1 for v in validation_scores.values() if v['confidence_level'] == 'medium'),
                "low_confidence_count": sum(1 for v in validation_scores.values() if v['confidence_level'] == 'low'),
                "novelty_tiers": tier_counts,
                "mean_validation_score": (
                    sum(v['total_validation_score'] for v in validation_scores.values())
                    / len(validation_scores)
                ) if validation_scores else 0,
                "ranked_by": "discovery_score",
                "saturation_ceiling": self.hypothesis_validator.SATURATION_CEILING,
            }

            # Re-store the stage_3 snapshot. It is written earlier (after
            # semantic filtering, then again after seed tracing) as a
            # model_dump(), i.e. a frozen copy -- so every mutation Stage 8 makes
            # was invisible to it. results.json is what the UI and the JSON API
            # load, which meant the Discovery Score, novelty tier and permutation
            # q-value existed in the PDF/markdown report but not in the app.
            self.results["stage_3"] = scored_hypotheses.model_dump()

            logger.info(
                f"Stage 8 complete: {len(validation_scores)} hypotheses scored; "
                f"novelty tiers {tier_counts}"
            )

            return scored_hypotheses

        except Exception as e:
            logger.error(f"Stage 8 validation failed: {str(e)}")
            self.warnings.append(f"Stage 8 validation failed: {str(e)}")
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
        
        try:
            # Trace seed genes to pathways
            trace_msg = f"[STAGE 4 DEBUG] Step 1: Tracing seed genes to pathways..."
            logger.info(f"Tracing {len(seed_genes)} seed genes to {scored_hypotheses.total_count} hypotheses")
            
            traced_hypotheses = self.seed_gene_tracer.trace_seed_genes_to_pathways(
                scored_hypotheses.hypotheses,
                seed_genes,
                primary_result.primary_pathways,
                {}  # secondary_pathways not needed for current implementation
            )
            
            scored_hypotheses.hypotheses = traced_hypotheses
            
            # Check literature associations with enhanced visibility
            step2_msg = f"[STAGE 4 DEBUG] Step 2: Checking literature associations..."
            max_lit_check = min(50, scored_hypotheses.total_count)
            lit_msg = f"[STAGE 4 DEBUG] Will check literature for top {max_lit_check} hypotheses"
            logger.info(f"Checking literature associations for top {max_lit_check} hypotheses")
            
            # This will trigger our enhanced debug output from seed_gene_tracer
            literature_checked_hypotheses = self.seed_gene_tracer.check_literature_associations(
                scored_hypotheses.hypotheses,
                max_hypotheses=max_lit_check
            )
            
            scored_hypotheses.hypotheses = literature_checked_hypotheses
            complete_msg = f"[STAGE 4 DEBUG] Step 2 complete: Literature association checking finished"
            
            # Store results with detailed statistics
            
            try:
                traced_count = sum(1 for h in scored_hypotheses.hypotheses if h.traced_seed_genes)
                lit_support_count = sum(
                    1 for h in scored_hypotheses.hypotheses 
                    if h.literature_associations.get('has_literature_support', False)
                )
            except AttributeError as e:
                pass
                traced_count = 0
                lit_support_count = 0
            
            
            self.results["stage_4_6_seed_tracing"] = {
                "hypotheses_traced": traced_count,
                "hypotheses_with_literature_support": lit_support_count,
                "total_hypotheses": scored_hypotheses.total_count
            }
            
            logger.info(
                f"Stage 4.6 complete: {traced_count} hypotheses traced, "
                f"{lit_support_count} with literature support"
            )
            
            # Update stage_3 results with traced seed genes and literature associations
            self.results["stage_3"] = scored_hypotheses.model_dump()
            logger.info(f"Updated stage_3 results with seed tracing and literature associations for {scored_hypotheses.total_count} hypotheses")
            
            return scored_hypotheses
            
        except Exception as e:
            pass
            logger.error(f"Stage 4.6 seed tracing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.warnings.append(f"Seed gene tracing failed: {str(e)}")
            return scored_hypotheses
    
    async def _generate_reports(self, *args) -> Dict[str, str]:
        """Generate analysis reports."""
        logger.info("Generating reports")
        logger.info(f"[PIPELINE DEBUG] Report generation arguments received: {len(args)} items")
        
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
    
    def _generate_top_genes(
        self,
        hypotheses: List,
        druggability_analyzer,
        topology_result,
        fn_result,
        top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Generate top therapeutic target candidates based on gene frequency across ALL final pathways.
        
        This identifies the top N genes by their occurrence count across all final pathways,
        then enriches them with druggability, topology, and cardiac disease scores.
        
        Args:
            hypotheses: List of scored hypotheses (all final pathways)
            druggability_analyzer: Druggability analyzer instance
            topology_result: Topology analysis result
            fn_result: Functional neighborhood result
            top_n: Number of top genes to return (default: 20)
            
        Returns:
            List of top gene dictionaries with druggability and topology metrics
        """
        # Collect all genes with their metrics across ALL pathways
        gene_scores = {}
        
        # Extract genes from ALL final pathways (not just top 50)
        for i, hyp in enumerate(hypotheses):  # ALL pathways
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
        
        # Add topology/centrality information
        if topology_result and hasattr(topology_result, 'hypothesis_networks'):
            for pathway_id, network_data in topology_result.hypothesis_networks.items():
                if hasattr(network_data, 'hub_genes'):
                    for hub_gene in network_data.hub_genes:
                        gene_symbol = hub_gene.gene if hasattr(hub_gene, 'gene') else str(hub_gene)
                        if gene_symbol in gene_scores:
                            centrality = hub_gene.centrality if hasattr(hub_gene, 'centrality') else 0.5
                            gene_scores[gene_symbol]['centrality'] = max(
                                gene_scores[gene_symbol]['centrality'],
                                centrality
                            )
        
        # Add gene-disease association scores using curated cardiovascular gene database
        try:
            from app.services.gene_disease_scorer import GeneDiseaseScorer
            gene_disease_scorer = GeneDiseaseScorer()
            
            logger.info(f"Querying gene-disease scorer for {len(gene_scores)} genes...")
            disease_scores = gene_disease_scorer.get_batch_scores(list(gene_scores.keys()))
            
            for gene_symbol in gene_scores:
                gene_scores[gene_symbol]['gene_disease_score'] = disease_scores.get(gene_symbol, 0.0)
            
            scored_genes = sum(1 for s in disease_scores.values() if s > 0)
            logger.info(f"Gene-disease scores obtained: {scored_genes}/{len(disease_scores)} genes have cardiac disease associations")
        except Exception as e:
            logger.warning(f"Gene-disease scoring failed (non-critical): {str(e)}")
            # Set default scores if gene-disease scoring fails
            for gene_symbol in gene_scores:
                gene_scores[gene_symbol]['gene_disease_score'] = 0.0
        
        # Calculate final score: importance * (1 + druggability_bonus + centrality_bonus + disease_bonus)
        for gene_symbol in gene_scores:
            druggability_bonus = 0.0
            if gene_scores[gene_symbol]['is_fda_approved']:
                druggability_bonus = 1.0
            elif gene_scores[gene_symbol]['is_clinical_trial']:
                druggability_bonus = 0.5
            elif gene_scores[gene_symbol]['is_druggable']:
                druggability_bonus = 0.25
            
            centrality_bonus = gene_scores[gene_symbol]['centrality'] * 0.5
            disease_bonus = gene_scores[gene_symbol]['gene_disease_score'] * 0.75  # Weight gene-disease score
            
            gene_scores[gene_symbol]['final_score'] = gene_scores[gene_symbol]['importance_score'] * (
                1.0 + druggability_bonus + centrality_bonus + disease_bonus
            )
        
        # Sort by final score and return top N
        sorted_genes = sorted(
            gene_scores.values(),
            key=lambda x: x['final_score'],
            reverse=True
        )
        
        return sorted_genes[:top_n]
    
    def close(self):
        """Close all service connections."""
        self.input_validator.close()
        self.fn_builder.close()
        self.primary_analyzer.close()
        self.secondary_analyzer.close()
        
        logger.info("Pipeline services closed")
