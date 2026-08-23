"""Regression tests for the scientific-correctness defects found in the audit.

Each test pins one specific failure that shipped in a previous revision and
produced results that looked plausible but carried no information. They are
written against the observable behaviour, not the implementation, so a future
refactor is free to change how the property is achieved.
"""

import asyncio
import math
from types import SimpleNamespace

import pytest

from app.models.pathway import AggregatedPathway, PathwayEntry
from app.models import GeneInfo
from app.services.gene_background import protein_coding_background
from app.services.hypothesis_validator import HypothesisValidator
from app.services.literature_miner import LiteratureMiner
from app.services.nes_scorer import NESScorer
from app.services.pathway_aggregator_rigorous import RigorousPathwayAggregator
from app.services.permutation_tester import PermutationTester
from app.services.secondary_pathway_analyzer import SecondaryPathwayAnalyzer


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

    def test_sampling_universe_is_sorted_before_seeded_draws(self):
        # Pin the cross-process requirement directly. Sampling from list(set)
        # can pass same-process tests while changing under another hash seed.
        import inspect

        source = inspect.getsource(PermutationTester.calculate_empirical_pvalue)
        assert "sampling_universe = sorted(all_genes_set)" in source

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


class TestFisherCombination:
    """Extreme but representable combined probabilities must not become zero."""

    def test_rigorous_aggregator_uses_stable_upper_tail(self):
        aggregator = RigorousPathwayAggregator.__new__(RigorousPathwayAggregator)
        combined = aggregator._fishers_combined_probability([1e-20, 1e-20])
        assert 0.0 < combined < 1e-30

    def test_secondary_analyzer_uses_stable_upper_tail(self):
        analyzer = SecondaryPathwayAnalyzer.__new__(SecondaryPathwayAnalyzer)
        combined = analyzer._calculate_fisher_combined_pvalue([1e-20, 1e-20])
        assert 0.0 < combined < 1e-30


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

    def test_display_retrieval_uses_configured_cap(self, monkeypatch):
        miner = LiteratureMiner()
        monkeypatch.setattr(miner.settings.nets, "pubmed_max_results", 7)
        observed = {}

        def fake_search(query, max_results):
            observed["query"] = query
            observed["max_results"] = max_results
            return ["123"]

        monkeypatch.setattr(miner.pubmed_client, "_search_pubmed", fake_search)
        monkeypatch.setattr(
            miner.pubmed_client,
            "_fetch_papers",
            lambda pmids: [{"pmid": pmids[0]}],
        )

        assert miner._search_pubmed("cardiac query") == [{"pmid": "123"}]
        assert observed == {"query": "cardiac query", "max_results": 7}

    def test_generic_unigrams_never_form_the_clause(self):
        # "heart", "muscle" and "rate" would re-admit the whole corpus.
        clause = LiteratureMiner._pathway_clause("regulation of heart rate")
        for generic in ('heart[Title/Abstract]', 'rate[Title/Abstract]',
                        'muscle[Title/Abstract]'):
            assert generic not in clause

    def test_fully_generic_name_keeps_an_exact_phrase_clause(self):
        # A generic label must not silently degrade to a gene x disease query.
        clause = LiteratureMiner._pathway_clause("multicellular organism development")
        assert clause == '"multicellular organism development"[Title/Abstract]'

        query = LiteratureMiner()._construct_hypothesis_query(
            "multicellular organism development",
            self.seeds(),
            disease_context="heart_failure",
        )
        assert query.count(" AND ") >= 2
        assert clause in query

    def test_reused_miner_does_not_leak_previous_run_provenance(self, monkeypatch):
        miner = LiteratureMiner()
        hypothesis = SimpleNamespace(
            aggregated_pathway=SimpleNamespace(
                pathway=SimpleNamespace(pathway_id="R:1", pathway_name="test pathway")
            ),
            traced_seed_genes=["VEGFA"],
        )
        seeds = [GeneInfo(input_id="VEGFA", entrez_id="0", symbol="VEGFA")]
        invocation = 0

        def fake_mine(_name, _genes, pathway_id, _context, _synonyms):
            nonlocal invocation
            invocation += 1
            if invocation == 1:
                miner._last_hit_counts[pathway_id] = 0
                miner._last_query_tier[pathway_id] = "strict"
                miner._last_queries[pathway_id] = "first-run-query"
                miner._last_concept_counts[pathway_id] = 500
            # The second call intentionally records nothing, simulating a
            # failure before fresh provenance is available.
            return []

        monkeypatch.setattr(miner, "_mine_hypothesis_literature", fake_mine)
        first = asyncio.run(miner.validate_hypotheses_async([hypothesis], seeds))
        second = asyncio.run(miner.validate_hypotheses_async([hypothesis], seeds))

        assert first.hypothesis_hit_counts["R:1"] == 0
        assert first.concept_hit_counts["R:1"] == 500
        assert second.hypothesis_hit_counts["R:1"] == -1
        assert second.query_tier["R:1"] == "unknown"
        assert second.hypothesis_queries["R:1"] == ""
        assert "R:1" not in second.concept_hit_counts

    def test_mining_uses_aggregated_contributors_before_tracing(self, monkeypatch):
        miner = LiteratureMiner()
        captured = {}
        hypothesis = SimpleNamespace(
            aggregated_pathway=SimpleNamespace(
                pathway=SimpleNamespace(
                    pathway_id="R:contributors",
                    pathway_name="test pathway",
                ),
                contributing_seed_genes=["TNF"],
            ),
            traced_seed_genes=[],
        )
        seeds = [
            GeneInfo(input_id=s, entrez_id="0", symbol=s)
            for s in ("VEGFA", "TNF", "IL6")
        ]

        def fake_mine(_name, genes, pathway_id, _context, _synonyms):
            captured["genes"] = [gene.symbol for gene in genes]
            miner._last_query_genes[pathway_id] = captured["genes"]
            miner._last_queries[pathway_id] = "strict query"
            miner._last_query_tier[pathway_id] = "strict"
            miner._last_hit_counts[pathway_id] = 1
            miner._last_concept_queries[pathway_id] = "(test pathway)"
            return []

        monkeypatch.setattr(miner, "_mine_hypothesis_literature", fake_mine)
        evidence = asyncio.run(miner.validate_hypotheses_async([hypothesis], seeds))

        assert captured["genes"] == ["TNF"]
        assert evidence.hypothesis_query_genes["R:contributors"] == ["TNF"]
        assert evidence.concept_queries["R:contributors"] == "(test pathway)"


class TestNoveltyScoring:
    """Saturation must come from the true corpus size, not the retrieval cap."""

    @staticmethod
    def score(hit_count, citations=None, concept=5000, seed_corpus=10_000,
              query_tier="strict"):
        validator = HypothesisValidator()
        hypothesis = _StubHypothesis(make_pathway())
        return validator.calculate_validation_score(
            hypothesis, citations or [], {},
            [GeneInfo(input_id="VEGFA", entrez_id="0", symbol="VEGFA")],
            pubmed_hit_count=hit_count,
            concept_hit_count=concept,
            seed_disease_corpus=seed_corpus,
            query_tier=query_tier,
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
        assert result["novelty_confidence"] == "unverified_measurement"
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

    def test_semantic_adjustment_preserves_base_pps_for_audit(self):
        import copy

        from app.core.config import get_settings
        from app.services.semantic_filter import SemanticFilter

        semantic_filter = SemanticFilter()
        semantic_filter.settings = copy.deepcopy(get_settings())
        hypothesis = _StubHypothesis(
            make_pathway(name="Cardiac muscle contraction"), nes_score=2.0
        )

        retained = semantic_filter.apply_semantic_boost_parallel(
            [hypothesis], min_threshold=0.0, max_workers=1
        )

        assert len(retained) == 1
        components = retained[0].score_components
        assert components["base_pps"] == 2.0
        assert retained[0].nes_score == pytest.approx(
            components["base_pps"] * components["semantic_boost"]
        )

    def test_configured_semantic_result_cap_is_enforced(self):
        import copy

        from app.core.config import get_settings
        from app.services.semantic_filter import SemanticFilter

        semantic_filter = SemanticFilter()
        semantic_filter.settings = copy.deepcopy(get_settings())
        semantic_filter.settings.nets.semantic_max_results = 15
        hypotheses = [
            _StubHypothesis(
                make_pathway(
                    pathway_id=f"X:{index}",
                    name=f"Cardiac signaling pathway {index}",
                ),
                nes_score=2.0 - index / 100.0,
            )
            for index in range(25)
        ]

        retained = semantic_filter.apply_semantic_boost_parallel(
            hypotheses, min_threshold=0.0, max_workers=1
        )

        assert len(retained) == 15


class TestNoveltyConfidence:
    """A zero-record intersection is only a gap if the concept is searchable."""

    @staticmethod
    def score(hits, concept, seed_corpus=10_000, query_tier="strict"):
        validator = HypothesisValidator()
        return validator.calculate_validation_score(
            _StubHypothesis(make_pathway()), [], {},
            [GeneInfo(input_id="VEGFA", entrez_id="0", symbol="VEGFA")],
            pubmed_hit_count=hits, concept_hit_count=concept,
            seed_disease_corpus=seed_corpus, query_tier=query_tier,
        )

    def test_unsearchable_concept_is_not_maximally_novel(self):
        # "GAB1 signalosome" style: no lexical footprint at all.
        unverified = self.score(0, concept=0)
        assert unverified["novelty_confidence"] == "unverified_concept"
        assert unverified["literature_saturation"] > 0.0
        assert unverified["pubmed_hit_count"] == 0
        assert unverified["saturation_corpus_size"] == 60
        assert unverified["novelty_tier"] == "Unverified"

    def test_genuine_gap_keeps_full_novelty(self):
        gap = self.score(0, concept=5000)
        assert gap["novelty_confidence"] == "verified_gap"
        assert gap["literature_saturation"] == 0.0

    def test_verified_gap_outranks_unverified(self):
        assert (self.score(0, concept=5000)["discovery_score"]
                > self.score(0, concept=0)["discovery_score"])

    @pytest.mark.parametrize("concept", [None, -1])
    def test_missing_or_failed_concept_prerequisite_is_unverified(self, concept):
        result = self.score(0, concept=concept)
        assert result["pubmed_hit_count"] == 0
        assert result["novelty_confidence"] == "unverified_concept"
        assert result["saturation_corpus_size"] == 60
        assert result["novelty_confidence"] != "verified_gap"

    @pytest.mark.parametrize("query_tier", [None, "unknown", "broad", "relaxed"])
    def test_only_an_explicit_strict_query_is_interpretable(self, query_tier):
        result = self.score(0, concept=5000, query_tier=query_tier)
        assert result["pubmed_hit_count"] == 0
        assert result["novelty_confidence"] == "unverified_query_scope"
        assert result["saturation_corpus_size"] == 60
        assert result["novelty_confidence"] != "verified_gap"

    def test_broad_query_is_not_scored_as_pathway_specific(self):
        validator = HypothesisValidator()
        result = validator.calculate_validation_score(
            _StubHypothesis(make_pathway()), [], {},
            [GeneInfo(input_id="VEGFA", entrez_id="0", symbol="VEGFA")],
            pubmed_hit_count=10_868,
            query_tier="broad",
            seed_disease_corpus=10_000,
        )

        assert result["pubmed_hit_count"] == 10_868
        assert result["saturation_corpus_size"] == validator.UNVERIFIED_CORPUS_PROXY
        assert result["saturation_basis"] == "unverified_query_scope"
        assert result["novelty_confidence"] == "unverified_query_scope"


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
            query_tier="strict",
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

    @pytest.mark.parametrize("seed_corpus", [None, -1])
    def test_missing_or_failed_seed_corpus_is_unverified(self, seed_corpus):
        result = self.score(seed_corpus=seed_corpus)
        assert result["pubmed_hit_count"] == 0
        assert result["novelty_confidence"] == "unverified_seed_corpus"
        assert result["saturation_corpus_size"] == 60
        assert result["novelty_confidence"] != "verified_gap"
        assert result["discovery_score"] < self.score(seed_corpus=10_000)["discovery_score"]

    def test_ungrounded_seeds_get_an_undefined_tier(self):
        # Not a weak result -- an undefined one. Reporting it on the same scale
        # as a grounded call is what let negative controls look like discoveries.
        assert self.score(seed_corpus=0)["novelty_tier"] == "Ungrounded"
        assert self.score(seed_corpus=10_000)["novelty_tier"] != "Ungrounded"


class TestLiteratureCorpusBackfill:
    """A measured zero is complete evidence, not a missing Python value."""

    def test_zero_count_is_not_backfilled_as_missing(self):
        from app.services.pipeline_stages.validation import ValidationStagesMixin

        calls = []

        class PubMed:
            @staticmethod
            def count_hits(query):
                calls.append(query)
                return 7

        miner = SimpleNamespace(
            pubmed_client=PubMed(),
            _construct_hypothesis_query=lambda name, genes, context, synonyms: name,
            _pathway_clause=lambda name: name,
        )
        stage = ValidationStagesMixin()
        stage.literature_miner = miner
        stage.disease_context = "heart_failure"
        stage.disease_synonyms = []

        def hypothesis(pathway_id):
            return SimpleNamespace(
                aggregated_pathway=SimpleNamespace(
                    pathway=SimpleNamespace(
                        pathway_id=pathway_id,
                        pathway_name=f"pathway {pathway_id}",
                    ),
                    contributing_seed_genes=["VEGFA"],
                ),
                traced_seed_genes=["VEGFA"],
            )

        scored = SimpleNamespace(hypotheses=[hypothesis("ZERO"), hypothesis("MISSING")])
        hit_counts = {"ZERO": 0}
        query_tiers = {"ZERO": "strict"}
        queries = {"ZERO": "measured-zero-query"}
        stage._backfill_corpus_counts(
            scored,
            hit_counts,
            {},
            query_tiers,
            queries,
            {},
            {},
            [GeneInfo(input_id="VEGFA", entrez_id="0", symbol="VEGFA")],
        )

        assert calls == ["pathway MISSING"]
        assert hit_counts["ZERO"] == 0
        assert queries["ZERO"] == "measured-zero-query"
        assert hit_counts["MISSING"] == 7


class TestNoveltyHeadline:
    """Headline literature-sparse counts include verified evidence only."""

    @staticmethod
    def response():
        def hypothesis(pathway_id, confidence, query_tier="strict"):
            return {
                "pathway_id": pathway_id,
                "pathway_name": pathway_id,
                "nes_score": 1.0,
                "score_components": {
                    "novelty_tier": "Highly Novel",
                    "novelty_confidence": confidence,
                    "query_tier": query_tier,
                    "discovery_score": 1.0,
                },
            }

        return {
            "hypotheses": {"hypotheses": [
                hypothesis("verified", "verified"),
                hypothesis("gap", "verified_gap"),
                hypothesis("concept", "unverified_concept"),
                hypothesis("seed", "unverified_seed_corpus"),
                hypothesis("scope", "unverified_query_scope", "broad"),
                hypothesis("legacy-missing", None),
            ]},
            "seed_genes": [],
        }

    def test_all_unverified_states_are_excluded_and_labelled(self):
        from app.web.view_models import hypothesis_rows, summary_stats

        response = self.response()
        rows = hypothesis_rows(response)
        summary = summary_stats(response, rows)

        assert summary["novel_count"] == 2
        by_id = {row["pathway_id"]: row for row in rows}
        for pathway_id in ("concept", "seed", "scope", "legacy-missing"):
            assert by_id[pathway_id]["novelty_interpretable"] is False
            assert by_id[pathway_id]["novelty_evidence_label"].startswith("Unverified:")
        assert by_id["verified"]["novelty_interpretable"] is True
        assert by_id["gap"]["novelty_interpretable"] is True


class TestEffectSizeFilter:
    """min_fold_enrichment was a declared setting that nothing ever read."""

    @staticmethod
    def result(pathways):
        from app.models import FinalPathwayResult
        return FinalPathwayResult(
            final_pathways=pathways, total_count=len(pathways),
            aggregation_strategy="frequency", min_support_threshold=1,
        )

    def test_weak_effect_pathways_are_dropped(self):
        scorer = NESScorer()
        scorer.settings.nets.min_fold_enrichment = 2.0
        # expected overlap = 100*200/20000 = 1.0, so evidence 1 -> fold 1.0
        weak = make_pathway("W:1", evidence=1, term_size=100)
        strong = make_pathway("S:1", evidence=10, term_size=100)
        out = scorer.score(self.result([weak, strong]))
        assert [h.aggregated_pathway.pathway.pathway_id for h in out.hypotheses] == ["S:1"]

    def test_pathways_without_a_measurable_fold_are_kept(self):
        # A missing measurement must not be treated as a failed one.
        scorer = NESScorer()
        scorer.settings.nets.min_fold_enrichment = 2.0
        entry = PathwayEntry(pathway_id="U:1", pathway_name="unknown sizes",
                             source_db="KEGG", p_value=1e-6, p_adj=1e-6,
                             evidence_count=5, evidence_genes=["A"] * 5)
        agg = AggregatedPathway(pathway=entry, support_count=1,
                                source_primary_pathways=[], aggregation_score=1.0,
                                combined_p_value=1e-6, aggregated_nes=0.0,
                                consistency_score=1.0, confidence_score=1.0,
                                support_fraction=1.0)
        assert entry.fold_enrichment is None
        assert scorer.score(self.result([agg])).total_count == 1


class TestNetworkEvidenceExcludedFromPPS:
    """PPS must not reward the neighborhood used to generate candidates."""

    def test_network_arguments_are_accepted_but_do_not_change_pps(self):
        scorer = NESScorer()
        pathway = make_pathway(evidence=4)

        baseline, baseline_components = scorer._calculate_nes(pathway)
        with_network, network_components = scorer._calculate_nes(
            pathway,
            fn_result=object(),
            topology_result=object(),
            seed_neighbors_1hop={"G0", "G1", "G2", "G3"},
        )

        assert with_network == pytest.approx(baseline)
        assert network_components == baseline_components
        assert network_components["network_proximity_weight"] == 1.0
        assert network_components["network_proximity_applied"] is False
        assert network_components["seed_proximity"] is None
        assert network_components["topology_in_pps"] is False

    def test_deprecated_proximity_helper_is_neutral(self):
        scorer = NESScorer()
        weight, proximity = scorer._calculate_proximity_weight(
            make_pathway(evidence=4).pathway,
            object(),
            {"G0", "G1", "G2", "G3"},
        )

        assert weight == 1.0
        assert proximity is None


class TestResultsSnapshot:
    """The snapshot the UI loads must reflect the final scores.

    stage_3 is written as a frozen model_dump() after semantic filtering and
    again after seed tracing, both before Stage 8. Discovery Score, novelty tier
    and permutation q therefore reached the PDF report but never results.json,
    so the app showed em-dashes for its own headline metric.
    """

    def test_stage_3_is_written_after_discovery_scoring(self):
        import inspect
        from app.services.pipeline import Pipeline

        source = inspect.getsource(Pipeline._run_stage_4_5_validation)
        assert 'self.results["stage_3"]' in source, (
            "Stage 8 must re-store stage_3 or the UI keeps a pre-Stage-8 snapshot"
        )


class TestCsvExport:
    """Header and row widths must agree, or every column after the mismatch is
    silently mislabelled in the export researchers actually analyse."""

    @staticmethod
    def response():
        return {
            "seed_genes": [{"symbol": "MYH7"}],
            "hypotheses": {"hypotheses": [{
                "pathway_id": "R:1", "pathway_name": "test", "source_db": "REAC",
                "nes_score": 1.5, "p_adj": 1e-6, "evidence_count": 4,
                "evidence_genes": ["A", "B", "C", "D"],
                "traced_seed_genes": ["MYH7"], "citations": [],
                "score_components": {
                    "discovery_score": 1.2, "novelty_tier": "Novel",
                    "novelty_confidence": "verified_gap",
                    "literature_saturation": 0.3, "pubmed_hit_count": 12,
                    "saturation_corpus_size": 12, "query_tier": "strict",
                    "literature_query": "(MYH7) AND (test) AND (cardiomyopathy)",
                    "literature_novelty": 0.7, "gene_novelty": 0.5,
                    "composite_novelty": 0.6333,
                    "empirical_qvalue": 0.01, "fold_enrichment": 5.0,
                    "term_size": 40, "cardiac_relevance": 0.2,
                    "cardiac_expression_ratio": 0.5, "druggability_tier": "medium",
                },
            }]},
        }

    def test_header_and_rows_have_equal_width(self):
        from app.web.view_models import csv_rows
        rows = csv_rows(self.response())
        header = rows[0]
        for row in rows[1:]:
            assert len(row) == len(header), (
                f"row has {len(row)} fields against a {len(header)}-field header"
            )

    def test_values_land_under_their_own_headers(self):
        from app.web.view_models import csv_rows
        rows = csv_rows(self.response())
        record = dict(zip(rows[0], rows[1]))
        assert record["novelty_tier"] == "Novel"
        assert record["novelty_confidence"] == "verified_gap"
        assert record["pubmed_hit_count"] == "12"
        assert record["query_tier"] == "strict"
        assert record["composite_novelty"] == "0.6333"


# ---------------------------------------------------------------------------
# API failure sentinels
# ---------------------------------------------------------------------------

class TestApiFailureSentinels:
    """A failed call must never be indistinguishable from a real measurement.

    This is the defect that made the novelty metric uninformative. `count_hits`
    returns -1 and every caller checks it. These tests pin the same discipline on
    the clients that feed centrality, druggability and the known-pathway filter.
    """

    def test_string_failure_is_flagged_not_reported_as_no_interactions(self, monkeypatch):
        import requests as _requests
        from app.services.string_client import STRINGClient

        client = STRINGClient()
        monkeypatch.setattr(
            client, "_get_network_data",
            lambda *a, **k: (_ for _ in ()).throw(_requests.RequestException("down")),
        )
        result = client.get_interactions(
            [GeneInfo(input_id="NKX2-5", entrez_id="1482", symbol="NKX2-5")]
        )

        # An outage yields an edgeless graph, which scores every gene's
        # betweenness centrality at 0.0 -- a real-looking measurement.
        assert result["available"] is False
        assert result["interactions"] == []

    def test_empty_network_is_still_flagged_available(self, monkeypatch):
        from app.services.string_client import STRINGClient

        client = STRINGClient()
        # A query that succeeds and finds nothing is a real result, not a failure.
        monkeypatch.setattr(client, "_get_network_data", lambda *a, **k: None)
        result = client.get_interactions(
            [GeneInfo(input_id="NKX2-5", entrez_id="1482", symbol="NKX2-5")]
        )

        assert result["available"] is True
        assert result["interactions"] == []

    def test_string_health_check_reports_an_outage(self, monkeypatch):
        from app.services.input_validator import InputValidator

        validator = InputValidator()
        monkeypatch.setattr(
            validator.string_client, "get_interactions",
            lambda *a, **k: {"neighbors": [], "interactions": [], "contributions": {},
                             "total_interactions": 0, "score_threshold": 0.6,
                             "available": False, "error": "down"},
        )
        status = validator._check_string()

        # get_interactions does not raise, so a health check that only catches
        # exceptions reports available=True during a total outage.
        assert status["available"] is False
        assert status["error"]

    def test_string_url_follows_the_configured_version(self):
        from app.services.string_client import STRINGClient
        from app.core.config import get_settings

        client = STRINGClient()
        version = get_settings().nets.string_version
        assert version.replace(".", "-") in client.base_url, (
            "the client must query the release the config advertises; a mismatch "
            "here is a wrong database version in the methods section"
        )

    def test_open_targets_failure_is_recorded_in_the_source_label(self, monkeypatch):
        import requests as _requests
        from app.services.druggability_analyzer import DruggabilityAnalyzer

        analyzer = DruggabilityAnalyzer()
        monkeypatch.setattr(
            _requests, "post",
            lambda *a, **k: (_ for _ in ()).throw(_requests.RequestException("down")),
        )
        score = analyzer.calculate_druggability_score(["SRC"], use_external=True)

        assert analyzer.last_lookup_failures == 1
        assert "unavailable" in score.druggability_source
        assert score.druggability_source != "curated"

    def test_reactome_failure_is_distinguishable_from_no_known_pathways(self, monkeypatch):
        import requests as _requests
        from app.services.reactome_client import ReactomeClient

        client = ReactomeClient()
        assert client.last_query_failed is False
        monkeypatch.setattr(
            client, "_query_analysis_service",
            lambda *a, **k: (_ for _ in ()).throw(_requests.RequestException("down")),
        )
        result = client.get_pathways_for_genes(
            [GeneInfo(input_id="MYH7", entrez_id="4625", symbol="MYH7")]
        )

        # An empty set from an outage means the known-pathway filter cannot run,
        # so already-annotated pathways would be reported as discoveries.
        assert result == []
        assert client.last_query_failed is True


class TestGtexPlaceholders:
    """The curated fallback must not emit constants that render as measurements."""

    def test_offline_estimate_reports_no_tpm_or_specificity(self):
        from app.services.tissue_expression_validator import TissueExpressionValidator

        score = TissueExpressionValidator().calculate_offline_expression_score(
            ["MYH7", "TTN", "ZZZ9"]
        )
        assert score.gtex_measured is False
        # 5.0 and 2.0 were previously rendered as "2.0x vs other tissues".
        assert score.mean_cardiac_tpm is None
        assert score.mean_cardiac_specificity_ratio is None
        # The ratio the curated list *can* support is still produced.
        assert score.cardiac_expression_ratio > 0


class TestGenericPathwayDetection:
    """Generic detection must not suppress the tool's best hits.

    `is_generic_pathway` gates literature expansion in Stage 2b. It matched
    generic terms as substrings, so the entry "signaling pathway" caught every
    named KEGG signaling pathway (TNF, NF-kappa B, Toll-like receptor, PI3K-Akt),
    and a "<= 2 words" heuristic caught "Inflammasomes", "Cardiogenesis" and
    "GAB1 signalosome". All of those are top-ranked discoveries in the benchmark
    panels.
    """

    @staticmethod
    def is_generic(name):
        from app.services.semantic_filter import SemanticFilter
        return SemanticFilter().is_generic_pathway(name)

    @pytest.mark.parametrize("name", [
        "TNF signaling pathway",
        "NF-kappa B signaling pathway",
        "Toll-like receptor signaling pathway",
        "PI3K-Akt signaling pathway",
        "Inflammasomes",
        "GAB1 signalosome",
        "Cardiogenesis",
        "Cardiac muscle contraction",
    ])
    def test_specific_pathways_are_not_suppressed(self, name):
        assert not self.is_generic(name), f"{name} must keep its literature expansion"

    @pytest.mark.parametrize("name", [
        "biological process",
        "cellular process",
        "developmental process",
        "regulation of cellular process",
        "positive regulation of cellular process",
        "binding",
        "signaling",
    ])
    def test_genuinely_generic_pathways_are_suppressed(self, name):
        assert self.is_generic(name), f"{name} carries no specific concept"

    def test_a_generic_suffix_alone_does_not_make_a_name_generic(self):
        # The prefix is where the specificity lives.
        assert self.is_generic("regulation of cellular process")
        assert not self.is_generic("TNF signaling pathway")
