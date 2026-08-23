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
                                {"label": "Advanced Clinical", "modality": "SM", "value": True},
                            ],
                            "knownDrugs": {
                                "count": 12,
                                "rows": [
                                    {
                                        "phase": 4,
                                        "status": "Completed",
                                        "disease": {"name": "cardiovascular disease"},
                                        "drug": {"id": "CHEMBL1", "name": "Drug A", "maximumClinicalTrialPhase": 4},
                                    },
                                    {
                                        "phase": 2,
                                        "status": "Recruiting",
                                        "disease": {"name": "heart failure"},
                                        "drug": {"id": "CHEMBL2", "name": "Drug B", "maximumClinicalTrialPhase": 2},
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
