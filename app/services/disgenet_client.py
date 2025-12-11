"""Cardiac Gene-Disease Association Scoring.

Uses curated cardiac gene database compiled from public sources including:
- ClinVar cardiovascular disease variants
- OMIM cardiac disease genes  
- Published literature on cardiac genetics
- GO annotations for heart development/function
"""

import logging
from typing import Dict, List, Optional
from functools import lru_cache
from .cardiac_genes_db import get_cardiac_score, get_batch_scores as db_get_batch_scores

logger = logging.getLogger(__name__)


class DisGeNETClient:
    """Client for cardiac gene-disease association scoring using curated database."""
    
    # Using curated cardiac gene database instead of API
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize cardiac gene scoring client.
        
        Args:
            api_key: Not used (kept for compatibility)
        """
        logger.info("Cardiac gene scoring client initialized with curated database")
    
    @lru_cache(maxsize=1000)
    def get_gene_disease_score(self, gene_symbol: str) -> float:
        """
        Get cardiac disease association score for a gene.
        
        Args:
            gene_symbol: Gene symbol (e.g., "SCN5A")
        
        Returns:
            Cardiac disease association score (0.0-1.0)
        """
        score = get_cardiac_score(gene_symbol)
        
        if score > 0:
            logger.debug(f"Cardiac score for {gene_symbol}: {score:.3f}")
        
        return score
    
    # Removed _calculate_cardiac_score - using curated database instead
    
    def get_batch_scores(self, gene_symbols: List[str]) -> Dict[str, float]:
        """
        Get cardiac disease association scores for multiple genes.
        
        Args:
            gene_symbols: List of gene symbols
        
        Returns:
            Dictionary mapping gene symbol to cardiac score
        """
        return db_get_batch_scores(gene_symbols)
    
    def get_top_cardiac_genes(self, gene_symbols: List[str], top_n: int = 10) -> List[Dict[str, any]]:
        """
        Get top genes ranked by cardiac disease association.
        
        Args:
            gene_symbols: List of gene symbols to score
            top_n: Number of top genes to return
        
        Returns:
            List of dicts with gene and score, sorted by score descending
        """
        scores = self.get_batch_scores(gene_symbols)
        
        # Sort by score descending
        ranked = [
            {"gene": gene, "disgenet_cardiac_score": score}
            for gene, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return ranked[:top_n]

