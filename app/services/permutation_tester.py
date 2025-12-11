"""Permutation-based empirical p-value calculation for pathway enrichment."""

import logging
import random
from typing import List, Dict, Set, Tuple, Any, Optional
import numpy as np
from collections import Counter

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PermutationTester:
    """
    Calculates empirical p-values using permutation testing.
    
    SCIENTIFIC RATIONALE:
    - Standard enrichment tests assume theoretical null distributions
    - Network structure creates biases (hub genes, degree distribution)
    - Permutation testing generates empirical nulls specific to your data
    - More conservative and accurate than parametric tests
    
    METHOD:
    1. Observe overlap between pathway genes and functional neighborhood
    2. Permute gene labels while preserving network structure
    3. Calculate null distribution of overlaps
    4. Empirical p-value = (# permutations >= observed + 1) / (n_permutations + 1)
    """
    
    def __init__(self):
        """Initialize permutation tester."""
        self.settings = get_settings()
        # Further reduced from 100 to 50 for speed optimization
        self.n_permutations = self.settings.nets.n_permutations if hasattr(
            self.settings.nets, 'n_permutations'
        ) else 50
        
        logger.info(f"PermutationTester initialized with {self.n_permutations} permutations")
    
    def calculate_empirical_pvalue(
        self,
        pathway_genes: List[str],
        fn_genes: List[str],
        all_genes: List[str],
        n_permutations: Optional[int] = None
    ) -> Tuple[float, Dict]:
        """
        Calculate empirical p-value for pathway enrichment.
        
        Args:
            pathway_genes: Genes in the pathway
            fn_genes: Genes in functional neighborhood
            all_genes: Universe of all possible genes
            n_permutations: Number of permutations (default from config)
            
        Returns:
            Tuple of (empirical_pvalue, statistics_dict)
        """
        if n_permutations is None:
            n_permutations = self.n_permutations
        
        # Convert to sets for faster operations
        pathway_set = set(pathway_genes)
        fn_set = set(fn_genes)
        all_genes_set = set(all_genes)
        
        # Observed overlap
        observed_overlap = len(pathway_set & fn_set)
        
        # If no overlap, return p=1.0
        if observed_overlap == 0:
            return 1.0, {
                'observed_overlap': 0,
                'mean_null_overlap': 0,
                'null_overlaps': [],
                'n_permutations': n_permutations
            }
        
        # Generate null distribution
        null_overlaps = []
        
        for i in range(n_permutations):
            # Randomly sample same number of genes from universe
            permuted_fn = set(random.sample(list(all_genes_set), len(fn_genes)))
            null_overlap = len(pathway_set & permuted_fn)
            null_overlaps.append(null_overlap)
        
        # Calculate empirical p-value
        # Add 1 to numerator and denominator to avoid p=0
        n_greater_equal = sum(1 for null in null_overlaps if null >= observed_overlap)
        empirical_p = (n_greater_equal + 1) / (n_permutations + 1)
        
        # Statistics
        mean_null = np.mean(null_overlaps)
        std_null = np.std(null_overlaps)
        
        logger.debug(
            f"Empirical p-value: {empirical_p:.4f} "
            f"(observed: {observed_overlap}, mean null: {mean_null:.2f} ± {std_null:.2f})"
        )
        
        statistics = {
            'observed_overlap': observed_overlap,
            'mean_null_overlap': mean_null,
            'std_null_overlap': std_null,
            'null_overlaps': null_overlaps,
            'n_permutations': n_permutations,
            'z_score': (observed_overlap - mean_null) / std_null if std_null > 0 else 0
        }
        
        return empirical_p, statistics
    
    def calculate_empirical_pvalue_adaptive(
        self,
        pathway_genes: List[str],
        fn_genes: List[str],
        all_genes: List[str],
        min_permutations: int = 100,
        max_permutations: int = 500
    ) -> Tuple[float, Dict]:
        """
        Calculate empirical p-value with adaptive sampling.
        
        Uses early stopping when result is clearly significant or non-significant.
        This provides major performance improvement while maintaining statistical validity.
        
        Algorithm:
        1. Start with min_permutations
        2. If p < 0.001 or p > 0.1: stop early (clear result)
        3. If 0.001 ≤ p ≤ 0.1: continue to max_permutations (borderline)
        
        Args:
            pathway_genes: Genes in the pathway
            fn_genes: Genes in functional neighborhood
            all_genes: Universe of all possible genes
            min_permutations: Minimum permutations (default 100)
            max_permutations: Maximum permutations (default 500)
            
        Returns:
            Tuple of (empirical_pvalue, statistics_dict)
        """
        # Convert to sets
        pathway_set = set(pathway_genes)
        fn_set = set(fn_genes)
        all_genes_set = set(all_genes)
        
        # Observed overlap
        observed_overlap = len(pathway_set & fn_set)
        
        if observed_overlap == 0:
            return 1.0, {
                'observed_overlap': 0,
                'mean_null_overlap': 0,
                'null_overlaps': [],
                'n_permutations': min_permutations,
                'early_stop': True,
                'stop_reason': 'no_overlap'
            }
        
        # Phase 1: Initial permutations
        null_overlaps = []
        for i in range(min_permutations):
            permuted_fn = set(random.sample(list(all_genes_set), len(fn_genes)))
            null_overlap = len(pathway_set & permuted_fn)
            null_overlaps.append(null_overlap)
        
        # Calculate preliminary p-value
        n_greater_equal = sum(1 for null in null_overlaps if null >= observed_overlap)
        prelim_p = (n_greater_equal + 1) / (min_permutations + 1)
        
        # Early stopping decision
        early_stop = False
        stop_reason = None
        
        if prelim_p < 0.001:
            # Clearly significant - stop early
            early_stop = True
            stop_reason = 'highly_significant'
            logger.debug(f"Early stop: p={prelim_p:.4f} < 0.001 (highly significant)")
        
        elif prelim_p > 0.1:
            # Clearly non-significant - stop early
            early_stop = True
            stop_reason = 'not_significant'
            logger.debug(f"Early stop: p={prelim_p:.4f} > 0.1 (not significant)")
        
        else:
            # Borderline result - continue to max_permutations
            logger.debug(
                f"Borderline p={prelim_p:.4f}, continuing to {max_permutations} permutations"
            )
            remaining = max_permutations - min_permutations
            for i in range(remaining):
                permuted_fn = set(random.sample(list(all_genes_set), len(fn_genes)))
                null_overlap = len(pathway_set & permuted_fn)
                null_overlaps.append(null_overlap)
        
        # Final p-value calculation
        n_permutations = len(null_overlaps)
        n_greater_equal = sum(1 for null in null_overlaps if null >= observed_overlap)
        empirical_p = (n_greater_equal + 1) / (n_permutations + 1)
        
        # Statistics
        mean_null = np.mean(null_overlaps)
        std_null = np.std(null_overlaps)
        
        logger.debug(
            f"Adaptive empirical p-value: {empirical_p:.4f} "
            f"(observed: {observed_overlap}, mean null: {mean_null:.2f}, "
            f"n_perm: {n_permutations}, early_stop: {early_stop})"
        )
        
        statistics = {
            'observed_overlap': observed_overlap,
            'mean_null_overlap': mean_null,
            'std_null_overlap': std_null,
            'null_overlaps': null_overlaps,
            'n_permutations': n_permutations,
            'z_score': (observed_overlap - mean_null) / std_null if std_null > 0 else 0,
            'early_stop': early_stop,
            'stop_reason': stop_reason,
            'min_permutations': min_permutations,
            'max_permutations': max_permutations
        }
        
        return empirical_p, statistics
    
    def calculate_degree_preserving_pvalue(
        self,
        pathway_genes: List[str],
        fn_genes: List[str],
        gene_degrees: Dict[str, int],
        all_genes: List[str],
        n_permutations: Optional[int] = None
    ) -> Tuple[float, Dict]:
        """
        Calculate empirical p-value preserving degree distribution.
        
        More sophisticated permutation that maintains network topology.
        
        Args:
            pathway_genes: Genes in the pathway
            fn_genes: Genes in functional neighborhood
            gene_degrees: Dictionary mapping gene -> degree (number of connections)
            all_genes: Universe of all possible genes
            n_permutations: Number of permutations
            
        Returns:
            Tuple of (empirical_pvalue, statistics_dict)
        """
        if n_permutations is None:
            n_permutations = self.n_permutations
        
        pathway_set = set(pathway_genes)
        fn_set = set(fn_genes)
        
        # Observed overlap
        observed_overlap = len(pathway_set & fn_set)
        
        if observed_overlap == 0:
            return 1.0, {
                'observed_overlap': 0,
                'mean_null_overlap': 0,
                'null_overlaps': [],
                'n_permutations': n_permutations
            }
        
        # Bin genes by degree
        degree_bins = self._bin_genes_by_degree(gene_degrees, all_genes)
        
        # Generate null distribution preserving degree
        null_overlaps = []
        
        for i in range(n_permutations):
            # Sample genes from same degree bins
            permuted_fn = self._sample_preserving_degree(fn_genes, degree_bins, gene_degrees)
            null_overlap = len(pathway_set & permuted_fn)
            null_overlaps.append(null_overlap)
        
        # Calculate empirical p-value
        n_greater_equal = sum(1 for null in null_overlaps if null >= observed_overlap)
        empirical_p = (n_greater_equal + 1) / (n_permutations + 1)
        
        mean_null = np.mean(null_overlaps)
        std_null = np.std(null_overlaps)
        
        logger.debug(
            f"Degree-preserving empirical p-value: {empirical_p:.4f} "
            f"(observed: {observed_overlap}, mean null: {mean_null:.2f})"
        )
        
        statistics = {
            'observed_overlap': observed_overlap,
            'mean_null_overlap': mean_null,
            'std_null_overlap': std_null,
            'null_overlaps': null_overlaps,
            'n_permutations': n_permutations,
            'z_score': (observed_overlap - mean_null) / std_null if std_null > 0 else 0,
            'degree_preserved': True
        }
        
        return empirical_p, statistics
    
    def _bin_genes_by_degree(
        self,
        gene_degrees: Dict[str, int],
        all_genes: List[str]
    ) -> Dict[int, List[str]]:
        """
        Bin genes by their degree (number of connections).
        
        Args:
            gene_degrees: Gene -> degree mapping
            all_genes: All genes to bin
            
        Returns:
            Dictionary mapping degree -> list of genes with that degree
        """
        bins = {}
        
        for gene in all_genes:
            degree = gene_degrees.get(gene, 0)
            if degree not in bins:
                bins[degree] = []
            bins[degree].append(gene)
        
        return bins
    
    def _sample_preserving_degree(
        self,
        original_genes: List[str],
        degree_bins: Dict[int, List[str]],
        gene_degrees: Dict[str, int]
    ) -> Set[str]:
        """
        Sample genes preserving degree distribution.
        
        Args:
            original_genes: Original gene list
            degree_bins: Genes binned by degree
            gene_degrees: Gene -> degree mapping
            
        Returns:
            Set of sampled genes with similar degree distribution
        """
        sampled = set()
        
        for gene in original_genes:
            degree = gene_degrees.get(gene, 0)
            
            # Sample from same degree bin
            if degree in degree_bins and len(degree_bins[degree]) > 0:
                # Exclude already sampled genes
                available = [g for g in degree_bins[degree] if g not in sampled]
                if available:
                    sampled.add(random.choice(available))
        
        return sampled
    
    def adjust_pvalues_with_permutation(
        self,
        pathways: List[Any],
        fn_genes: List[str],
        all_genes: List[str],
        n_permutations: Optional[int] = None
    ) -> List[Any]:
        """
        Adjust p-values for multiple pathways using permutation testing.
        
        Args:
            pathways: List of pathway objects with evidence_genes
            fn_genes: Functional neighborhood genes
            all_genes: Universe of genes
            n_permutations: Number of permutations
            
        Returns:
            Pathways with added empirical_pvalue attribute
        """
        if n_permutations is None:
            n_permutations = self.n_permutations
        
        logger.info(
            f"Calculating empirical p-values for {len(pathways)} pathways "
            f"using {n_permutations} permutations"
        )
        
        for i, pathway in enumerate(pathways):
            pathway_genes = getattr(pathway, 'evidence_genes', [])
            
            if not pathway_genes:
                continue
            
            # Calculate empirical p-value
            empirical_p, stats = self.calculate_empirical_pvalue(
                pathway_genes,
                fn_genes,
                all_genes,
                n_permutations
            )
            
            # Add to pathway object
            if hasattr(pathway, '__dict__'):
                pathway.empirical_pvalue = empirical_p
                pathway.permutation_z_score = stats['z_score']
                pathway.observed_overlap = stats['observed_overlap']
                pathway.expected_overlap = stats['mean_null_overlap']
            
            if (i + 1) % 100 == 0:
                logger.debug(f"Processed {i + 1}/{len(pathways)} pathways")
        
        logger.info(f"Completed empirical p-value calculation for {len(pathways)} pathways")
        
        return pathways
