import pytest
from pydantic import ValidationError

from app.core.config import get_settings
from app.services.pipeline import Pipeline, _software_provenance


def test_pipeline_preserves_context_and_syncs_service_settings():
    get_settings.cache_clear()
    pipeline = Pipeline(
        config_overrides={
            "disease_context": "diabetic_cardiomyopathy",
            "disease_synonyms": ["diabetic cardiomyopathy", "DCM"],
            "pubmed_max_results": 12,
            "redundancy_jaccard_threshold": 0.42,
        }
    )

    try:
        assert pipeline.disease_context == "diabetic_cardiomyopathy"
        assert pipeline.disease_synonyms == ["diabetic cardiomyopathy", "DCM"]
        assert pipeline.settings.nets.pubmed_max_results == 12
        assert pipeline.literature_miner.settings.nets.pubmed_max_results == 12
        assert pipeline.literature_miner.pubmed_client.max_results == 12
        assert pipeline.seed_gene_tracer.pubmed_client.max_results == 12
        assert pipeline.redundancy_detector.similarity_threshold == 0.42
    finally:
        pipeline.close()
        get_settings.cache_clear()


def test_pipeline_presets_reach_services_and_constructor_cached_fields():
    get_settings.cache_clear()
    pipeline = Pipeline(
        config_overrides={
            "string_version": "12.0",
            "string_neighbor_count": 50,
            "string_score_threshold": 0.65,
            "fdr_threshold": 0.08,
            "primary_pathways_to_expand": 5,
            "n_permutations": 250,
            "pubmed_max_results": 12,
            "gprofiler_timeout_seconds": 7.0,
            "gprofiler_api_url": "https://example.org/gprofiler/api",
        }
    )

    try:
        assert pipeline.fn_builder.settings is pipeline.settings
        assert pipeline.fn_builder.string_client.settings is pipeline.settings
        assert pipeline.fn_builder.string_client.base_url == (
            "https://version-12-0.string-db.org/api"
        )
        assert pipeline.primary_analyzer.settings.nets.fdr_threshold == 0.08
        assert pipeline.secondary_analyzer.settings.nets.primary_pathways_to_expand == 5
        assert pipeline.permutation_tester.n_permutations == 250
        assert pipeline.literature_miner.pubmed_client.max_results == 12
        assert pipeline.secondary_analyzer.literature_expander.pubmed_client.max_results == 12
        for analyzer in (pipeline.primary_analyzer, pipeline.secondary_analyzer):
            assert analyzer.gprofiler_client.timeout_seconds == 7.0
            assert analyzer.gprofiler_client.base_url == "https://example.org/gprofiler"
    finally:
        pipeline.close()
        get_settings.cache_clear()


def test_pipeline_preserves_zero_valued_stage8_limits():
    get_settings.cache_clear()
    pipeline = Pipeline(
        config_overrides={
            "gtex_top_pathways": 0,
            "permutation_top_pathways": 0,
            "external_druggability_top_pathways": 0,
            "external_druggability_enabled": False,
            "permutation_test_enabled": False,
        }
    )

    try:
        assert pipeline.settings.nets.gtex_top_pathways == 0
        assert pipeline.settings.nets.permutation_top_pathways == 0
        assert pipeline.settings.nets.external_druggability_top_pathways == 0
        assert pipeline.settings.nets.external_druggability_enabled is False
        assert pipeline.settings.nets.permutation_test_enabled is False
    finally:
        pipeline.close()
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_retries": 6},
        {"request_timeout": 301},
        {"gprofiler_timeout_seconds": 601},
    ],
)
def test_pipeline_revalidates_merged_config(overrides):
    get_settings.cache_clear()
    try:
        with pytest.raises(ValidationError):
            Pipeline(config_overrides=overrides)
    finally:
        get_settings.cache_clear()


def test_software_provenance_is_explicit_and_stable():
    provenance = _software_provenance()
    assert provenance["name"] == "CardioXNet"
    assert provenance["version"]
    revision = provenance["git_revision"]
    assert revision is None or (
        len(revision) == 40
        and all(character in "0123456789abcdef" for character in revision.lower())
    )
