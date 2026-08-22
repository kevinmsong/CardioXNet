"""Tests for the size-matched permutation null.

These replace an earlier pair of tests that exercised
``calculate_degree_preserving_pvalue_adaptive`` and asserted
``stats["degree_preserved"] is True``. Those methods drew replacements from
per-degree bins built over the supplied universe, which in this pipeline means
almost exclusively from the functional neighbourhood itself -- the permuted set
was the original set and the p-value was uninformative. The tests passed anyway,
because one of them supplied a 5-gene universe for a 3-gene neighbourhood: the
degenerate case the assertions were meant to catch. The methods have been
removed; these tests cover the remaining guarded path.
"""

import pytest

from app.services.gene_background import protein_coding_background
from app.services.permutation_tester import PermutationTester


def test_removed_methods_are_gone():
    """The degenerate variants must not come back by copy-paste."""
    for name in (
        "calculate_degree_preserving_pvalue",
        "calculate_degree_preserving_pvalue_adaptive",
        "calculate_empirical_pvalue_adaptive",
    ):
        assert not hasattr(PermutationTester, name), (
            f"{name} produced degenerate p-values and was removed deliberately"
        )


def test_empirical_pvalue_returns_valid_stats():
    tester = PermutationTester()
    fn_genes = [f"N{i}" for i in range(120)]
    universe = protein_coding_background() + fn_genes
    pathway_genes = fn_genes[:10] + ["QQ1", "QQ2"]

    pvalue, stats = tester.calculate_empirical_pvalue(
        pathway_genes, fn_genes, universe, n_permutations=200
    )

    assert 0 < pvalue <= 1
    assert stats["n_permutations"] == 200
    assert stats["observed_overlap"] == 10
    assert stats["testable"] is True
    # The control that is not applied must be reported as not applied.
    assert stats["degree_preserved"] is False


def test_small_universe_is_refused():
    tester = PermutationTester()
    fn_genes = ["SRC", "MAPK1", "AKT1"]
    universe = ["SRC", "AKT1", "MAPK1", "TP53", "STAT3"]

    pvalue, stats = tester.calculate_empirical_pvalue(
        ["SRC", "AKT1"], fn_genes, universe
    )

    assert pvalue is None
    assert stats["testable"] is False


def test_no_overlap_returns_one():
    tester = PermutationTester()
    fn_genes = [f"N{i}" for i in range(120)]
    universe = protein_coding_background() + fn_genes

    pvalue, stats = tester.calculate_empirical_pvalue(["ZZZ1"], fn_genes, universe)

    assert pvalue == 1.0
    assert stats["observed_overlap"] == 0


def test_adjust_pvalues_over_a_pathway_list():
    class Pathway:
        def __init__(self, genes):
            self.evidence_genes = genes

    tester = PermutationTester()
    fn_genes = [f"N{i}" for i in range(120)]
    universe = protein_coding_background() + fn_genes
    pathways = [Pathway(fn_genes[:12]), Pathway(["ZZZ1", "ZZZ2"])]

    result = tester.adjust_pvalues_with_permutation(
        pathways, fn_genes, universe, n_permutations=100
    )

    assert len(result) == 2
    assert getattr(result[0], "empirical_pvalue", None) is not None
