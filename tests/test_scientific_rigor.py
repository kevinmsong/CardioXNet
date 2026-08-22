"""Regression tests for the scientific-correctness defects found in the audit.

Each test pins one specific failure that shipped in a previous revision and
produced results that looked plausible but carried no information. They are
written against the observable behaviour, not the implementation, so a future
refactor is free to change how the property is achieved.
"""

import math

import pytest

from app.models.pathway import AggregatedPathway, PathwayEntry
from app.models import GeneInfo
from app.services.gene_background import protein_coding_background
from app.services.hypothesis_validator import HypothesisValidator
from app.services.literature_miner import LiteratureMiner
from app.services.nes_scorer import NESScorer
from app.services.permutation_tester import PermutationTester


def make_pathway(pathway_id="X:1", name="test pathway", db="KEGG", p_adj=1e-8,
                 evidence=10, term_size=50, support=3):
    entry = PathwayEntry(
        pathway_id=pathway_id, pathway_name=name, source_db=db,
        p_value=p_adj, p_adj=p_adj,
        evidence_count=evidence, evidence_genes=[f"G{i}" for i in range(evidence)],
        term_size=term_size, query_size=200, effective_domain_size=20000,
    )
    return AggregatedPathway(
        pathway=entry, support_count=support, source_primary_pathways=[],
        aggregation_score=1.0, combined_p_value=p_adj, aggregated_nes=0.0,
        consistency_score=1.0, confidence_score=1.0, support_fraction=1.0,
    )


# ---------------------------------------------------------------------------
# Permutation null
# ---------------------------------------------------------------------------

class TestPermutationNull:
    """The null must be built from a pool much larger than the sample.

    Previously the pipeline passed the functional neighbourhood as both the
    sample and the universe. Every permuted set was then the neighbourhood
    itself, so the null overlap equalled the observed overlap and the empirical
    p-value was uninformative for every pathway.
    """

    def test_degenerate_universe_is_refused_not_answered(self):
        tester = PermutationTester()
        fn = [f"N{i}" for i in range(300)]
        universe = fn + ["EXTRA1", "EXTRA2"]  # the old, degenerate pool

        p, stats = tester.calculate_empirical_pvalue(fn[:40], fn, universe)

        assert p is None, "a test that cannot be run must not return a p-value"
        assert stats["testable"] is False
        assert "universe_too_small" in stats["reason"]

    def test_genome_background_discriminates_overlap(self):
        tester = PermutationTester()
        fn = [f"N{i}" for i in range(300)]
        universe = protein_coding_background() + fn

        strong, strong_stats = tester.calculate_empirical_pvalue(fn[:30], fn, universe)
        none_p, none_stats = tester.calculate_empirical_pvalue(["ZZZ1", "ZZZ2"], fn, universe)

        # A real overlap must be separated from the null by a wide margin.
        assert strong_stats["mean_null_overlap"] < 5
        assert strong_stats["observed_overlap"] == 30
        assert strong < 0.01
        # No overlap is the one case that legitimately returns 1.0.
        assert none_p == 1.0
        assert none_stats["observed_overlap"] == 0

    def test_results_are_reproducible_across_instances(self):
        fn = [f"N{i}" for i in range(200)]
        universe = protein_coding_background() + fn
        pathway = fn[:20] + ["QQ1", "QQ2"]

        a, _ = PermutationTester(random_seed=7).calculate_empirical_pvalue(pathway, fn, universe)
        b, _ = PermutationTester(random_seed=7).calculate_empirical_pvalue(pathway, fn, universe)
        assert a == b

    def test_does_not_claim_degree_preservation_it_does_not_apply(self):
        tester = PermutationTester()
        fn = [f"N{i}" for i in range(200)]
        universe = protein_coding_background() + fn
        _, stats = tester.calculate_empirical_pvalue(fn[:20], fn, universe)
        assert stats["degree_preserved"] is False
        assert stats["null_model"] == "size_matched_uniform"

    def test_resolution_floor_is_reported(self):
        tester = PermutationTester()
        fn = [f"N{i}" for i in range(200)]
        universe = protein_coding_background() + fn
        _, stats = tester.calculate_empirical_pvalue(fn[:20], fn, universe)
        # p can never be smaller than 1/(n+1); the report must say so.
        assert stats["p_resolution_floor"] == pytest.approx(1 / (stats["n_permutations"] + 1))


class TestBenjaminiHochberg:
    """Empirical p-values are a family and require FDR control."""

    def test_matches_reference_implementation(self):
        pvals = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.99]
        got = PermutationTester.benjamini_hochberg(pvals)
        statsmodels = pytest.importorskip("statsmodels.stats.multitest")
        expected = list(statsmodels.multipletests(pvals, method="fdr_bh")[1])
        assert got == pytest.approx(expected)

    def test_untestable_entries_excluded_from_family(self):
        # None entries must neither receive a q-value nor inflate m.
        with_none = PermutationTester.benjamini_hochberg([0.01, None, 0.02, None])
        without = PermutationTester.benjamini_hochberg([0.01, 0.02])
        assert with_none[1] is None and with_none[3] is None
        assert [with_none[0], with_none[2]] == pytest.approx(without)

    def test_monotonic_and_bounded(self):
        pvals = [0.5, 0.001, 0.9, 0.02]
        qs = PermutationTester.benjamini_hochberg(pvals)
        assert all(0.0 <= q <= 1.0 for q in qs)
        ordered = [q for _, q in sorted(zip(pvals, qs))]
        assert ordered == sorted(ordered), "q must not decrease as p increases"


# ---------------------------------------------------------------------------
# Pathway scoring
# ---------------------------------------------------------------------------

class TestPathwayScoring:
    """Generic gene sets must not win on size alone.

    The previous score multiplied significance by raw gene count while capping
    -log10(p) at 50, a cap nearly every candidate reached, so ranking collapsed
    into "sort by term size" and maximally generic GO terms took the top slots.
    """

    def test_specific_term_outranks_generic_term(self):
        scorer = NESScorer()
        generic = make_pathway("GO:1", "cell surface receptor signaling pathway",
                               "GO:BP", p_adj=0.0, evidence=187, term_size=4200, support=20)
        specific = make_pathway("KEGG:1", "Cardiac muscle contraction",
                                "KEGG", p_adj=1e-9, evidence=14, term_size=87, support=3)

        generic_score, _ = scorer._calculate_nes(generic)
        specific_score, _ = scorer._calculate_nes(specific)
        assert specific_score > generic_score

    def test_specificity_falls_with_term_size(self):
        small = make_pathway(term_size=20).pathway
        large = make_pathway(term_size=2000).pathway
        assert small.gene_set_specificity > large.gene_set_specificity
        assert large.gene_set_specificity == 0.0

    def test_fold_enrichment_matches_definition(self):
        entry = make_pathway(evidence=10, term_size=100).pathway
        expected = (100 * 200) / 20000
        assert entry.fold_enrichment == pytest.approx(10 / expected)

    def test_fold_enrichment_absent_without_sizes(self):
        entry = PathwayEntry(pathway_id="a", pathway_name="b", source_db="KEGG",
                             p_value=0.01, p_adj=0.01, evidence_count=5,
                             evidence_genes=["A"] * 5)
        assert entry.fold_enrichment is None

    def test_score_components_are_reported(self):
        scorer = NESScorer()
        _, components = scorer._calculate_nes(make_pathway())
        for key in ("significance", "effect_size", "specificity", "replication",
                    "fold_enrichment", "term_size"):
            assert key in components


# ---------------------------------------------------------------------------
# Literature novelty
# ---------------------------------------------------------------------------

class TestLiteratureQuery:
    """The pathway concept must actually constrain the query.

    Previously the pathway terms were OR-ed into the same clause as a broad
    cardiac fallback, so every pathway resolved to the same
    "(genes) AND (cardiac OR heart OR ...)" query and returned the same papers.
    """

    @staticmethod
    def seeds():
        return [GeneInfo(input_id=s, entrez_id="0", symbol=s)
                for s in ("VEGFA", "IL6", "TNF")]

    def test_pathway_clause_is_a_separate_and_term(self):
        miner = LiteratureMiner()
        query = miner._construct_hypothesis_query(
            "sprouting angiogenesis", self.seeds(), disease_context="heart_failure")
        assert query.count(" AND ") >= 2, "genes, pathway and disease must be AND-ed"
        assert "angiogenesis" in query

    def test_distinct_pathways_give_distinct_queries(self):
        miner = LiteratureMiner()
        a = miner._construct_hypothesis_query("sprouting angiogenesis", self.seeds(),
                                              disease_context="heart_failure")
        b = miner._construct_hypothesis_query("sphingolipid metabolism", self.seeds(),
                                              disease_context="heart_failure")
        assert a != b

    def test_generic_unigrams_never_form_the_clause(self):
        # "heart", "muscle" and "rate" would re-admit the whole corpus.
        clause = LiteratureMiner._pathway_clause("regulation of heart rate")
        for generic in ('heart[Title/Abstract]', 'rate[Title/Abstract]',
                        'muscle[Title/Abstract]'):
            assert generic not in clause

    def test_fully_generic_name_yields_no_clause(self):
        # Such a pathway is correctly treated as saturated, not novel.
        assert LiteratureMiner._pathway_clause("multicellular organism development") == ""


class TestNoveltyScoring:
    """Saturation must come from the true corpus size, not the retrieval cap."""

    @staticmethod
    def score(hit_count, citations=None):
        validator = HypothesisValidator()
        hypothesis = _StubHypothesis(make_pathway())
        return validator.calculate_validation_score(
            hypothesis, citations or [], {},
            [GeneInfo(input_id="VEGFA", entrez_id="0", symbol="VEGFA")],
            pubmed_hit_count=hit_count,
        )

    def test_saturation_tracks_corpus_size(self):
        sparse = self.score(5)
        dense = self.score(9000)
        assert sparse["literature_saturation"] < dense["literature_saturation"]
        assert sparse["discovery_score"] > dense["discovery_score"]

    def test_zero_hits_is_maximally_novel(self):
        assert self.score(0)["literature_saturation"] == 0.0

    def test_ceiling_saturates(self):
        assert self.score(10_000)["literature_saturation"] == 1.0

    def test_unmeasured_corpus_is_flagged_and_not_maximally_novel(self):
        # A pathway whose corpus was never measured (lookup failed, or it fell
        # outside the literature-mining window) must not inherit the novelty of
        # a genuinely unstudied pathway.
        result = self.score(-1)
        assert result["saturation_basis"] == "not_measured"
        assert result["novelty_confidence"] == "unverified"
        assert result["literature_saturation"] > 0.0
        # A verified gap (0 records, searchable concept) must still beat it.
        verified = self.score(0, citations=None)
        assert verified["literature_saturation"] < result["literature_saturation"]

    def test_discovery_fields_are_all_present(self):
        result = self.score(50)
        for key in ("discovery_score", "novelty_tier", "literature_saturation",
                    "pubmed_hit_count"):
            assert key in result, f"{key} must be produced for the report to show it"

    def test_accepts_citation_objects_not_only_dicts(self):
        # The pipeline passes Citation models; .get() on them used to raise.
        class Citation:
            relevance_score = 0.9

        result = self.score(20, citations=[Citation(), Citation()])
        assert result["literature_evidence"] > 0

    def test_tier_boundaries(self):
        validator = HypothesisValidator()
        ceiling = validator.SATURATION_CEILING
        # A corpus of 1 record is close to unstudied.
        novelty = 1.0 - math.log10(2) / math.log10(ceiling + 1)
        assert novelty >= 0.80


class _StubHypothesis:
    """Minimal stand-in for ScoredPathway with the fields the validator reads."""

    def __init__(self, aggregated_pathway, nes_score=1.5):
        self.aggregated_pathway = aggregated_pathway
        self.nes_score = nes_score
        self.score_components = {}


class TestBackgroundGeneSet:
    def test_background_is_genome_scale(self):
        genes = protein_coding_background()
        assert len(genes) > 15_000
        assert "VEGFA" in genes and "MYH7" in genes

    def test_background_is_deduplicated_and_sorted(self):
        genes = protein_coding_background()
        assert genes == sorted(set(genes))


class TestSemanticRelevance:
    """Cardiac relevance must actually discriminate.

    A normalisation shift gave every pathway with no cardiac evidence an
    identical score of 0.304, so the metric carried no information and every
    configured threshold (the presets used 0.01) filtered nothing.
    """

    @staticmethod
    def score(name):
        from app.services.semantic_filter import SemanticFilter
        return SemanticFilter().calculate_cardiac_relevance(
            name, disease_context="heart_failure")["overall"]

    def test_no_cardiac_evidence_scores_zero(self):
        for name in ("Malaria", "Leishmaniasis", "Olfactory transduction"):
            assert self.score(name) == 0.0, f"{name} must not score above zero"

    def test_cardiac_pathways_outrank_non_cardiac(self):
        assert self.score("Dilated cardiomyopathy") > self.score("Melanoma")
        assert self.score("heart valve morphogenesis") > self.score("Cocaine addiction")

    def test_generic_tissue_penalty_does_not_veto_cardiac_pathways(self):
        # "muscle" is a negative term; it must not cancel an explicitly
        # cardiac-qualified pathway.
        assert self.score("Cardiac muscle contraction") > 0.0

    def test_penalty_still_applies_without_a_cardiac_qualifier(self):
        assert self.score("Skeletal muscle contraction") == 0.0


class TestNoveltyConfidence:
    """A zero-record intersection is only a gap if the concept is searchable."""

    @staticmethod
    def score(hits, concept):
        validator = HypothesisValidator()
        return validator.calculate_validation_score(
            _StubHypothesis(make_pathway()), [], {},
            [GeneInfo(input_id="VEGFA", entrez_id="0", symbol="VEGFA")],
            pubmed_hit_count=hits, concept_hit_count=concept,
        )

    def test_unsearchable_concept_is_not_maximally_novel(self):
        # "GAB1 signalosome" style: no lexical footprint at all.
        unverified = self.score(0, concept=0)
        assert unverified["novelty_confidence"] == "unverified"
        assert unverified["literature_saturation"] > 0.0

    def test_genuine_gap_keeps_full_novelty(self):
        gap = self.score(0, concept=5000)
        assert gap["novelty_confidence"] == "verified_gap"
        assert gap["literature_saturation"] == 0.0

    def test_verified_gap_outranks_unverified(self):
        assert (self.score(0, concept=5000)["discovery_score"]
                > self.score(0, concept=0)["discovery_score"])


class TestSeedLiteratureGrounding:
    """Novelty is meaningless when the seeds have no literature to be novel against.

    Negative controls exposed this: olfactory-receptor and random gene panels
    produced more Highly Novel calls (13/13 and 21/23) than any real
    cardiovascular panel, because nobody has written about those genes in heart
    failure, so every pathway intersection returned zero records.
    """

    @staticmethod
    def score(seed_corpus, hits=0):
        validator = HypothesisValidator()
        return validator.calculate_validation_score(
            _StubHypothesis(make_pathway()), [], {},
            [GeneInfo(input_id="OR51E2", entrez_id="0", symbol="OR51E2")],
            pubmed_hit_count=hits, concept_hit_count=5000,
            seed_disease_corpus=seed_corpus,
        )

    def test_ungrounded_seeds_suppress_novelty(self):
        result = self.score(seed_corpus=0)
        assert result["novelty_confidence"] == "ungrounded_seeds"
        assert result["literature_saturation"] > 0.0

    def test_grounded_seeds_allow_a_verified_gap(self):
        result = self.score(seed_corpus=10_000)
        assert result["novelty_confidence"] == "verified_gap"
        assert result["literature_saturation"] == 0.0

    def test_grounded_gap_outranks_ungrounded(self):
        assert (self.score(seed_corpus=10_000)["discovery_score"]
                > self.score(seed_corpus=0)["discovery_score"])

    def test_missing_corpus_does_not_suppress(self):
        # A failed lookup must not silently veto every novelty call.
        assert self.score(seed_corpus=None)["novelty_confidence"] == "verified_gap"

    def test_ungrounded_seeds_get_an_undefined_tier(self):
        # Not a weak result -- an undefined one. Reporting it on the same scale
        # as a grounded call is what let negative controls look like discoveries.
        assert self.score(seed_corpus=0)["novelty_tier"] == "Ungrounded"
        assert self.score(seed_corpus=10_000)["novelty_tier"] != "Ungrounded"
