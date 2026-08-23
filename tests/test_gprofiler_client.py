import json
import multiprocessing
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models import FunctionalNeighborhood, GeneInfo
from app.services.api_client import APIClientError, APITimeoutError
from app.services import gprofiler_client as module
from app.services.gprofiler_client import GProfilerClient
from app.services.primary_pathway_analyzer import PrimaryPathwayAnalyzer
from app.services.secondary_pathway_analyzer import SecondaryPathwayAnalyzer


def _gene(symbol: str = "GATA4") -> GeneInfo:
    return GeneInfo(
        input_id=symbol,
        entrez_id="2626",
        hgnc_id="HGNC:4173",
        symbol=symbol,
    )


# Spawn-process targets must be defined at module scope so Windows can pickle
# and import them. They exercise the real parent-side protocol without network
# access or inherited monkeypatches.
def _spawn_success(connection, _kwargs, _base_url, result_path):
    results = [{"native": "REAC:R-HSA-123", "p_value": 0.001}]
    encoded = json.dumps(results, separators=(",", ":")).encode("utf-8")
    Path(result_path).write_bytes(encoded)
    connection.send({
        "protocol": module._WORKER_PROTOCOL,
        "status": "ok",
        "bytes": len(encoded),
        "records": len(results),
    })
    connection.close()


def _spawn_error(connection, _kwargs, _base_url, _result_path):
    connection.send({
        "protocol": module._WORKER_PROTOCOL,
        "status": "error",
        "error_type": "SyntheticError",
        "message": "bounded failure",
    })
    connection.close()


def _spawn_malformed(connection, _kwargs, _base_url, _result_path):
    connection.send({"protocol": 999, "status": "ok"})
    connection.close()


def _spawn_crash(_connection, _kwargs, _base_url, _result_path):
    os._exit(23)


def _spawn_hang(_connection, _kwargs, _base_url, _result_path):
    time.sleep(5.0)


def test_profile_call_runs_with_hard_timeout_and_preserves_evidence(monkeypatch):
    captured = {}

    def fake_profile(kwargs, timeout_seconds, base_url):
        captured["kwargs"] = kwargs
        captured["timeout"] = timeout_seconds
        captured["base_url"] = base_url
        return [{
            "source": "REAC",
            "native": "REAC:R-HSA-123",
            "name": "Cardiac signaling",
            "p_value": 0.001,
            "intersection_size": 1,
            "intersections": ["GATA4"],
            "term_size": 10,
            "query_size": 1,
            "effective_domain_size": 1000,
        }]

    monkeypatch.setattr(module, "_run_profile_in_subprocess", fake_profile)
    client = GProfilerClient()

    pathways = client.get_enrichment([_gene()], sources=["REAC"])

    assert captured["timeout"] == client.settings.nets.gprofiler_timeout_seconds
    assert captured["base_url"] == "https://biit.cs.ut.ee/gprofiler"
    assert captured["kwargs"]["no_evidences"] is False
    assert captured["kwargs"]["query"] == ["GATA4"]
    assert pathways[0].evidence_genes == ["GATA4"]
    assert pathways[0].fold_enrichment == pytest.approx(100.0)


def test_timeout_is_retried_then_preserved_as_typed_failure(monkeypatch):
    attempts = 0
    sleeps = []

    def timed_out(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        raise APITimeoutError("g:Profiler request exceeded deadline")

    client = GProfilerClient()
    monkeypatch.setattr(module, "_run_profile_in_subprocess", timed_out)
    monkeypatch.setattr(module.time, "sleep", sleeps.append)
    monkeypatch.setattr(client.settings.nets, "max_retries", 1)

    with pytest.raises(APITimeoutError, match="no enrichment result was produced"):
        client.get_enrichment([_gene()])

    assert attempts == 2
    assert sleeps == [client.settings.nets.retry_backoff_factor]


def test_spawn_protocol_transfers_result_without_pipe_payload():
    results = module._run_profile_in_subprocess(
        {},
        10.0,
        "https://example.test/gprofiler",
        worker_target=_spawn_success,
    )
    assert results == [{"native": "REAC:R-HSA-123", "p_value": 0.001}]


def test_spawn_worker_error_sentinel_is_not_an_empty_result():
    with pytest.raises(APIClientError, match="SyntheticError: bounded failure"):
        module._run_profile_in_subprocess(
            {},
            10.0,
            "https://example.test/gprofiler",
            worker_target=_spawn_error,
        )


@pytest.mark.parametrize(
    ("worker_target", "message"),
    [
        (_spawn_malformed, "malformed sentinel"),
        (_spawn_crash, "exit code 23"),
    ],
)
def test_spawn_protocol_rejects_malformed_or_crashed_workers(
    worker_target, message
):
    with pytest.raises(APIClientError, match=message):
        module._run_profile_in_subprocess(
            {},
            10.0,
            "https://example.test/gprofiler",
            worker_target=worker_target,
        )


def test_process_deadline_terminates_reaps_and_closes_a_hung_worker():
    baseline = {
        process.pid
        for process in multiprocessing.active_children()
        if process.name == "cardioxnet-gprofiler"
    }
    started = time.monotonic()

    with pytest.raises(APITimeoutError, match="worker was terminated"):
        module._run_profile_in_subprocess(
            {},
            0.1,
            "https://example.test/gprofiler",
            worker_target=_spawn_hang,
        )

    assert time.monotonic() - started < 2.0
    leaked = [
        process
        for process in multiprocessing.active_children()
        if process.name == "cardioxnet-gprofiler" and process.pid not in baseline
    ]
    assert leaked == []


def test_invalid_worker_payload_is_not_treated_as_empty_enrichment(monkeypatch):
    monkeypatch.setattr(
        module,
        "_run_profile_in_subprocess",
        lambda *_args, **_kwargs: {"unexpected": "mapping"},
    )
    client = GProfilerClient()

    with pytest.raises(APIClientError, match="invalid result payload"):
        client.get_enrichment([_gene()])


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("https://biit.cs.ut.ee/gprofiler/api", "https://biit.cs.ut.ee/gprofiler"),
        ("https://biit.cs.ut.ee/gprofiler/api/", "https://biit.cs.ut.ee/gprofiler"),
        ("https://example.org/custom/", "https://example.org/custom"),
    ],
)
def test_gprofiler_base_url_normalization(configured, expected):
    assert module._normalize_gprofiler_base_url(configured) == expected


@pytest.mark.parametrize(
    "configured",
    ["", "biit.cs.ut.ee/gprofiler", "ftp://example.org/gprofiler", "https://example.org/gprofiler?q=1"],
)
def test_gprofiler_base_url_rejects_invalid_values(configured):
    with pytest.raises(ValueError, match=r"absolute HTTP\(S\) URL"):
        module._normalize_gprofiler_base_url(configured)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (APITimeoutError("deadline"), True),
        (APIClientError("HTTP 408 request timeout"), True),
        (APIClientError("HTTP 503 Service Unavailable"), True),
        (APIClientError("ConnectionError: connection reset"), True),
        (APIClientError("invalid payload from localhost:5000"), False),
        (APIClientError("HTTP 400 bad request"), False),
    ],
)
def test_transient_error_classification_is_bounded(error, expected):
    assert module._is_transient_gprofiler_error(error) is expected


class _FailingEnrichmentClient:
    def get_enrichment(self, **_kwargs):
        raise APITimeoutError("hard deadline reached")


@pytest.mark.parametrize(
    ("analyzer_class", "argument"),
    [
        (
            PrimaryPathwayAnalyzer,
            FunctionalNeighborhood(seed_genes=[_gene()], neighbors=[], size=1),
        ),
        (SecondaryPathwayAnalyzer, [_gene()]),
    ],
)
def test_enrichment_failure_never_becomes_an_empty_result(analyzer_class, argument):
    analyzer = analyzer_class.__new__(analyzer_class)
    analyzer.gprofiler_client = _FailingEnrichmentClient()
    analyzer.settings = SimpleNamespace(nets=SimpleNamespace(fdr_threshold=0.05))

    with pytest.raises(APITimeoutError, match="hard deadline"):
        analyzer._query_enrichment(argument)
