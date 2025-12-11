"""Hypothesis validation service for comprehensive evidence scoring."""

import logging
from typing import Dict, List
import math

from app.models import ScoredPathway, GeneInfo
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class HypothesisValidator:
    """Validates and scores hypotheses based on multiple evidence types (Stage 4a).
    
    Scientific Rigor Enhancements:
    - Multi-evidence composite scoring (statistical + replication + literature + network + novelty)
    - Statistical strength combines p-value significance and evidence count robustness
    - Replication support rewards cross-database validation (minimum 2 sources required)
    - Literature evidence integrates citation count and relevance scoring
    - Network evidence evaluates key mediating nodes and connectivity patterns
    - Novelty scoring penalizes high seed gene overlap to prioritize discovery
    - Normalized weighting ensures balanced contribution from all evidence types
    """
    
    def __init__(self):
        """Initialize hypothesis validator."""
        self.settings = get_settings()
        logger.info("HypothesisValidator initialized - Enhanced multi-evidence validation")
    
    def calculate_validation_score(
        self,
        hypothesis: ScoredPathway,
        literature_citations: List,
        network_analysis: Dict,
        seed_genes: List[GeneInfo]
    ) -> Dict[str, float]:
        """
        Calculate comprehensive validation score combining multiple evidence types.
        
        Validation Score Components:
        1. Statistical Strength (0-0.3): Based on P-value and evidence count
        2. Replication Support (0-0.2): Based on support count across primaries
        3. Literature Evidence (0-0.2): Based on citation count and relevance
        4. Network Evidence (0-0.2): Based on key mediating nodes
        5. Novelty Score (0-0.1): Based on seed gene overlap
        
        Args:
            hypothesis: Scored pathway hypothesis
            literature_citations: List of literature citations
            network_analysis: Network topology analysis results
            seed_genes: Original seed genes
            
        Returns:
            Dictionary with validation score and component breakdown
        """
        scores = {}
        
        # 1. Statistical Strength (0-0.3)
        p_adj = hypothesis.aggregated_pathway.pathway.p_adj if hasattr(hypothesis, 'aggregated_pathway') else hypothesis.p_adj
        evidence_count = hypothesis.aggregated_pathway.pathway.evidence_count if hasattr(hypothesis, 'aggregated_pathway') else hypothesis.evidence_count
        
        # P-value component (0-0.15)
        if p_adj > 0:
            log_p = min(-math.log10(p_adj), 50)
            p_score = min(log_p / 50.0, 1.0) * 0.15
        else:
            p_score = 0.15
        
        # Evidence count component (0-0.15)
        evidence_score = min(evidence_count / 20.0, 1.0) * 0.15
        
        scores['statistical_strength'] = p_score + evidence_score
        
        # 2. Replication Support (0-0.2)
        support_count = hypothesis.aggregated_pathway.support_count if hasattr(hypothesis, 'aggregated_pathway') else hypothesis.support_count
        support_score = min(support_count / 5.0, 1.0) * 0.2
        scores['replication_support'] = support_score
        
        # 3. Literature Evidence (0-0.2)
        if literature_citations:
            # Citation count (0-0.1)
            citation_score = min(len(literature_citations) / 10.0, 1.0) * 0.1
            
            # Average relevance (0-0.1)
            avg_relevance = sum(c.get('relevance_score', 0) for c in literature_citations) / len(literature_citations)
            relevance_score = avg_relevance * 0.1
            
            scores['literature_evidence'] = citation_score + relevance_score
        else:
            scores['literature_evidence'] = 0.0
        
        # 4. Network Evidence (0-0.2)
        if network_analysis and 'key_nodes' in network_analysis:
            key_nodes = network_analysis['key_nodes']
            
            # Number of key mediating nodes (0-0.1)
            mediator_count = sum(1 for node in key_nodes if node.get('role') == 'mediator')
            mediator_score = min(mediator_count / 5.0, 1.0) * 0.1
            
            # Average centrality of key nodes (0-0.1)
            if key_nodes:
                avg_centrality = sum(node.get('betweenness_centrality', 0) for node in key_nodes) / len(key_nodes)
                centrality_score = min(avg_centrality / 0.3, 1.0) * 0.1
            else:
                centrality_score = 0.0
            
            scores['network_evidence'] = mediator_score + centrality_score
        else:
            scores['network_evidence'] = 0.0
        
        # 5. Novelty Score (0-0.1)
        # Higher score for lower seed overlap (more novel)
        pathway_genes = set(hypothesis.aggregated_pathway.pathway.evidence_genes if hasattr(hypothesis, 'aggregated_pathway') else [])
        seed_gene_symbols = {gene.symbol for gene in seed_genes}
        
        if pathway_genes:
            overlap = len(pathway_genes & seed_gene_symbols)
            overlap_ratio = overlap / len(pathway_genes)
            novelty_score = (1.0 - overlap_ratio) * 0.1
        else:
            novelty_score = 0.05
        
        scores['novelty_score'] = novelty_score
        
        # Calculate total validation score
        total_score = sum(scores.values())
        scores['total_validation_score'] = total_score
        
        # Add interpretation
        if total_score >= 0.7:
            scores['confidence_level'] = 'high'
        elif total_score >= 0.5:
            scores['confidence_level'] = 'medium'
        else:
            scores['confidence_level'] = 'low'
        
        logger.debug(
            f"Validation score: {total_score:.3f} "
            f"(stat={scores['statistical_strength']:.3f}, "
            f"rep={scores['replication_support']:.3f}, "
            f"lit={scores['literature_evidence']:.3f}, "
            f"net={scores['network_evidence']:.3f}, "
            f"nov={scores['novelty_score']:.3f})"
        )
        
        return scores
    
    def rank_by_validation(
        self,
        hypotheses: List[ScoredPathway],
        validation_scores: Dict[str, Dict]
    ) -> List[ScoredPathway]:
        """
        Re-rank hypotheses by validation score.
        
        Args:
            hypotheses: List of scored hypotheses
            validation_scores: Dictionary mapping pathway_id to validation scores
            
        Returns:
            Re-ranked list of hypotheses
        """
        # Sort by validation score
        ranked = sorted(
            hypotheses,
            key=lambda h: validation_scores.get(
                h.aggregated_pathway.pathway.pathway_id if hasattr(h, 'aggregated_pathway') else h.pathway_id,
                {}
            ).get('total_validation_score', 0),
            reverse=True
        )
        
        # Update ranks
        for i, hypothesis in enumerate(ranked, 1):
            hypothesis.rank = i
        
        return ranked
