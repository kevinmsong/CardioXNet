"""Discovery stages: literature mining, seed-gene tracing, the novelty and
Discovery Score computation, and therapeutic-target generation.

Mixed into :class:`app.services.pipeline.Pipeline`.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from app.models import (
    FunctionalNeighborhood,
    GeneInfo,
    LiteratureEvidence,
    PrimaryTriageResult,
    ScoredHypotheses,
    SecondaryTriageResult,
    TopologyResult,
)

logger = logging.getLogger(__name__)


class DiscoveryStagesMixin:
    """Literature, novelty, Discovery Score and target generation."""

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
            
            # See the note in enrichment.py: the authoritative stage_3 snapshot
            # is written at the end of the discovery stage, after re-ranking.
            
            return scored_hypotheses
            
        except Exception as e:
            pass
            logger.error(f"Stage 4.6 seed tracing failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.warnings.append(f"Seed gene tracing failed: {str(e)}")
            return scored_hypotheses

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
        
        # Add topology/centrality information.
        #
        # This reads `hub_genes`, the field the comprehensive topology analyzer
        # actually produces. It previously guarded on `hypothesis_networks`, which
        # exists only on the TopologyResult of the analyzer that run() never calls
        # -- so the branch was permanently false and every gene kept centrality
        # 0.0, zeroing the centrality term of the final score.
        for hub_gene in getattr(topology_result, 'hub_genes', None) or []:
            gene_symbol = getattr(hub_gene, 'gene_symbol', None)
            if gene_symbol in gene_scores:
                gene_scores[gene_symbol]['centrality'] = max(
                    gene_scores[gene_symbol]['centrality'],
                    getattr(hub_gene, 'hub_score', 0.0) or 0.0,
                )

        # Add gene-disease association scores from the curated cardiovascular
        # gene database.
        #
        # This imported app.services.gene_disease_scorer, a module deleted in
        # commit 6bffbe7. The import lived inside the try, so every run took the
        # except branch and set every gene's disease score to 0.0 -- silently
        # removing the disease term from the therapeutic-target ranking.
        # cardiac_genes_db.get_batch_scores has the same name and signature as
        # the API that went away.
        try:
            from app.services.cardiac_genes_db import get_batch_scores

            logger.info(f"Scoring {len(gene_scores)} genes against the curated cardiac gene database")
            disease_scores = get_batch_scores(list(gene_scores.keys()))

            for gene_symbol in gene_scores:
                gene_scores[gene_symbol]['gene_disease_score'] = disease_scores.get(gene_symbol, 0.0)

            scored_genes = sum(1 for s in disease_scores.values() if s > 0)
            logger.info(
                f"Gene-disease scores obtained: {scored_genes}/{len(disease_scores)} "
                f"genes have curated cardiac disease associations"
            )
        except Exception as e:
            logger.warning(f"Gene-disease scoring failed (non-critical): {str(e)}")
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
