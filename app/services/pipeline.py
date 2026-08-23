"""CardioXNet pipeline orchestrator."""

import contextlib
import logging
import asyncio
import json
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timezone

from app import __version__
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
from app.services.pipeline_errors import PipelineError
from app.services.pipeline_stages import (
    EnrichmentStagesMixin,
    ValidationStagesMixin,
    DiscoveryStagesMixin,
)

logger = logging.getLogger(__name__)


def _software_provenance() -> Dict[str, Optional[str]]:
    """Return stable software identifiers without making startup fail.

    Source archives may not include ``.git``. In that case an explicit null is
    retained rather than inventing a revision.
    """
    repository_root = Path(__file__).resolve().parents[2]
    revision: Optional[str] = None
    try:
        completed = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={repository_root.as_posix()}",
                "rev-parse",
                "HEAD",
            ],
            cwd=repository_root,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if completed.returncode == 0:
            candidate = completed.stdout.strip()
            if candidate:
                revision = candidate
    except (OSError, subprocess.SubprocessError):
        pass

    return {
        "name": "CardioXNet",
        "version": __version__,
        "git_revision": revision,
    }




class Pipeline(EnrichmentStagesMixin, ValidationStagesMixin, DiscoveryStagesMixin):
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

        # Apply config overrides as one validated model update. Direct setattr
        # bypasses Pydantic's bounds, which previously allowed an out-of-range
        # timeout or retry count to enter a run even though NETSConfig declared
        # validation constraints.
        if config_overrides:
            logger.info(f"Applying {len(config_overrides)} configuration overrides: {config_overrides}")
            nets_overrides = {}
            for key, value in config_overrides.items():
                if key in type(self.settings.nets).model_fields:
                    nets_overrides[key] = value
                elif key == 'disease_context':
                    self.disease_context = value
                    logger.info(f"Disease context set: {value}")
                elif key == 'disease_synonyms':
                    self.disease_synonyms = value or []
                    logger.info(f"Disease synonyms set: {value}")
                else:
                    logger.warning(f"Unknown configuration parameter: {key}")

            if nets_overrides:
                previous = self.settings.nets.model_dump()
                merged = {**previous, **nets_overrides}
                self.settings.nets = type(self.settings.nets).model_validate(merged)
                for key in nets_overrides:
                    logger.info(
                        "Override: %s = %r -> %r",
                        key,
                        previous[key],
                        getattr(self.settings.nets, key),
                    )
        
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
        """Push per-run settings into every service and derived client field.

        Services are constructed from the cached global settings, while a
        pipeline deliberately holds a deep-copied settings object so one run's
        preset cannot affect another. Merely changing ``self.settings`` left
        several advertised preset values, including STRING breadth, secondary
        expansion depth, FDR, and permutation count, at global defaults. Keep
        all service instances on the per-run copy and refresh fields captured
        during their constructors.
        """
        nets = self.settings.nets

        # Walk the pipeline services plus their direct clients. Most consumers
        # read settings lazily, so assigning the same per-run object is enough.
        objects = []
        seen = set()
        frontier = [
            value for value in vars(self).values()
            if hasattr(value, "__dict__") and hasattr(value, "settings")
        ]
        for _depth in range(3):
            next_frontier = []
            for obj in frontier:
                if id(obj) in seen:
                    continue
                seen.add(id(obj))
                objects.append(obj)
                obj.settings = self.settings
                next_frontier.extend(
                    value for value in vars(obj).values()
                    if hasattr(value, "__dict__") and hasattr(value, "settings")
                )
            frontier = next_frontier

        # A few clients cache configuration-derived scalars at construction.
        # Refresh those fields explicitly after assigning the per-run settings.
        from app.services.gprofiler_client import (
            GProfilerClient,
            _normalize_gprofiler_base_url,
        )
        from app.services.pubmed_client import PubMedClient
        from app.services.string_client import STRINGClient
        from app.services.reactome_client import ReactomeClient

        for obj in objects:
            if isinstance(obj, GProfilerClient):
                obj.timeout_seconds = nets.gprofiler_timeout_seconds
                obj.base_url = _normalize_gprofiler_base_url(
                    nets.gprofiler_api_url
                )
            elif isinstance(obj, PubMedClient):
                obj.max_results = nets.pubmed_max_results
            elif isinstance(obj, STRINGClient):
                version_slug = nets.string_version.replace(".", "-")
                obj.base_url = f"https://version-{version_slug}.string-db.org/api"
            elif isinstance(obj, ReactomeClient):
                obj.base_url = nets.reactome_api_url.rstrip("/")

        # SeedGeneTracer intentionally has no settings attribute of its own, so
        # its PubMed client is not reached by the generic settings walk above.
        self.seed_gene_tracer.pubmed_client.settings = self.settings
        self.seed_gene_tracer.pubmed_client.max_results = nets.pubmed_max_results
        self.permutation_tester.n_permutations = nets.n_permutations

    @contextlib.asynccontextmanager
    async def _timed(self, label: str):
        """Time a stage and log its duration against the pipeline start.

        Replaces 23 near-identical blocks of
            stage_start_time = time.time()
            ...
            elapsed = time.time() - stage_start_time
            logger.info(f"[TIMING] {label} completed in {elapsed:.2f}s (Total: ...)")
        Four of those had lost their f-string prefix and were logging literal
        braces; collapsing them here fixed all four.
        """
        started = time.time()
        try:
            yield
        finally:
            logger.info(
                f"[TIMING] {label} completed in {time.time() - started:.2f}s "
                f"(Total: {time.time() - self._pipeline_started:.2f}s)"
            )

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
        pipeline_start_time = time.time()
        self._pipeline_started = pipeline_start_time
        stage_start_time = pipeline_start_time
        self.results["run_metadata"] = {
            "analysis_id": self.analysis_id,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "software": _software_provenance(),
            "resource_identifiers": {
                "string": {
                    "configured_release": self.settings.nets.string_version,
                    "endpoint": self.settings.nets.string_api_url,
                    "configured_endpoint": self.settings.nets.string_api_url,
                    "effective_endpoint": self.fn_builder.string_client.base_url,
                },
                "gprofiler": {
                    "configured_identifier": self.settings.nets.gprofiler_version,
                    "endpoint": self.settings.nets.gprofiler_api_url,
                    "configured_endpoint": self.settings.nets.gprofiler_api_url,
                    "effective_endpoint": (
                        self.primary_analyzer.gprofiler_client.base_url
                    ),
                    "verified_from_response": False,
                },
                "reactome": {
                    "configured_identifier": self.settings.nets.reactome_version,
                    "endpoint": self.settings.nets.reactome_api_url,
                    "configured_endpoint": self.settings.nets.reactome_api_url,
                    "effective_endpoint": (
                        self.primary_analyzer.reactome_client.base_url
                    ),
                    "effective_analysis_endpoint": (
                        self.primary_analyzer.reactome_client.analysis_base_url
                    ),
                    "verified_from_response": False,
                },
                "gtex": {"configured_release": "v8"},
                "pubmed": {
                    "service": "NCBI E-utilities",
                    "retrieval": "live",
                    "corpus_release": None,
                    "corpus_pinned": False,
                },
                "druggability": {
                    "embedded_snapshot": dict(
                        DruggabilityAnalyzer.EMBEDDED_RESOURCE_VERSIONS
                    ),
                    "open_targets": {
                        "endpoint": DruggabilityAnalyzer.OPEN_TARGETS_GRAPHQL_URL,
                        "api_family": DruggabilityAnalyzer.OPEN_TARGETS_API_FAMILY,
                        "retrieval": "live when enabled",
                    },
                },
                "permutation_background": BACKGROUND_SOURCE,
                "permutation_background_retrieved": BACKGROUND_RETRIEVED,
            },
            "configured_gprofiler_timeout_seconds": (
                self.settings.nets.gprofiler_timeout_seconds
            ),
            "configured_max_retries": self.settings.nets.max_retries,
        }
        
        logger.info(
            f"Starting NETS pipeline analysis (ID: {self.analysis_id}) "
            f"with {len(seed_genes)} seed genes"
        )
        
        try:
            # Stage 0: Input Validation
            await self._update_progress("input_validation", 5, "Validating input")
            async with self._timed("Stage 0"):
                validation_result = await self._run_stage_0(seed_genes)
            
            # Stage 1: Functional Neighborhood Assembly
            await self._update_progress("functional_neighborhood", 15, "Building functional neighborhood")
            async with self._timed("Stage 1"):
                fn_result = await self._run_stage_1(validation_result.valid_genes)
            
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
            
            # Stage 5a: Base Pathway Prioritization Score
            await self._update_progress("nes_scoring", 65, "Calculating pathway prioritization scores")
            stage_start_time = time.time()
            logger.info(f"[PIPELINE] Calling Stage 5a with {final_result.total_count} pathways")
            scored_hypotheses = await self._run_stage_5_scoring(final_result, fn_result=fn_result)
            elapsed = time.time() - stage_start_time
            logger.info(f"Stage 5a complete: {scored_hypotheses.total_count} scored hypotheses")
            logger.info(f"[TIMING] Stage 5a completed in {elapsed:.2f}s (Total: {time.time() - pipeline_start_time:.2f}s)")
            await self._update_progress("nes_scoring", 70, f"PPS scoring complete: {scored_hypotheses.total_count} hypotheses")
            
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
            logger.info(f"Starting enhanced validation with {scored_hypotheses.total_count} hypotheses")

            # No outer try/except: _run_stage_4_enhanced_validation catches its
            # own exceptions and returns the hypotheses unchanged, so the wrapper
            # that used to sit here could never fire.
            async with self._timed("Stage 4b enhanced validation"):
                scored_hypotheses = await self._run_stage_4_enhanced_validation(
                    scored_hypotheses,
                    fn_result,
                    validation_result.valid_genes
                )
            logger.info(f"Enhanced validation applied to {scored_hypotheses.total_count} hypotheses")
            await self._update_progress("enhanced_validation", 84, "Enhanced validation complete")
            
            # Stage 6: Literature Mining & Seed Gene Traceability
            await self._update_progress("literature_mining", 85, "Mining literature and tracing seed genes")
            
            # Stage 6a: Literature Mining (detailed citations).
            # _run_stage_6_literature returns an empty LiteratureEvidence on
            # failure, so no outer handler is needed here.
            async with self._timed("Stage 6a literature mining"):
                literature_evidence = await self._run_stage_6_literature(
                    scored_hypotheses,
                    validation_result.valid_genes
                )
            logger.info(
                f"Literature mining found citations for "
                f"{len(literature_evidence.hypothesis_citations)} hypotheses"
            )
            
            # Stage 6b: Seed Gene Traceability & Literature Association.
            # Returns the hypotheses unchanged on failure.
            async with self._timed("Stage 6b seed tracing"):
                scored_hypotheses = await self._run_stage_6_seed_tracing(
                    scored_hypotheses,
                    validation_result.valid_genes,
                    primary_result,
                    secondary_result
                )
            
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
                logger.exception(f"Stage 8 discovery scoring failed but continuing: {str(e)}")
                self.warnings.append(f"Stage 8 discovery scoring failed: {str(e)}")

            # Freeze analytical completion metadata before serializing reports
            # so the downloadable JSON contains a meaningful end timestamp and
            # elapsed duration. Final pipeline completion, including report
            # serialization and result persistence, is recorded separately.
            analytical_completion = datetime.now(timezone.utc).isoformat()
            analytical_elapsed = round(time.time() - pipeline_start_time, 3)
            self.results["run_metadata"].update({
                "analysis_completed_at_utc": analytical_completion,
                "analysis_elapsed_seconds": analytical_elapsed,
                # Reports are serialized next, so these stable aliases ensure
                # their metadata contains a complete analytical interval.
                "completed_at_utc": analytical_completion,
                "elapsed_seconds": analytical_elapsed,
            })

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
                logger.info(
                    f"[TIMING] Report generation completed in {elapsed:.2f}s "
                    f"(Total: {time.time() - pipeline_start_time:.2f}s)"
                )
            except Exception as e:
                elapsed = time.time() - stage_start_time
                logger.info(f"[PIPELINE DEBUG] Report generation failed: {str(e)}")
                logger.error(f"Report generation failed: {str(e)}")
                logger.info(
                    f"[TIMING] Report generation failed after {elapsed:.2f}s "
                    f"(Total: {time.time() - pipeline_start_time:.2f}s)"
                )
                self.warnings.append(f"Report generation failed: {str(e)}")
                report_files = {}
            
            # Save final results
            await self._update_progress("complete", 100, "Analysis complete")
            stage_start_time = time.time()
            self.results["run_metadata"].update({
                "report_finalized_at_utc": datetime.now(timezone.utc).isoformat(),
                "total_elapsed_seconds": round(time.time() - pipeline_start_time, 3),
            })
            
            try:
                await self._save_results()
                elapsed = time.time() - stage_start_time
                logger.info(
                    f"[TIMING] Save results completed in {elapsed:.2f}s "
                    f"(Total: {time.time() - pipeline_start_time:.2f}s)"
                )
            except Exception as e:
                elapsed = time.time() - stage_start_time
                logger.info(f"[PIPELINE DEBUG] Error saving results: {str(e)}")
                logger.error(f"Error saving results: {str(e)}")
                logger.info(
                    f"[TIMING] Save results failed after {elapsed:.2f}s "
                    f"(Total: {time.time() - pipeline_start_time:.2f}s)"
                )
            
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
            logger.exception(f"Pipeline execution failed: {str(e)}")
            
            try:
                await self._update_progress("Error", 0, f"Pipeline failed: {str(e)}")
            except Exception as progress_error:
                pass
                
            raise PipelineError(f"Pipeline execution failed: {str(e)}")
    
    async def _generate_reports(self, *args) -> Dict[str, str]:
        """Generate analysis reports."""
        logger.info("Generating reports")
        logger.info(f"[PIPELINE DEBUG] Report generation arguments received: {len(args)} items")
        
        try:
            report_files = self.report_generator.generate_report(
                self.analysis_id,
                *args,
                output_formats=self.settings.nets.output_formats,
                run_metadata=self.results.get("run_metadata"),
            )
            
            return report_files
            
        except Exception as e:
            logger.warning(f"Report generation failed: {str(e)}")
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
    
    def close(self):
        """Close all service connections."""
        self.input_validator.close()
        self.fn_builder.close()
        self.primary_analyzer.close()
        self.secondary_analyzer.close()
        
        logger.info("Pipeline services closed")
