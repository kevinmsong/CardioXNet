"""Biological validation stages: cardiac expression, the permutation null with
Benjamini-Hochberg control, druggability, and the corpus/permutation backfills.

Mixed into :class:`app.services.pipeline.Pipeline`.
"""

import logging
import time
from typing import Dict, List, Optional

from app.models import (
    FunctionalNeighborhood,
    GeneInfo,
    ScoredHypotheses,
    TopologyResult,
)
from app.services.gene_background import (
    background_with,
    BACKGROUND_SOURCE,
    BACKGROUND_RETRIEVED,
)

logger = logging.getLogger(__name__)


class ValidationStagesMixin:
    """Enhanced biological validation and the measurement backfills."""

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
                        # None for both above means the curated fallback or the
                        # offline estimate produced the ratio; TPM and specificity
                        # were not measured and must not be rendered as if they were.
                        hypothesis.score_components['gtex_measured'] = tissue_score.gtex_measured

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
