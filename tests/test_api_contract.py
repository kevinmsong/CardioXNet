"""Security and provenance checks for the public API contract."""

import pytest
from pydantic import ValidationError

from app.api import endpoints
from app.models import AnalysisRequest


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_retries": 1_000_000},
        {"request_timeout": 1_000_000},
        {"gprofiler_timeout_seconds": 1_000_000},
        {"string_api_url": "http://127.0.0.1:8080"},
        {"gprofiler_api_url": "http://169.254.169.254/latest/meta-data"},
        {"reactome_api_url": "https://example.invalid/private"},
        {"resource_url": "http://10.0.0.1/internal"},
    ],
)
def test_public_analysis_overrides_reject_unbounded_or_endpoint_values(overrides):
    with pytest.raises(ValidationError):
        AnalysisRequest(seed_genes=["MYH7"], config_overrides=overrides)


def test_public_analysis_overrides_preserve_supported_keys():
    request = AnalysisRequest(
        seed_genes=["MYH7", "TTN"],
        config_overrides={
            "string_neighbor_count": 50,
            "fdr_threshold": 0.01,
            "top_hypotheses_count": 20,
            "max_retries": 3,
            "request_timeout": 30,
            "disease_synonyms": ["dilated cardiomyopathy", "DCM"],
        },
    )

    assert request.config_overrides is not None
    assert request.config_overrides.model_dump(exclude_none=True) == {
        "string_neighbor_count": 50,
        "fdr_threshold": 0.01,
        "top_hypotheses_count": 20,
        "max_retries": 3,
        "request_timeout": 30,
        "disease_synonyms": ["dilated cardiomyopathy", "DCM"],
    }


@pytest.mark.asyncio
async def test_results_response_exposes_run_metadata(tmp_path, monkeypatch):
    metadata = {
        "analysis_id": "analysis_metadata_test",
        "resource_identifiers": {
            "gprofiler": {
                "configured_endpoint": "https://biit.cs.ut.ee/gprofiler",
                "effective_endpoint": "https://biit.cs.ut.ee/gprofiler",
            }
        },
    }
    analysis = {
        "status": "completed",
        "results": {"run_metadata": metadata},
        "report_files": {},
    }
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(endpoints.analysis_store, "get_analysis", lambda _analysis_id: analysis)

    response = await endpoints.get_analysis_results("analysis_metadata_test")

    assert response.run_metadata == metadata
    assert response.model_dump()["run_metadata"] == metadata
