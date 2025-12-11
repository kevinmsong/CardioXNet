"""Pathway redundancy detection and removal utilities."""

import logging
from typing import List, Set, Dict
from app.models import ScoredPathway

logger = logging.getLogger(__name__)


class PathwayRedundancyDetector:
    """Detects and removes redundant pathways using Jaccard similarity."""
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize redundancy detector.
        
        Args:
            similarity_threshold: Jaccard similarity threshold for considering pathways redundant (default: 0.7)
        """
        self.similarity_threshold = similarity_threshold
        logger.info(f"PathwayRedundancyDetector initialized with threshold={similarity_threshold}")
    
    def calculate_jaccard_similarity(self, genes1: List[str], genes2: List[str]) -> float:
        """
        Calculate Jaccard similarity between two gene sets.
        
        Jaccard similarity = |intersection| / |union|
        
        Args:
            genes1: First gene list
            genes2: Second gene list
            
        Returns:
            Jaccard similarity score [0, 1]
        """
        set1 = set(genes1)
        set2 = set(genes2)
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def remove_redundant_pathways(
        self,
        pathways: List[ScoredPathway],
        keep_best_scored: bool = True
    ) -> List[ScoredPathway]:
        """
        Remove redundant pathways based on Jaccard similarity.
        
        Strategy:
        1. Sort pathways by NES score (descending) if keep_best_scored=True
        2. For each pathway, check if it's similar to any already-kept pathway
        3. If Jaccard similarity > threshold, skip it (redundant)
        4. Otherwise, add it to non-redundant list
        
        Args:
            pathways: List of scored pathways
            keep_best_scored: If True, keep pathway with better statistics when redundant
            
        Returns:
            List of non-redundant pathways
        """
        if not pathways:
            return []
        
        logger.info(f"Detecting redundant pathways in {len(pathways)} pathways...")
        
        # Sort by NES score if requested (higher is better)
        if keep_best_scored:
            pathways = sorted(pathways, key=lambda p: p.nes_score, reverse=True)
        
        non_redundant = []
        redundant_pairs = []
        
        for pathway in pathways:
            is_redundant = False
            
            # Get genes for this pathway (ScoredPathway has aggregated_pathway.pathway.evidence_genes)
            try:
                current_genes = pathway.aggregated_pathway.pathway.evidence_genes
            except (AttributeError, TypeError):
                # No genes available, can't check similarity
                logger.warning(f"Could not extract genes from pathway, skipping similarity check")
                non_redundant.append(pathway)
                continue
            
            # Check against all non-redundant pathways
            for kept_pathway in non_redundant:
                # Get genes for kept pathway
                try:
                    kept_genes = kept_pathway.aggregated_pathway.pathway.evidence_genes
                except (AttributeError, TypeError):
                    continue
                
                # Calculate similarity
                similarity = self.calculate_jaccard_similarity(current_genes, kept_genes)
                
                if similarity >= self.similarity_threshold:
                    # Redundant pathway found
                    is_redundant = True
                    # Get pathway names
                    current_name = pathway.aggregated_pathway.pathway.pathway_name
                    kept_name = kept_pathway.aggregated_pathway.pathway.pathway_name
                    
                    redundant_pairs.append({
                        'redundant': current_name,
                        'kept': kept_name,
                        'similarity': similarity,
                        'redundant_nes': pathway.nes_score,
                        'kept_nes': kept_pathway.nes_score
                    })
                    logger.debug(
                        f"Pathway '{current_name}' "
                        f"is redundant with '{kept_name}' "
                        f"(Jaccard={similarity:.3f})"
                    )
                    break
            
            if not is_redundant:
                non_redundant.append(pathway)
        
        removed_count = len(pathways) - len(non_redundant)
        logger.info(
            f"Redundancy detection complete: {len(pathways)} → {len(non_redundant)} pathways "
            f"({removed_count} redundant pathways removed)"
        )
        
        # Log summary of removed pathways
        if redundant_pairs:
            logger.info(f"Removed {len(redundant_pairs)} redundant pathway pairs:")
            for i, pair in enumerate(redundant_pairs[:10], 1):  # Log first 10
                logger.info(
                    f"  {i}. '{pair['redundant']}' (NES={pair['redundant_nes']:.1f}) → "
                    f"'{pair['kept']}' (NES={pair['kept_nes']:.1f}), similarity={pair['similarity']:.3f}"
                )
            if len(redundant_pairs) > 10:
                logger.info(f"  ... and {len(redundant_pairs) - 10} more")
        
        return non_redundant
    
    def get_redundancy_statistics(self, pathways: List[ScoredPathway]) -> Dict:
        """
        Calculate redundancy statistics for a pathway list.
        
        Args:
            pathways: List of scored pathways
            
        Returns:
            Dictionary with redundancy statistics
        """
        if len(pathways) < 2:
            return {
                'total_pathways': len(pathways),
                'redundant_pairs': 0,
                'avg_similarity': 0.0,
                'max_similarity': 0.0
            }
        
        similarities = []
        redundant_pairs = 0
        
        for i, pathway1 in enumerate(pathways):
            # Get genes for pathway1
            try:
                genes1 = pathway1.aggregated_pathway.pathway.evidence_genes
            except (AttributeError, TypeError):
                continue
            
            for pathway2 in pathways[i+1:]:
                # Get genes for pathway2
                try:
                    genes2 = pathway2.aggregated_pathway.pathway.evidence_genes
                except (AttributeError, TypeError):
                    continue
                
                similarity = self.calculate_jaccard_similarity(genes1, genes2)
                similarities.append(similarity)
                
                if similarity >= self.similarity_threshold:
                    redundant_pairs += 1
        
        return {
            'total_pathways': len(pathways),
            'redundant_pairs': redundant_pairs,
            'avg_similarity': sum(similarities) / len(similarities) if similarities else 0.0,
            'max_similarity': max(similarities) if similarities else 0.0,
            'similarity_distribution': {
                'high (>0.7)': sum(1 for s in similarities if s > 0.7),
                'medium (0.4-0.7)': sum(1 for s in similarities if 0.4 <= s <= 0.7),
                'low (<0.4)': sum(1 for s in similarities if s < 0.4)
            }
        }
