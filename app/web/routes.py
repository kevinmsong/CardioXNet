"""Server-rendered HTML routes (no-build UI).

These routes render Jinja2 templates and reuse the existing JSON API handlers
(``validate_genes``, ``run_analysis``, ``get_analysis_results``) so there is a
single source of truth for validation, pipeline execution, and result assembly.
"""

import csv
import io
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.api import endpoints
from app.api.state import analysis_store
from app.models import AnalysisRequest, GeneValidationRequest
from app.web import constants, view_models

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

web_router = APIRouter(tags=["web"])

# Pipeline stage labels for the progress page checklist (ordered, with the
# approximate progress percentage at which each becomes active).
STAGE_TIMELINE = [
    (5, "Validating seed genes"),
    (15, "Assembling functional neighborhood (STRING)"),
    (25, "Primary pathway enrichment"),
    (40, "Secondary literature-driven expansion"),
    (55, "Aggregating & deduplicating pathways"),
    (70, "NES scoring"),
    (78, "Cardiac semantic filtering"),
    (85, "Comprehensive literature mining"),
    (91, "Network topology analysis"),
    (97, "Generating report"),
]


def _base_context(request: Request) -> dict:
    return {"request": request, "active": ""}


@web_router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    ctx = _base_context(request)
    ctx.update({
        "active": "home",
        "disease_options": constants.DISEASE_OPTIONS,
        "presets": constants.PRESETS,
        "default_preset": constants.DEFAULT_PRESET,
        "advanced_fields": constants.ADVANCED_FIELDS,
    })
    return templates.TemplateResponse("home.html", ctx)


@web_router.post("/ui/validate", response_class=HTMLResponse)
async def ui_validate(request: Request, genes: str = Form("")):
    """htmx fragment: validate pasted gene symbols and return a chip list."""
    symbols = [g.strip() for g in genes.replace(",", " ").split() if g.strip()]
    # de-duplicate, preserve order
    seen, unique = set(), []
    for s in symbols:
        if s.upper() not in seen:
            seen.add(s.upper())
            unique.append(s)
    result = None
    error = None
    if unique:
        try:
            resp = await endpoints.validate_genes(GeneValidationRequest(gene_ids=unique))
            result = resp.result.model_dump()
        except Exception as exc:  # pragma: no cover - surfaced to the user
            logger.warning("Gene validation failed: %s", exc)
            error = str(exc)
    ctx = _base_context(request)
    ctx.update({"result": result, "error": error, "submitted": unique})
    return templates.TemplateResponse("_validation.html", ctx)


@web_router.post("/ui/analyze")
async def ui_analyze(
    request: Request,
    background_tasks: BackgroundTasks,
    genes: str = Form(""),
    disease_context: str = Form(""),
    preset: str = Form(constants.DEFAULT_PRESET),
):
    """Start an analysis from the home form and redirect to the progress page."""
    form = await request.form()
    symbols = [g.strip() for g in genes.replace(",", " ").split() if g.strip()]
    if not symbols:
        return RedirectResponse(url="/", status_code=303)

    # Collect any advanced numeric overrides that were submitted.
    overrides = {}
    for key, _label, _mn, _mx, _step in constants.ADVANCED_FIELDS:
        raw = form.get(key)
        if raw not in (None, ""):
            try:
                overrides[key] = float(raw) if ("." in str(raw) or key.endswith("threshold")) else int(raw)
            except (TypeError, ValueError):
                pass
    config_overrides = constants.build_config(preset, overrides)

    req = AnalysisRequest(
        seed_genes=symbols,
        disease_context=disease_context or None,
        config_overrides=config_overrides,
    )
    resp = await endpoints.run_analysis(req, background_tasks)
    return RedirectResponse(url=f"/progress/{resp.analysis_id}", status_code=303)


def _status(analysis_id: str) -> Optional[dict]:
    analysis = analysis_store.get_analysis(analysis_id)
    if not analysis:
        analysis_store._load_existing_analyses()
        analysis = analysis_store.get_analysis(analysis_id)
    return analysis


@web_router.get("/progress/{analysis_id}", response_class=HTMLResponse)
async def progress_page(request: Request, analysis_id: str):
    analysis = _status(analysis_id)
    if analysis and analysis.get("status") == "completed":
        return RedirectResponse(url=f"/results/{analysis_id}", status_code=303)
    ctx = _base_context(request)
    ctx.update({
        "active": "",
        "analysis_id": analysis_id,
        "analysis": analysis,
        "timeline": STAGE_TIMELINE,
    })
    return templates.TemplateResponse("progress.html", ctx)


@web_router.get("/progress/{analysis_id}/fragment", response_class=HTMLResponse)
async def progress_fragment(request: Request, analysis_id: str):
    analysis = _status(analysis_id)
    ctx = _base_context(request)
    ctx.update({
        "analysis_id": analysis_id,
        "analysis": analysis,
        "timeline": STAGE_TIMELINE,
    })
    headers = {}
    if analysis and analysis.get("status") == "completed":
        # htmx will navigate the browser to the results page.
        headers["HX-Redirect"] = f"/results/{analysis_id}"
    return templates.TemplateResponse("_progress.html", ctx, headers=headers)


async def _load_results_dump(analysis_id: str):
    """Return (status, results_dump) reusing the JSON endpoint's normalization.

    status is one of: 'ok', 'not_found', 'not_completed'.
    """
    from fastapi import HTTPException
    try:
        resp = await endpoints.get_analysis_results(analysis_id)
        return "ok", resp.model_dump()
    except HTTPException as exc:
        if exc.status_code == 404:
            return "not_found", None
        return "not_completed", None


@web_router.get("/results/{analysis_id}", response_class=HTMLResponse)
async def results_page(request: Request, analysis_id: str):
    status, dump = await _load_results_dump(analysis_id)
    if status == "not_completed":
        return RedirectResponse(url=f"/progress/{analysis_id}", status_code=303)
    if status == "not_found":
        ctx = _base_context(request)
        ctx.update({"message": f"Analysis '{analysis_id}' was not found.", "analysis_id": analysis_id})
        return templates.TemplateResponse("not_found.html", ctx, status_code=404)

    rows = view_models.hypothesis_rows(dump)
    ctx = _base_context(request)
    ctx.update({
        "analysis_id": analysis_id,
        "results": dump,
        "rows": rows,
        "summary": view_models.summary_stats(dump, rows),
        "network": view_models.cytoscape_elements(dump),
        "top_genes": dump.get("top_genes") or [],
        "report_urls": dump.get("report_urls") or {},
    })
    return templates.TemplateResponse("results.html", ctx)


@web_router.get("/results/{analysis_id}/export.csv")
async def results_csv(analysis_id: str):
    status, dump = await _load_results_dump(analysis_id)
    if status != "ok":
        return RedirectResponse(url=f"/results/{analysis_id}", status_code=303)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(view_models.csv_rows(dump))
    buf.seek(0)
    filename = f"cardioxnet_results_{analysis_id}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@web_router.get("/results/{analysis_id}/pathway/{pathway_id:path}", response_class=HTMLResponse)
async def pathway_detail(request: Request, analysis_id: str, pathway_id: str):
    status, dump = await _load_results_dump(analysis_id)
    if status != "ok":
        return RedirectResponse(url=f"/progress/{analysis_id}", status_code=303)
    hyp = view_models.find_hypothesis(dump, pathway_id)
    if not hyp:
        ctx = _base_context(request)
        ctx.update({"message": f"Pathway '{pathway_id}' not found in this analysis.",
                    "analysis_id": analysis_id})
        return templates.TemplateResponse("not_found.html", ctx, status_code=404)

    seed_symbols = {g.get("symbol") for g in (dump.get("seed_genes") or []) if g.get("symbol")}
    citations = sorted(
        hyp.get("citations") or [],
        key=lambda c: (c.get("relevance_score") or 0.0),
        reverse=True,
    )
    ctx = _base_context(request)
    ctx.update({
        "analysis_id": analysis_id,
        "hyp": hyp,
        "lineage": hyp.get("lineage") or {},
        "score_components": hyp.get("score_components") or {},
        "citations": citations,
        "seed_symbols": seed_symbols,
        "is_novel": view_models._is_seed_independent(hyp, seed_symbols),
    })
    return templates.TemplateResponse("pathway_detail.html", ctx)


@web_router.get("/documentation", response_class=HTMLResponse)
async def documentation(request: Request):
    ctx = _base_context(request)
    ctx["active"] = "documentation"
    return templates.TemplateResponse("documentation.html", ctx)


@web_router.get("/api-reference", response_class=HTMLResponse)
async def api_reference(request: Request):
    ctx = _base_context(request)
    ctx["active"] = "api"
    return templates.TemplateResponse("api_reference.html", ctx)
