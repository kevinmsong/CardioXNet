"""Final NES scoring service (Stage 5a)."""

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
    """Calculates final NES scores for pathway hypotheses (Stage 3a).
    
    Scientific Rigor Enhancements:
    - Log-scale statistical significance prevents p-value dominance
    - Evidence count weighting ensures robust pathway membership
    - Multi-database quality weighting (Reactome > GO > KEGG > WikiPathways)
    - Replication-based aggregation weight rewards cross-source validation
    - Composite scoring balances statistical significance with biological evidence
    """
    
    def __init__(self):
        """Initialize NES scorer."""
        self.settings = get_settings()
        logger.info("NESScorer initialized - Enhanced composite scoring for pathway prioritization")
    
    def score(
        self,
        final_result: FinalPathwayResult,
        fn_result = None,
        topology_result = None
    ) -> ScoredHypotheses:
        """
        Calculate final NES scores for aggregated pathways with optional network centrality.
        
        Enhanced NES = -log10(P_adj) * evidence_count * db_weight * agg_weight * centrality_weight
        
        Where:
        - -log10(P_adj): Statistical significance
        - evidence_count: Number of genes in pathway
        - db_weight: Database quality weight from config
        - agg_weight: Aggregation weight based on support count
        - centrality_weight: Network centrality bonus (1.0-1.8×) based on:
            * Seed gene proximity (% genes within 1-hop of seed genes)
            * PageRank centrality (network importance of pathway genes)
            
        Args:
            final_result: Final pathway result from Stage 2c
            fn_result: Optional functional neighborhood result for proximity calculation
            topology_result: Optional topology result for centrality metrics
            
        Returns:
            ScoredHypotheses with ranked pathway hypotheses
        """
        print(f"[NES SCORER DEBUG] Received {final_result.total_count} pathways to score")
        print(f"[NES SCORER DEBUG] final_pathways list length: {len(final_result.final_pathways)}")
        
        logger.info(
            f"Calculating final NES scores for {final_result.total_count} pathways"
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
        
        for i, agg_pathway in enumerate(final_result.final_pathways):
            if i < 3:  # Log first 3 pathways
                print(f"[NES SCORER DEBUG] Processing pathway {i+1}: {agg_pathway.pathway.pathway_name}")
            
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
        
        print(f"[NES SCORER DEBUG] Scored {len(scored_pathways)} pathways")
        
        # Sort by NES score (descending)
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
    
    def _calculate_nes(
        self,
        agg_pathway: AggregatedPathway,
        fn_result = None,
        topology_result = None,
        seed_neighbors_1hop: Optional[set] = None
    ) -> tuple[float, Dict[str, float]]:
        """
        Calculate final NES score with component breakdown including network centrality.
        
        Args:
            agg_pathway: Aggregated pathway
            fn_result: Optional functional neighborhood for proximity calculation
            topology_result: Optional topology result for PageRank centrality
            seed_neighbors_1hop: Pre-calculated set of seed genes + 1-hop neighbors
            
        Returns:
            Tuple of (nes_score, components_dict)
        """
        pathway = agg_pathway.pathway
        
        # Component 1: -log10(P_adj)
        # Handle zero or extremely small p-values with a reasonable cap
        if pathway.p_adj > 0:
            p_adj_component = -math.log10(pathway.p_adj)
        else:
            # For p-values reported as 0, use a very small value
            # Equivalent to p_adj = 1e-50 (extremely significant but not infinite)
            p_adj_component = 50.0
        
        # Cap at 50 to prevent extreme scores from numerical precision issues
        p_adj_component = min(p_adj_component, 50.0)
        
        # Component 2: Evidence count
        evidence_component = float(pathway.evidence_count)
        
        # Component 3: Database weight
        db_weights = self.settings.nets.db_weights
        db_weight = db_weights.get(pathway.source_db, 1.0)
        
        # Component 4: Aggregation weight
        agg_weight = self._calculate_aggregation_weight(agg_pathway.support_count)
        
        # Component 5: Network Centrality Weight (NEW - Enhanced Scoring)
        centrality_weight = self._calculate_centrality_weight(
            pathway,
            fn_result,
            topology_result,
            seed_neighbors_1hop
        )
        
        # Calculate raw NES with centrality component
        raw_nes = p_adj_component * evidence_component * db_weight * agg_weight * centrality_weight
        
        # Apply log10 transformation for better interpretability
        # log10(abs(raw_nes) + 1) compresses large values (50 -> 1.7, 100 -> 2.0)
        # +1 ensures log is defined for raw_nes = 0
        import math as m
        nes_score = m.log10(abs(raw_nes) + 1) * (1 if raw_nes >= 0 else -1)
        
        # Build components breakdown
        components = {
            "p_adj_component": p_adj_component,
            "evidence_component": evidence_component,
            "db_weight": db_weight,
            "agg_weight": agg_weight,
            "centrality_weight": centrality_weight,  # NEW
            "raw_p_adj": pathway.p_adj,
            "support_count": agg_pathway.support_count,
            "raw_nes": raw_nes  # Store raw NES for reference
        }
        
        logger.debug(
            f"Pathway {pathway.pathway_id}: "
            f"P_adj={pathway.p_adj:.2e}, "
            f"evidence={pathway.evidence_count}, "
            f"db_weight={db_weight:.2f}, "
            f"agg_weight={agg_weight:.2f}, "
            f"centrality_weight={centrality_weight:.2f}, "
            f"NES={nes_score:.2f}"
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
    
    def _get_seed_neighbors_1hop(self, fn_result) -> set:
        """
        Get set of seed genes and their 1-hop neighbors.
        
        Args:
            fn_result: Functional neighborhood result
            
        Returns:
            Set of gene symbols (seed genes + 1-hop neighbors)
        """
        if not fn_result:
            return set()
        
        seed_genes = {g.symbol for g in fn_result.seed_genes}
        neighbors_1hop = {g.symbol for g in fn_result.neighbors}
        return seed_genes | neighbors_1hop
    
    def _calculate_aggregation_weight(self, support_count: int) -> float:
        """
        Calculate aggregation weight based on support count.
        
        Weight increases with support count using a logarithmic scale:
        - support_count = 1: weight = 1.0 (baseline)
        - support_count = 2: weight = 1.2
        - support_count = 3: weight = 1.35
        - support_count = 4: weight = 1.45
        - support_count = 5+: weight = 1.5 (cap)
        
        Args:
            support_count: Number of primary pathways supporting this pathway
            
        Returns:
            Aggregation weight (1.0 - 1.5)
        """
        if support_count <= 1:
            return 1.0
        
        # Logarithmic scaling with cap at 1.5
        weight = 1.0 + (0.5 * math.log(support_count) / math.log(5))
        
        return min(weight, 1.5)
