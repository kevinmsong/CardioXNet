"""
Novelty Scorer for Scientific Discovery

Calculates novelty scores for pathways based on:
1. Literature saturation (inverse of citation count)
2. Pathway specificity (cardiac relevance × uniqueness)
3. Network uniqueness (non-overlapping genes)

Author: CardioXNet Team
Date: 2025-10-27
"""

import logging
from typing import List, Dict, Any, Optional
import math

logger = logging.getLogger(__name__)


class NoveltyScorer:
    """
    Calculate novelty scores for pathway discovery.
    
    Novelty Score Formula:
    novelty_score = (1 - literature_saturation) × pathway_specificity × network_uniqueness
    
    Where:
    - literature_saturation = log(citations + 1) / log(max_citations + 1)
    - pathway_specificity = cardiac_relevance × (1 - pathway_generality)
    - network_uniqueness = 1 - (shared_genes / total_genes)
    """
    
    def __init__(self):
        """Initialize novelty scorer."""
        self.max_citations = 1000  # Threshold for highly studied pathways
        
        # Generic pathway terms indicating low specificity
        self.generic_terms = {
            'regulation', 'process', 'pathway', 'signaling', 'response',
            'metabolism', 'biosynthesis', 'catabolism', 'transport',
            'localization', 'organization', 'development', 'differentiation'
        }
    
    def calculate_novelty_score(
        self,
        pathway_name: str,
        literature_citations: int,
        cardiac_relevance: float,
        pathway_genes: List[str],
        all_pathway_genes: List[List[str]],
        max_citations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive novelty score for a pathway.
        
        Args:
            pathway_name: Name of the pathway
            literature_citations: Number of PubMed citations
            cardiac_relevance: Cardiac relevance score (0-1)
            pathway_genes: List of genes in this pathway
            all_pathway_genes: List of gene lists from all pathways
            max_citations: Optional override for max citation threshold
            
        Returns:
            Dictionary with novelty score and components
        """
        if max_citations:
            self.max_citations = max_citations
        
        # Component 1: Literature saturation (0 = novel, 1 = saturated)
        literature_saturation = self._calculate_literature_saturation(literature_citations)
        
        # Component 2: Pathway specificity (0 = generic, 1 = specific)
        pathway_specificity = self._calculate_pathway_specificity(
            pathway_name, cardiac_relevance
        )
        
        # Component 3: Network uniqueness (0 = redundant, 1 = unique)
        network_uniqueness = self._calculate_network_uniqueness(
            pathway_genes, all_pathway_genes
        )
        
        # Calculate composite novelty score
        novelty_score = (
            (1 - literature_saturation) * 
            pathway_specificity * 
            network_uniqueness
        )
        
        # Determine novelty tier
        novelty_tier = self._determine_novelty_tier(novelty_score)
        
        return {
            'novelty_score': novelty_score,
            'literature_saturation': literature_saturation,
            'pathway_specificity': pathway_specificity,
            'network_uniqueness': network_uniqueness,
            'novelty_tier': novelty_tier,
            'is_novel': novelty_score > 0.5,  # Threshold for "novel" classification
            'discovery_priority': 'high' if novelty_score > 0.7 else 'medium' if novelty_score > 0.4 else 'low'
        }
    
    def _calculate_literature_saturation(self, citations: int) -> float:
        """
        Calculate literature saturation score.
        
        Args:
            citations: Number of PubMed citations
            
        Returns:
            Saturation score (0 = no literature, 1 = highly studied)
        """
        if citations <= 0:
            return 0.0
        
        # Log-scale normalization to handle wide citation ranges
        saturation = math.log(citations + 1) / math.log(self.max_citations + 1)
        
        return min(saturation, 1.0)
    
    def _calculate_pathway_specificity(
        self,
        pathway_name: str,
        cardiac_relevance: float
    ) -> float:
        """
        Calculate pathway specificity score.
        
        Args:
            pathway_name: Name of the pathway
            cardiac_relevance: Cardiac relevance score (0-1)
            
        Returns:
            Specificity score (0 = generic, 1 = specific)
        """
        # Calculate pathway generality based on generic terms
        pathway_name_lower = pathway_name.lower()
        generic_term_count = sum(
            1 for term in self.generic_terms 
            if term in pathway_name_lower
        )
        
        # Generality score (0 = specific, 1 = generic)
        generality = min(generic_term_count / 3.0, 1.0)  # Max 3 generic terms
        
        # Specificity = cardiac relevance × (1 - generality)
        specificity = cardiac_relevance * (1 - generality)
        
        return specificity
    
    def _calculate_network_uniqueness(
        self,
        pathway_genes: List[str],
        all_pathway_genes: List[List[str]]
    ) -> float:
        """
        Calculate network uniqueness score.
        
        Args:
            pathway_genes: List of genes in this pathway
            all_pathway_genes: List of gene lists from all pathways
            
        Returns:
            Uniqueness score (0 = highly redundant, 1 = unique)
        """
        if not pathway_genes or not all_pathway_genes:
            return 0.5  # Neutral score if no data
        
        pathway_genes_set = set(pathway_genes)
        total_genes = len(pathway_genes_set)
        
        if total_genes == 0:
            return 0.0
        
        # Calculate maximum overlap with any other pathway
        max_overlap = 0
        for other_genes in all_pathway_genes:
            if other_genes == pathway_genes:
                continue  # Skip self
            
            other_genes_set = set(other_genes)
            overlap = len(pathway_genes_set & other_genes_set)
            max_overlap = max(max_overlap, overlap)
        
        # Uniqueness = 1 - (max_shared_genes / total_genes)
        uniqueness = 1 - (max_overlap / total_genes)
        
        return uniqueness
    
    def _determine_novelty_tier(self, novelty_score: float) -> str:
        """
        Determine novelty tier based on score.
        
        Args:
            novelty_score: Novelty score (0-1)
            
        Returns:
            Novelty tier string
        """
        if novelty_score >= 0.8:
            return 'Highly Novel'
        elif novelty_score >= 0.6:
            return 'Novel'
        elif novelty_score >= 0.4:
            return 'Moderately Novel'
        elif novelty_score >= 0.2:
            return 'Established'
        else:
            return 'Well-Studied'
    
    def annotate_pathways_with_novelty(
        self,
        hypotheses: List[Any]
    ) -> List[Any]:
        """
        Annotate all pathways with novelty scores.
        
        Args:
            hypotheses: List of pathway hypotheses
            
        Returns:
            Annotated hypotheses with novelty scores
        """
        if not hypotheses:
            return hypotheses
        
        # Extract all pathway genes for uniqueness calculation
        all_pathway_genes = []
        for hyp in hypotheses:
            if hasattr(hyp, 'aggregated_pathway'):
                genes = hyp.aggregated_pathway.pathway.evidence_genes or []
                all_pathway_genes.append(genes)
        
        # Calculate novelty for each pathway
        for hyp in hypotheses:
            if not hasattr(hyp, 'aggregated_pathway'):
                continue
            
            pathway = hyp.aggregated_pathway.pathway
            pathway_name = pathway.pathway_name
            literature_citations = getattr(hyp, 'literature_citations', 0)
            
            # Get cardiac relevance from score components
            cardiac_relevance = 0.5  # Default
            if hasattr(hyp, 'score_components') and hyp.score_components:
                cardiac_relevance = hyp.score_components.get('cardiac_relevance', 0.5)
            
            pathway_genes = pathway.evidence_genes or []
            
            # Calculate novelty score
            novelty_data = self.calculate_novelty_score(
                pathway_name=pathway_name,
                literature_citations=literature_citations,
                cardiac_relevance=cardiac_relevance,
                pathway_genes=pathway_genes,
                all_pathway_genes=all_pathway_genes
            )
            
            # Store novelty data in score components
            if not hasattr(hyp, 'score_components') or hyp.score_components is None:
                hyp.score_components = {}
            
            hyp.score_components['novelty_score'] = novelty_data['novelty_score']
            hyp.score_components['literature_saturation'] = novelty_data['literature_saturation']
            hyp.score_components['pathway_specificity'] = novelty_data['pathway_specificity']
            hyp.score_components['network_uniqueness'] = novelty_data['network_uniqueness']
            hyp.score_components['novelty_tier'] = novelty_data['novelty_tier']
            hyp.score_components['is_novel'] = novelty_data['is_novel']
            hyp.score_components['discovery_priority'] = novelty_data['discovery_priority']
        
        logger.info(f"Annotated {len(hypotheses)} pathways with novelty scores")
        
        return hypotheses

