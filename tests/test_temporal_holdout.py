import pytest

from app.services.hypothesis_validator import HypothesisValidator
from bench.temporal_holdout import (
    composite_novelty,
    gene_novelty_from_report,
    novelty_gate_state,
    persisted_query_provenance,
    saturation,
    tier,
)


def test_legacy_report_recovers_deployed_gene_novelty():
    gene_novelty = 0.4
    literature_novelty = 1.0 - saturation(0)
    weighted = composite_novelty(literature_novelty, gene_novelty) * 0.15
    hypothesis = {
        "pathway_name": "Test pathway",
        "score_components": {"novelty_score": weighted, "pubmed_hit_count": 0},
    }

    assert gene_novelty_from_report(hypothesis) == pytest.approx(gene_novelty)


def test_ungrounded_gate_uses_conservative_proxy_and_undefined_tier():
    state = novelty_gate_state(hits_pre=0, seed_disease_pre=0)

    assert state["saturation_hits_pre"] == HypothesisValidator.UNVERIFIED_CORPUS_PROXY
    assert state["saturation_basis"] == "ungrounded_seeds"
    assert tier(0.9, state["novelty_confidence"]) == "Ungrounded"


def test_unsearchable_concept_does_not_receive_maximal_novelty():
    state = novelty_gate_state(
        hits_pre=0,
        seed_disease_pre=HypothesisValidator.MIN_SEED_DISEASE_CORPUS,
        concept_hits_pre=HypothesisValidator.MIN_CONCEPT_CORPUS - 1,
    )

    assert state["saturation_hits_pre"] == HypothesisValidator.UNVERIFIED_CORPUS_PROXY
    assert state["novelty_confidence"] == "unverified_concept"
    assert tier(0.9, state["novelty_confidence"]) == "Unverified"


def test_searchable_zero_is_retained_as_verified_gap():
    state = novelty_gate_state(
        hits_pre=0,
        seed_disease_pre=HypothesisValidator.MIN_SEED_DISEASE_CORPUS,
        concept_hits_pre=HypothesisValidator.MIN_CONCEPT_CORPUS,
    )

    assert state["saturation_hits_pre"] == 0
    assert state["novelty_confidence"] == "verified_gap"


def test_grounded_zero_requires_concept_measurement():
    with pytest.raises(ValueError, match="requires a concept count"):
        novelty_gate_state(
            hits_pre=0,
            seed_disease_pre=HypothesisValidator.MIN_SEED_DISEASE_CORPUS,
        )


def test_holdout_uses_exact_persisted_query_provenance():
    hypothesis = {
        "pathway_name": "Test pathway",
        "literature_query": "(LMNA) AND (test pathway) AND (cardiomyopathy)",
        "literature_query_genes": ["LMNA"],
        "query_tier": "strict",
        "literature_concept_query": "(test pathway)",
        # A different later rendering must not affect the deployed query.
        "seed_genes": ["LMNA", "TTN", "MYH7"],
    }

    provenance = persisted_query_provenance(hypothesis)

    assert provenance["query"] == hypothesis["literature_query"]
    assert provenance["query_genes"] == ["LMNA"]
    assert provenance["concept_query"] == "(test pathway)"


def test_holdout_refuses_reconstructed_legacy_query():
    with pytest.raises(ValueError, match="exact persisted query provenance"):
        persisted_query_provenance({
            "pathway_name": "Legacy pathway",
            "seed_genes": ["LMNA"],
        })
