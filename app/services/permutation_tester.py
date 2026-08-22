"""Permutation-based empirical p-value calculation for pathway enrichment."""

import logging
import random
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PermutationTester:
    """
    Empirical p-values for the overlap between a pathway and the functional
    neighbourhood, against a size-matched null.

    METHOD
    1. Observe the overlap between the pathway genes and the neighbourhood.
    2. Draw ``n_permutations`` random gene sets of the same size as the
       neighbourhood, uniformly from a background pool supplied by the caller.
    3. Empirical p = (# null overlaps >= observed + 1) / (n_permutations + 1).

    WHAT THIS CONTROLS FOR, AND WHAT IT DOES NOT
    The null answers "is this overlap larger than for a random neighbourhood-sized
    set drawn from the same gene space?". It does **not** control for the
    degree bias of the neighbourhood itself: the neighbourhood is a STRING
    expansion and so is enriched for high-degree genes. Degree matching would
    require genome-wide degrees, which are not available in-process, and the
    earlier attempt to approximate it drew replacements from the neighbourhood
    and destroyed the null (see the note above ``benjamini_hochberg``). The
    statistics dict reports ``degree_preserved: False`` so no downstream consumer
    can claim a control that was not applied.

    Because the pool is genome-scale, genuinely enriched pathways clear this null
    by a wide margin and commonly reach the resolution floor of 1/(n+1). The test
    establishes that an overlap is not chance; it does not rank among strong
    hypotheses.
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
    
    # NOTE: the degree-preserving and adaptive permutation variants that used to
    # live here have been removed rather than left unused.
    #
    # They sampled replacements from per-degree bins built over the supplied
    # universe. In this pipeline STRING degrees are known only for genes inside
    # the functional neighbourhood, so those bins drew almost exclusively from
    # the neighbourhood itself: the permuted set was the original set, the null
    # overlap equalled the observed overlap, and the p-value was uninformative
    # for every pathway. They nonetheless reported `degree_preserved: True`.
    #
    # Keeping a method that produces a confident-looking but degenerate p-value
    # is a live hazard, so the single guarded, size-matched null below is now the
    # only way to compute one.

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
