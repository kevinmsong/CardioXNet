"""Permutation-based empirical p-value calculation for pathway enrichment."""

import logging
import random
from typing import List, Dict, Set, Tuple, Any, Optional
import numpy as np
from collections import Counter
import threading

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
    
    # The null is only meaningful if the background pool is substantially larger
    # than the sample drawn from it. When the universe equals the functional
    # neighbourhood, every "permuted" neighbourhood is the neighbourhood itself,
    # the null overlap equals the observed overlap, and the p-value is ~1 for
    # every pathway regardless of the biology. Enforced rather than assumed,
    # because that is exactly the defect this guard was written to catch.
    MIN_UNIVERSE_RATIO = 3.0

    def __init__(self, random_seed: int = 20260821):
        """Initialize permutation tester.

        Args:
            random_seed: Seed for the dedicated RNG. A private ``random.Random``
                instance is used rather than the module-level functions so that
                empirical p-values are reproducible and are not perturbed by
                unrelated callers consuming from the global random stream.
        """
        self.settings = get_settings()
        self.n_permutations = self.settings.nets.n_permutations if hasattr(
            self.settings.nets, 'n_permutations'
        ) else 1000
        self._rng = random.Random(random_seed)
        self.random_seed = random_seed
        self._cache: Dict[Tuple[Any, ...], Tuple[float, Dict]] = {}
        self._cache_lock = threading.Lock()

        logger.info(
            f"PermutationTester initialized with {self.n_permutations} permutations "
            f"(seed={random_seed}, resolution floor p={1/(self.n_permutations+1):.2g})"
        )

    def _validate_universe(
        self, fn_genes: List[str], all_genes: List[str]
    ) -> Optional[str]:
        """Return a reason string if the background pool cannot support a test."""
        n_universe = len(set(all_genes))
        n_sample = len(set(fn_genes))
        if n_sample == 0:
            return "empty_sample"
        if n_universe < n_sample * self.MIN_UNIVERSE_RATIO:
            return (
                f"universe_too_small: {n_universe} background genes for a "
                f"{n_sample}-gene sample (need >= {int(n_sample * self.MIN_UNIVERSE_RATIO)})"
            )
        return None

    @staticmethod
    def undefined_result(reason: str, observed_overlap: int = 0) -> Tuple[Optional[float], Dict]:
        """A test that could not be run. p is None -- never 1.0.

        Returning 1.0 for an untestable pathway would be indistinguishable from
        a genuine null result and would silently propagate into the report.
        """
        return None, {
            'observed_overlap': observed_overlap,
            'mean_null_overlap': None,
            'std_null_overlap': None,
            'null_overlaps': [],
            'n_permutations': 0,
            'z_score': None,
            'testable': False,
            'reason': reason,
        }
    
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

        reason = self._validate_universe(fn_genes, all_genes)
        if reason:
            logger.warning(f"Permutation test not run: {reason}")
            return self.undefined_result(reason, len(pathway_set & fn_set))

        # Observed overlap
        observed_overlap = len(pathway_set & fn_set)

        # If no overlap, return p=1.0
        if observed_overlap == 0:
            return 1.0, {
                'observed_overlap': 0,
                'mean_null_overlap': 0.0,
                'std_null_overlap': 0.0,
                'null_overlaps': [],
                'n_permutations': n_permutations,
                'z_score': 0.0,
                'testable': True,
                'reason': 'no_overlap',
                'degree_preserved': False,
            }
        
        # Generate null distribution
        null_overlaps = []
        
        for i in range(n_permutations):
            # Randomly sample same number of genes from universe
            permuted_fn = set(self._rng.sample(list(all_genes_set), min(len(fn_genes), len(all_genes_set))))
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
            'z_score': (observed_overlap - mean_null) / std_null if std_null > 0 else 0,
            'testable': True,
            # Uniform size-matched sampling. Degree matching is not applied --
            # see the note at the pipeline call site.
            'degree_preserved': False,
            'null_model': 'size_matched_uniform',
            'p_resolution_floor': 1.0 / (n_permutations + 1),
            'universe_size': len(all_genes_set),
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
            permuted_fn = set(self._rng.sample(list(all_genes_set), min(len(fn_genes), len(all_genes_set))))
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
                permuted_fn = set(self._rng.sample(list(all_genes_set), min(len(fn_genes), len(all_genes_set))))
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

        # Refuse to produce a number when the background pool cannot support a
        # null. See MIN_UNIVERSE_RATIO.
        reason = self._validate_universe(fn_genes, all_genes)
        if reason:
            logger.warning(f"Permutation test not run: {reason}")
            return self.undefined_result(reason, len(pathway_set & fn_set))

        # Observed overlap
        observed_overlap = len(pathway_set & fn_set)

        if observed_overlap == 0:
            return 1.0, {
                'observed_overlap': 0,
                'mean_null_overlap': 0.0,
                'std_null_overlap': 0.0,
                'null_overlaps': [],
                'n_permutations': n_permutations,
                'z_score': 0.0,
                'testable': True,
                'reason': 'no_overlap',
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
            'degree_preserved': True,
            'testable': True,
            'p_resolution_floor': 1.0 / (n_permutations + 1),
            'universe_size': len(set(all_genes)),
        }

        return empirical_p, statistics

    def calculate_degree_preserving_pvalue_adaptive(
        self,
        pathway_genes: List[str],
        fn_genes: List[str],
        gene_degrees: Dict[str, int],
        all_genes: List[str],
        min_permutations: int = 10,
        max_permutations: Optional[int] = None
    ) -> Tuple[float, Dict]:
        """
        Calculate degree-preserving empirical p-value with early stopping.

        The degree-preserving null is retained, but borderline pathways receive the
        full permutation budget while clearly significant or clearly null pathways stop early.
        """
        if max_permutations is None:
            max_permutations = self.n_permutations

        pathway_key = tuple(sorted(set(pathway_genes)))
        fn_key = tuple(sorted(set(fn_genes)))
        degree_key = tuple(sorted((gene, gene_degrees.get(gene, 0)) for gene in all_genes))
        cache_key = (
            pathway_key,
            fn_key,
            degree_key,
            min_permutations,
            max_permutations,
            "adaptive_degree",
        )
        with self._cache_lock:
            cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        pathway_set = set(pathway_genes)
        fn_set = set(fn_genes)

        observed_overlap = len(pathway_set & fn_set)
        if observed_overlap == 0:
            result = (
                1.0,
                {
                    'observed_overlap': 0,
                    'mean_null_overlap': 0,
                    'std_null_overlap': 0,
                    'null_overlaps': [],
                    'n_permutations': min_permutations,
                    'early_stop': True,
                    'stop_reason': 'no_overlap',
                    'degree_preserved': True,
                },
            )
            with self._cache_lock:
                self._cache[cache_key] = result
            return result

        degree_bins = self._bin_genes_by_degree(gene_degrees, all_genes)
        min_permutations = max(5, min(min_permutations, max_permutations))
        null_overlaps = []

        for _ in range(min_permutations):
            permuted_fn = self._sample_preserving_degree(fn_genes, degree_bins, gene_degrees)
            null_overlaps.append(len(pathway_set & permuted_fn))

        n_greater_equal = sum(1 for null in null_overlaps if null >= observed_overlap)
        prelim_p = (n_greater_equal + 1) / (min_permutations + 1)
        early_stop = False
        stop_reason = None

        if prelim_p <= 0.01:
            early_stop = True
            stop_reason = 'highly_significant'
        elif prelim_p >= 0.2:
            early_stop = True
            stop_reason = 'not_significant'
        else:
            for _ in range(max_permutations - min_permutations):
                permuted_fn = self._sample_preserving_degree(fn_genes, degree_bins, gene_degrees)
                null_overlaps.append(len(pathway_set & permuted_fn))

        n_permutations = len(null_overlaps)
        n_greater_equal = sum(1 for null in null_overlaps if null >= observed_overlap)
        empirical_p = (n_greater_equal + 1) / (n_permutations + 1)
        mean_null = np.mean(null_overlaps)
        std_null = np.std(null_overlaps)

        result = (
            empirical_p,
            {
                'observed_overlap': observed_overlap,
                'mean_null_overlap': mean_null,
                'std_null_overlap': std_null,
                'null_overlaps': null_overlaps,
                'n_permutations': n_permutations,
                'z_score': (observed_overlap - mean_null) / std_null if std_null > 0 else 0,
                'early_stop': early_stop,
                'stop_reason': stop_reason,
                'min_permutations': min_permutations,
                'max_permutations': max_permutations,
                'degree_preserved': True,
            },
        )
        with self._cache_lock:
            self._cache[cache_key] = result
        return result
    
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
                    sampled.add(self._rng.choice(available))
        
        return sampled
    
    @staticmethod
    def benjamini_hochberg(pvalues: List[Optional[float]]) -> List[Optional[float]]:
        """Benjamini-Hochberg FDR correction, preserving input order.

        ``None`` entries (tests that could not be run) are carried through as
        ``None`` and are excluded from the ranking and from ``m``, so untestable
        pathways neither receive a q-value nor dilute the correction applied to
        the pathways that were actually tested.

        The step-up procedure enforces monotonicity: q_(i) = min over j >= i of
        (m/j) * p_(j), clipped to 1.
        """
        indexed = [(i, p) for i, p in enumerate(pvalues) if p is not None]
        out: List[Optional[float]] = [None] * len(pvalues)
        m = len(indexed)
        if m == 0:
            return out

        indexed.sort(key=lambda t: t[1])
        running_min = 1.0
        # Walk from the largest p-value down so the min-suffix is available.
        for rank in range(m, 0, -1):
            orig_idx, p = indexed[rank - 1]
            q = (m / rank) * p
            running_min = min(running_min, q)
            out[orig_idx] = min(1.0, running_min)
        return out

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
