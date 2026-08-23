import pytest
import requests

from app.services.druggability_analyzer import DruggabilityAnalyzer


class _MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_calculate_druggability_score_includes_live_target_evidence(monkeypatch):
    payload = {
        "data": {
            "search": {
                "hits": [
                    {
                        "id": "ENSG00000197122",
                        "entity": "target",
                        "object": {
                            "approvedSymbol": "SRC",
                            "approvedName": "SRC proto-oncogene",
                            "tractability": [
                                {"label": "Approved Drug", "modality": "SM", "value": True},
                            ],
                            # Current Open Targets shape: drugAndClinicalCandidates,
                            # maxClinicalStage, and diseases nested under `disease`.
                            "drugAndClinicalCandidates": {
                                "count": 12,
                                "rows": [
                                    {
                                        "maxClinicalStage": "APPROVAL",
                                        "drug": {"id": "CHEMBL1", "name": "Drug A",
                                                 "maximumClinicalStage": "APPROVAL"},
                                        "diseases": [{"disease": {"name": "cardiovascular disease"}}],
                                    },
                                    {
                                        "maxClinicalStage": "PHASE_2",
                                        "drug": {"id": "CHEMBL2", "name": "Drug B",
                                                 "maximumClinicalStage": "PHASE_2"},
                                        "diseases": [{"disease": {"name": "heart failure"}}],
                                    },
                                ],
                            },
                        },
                    }
                ]
            }
        }
    }

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: _MockResponse(payload))

    analyzer = DruggabilityAnalyzer()
    score = analyzer.calculate_druggability_score(["SRC", "MAPK1"])

    assert score.druggability_source == "Open Targets + curated"
    assert score.external_target_count == 1
    assert score.external_approved_target_count == 1
    assert score.external_clinical_target_count == 1
    assert score.cardiovascular_target_count == 1
    assert score.approved_drug_count >= 1
    assert score.target_evidence[0]["gene_symbol"] == "SRC"
    assert score.target_evidence[0]["top_drugs"][0]["name"] == "Drug A"
    assert score.external_lookup_attempted == 2
    assert score.external_lookup_failures == 0
    assert score.external_lookup_complete is True
    assert score.external_lookup_error is None


def test_calculate_druggability_score_falls_back_when_live_lookup_fails(monkeypatch):
    def _raise(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr(requests, "post", _raise)

    analyzer = DruggabilityAnalyzer()
    score = analyzer.calculate_druggability_score(["SRC"])

    # The curated fallback still works...
    assert score.external_target_count == 0
    assert score.target_evidence == []
    assert "SRC" in score.druggable_genes

    # ...but the failure must be recorded, not laundered into a plain "curated"
    # label. external_approved_target_count == 0 is otherwise read as the finding
    # "no pathway gene has an approved drug", which a failed lookup cannot support.
    assert score.druggability_source != "curated"
    assert "unavailable" in score.druggability_source
    assert analyzer.last_lookup_failures == 1
    assert score.external_lookup_attempted == 1
    assert score.external_lookup_failures == 1
    assert score.external_lookup_complete is False
    assert "boom" in score.external_lookup_error


def test_query_does_not_use_fields_open_targets_removed():
    """Static guard against the schema drift that silently zeroed druggability.

    The query asked for `knownDrugs(size:)`, `phase`, `status`, `disease { name }`
    and `drug { maximumClinicalTrialPhase }`. Open Targets removed all of them, so
    every request returned HTTP 400 -- and `except Exception: pass` in the caller
    meant external druggability read 0 for every gene in every run, indefinitely.
    """
    query = DruggabilityAnalyzer._OT_QUERY
    for removed in ("knownDrugs", "maximumClinicalTrialPhase"):
        assert removed not in query, f"{removed} no longer exists on the Open Targets schema"
    assert "drugAndClinicalCandidates" in query
    assert "maxClinicalStage" in query


@pytest.mark.live
def test_open_targets_query_is_accepted_by_the_live_schema():
    """Opt-in live check that the query still matches the API.

    Run with `pytest -m live`. Skipped when the network is unavailable so the
    default suite stays offline-safe.
    """
    import requests

    analyzer = DruggabilityAnalyzer()
    try:
        resp = requests.post(
            analyzer._OT_GRAPHQL_URL,
            json={"query": analyzer._OT_QUERY, "variables": {"term": "MYH7"}},
            timeout=30,
        )
    except requests.RequestException as exc:
        pytest.skip(f"Open Targets unreachable: {exc}")

    assert resp.status_code == 200, resp.text[:400]
    assert "errors" not in resp.json(), resp.text[:400]
