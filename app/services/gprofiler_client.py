"""g:Profiler client with a hard, process-enforced request deadline."""

import json
import logging
import multiprocessing
import os
import re
import tempfile
import time
from multiprocessing.connection import Connection
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
from urllib.parse import urlsplit

from gprofiler import GProfiler

from app.services.api_client import APIClientError, APITimeoutError
from app.models import GeneInfo, PathwayEntry
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_WORKER_PROTOCOL = 1
_MAX_RESULT_BYTES = 256 * 1024 * 1024
_MAX_ERROR_MESSAGE_CHARS = 4096
_TRANSIENT_HTTP_STATUS = re.compile(
    r"(?<!\d)(?:408|429|500|502|503|504)(?!\d)"
)
_TRANSIENT_ERROR_MARKERS = (
    "service unavailable",
    "timed out",
    "timeout",
    "connectionerror",
    "connection reset",
    "connection aborted",
    "connection refused",
    "remote disconnected",
    "server disconnected",
    "temporary failure in name resolution",
    "name or service not known",
)


def _gprofiler_profile_worker(
    connection: Connection,
    profile_kwargs: Dict[str, Any],
    base_url: str,
    result_path: str,
) -> None:
    """Run one official-library request in an independently killable process.

    ``gprofiler-official`` calls ``requests.post`` without a timeout and does
    not expose the underlying request object. A process boundary is therefore
    the only reliable way to cancel a blocked call without leaving a live
    thread behind. The potentially large result is written atomically to a
    private temporary file; only a small protocol sentinel crosses the pipe, so
    pipe backpressure cannot defeat the deadline.
    """
    try:
        client = GProfiler(
            user_agent="CardioXNet/0.1",
            base_url=base_url,
            return_dataframe=False,
        )
        results = client.profile(**profile_kwargs)
        if not isinstance(results, list):
            raise TypeError("g:Profiler returned a non-list result")

        final_path = Path(result_path)
        partial_path = final_path.with_suffix(".partial")
        with partial_path.open("w", encoding="utf-8", newline="") as handle:
            # Stream JSON directly to disk. Building one large serialized string
            # in memory would unnecessarily duplicate a large enrichment result.
            json.dump(
                results,
                handle,
                ensure_ascii=True,
                allow_nan=False,
                separators=(",", ":"),
            )
        os.replace(partial_path, final_path)
        connection.send({
            "protocol": _WORKER_PROTOCOL,
            "status": "ok",
            "bytes": final_path.stat().st_size,
            "records": len(results),
        })
    except Exception as exc:
        try:
            connection.send({
                "protocol": _WORKER_PROTOCOL,
                "status": "error",
                "error_type": type(exc).__name__,
                # Keep the control message safely below pipe-buffer sizes even
                # if an upstream exception contains an unexpectedly large body.
                "message": str(exc)[:_MAX_ERROR_MESSAGE_CHARS],
            })
        except (BrokenPipeError, EOFError, OSError):
            # The parent reached its deadline and closed the pipe before the
            # worker could report its exception.
            pass
    finally:
        connection.close()


def _terminate_process(process: multiprocessing.Process) -> None:
    """Terminate and reap a worker, escalating to kill if necessary."""
    if process.is_alive():
        process.terminate()
    process.join(timeout=2.0)
    if process.is_alive():
        kill = getattr(process, "kill", None)
        if kill is not None:
            kill()
        process.join(timeout=2.0)
    if process.is_alive():
        raise APIClientError("g:Profiler worker could not be terminated cleanly")


def _await_worker_message(
    process: multiprocessing.Process,
    connection: Connection,
    timeout_seconds: float,
) -> Dict[str, Any]:
    """Receive a worker result before the deadline or terminate the worker."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _terminate_process(process)
            raise APITimeoutError(
                f"g:Profiler request exceeded {timeout_seconds:g} seconds; "
                "the isolated worker was terminated"
            )

        if connection.poll(min(0.05, remaining)):
            try:
                return connection.recv()
            except EOFError as exc:
                process.join(timeout=0.2)
                if process.is_alive():
                    _terminate_process(process)
                raise APIClientError(
                    "g:Profiler worker closed without returning a result "
                    f"(exit code {process.exitcode})"
                ) from exc

        if not process.is_alive():
            # A final poll covers the small interval between send() and process
            # shutdown. If no message is present, the child crashed before it
            # could report an exception.
            if connection.poll(0):
                try:
                    return connection.recv()
                except EOFError:
                    pass
            process.join(timeout=0.2)
            raise APIClientError(
                f"g:Profiler worker exited without a result "
                f"(exit code {process.exitcode})"
            )


def _run_profile_in_subprocess(
    profile_kwargs: Dict[str, Any],
    timeout_seconds: float,
    base_url: str,
    *,
    worker_target: Optional[Callable[..., None]] = None,
) -> List[Dict[str, Any]]:
    """Execute the official g:Profiler call with a hard wall-clock deadline."""
    if worker_target is None:
        worker_target = _gprofiler_profile_worker

    with tempfile.TemporaryDirectory(prefix="cardioxnet_gprofiler_") as temp_dir:
        result_path = Path(temp_dir) / "result.json"
        context = multiprocessing.get_context("spawn")
        receive_connection, send_connection = context.Pipe(duplex=False)
        process = context.Process(
            target=worker_target,
            args=(send_connection, profile_kwargs, base_url, str(result_path)),
            name="cardioxnet-gprofiler",
            daemon=True,
        )
        started = False

        try:
            process.start()
            started = True
            # The parent must close its copy so EOF accurately reflects child exit.
            send_connection.close()
            message = _await_worker_message(
                process,
                receive_connection,
                timeout_seconds,
            )
            process.join(timeout=2.0)
            if process.is_alive():
                _terminate_process(process)
        finally:
            receive_connection.close()
            send_connection.close()
            if started:
                try:
                    if process.is_alive():
                        _terminate_process(process)
                finally:
                    # ``close`` releases the native process HANDLE on Windows.
                    # It is only legal after the child has stopped.
                    if not process.is_alive():
                        process.close()

        if (
            not isinstance(message, dict)
            or message.get("protocol") != _WORKER_PROTOCOL
        ):
            raise APIClientError("g:Profiler worker returned a malformed sentinel")

        if message.get("status") == "ok":
            if not result_path.is_file():
                raise APIClientError("g:Profiler worker omitted its result file")
            result_size = result_path.stat().st_size
            expected_size = message.get("bytes")
            if (
                not isinstance(expected_size, int)
                or expected_size < 0
                or expected_size != result_size
            ):
                raise APIClientError("g:Profiler result size did not match its sentinel")
            if result_size > _MAX_RESULT_BYTES:
                raise APIClientError("g:Profiler result exceeded the 256 MB safety limit")
            try:
                results = json.loads(result_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise APIClientError("g:Profiler returned an unreadable result") from exc
            if not isinstance(results, list) or not all(
                isinstance(entry, dict) for entry in results
            ):
                raise APIClientError("g:Profiler returned an invalid result payload")
            expected_records = message.get("records")
            if (
                not isinstance(expected_records, int)
                or expected_records != len(results)
            ):
                raise APIClientError("g:Profiler result count did not match its sentinel")
            return results

        if message.get("status") != "error":
            raise APIClientError("g:Profiler worker returned an unknown status")
        error_type = message.get("error_type", "Error")
        error_message = message.get("message", "unknown worker failure")
        raise APIClientError(f"g:Profiler {error_type}: {error_message}")


def _normalize_gprofiler_base_url(url: str) -> str:
    """Normalize legacy endpoint settings to the base URL expected by the SDK."""
    normalized = url.rstrip("/")
    if normalized.endswith("/api"):
        normalized = normalized[:-4]
    parsed = urlsplit(normalized)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "g:Profiler base URL must be an absolute HTTP(S) URL without "
            "a query string or fragment"
        )
    return normalized


def _is_transient_gprofiler_error(error: Exception) -> bool:
    """Return whether a failed request is safe and useful to retry."""
    if isinstance(error, APITimeoutError):
        return True
    detail = f"{type(error).__name__}: {error}".lower()
    return bool(_TRANSIENT_HTTP_STATUS.search(detail)) or any(
        marker in detail for marker in _TRANSIENT_ERROR_MARKERS
    )


class GProfilerClient:
    """Client for g:Profiler functional enrichment analysis using official library."""
    
    def __init__(self):
        """Initialize g:Profiler client."""
        self.settings = get_settings()
        self.organism = "hsapiens"
        self.timeout_seconds = self.settings.nets.gprofiler_timeout_seconds
        self.base_url = _normalize_gprofiler_base_url(
            self.settings.nets.gprofiler_api_url
        )
        logger.info(
            "GProfilerClient initialized with a %.0f s process-enforced timeout",
            self.timeout_seconds,
        )
    
    def get_enrichment(
        self,
        genes: List[GeneInfo],
        sources: Optional[List[str]] = None,
        fdr_threshold: Optional[float] = None
    ) -> List[PathwayEntry]:
        """
        Query g:Profiler for pathway enrichment using official library.
        
        Args:
            genes: List of genes to analyze
            sources: Data sources to query (REAC, KEGG, WP, GO:BP)
            fdr_threshold: FDR significance threshold
            
        Returns:
            List of enriched PathwayEntry objects
            
        Raises:
            APIClientError: On API errors
        """
        if not genes:
            raise ValueError("At least one gene is required")
        
        # Default sources: Reactome, KEGG, WikiPathways, GO:BP, GO:MF, GO:CC
        # Added GO:MF (Molecular Function) and GO:CC (Cellular Component) for comprehensive coverage
        sources = sources or ["REAC", "KEGG", "WP", "GO:BP", "GO:MF", "GO:CC"]
        if fdr_threshold is None:
            fdr_threshold = self.settings.nets.fdr_threshold
        
        gene_symbols = [gene.symbol for gene in genes]
        
        logger.info(
            f"Querying g:Profiler for {len(gene_symbols)} genes, "
            f"sources: {sources}, FDR threshold: {fdr_threshold}"
        )
        
        # Retry transient service failures. ``max_retries`` is the number of
        # retries after the initial attempt.
        max_attempts = self.settings.nets.max_retries + 1
        profile_kwargs = {
            "organism": self.organism,
            "query": gene_symbols,
            "sources": sources,
            "user_threshold": fdr_threshold,
            "significance_threshold_method": "fdr",
            "no_evidences": False,
        }

        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    logger.info(
                        f"g:Profiler retry attempt {attempt + 1}/{max_attempts}"
                    )

                # The official client runs in a fresh process because its
                # requests.post call has no timeout and cannot be cancelled.
                results = _run_profile_in_subprocess(
                    profile_kwargs,
                    self.timeout_seconds,
                    self.base_url,
                )
                break

            except Exception as exc:
                error_msg = str(exc)
                if _is_transient_gprofiler_error(exc):
                    if attempt < max_attempts - 1:
                        wait_time = self.settings.nets.retry_backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"g:Profiler unavailable or timed out "
                            f"(attempt {attempt + 1}/{max_attempts}). "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            f"g:Profiler unavailable after {max_attempts} attempts"
                        )
                        message = (
                            "g:Profiler service temporarily unavailable or timed "
                            f"out after {max_attempts} attempts; no enrichment "
                            "result was produced."
                        )
                        if isinstance(exc, APITimeoutError):
                            raise APITimeoutError(message) from exc
                        raise APIClientError(message) from exc
                else:
                    # Deterministic request/schema and local worker failures do
                    # not improve with an identical retry.
                    logger.error(f"g:Profiler query failed: {error_msg}")
                    raise APIClientError(
                        f"g:Profiler query failed: {error_msg}"
                    ) from exc

        # Keep response validation outside the retry block. A schema/programming
        # error must not be retried merely because its text resembles an HTTP
        # status code.
        if not isinstance(results, list) or not all(
            isinstance(entry, dict) for entry in results
        ):
            raise APIClientError("g:Profiler returned an invalid result payload")
        try:
            pathways = self._parse_library_response(results, fdr_threshold)
        except Exception as exc:
            raise APIClientError(
                "g:Profiler returned a result that could not be parsed"
            ) from exc

        logger.info(
            f"Retrieved {len(pathways)} significant pathways from g:Profiler"
        )
        return pathways

    def close(self):
        """No persistent worker exists; each request reaps and closes its child."""
        return None
    
    def _parse_library_response(
        self,
        results: List[Dict[str, Any]],
        fdr_threshold: float
    ) -> List[PathwayEntry]:
        """
        Parse g:Profiler library response.
        
        Args:
            results: Results from official g:Profiler library
            fdr_threshold: FDR threshold for filtering
            
        Returns:
            List of PathwayEntry objects
        """
        pathways = []
        
        for entry in results:
            # Extract fields
            source = entry.get("source")
            term_id = entry.get("native")
            term_name = entry.get("name")
            p_value = entry.get("p_value")
            p_adj = entry.get("p_value")  # Already adjusted
            
            # Extract evidence genes - library returns actual gene symbols!
            intersection = entry.get("intersections", [])
            evidence_count = entry.get("intersection_size", len(intersection))
            
            # Skip if missing required fields
            if not all([source, term_id, term_name, p_value is not None]):
                logger.warning(f"Skipping entry with missing fields: {entry}")
                continue
            
            # Filter by FDR threshold
            if p_adj > fdr_threshold:
                continue
            
            # Map source to standard format
            source_db = self._map_source(source)
            
            # Create PathwayEntry. term_size/query_size/effective_domain_size are
            # carried through so fold enrichment (effect size) can be computed
            # downstream; ranking on the p-value alone favors large generic terms.
            pathway = PathwayEntry(
                pathway_id=term_id,
                pathway_name=term_name,
                source_db=source_db,
                p_value=p_value,
                p_adj=p_adj,
                evidence_count=evidence_count,
                evidence_genes=intersection,  # Actual gene symbols from library!
                term_size=entry.get("term_size"),
                query_size=entry.get("query_size"),
                effective_domain_size=entry.get("effective_domain_size"),
            )
            
            pathways.append(pathway)
        
        # Sort by adjusted p-value
        pathways.sort(key=lambda p: p.p_adj)
        
        return pathways
    
    def _map_source(self, source: str) -> str:
        """
        Map g:Profiler source to standard database name.
        
        Args:
            source: g:Profiler source identifier
            
        Returns:
            Standard database name
        """
        source_map = {
            "REAC": "REAC",
            "KEGG": "KEGG",
            "WP": "WP",
            "GO:BP": "GO:BP",
            "GO:MF": "GO:MF",
            "GO:CC": "GO:CC"
        }
        
        return source_map.get(source, source)
    
