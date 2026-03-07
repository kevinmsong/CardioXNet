from app.core.config import get_settings
from app.services.pipeline import Pipeline


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
