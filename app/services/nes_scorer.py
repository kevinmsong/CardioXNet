"""Pathway Prioritization Score (PPS) computation -- Stage 3 of the pipeline.

The score is stored on ``ScoredPathway.nes_score`` for backwards compatibility
with the persisted reports and the JSON API, but it is *not* a GSEA normalized
enrichment score and must not be described as one: there is no running-sum
statistic and no permutation-derived normalisation behind it. It is a weighted
composite of significance, effect size, gene-set specificity and replication.
"""

import logging
import math
from typing import List, Dict, Optional

from app.models import (
    FinalPathwayResult,
    AggregatedPathway,
    ScoredPathway,
    ScoredHypotheses
)
from app.core.config import get_settings
from app.services.cardiac_genes_db import calculate_pathway_cardiac_score

logger = logging.getLogger(__name__)


class NESScorer:
    """Computes the Pathway Prioritization Score for each aggregated pathway.

    The score balances four normalised, independently interpretable terms:
    statistical significance, effect size (fold enrichment), gene-set
    specificity, and cross-source replication. Weighting them -- rather than
    multiplying significance by raw gene count, as an earlier revision did --
    is what stops maximally generic gene sets from dominating the ranking.
    """
    
    def __init__(self):
        """Initialize the Pathway Prioritization scorer."""
        self.settings = get_settings()
        logger.info("NESScorer initialized - Enhanced composite scoring for pathway prioritization")
    
    def score(
        self,
        final_result: FinalPathwayResult,
        fn_result = None,
        topology_result = None
    ) -> ScoredHypotheses:
        """
        Score and rank aggregated pathways.

        PPS = db_weight * centrality_weight * (
                 0.30 * significance + 0.30 * effect_size
               + 0.25 * specificity  + 0.15 * replication )

        See :meth:`_calculate_nes` for the definition of each term and for why
        the previous multiplicative formula was replaced.

        Args:
            final_result: Final pathway result from Stage 2c
            fn_result: Optional functional neighborhood, for seed-proximity weighting
            topology_result: Optional topology result, for PageRank weighting

        Returns:
            ScoredHypotheses with ranked pathway hypotheses
        """
        
        logger.info(
            f"Scoring {final_result.total_count} pathways (Pathway Prioritization Score)"
        )
        
        scored_pathways = []
        
        # Pre-calculate seed genes and 1-hop neighbors for proximity scoring
        seed_gene_symbols = set()
        seed_neighbors_1hop = set()
        if fn_result:
            seed_gene_symbols = {g.symbol for g in fn_result.seed_genes}
            # All direct neighbors are 1-hop from seed genes
            seed_neighbors_1hop = {g.symbol for g in fn_result.neighbors}
            seed_neighbors_1hop.update(seed_gene_symbols)  # Include seed genes themselves
        
        min_fold = getattr(self.settings.nets, 'min_fold_enrichment', 0.0) or 0.0
        n_below_fold = 0

        for agg_pathway in final_result.final_pathways:
            # Effect-size floor. min_fold_enrichment has always been a declared
            # setting but was never read, so a pathway could reach the report on
            # significance alone with an overlap barely above chance. Pathways
            # whose enrichment test did not report the sizes needed to compute a
            # fold are kept: the filter must not silently drop them for a missing
            # measurement.
            fold = agg_pathway.pathway.fold_enrichment
            if min_fold > 1.0 and fold is not None and fold < min_fold:
                n_below_fold += 1
                continue

            # Calculate final NES with optional centrality
            nes_score, components = self._calculate_nes(
                agg_pathway,
                fn_result=fn_result,
                topology_result=topology_result,
                seed_neighbors_1hop=seed_neighbors_1hop
            )
            
            # Calculate cardiac disease score based on evidence genes
            cardiac_score = 0.0
            if agg_pathway.pathway.evidence_genes:
                cardiac_score = calculate_pathway_cardiac_score(agg_pathway.pathway.evidence_genes)
            
            # Create scored pathway
            scored_pathway = ScoredPathway(
                aggregated_pathway=agg_pathway,
                nes_score=nes_score,
                rank=0,  # Will be set after sorting
                score_components=components,
                cardiac_disease_score=cardiac_score
            )
            
            scored_pathways.append(scored_pathway)

        if n_below_fold:
            logger.info(
                f"Effect-size filter removed {n_below_fold} pathways below "
                f"{min_fold}x fold enrichment"
            )

        # Sort by the Pathway Prioritization Score (descending)
        scored_pathways.sort(key=lambda p: p.nes_score, reverse=True)
        
        # Assign ranks
        for i, pathway in enumerate(scored_pathways, 1):
            pathway.rank = i
        
        result = ScoredHypotheses(
            hypotheses=scored_pathways,
            total_count=len(scored_pathways)
        )
        
        logger.info(
            f"NES scoring complete: {len(scored_pathways)} hypotheses ranked, "
            f"top score: {scored_pathways[0].nes_score:.2f}" 
            if scored_pathways else "NES scoring complete: no hypotheses"
        )
        
        return result
    
    # Saturation points for the individual score terms.
    #  - p = 1e-10 is where additional significance stops carrying information:
    #    beyond it the differences are dominated by annotation bias and the
    #    numerical floor of the enrichment test, not by biology.
    #  - 10x fold enrichment is a strong, uncommon effect size.
    P_SATURATION_EXP = 10.0
    FOLD_SATURATION = 10.0

    # Weights of the four evidence terms. They sum to 1.0, so the composite
    # before the database multiplier is bounded in [0, 1] and is directly
    # interpretable as "fraction of attainable evidence".
    W_SIGNIFICANCE = 0.30
    W_EFFECT = 0.30
    W_SPECIFICITY = 0.25
    W_REPLICATION = 0.15

    def _calculate_nes(
        self,
        agg_pathway: AggregatedPathway,
        fn_result = None,
        topology_result = None,
        seed_neighbors_1hop: Optional[set] = None
    ) -> tuple[float, Dict[str, float]]:
        """
        Compute the Pathway Prioritization Score (PPS) with a component breakdown.

        PPS = db_weight * centrality_weight * (
                 0.30 * significance
               + 0.30 * effect_size
               + 0.25 * specificity
               + 0.15 * replication )

        Every term is normalised to [0, 1] before weighting:

        significance = min(-log10(p_adj) / 10, 1)
            Statistical evidence, saturating at p_adj = 1e-10.

        effect_size   = min(log2(fold_enrichment) / log2(10), 1)
            Observed/expected overlap. Falls back to a set-size-normalised
            proxy when the enrichment test did not report the sizes needed.

        specificity   = 1 - min(log10(term_size) / log10(500), 1)
            How tightly scoped the gene set is.

        replication   = min(support_count / 5, 1)
            Agreement across independent primary enrichments.

        Why this replaces the previous formula
        --------------------------------------
        The earlier score was

            log10(-log10(p_adj) * evidence_count * db_weight * agg_weight * cw + 1)

        which multiplied significance by the *raw* gene count. Because -log10(p)
        was additionally capped at 50 and essentially every top term hit that
        cap, the ranking reduced to "sort by gene count". The result was that
        maximally generic GO terms won every time: on the reference VEGFA/MMP9/
        IL6/TNF/ACE run the top hits were "cell surface receptor signaling
        pathway" (187 genes), "multicellular organism development" (152) and
        "developmental process" (202) -- terms that are true of almost any gene
        list and carry no discovery value. Weighting effect size and specificity
        against significance, rather than multiplying by set size, removes that
        bias.
        """
        pathway = agg_pathway.pathway

        # -- Significance ----------------------------------------------------
        if pathway.p_adj > 0:
            neg_log_p = -math.log10(pathway.p_adj)
        else:
            # p reported as exactly 0 is a numerical floor, not infinite
            # evidence. Treat it as the saturation point, no more.
            neg_log_p = self.P_SATURATION_EXP
        significance = min(neg_log_p / self.P_SATURATION_EXP, 1.0)

        # -- Effect size -----------------------------------------------------
        fold = pathway.fold_enrichment
        if fold and fold > 0:
            effect_size = min(math.log2(fold) / math.log2(self.FOLD_SATURATION), 1.0)
            effect_size = max(0.0, effect_size)
            fold_reported = fold
        else:
            # The enrichment test did not report term/query/domain sizes.
            # Approximate the effect with the share of the term recovered by the
            # query, which is the part of fold enrichment we can still observe.
            term_size = pathway.term_size or max(pathway.evidence_count, 1)
            effect_size = min(pathway.evidence_count / term_size, 1.0)
            fold_reported = None

        # -- Specificity -----------------------------------------------------
        specificity = pathway.gene_set_specificity

        # -- Replication -----------------------------------------------------
        replication = min(agg_pathway.support_count / 5.0, 1.0)

        composite = (
            self.W_SIGNIFICANCE * significance
            + self.W_EFFECT * effect_size
            + self.W_SPECIFICITY * specificity
            + self.W_REPLICATION * replication
        )

        db_weights = self.settings.nets.db_weights
        db_weight = db_weights.get(pathway.source_db, 1.0)

        centrality_weight = self._calculate_centrality_weight(
            pathway, fn_result, topology_result, seed_neighbors_1hop
        )

        nes_score = composite * db_weight * centrality_weight

        components = {
            "significance": round(significance, 4),
            "effect_size": round(effect_size, 4),
            "specificity": round(specificity, 4),
            "replication": round(replication, 4),
            "composite": round(composite, 4),
            "db_weight": db_weight,
            "centrality_weight": round(centrality_weight, 4),
            "raw_p_adj": pathway.p_adj,
            "neg_log10_p_adj": round(neg_log_p, 4),
            "fold_enrichment": round(fold_reported, 3) if fold_reported else None,
            "term_size": pathway.term_size,
            "support_count": agg_pathway.support_count,
        }

        logger.debug(
            f"Pathway {pathway.pathway_id}: "
            f"sig={significance:.2f} eff={effect_size:.2f} spec={specificity:.2f} "
            f"rep={replication:.2f} -> PPS={nes_score:.3f}"
        )

        return nes_score, components

    def _calculate_centrality_weight(
        self,
        pathway,
        fn_result,
        topology_result,
        seed_neighbors_1hop: Optional[set]
    ) -> float:
        """
        Calculate network centrality weight based on seed proximity and PageRank.
        
        Centrality Weight = 1.0 + (0.5 × proximity_score) + (0.3 × pagerank_score)
        
        Where:
        - proximity_score: % of pathway genes within 1-hop of seed genes (0-1)
        - pagerank_score: Average PageRank percentile of pathway genes (0-1)
        
        Range: 1.0 (no centrality data) to 1.8 (perfect proximity + high PageRank)
        
        Args:
            pathway: Pathway entry with evidence genes
            fn_result: Functional neighborhood result
            topology_result: Topology result with PageRank scores
            seed_neighbors_1hop: Pre-calculated set of seed genes + 1-hop neighbors
            
        Returns:
            Centrality weight (1.0 - 1.8)
        """
        if not fn_result or not seed_neighbors_1hop:
            return 1.0  # No bonus if no network data
        
        pathway_genes = set(pathway.evidence_genes)
        
        # Calculate seed proximity (% within 1-hop)
        proximal_genes = pathway_genes & seed_neighbors_1hop
        proximity_score = len(proximal_genes) / len(pathway_genes) if pathway_genes else 0.0
        
        # Calculate average PageRank percentile
        pagerank_score = 0.0
        if topology_result and hasattr(topology_result, 'gene_pageranks'):
            pagerank_dict = topology_result.gene_pageranks
            if pagerank_dict:
                # Get PageRank values for pathway genes
                pathway_pageranks = [pagerank_dict.get(g, 0.0) for g in pathway_genes]
                
                if pathway_pageranks:
                    # Calculate average PageRank
                    avg_pagerank = sum(pathway_pageranks) / len(pathway_pageranks)
                    
                    # Calculate percentile relative to all genes
                    all_pageranks = list(pagerank_dict.values())
                    if all_pageranks:
                        # Simple percentile: % of genes with lower PageRank
                        lower_count = sum(1 for pr in all_pageranks if pr < avg_pagerank)
                        pagerank_score = lower_count / len(all_pageranks)
        
        # Combined centrality weight
        centrality_weight = 1.0 + (0.5 * proximity_score) + (0.3 * pagerank_score)
        
        return centrality_weight
    
    
