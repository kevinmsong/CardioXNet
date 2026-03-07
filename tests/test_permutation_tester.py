from app.services.permutation_tester import PermutationTester


def test_degree_preserving_adaptive_permutation_returns_valid_stats():
    tester = PermutationTester()
    pathway_genes = ["A", "B", "C", "D"]
    fn_genes = ["A", "B", "X", "Y"]
    all_genes = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "X", "Y"]
    gene_degrees = {
        "A": 5,
        "B": 4,
        "C": 3,
        "D": 2,
        "E": 1,
        "F": 2,
        "G": 3,
        "H": 4,
        "I": 5,
        "J": 1,
        "X": 5,
        "Y": 4,
    }

    pvalue, stats = tester.calculate_degree_preserving_pvalue_adaptive(
        pathway_genes=pathway_genes,
        fn_genes=fn_genes,
        gene_degrees=gene_degrees,
        all_genes=all_genes,
        min_permutations=5,
        max_permutations=12,
    )

    assert 0 <= pvalue <= 1
    assert stats["n_permutations"] >= 5
    assert stats["n_permutations"] <= 12
    assert stats["degree_preserved"] is True


def test_degree_preserving_adaptive_permutation_caches_results():
    tester = PermutationTester()
    pathway_genes = ["SRC", "AKT1"]
    fn_genes = ["SRC", "MAPK1", "AKT1"]
    all_genes = ["SRC", "AKT1", "MAPK1", "TP53", "STAT3"]
    gene_degrees = {gene: index + 1 for index, gene in enumerate(all_genes)}

    first = tester.calculate_degree_preserving_pvalue_adaptive(
        pathway_genes=pathway_genes,
        fn_genes=fn_genes,
        gene_degrees=gene_degrees,
        all_genes=all_genes,
        min_permutations=5,
        max_permutations=10,
    )
    second = tester.calculate_degree_preserving_pvalue_adaptive(
        pathway_genes=pathway_genes,
        fn_genes=fn_genes,
        gene_degrees=gene_degrees,
        all_genes=all_genes,
        min_permutations=5,
        max_permutations=10,
    )

    assert first == second
