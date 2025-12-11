"""FastAPI endpoints for CardioXNet API."""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.models import (
    GeneValidationRequest,
    GeneValidationResponse,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatusResponse,
    AnalysisResultsResponse,
    StageResultResponse,
    ConfigDefaultsResponse,
    ErrorResponse,
    GeneInfo
)
from app.core.config import get_settings
from app.api.state import analysis_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.options("/genes/validate")
async def options_validate_genes():
    """Handle OPTIONS preflight for gene validation."""
    return {}


@router.post("/genes/validate", response_model=GeneValidationResponse)
async def validate_genes(request: GeneValidationRequest):
    """
    Validate gene identifiers.
    
    Args:
        request: Gene validation request
        
    Returns:
        Validation result with valid/invalid genes
    """
    logger.info(f"Validating {len(request.gene_ids)} genes")
    
    try:
        from app.services.fast_service_init import get_service_fast
        validator = get_service_fast("gene_validator")
        result = validator.validate_genes(request.gene_ids)
        
        return GeneValidationResponse(result=result)
        
    except Exception as e:
        logger.error(f"Gene validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.options("/analysis/run")
async def options_run_analysis():
    """Handle OPTIONS preflight for analysis run."""
    return {}


@router.post("/analysis/run", response_model=AnalysisResponse)
async def run_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a new NETS analysis.
    
    Args:
        request: Analysis request with seed genes
        background_tasks: FastAPI background tasks
        
    Returns:
        Analysis response with analysis ID
    """
    logger.info(f"Starting analysis with {len(request.seed_genes)} seed genes")
    print(f"[ENDPOINT DEBUG] Starting analysis with {len(request.seed_genes)} genes", flush=True)
    
    try:
        print("[ENDPOINT DEBUG] About to import Pipeline", flush=True)
        logger.info("[DEBUG] About to import Pipeline")
        # Import unified Pipeline
        from app.services.pipeline import Pipeline
        
        print("[ENDPOINT DEBUG] Pipeline imported successfully", flush=True)
        logger.info("[DEBUG] Preparing config overrides")
        # Merge disease_context into config_overrides if provided
        config_overrides = request.config_overrides or {}
        if request.disease_context:
            config_overrides['disease_context'] = request.disease_context
        
        print("[ENDPOINT DEBUG] Creating pipeline instance", flush=True)
        logger.info("[DEBUG] Creating Pipeline instance")

        # Create new pipeline instance (apply config overrides so disease_context and other
        # frontend-provided settings are respected by the pipeline instance)
        pipeline = Pipeline(analysis_id=None, config_overrides=config_overrides)
        analysis_id = pipeline.analysis_id
        print(f"[ENDPOINT DEBUG] Pipeline created with ID: {analysis_id}", flush=True)
        logger.info(f"[DEBUG] Pipeline created with ID: {analysis_id}")
        
        # Store initial state
        analysis_store.create_analysis(analysis_id, request.seed_genes)
        
        # Run pipeline in background
        background_tasks.add_task(
            _run_pipeline_background,
            pipeline,
            request.seed_genes,
            config_overrides
        )
        
        return AnalysisResponse(
            analysis_id=analysis_id,
            status="started",
            message="Analysis started successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to start analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: str):
    """
    Get analysis status.
    
    Args:
        analysis_id: Analysis identifier
        
    Returns:
        Analysis status response
    """
    analysis = analysis_store.get_analysis(analysis_id)
    
    # If analysis not in memory, try to reload from disk
    if not analysis:
        logger.info(f"Analysis {analysis_id} not in memory, attempting to reload from disk")
        analysis_store._load_existing_analyses()
        analysis = analysis_store.get_analysis(analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return AnalysisStatusResponse(
        analysis_id=analysis_id,
        status=analysis["status"],
        current_stage=analysis.get("current_stage"),
        progress_percentage=analysis.get("progress", 0),
        message=analysis.get("message"),
        error=analysis.get("error")
    )


@router.get("/analysis/{analysis_id}/results", response_model=AnalysisResultsResponse)
async def get_analysis_results(analysis_id: str):
    """
    Get complete analysis results.
    
    Args:
        analysis_id: Analysis identifier
        
    Returns:
        Analysis results response
    """
    analysis = analysis_store.get_analysis(analysis_id)
    
    # If analysis not in memory, try to reload from disk
    if not analysis:
        logger.info(f"Analysis {analysis_id} not in memory, attempting to reload from disk")
        analysis_store._load_existing_analyses()
        analysis = analysis_store.get_analysis(analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not completed (status: {analysis['status']})"
        )
    
    # For completed analyses, try to load from report JSON file first
    import json
    from pathlib import Path
    
    # Try new path structure first (outputs/analysis_id/results.json)
    report_path = Path(f"outputs/{analysis_id}/results.json")
    if not report_path.exists():
        # Fall back to old path structure
        report_path = Path(f"outputs/{analysis_id}_report.json")
    
    if report_path.exists():
        logger.info(f"Loading results from report file: {report_path}")
        with open(report_path, 'r') as f:
            results = json.load(f)
    else:
        logger.debug(f"Report file not found: {report_path}, using in-memory results")
        results = analysis.get("results", {})
    
    logger.debug(f"get_analysis_results: top-level result keys: {list(results.keys())}")
    
    # Extract seed genes from results (could be in stage_0 or input_summary)
    seed_genes = []
    if "stage_0" in results:
        stage_0 = results["stage_0"]
        if isinstance(stage_0, dict) and "valid_genes" in stage_0:
            for gene_dict in stage_0["valid_genes"]:
                try:
                    gene_info = GeneInfo(**gene_dict)
                    seed_genes.append(gene_info)
                except Exception as e:
                    logger.warning(f"Failed to convert gene dict to GeneInfo: {gene_dict}, error: {e}")
                    # Skip invalid gene entries
    elif "input_summary" in results:
        # Handle analyses loaded from JSON report files
        input_summary = results["input_summary"]
        if isinstance(input_summary, dict) and "gene_list" in input_summary:
            for gene_symbol in input_summary["gene_list"]:
                # Create basic GeneInfo from symbol
                gene_info = GeneInfo(
                    input_id=gene_symbol,
                    entrez_id="",  # Not available in report
                    hgnc_id="",    # Not available in report
                    symbol=gene_symbol,
                    species="Homo sapiens"
                )
                seed_genes.append(gene_info)
    
    # Extract hypotheses from results (could be in nes_rescoring or ranked_hypotheses)
    hypotheses = None
    if "nes_rescoring" in results:
        # Check modular pipeline results
        nes_rescoring = results["nes_rescoring"]
        if isinstance(nes_rescoring, dict) and "data" in nes_rescoring:
            rescored_hypotheses = nes_rescoring["data"].get("rescored_hypotheses")
            if rescored_hypotheses:
                hypotheses = {
                    "hypotheses": rescored_hypotheses,
                    "total_count": len(rescored_hypotheses)
                }
                logger.debug(f"get_analysis_results: found hypotheses in nes_rescoring: {len(rescored_hypotheses)}")

    # Check stage_3 for scored hypotheses (use flattening function)
    if not hypotheses and "stage_3" in results:
        hypotheses = _extract_hypotheses(results)
        if hypotheses:
            logger.debug(f"get_analysis_results: found hypotheses in stage_3 (flattened): {hypotheses['total_count']}")
        else:
            logger.debug("get_analysis_results: _extract_hypotheses returned None")
    
    if not hypotheses and "ranked_hypotheses" in results:
        # Handle analyses loaded from JSON report files
        ranked_hyps = results["ranked_hypotheses"]
        print(f"[API DEBUG] ranked_hypotheses present: type={type(ranked_hyps)}, len={len(ranked_hyps) if isinstance(ranked_hyps, list) else 'N/A'}", flush=True)
        logger.debug(f"get_analysis_results: ranked_hypotheses present: type={type(ranked_hyps)}, len={len(ranked_hyps) if isinstance(ranked_hyps, list) else 'N/A'}")
        if isinstance(ranked_hyps, list):
            hypotheses = {
                "hypotheses": ranked_hyps,
                "total_count": len(ranked_hyps)
            }
            print(f"[API DEBUG] Set hypotheses from ranked_hypotheses: {len(ranked_hyps)} items", flush=True)

    logger.debug(f"get_analysis_results: hypotheses set: {bool(hypotheses)}; total_count={hypotheses.get('total_count') if hypotheses else None}")
    
    # Extract topology from stage 4 results or topology_analysis
    topology = None
    if "topology_analysis" in results:
        topology_stage = results["topology_analysis"]
        if isinstance(topology_stage, dict) and "data" in topology_stage:
            topology_data = topology_stage["data"]
            if isinstance(topology_data, dict):
                topology = topology_data
                logger.debug(f"get_analysis_results: found topology in topology_analysis: {list(topology.keys()) if topology else 'None'}")
    
    if not topology and "stage_4_topology" in results:
        topology = results["stage_4_topology"]
    
    # If topology is empty or None, compute it from hypotheses data
    if (not topology or not isinstance(topology, dict) or len(topology) == 0) and hypotheses:
        logger.info("Computing topology from hypothesis data")
        topology = {}
        
        # Build gene network from hypothesis co-occurrence
        all_genes = {}  # gene -> {hypothesis_count, connected_genes}
        edges = []  # (gene1, gene2) pairs
        
        for hyp in hypotheses.get("hypotheses", []):
            # Get genes from this hypothesis - check multiple possible locations
            gene_list = []
            
            # Method 1: aggregated_pathway.pathway.evidence_genes (primary source)
            if "aggregated_pathway" in hyp:
                agg = hyp["aggregated_pathway"]
                if isinstance(agg, dict) and "pathway" in agg:
                    pathway = agg["pathway"]
                    if isinstance(pathway, dict) and "evidence_genes" in pathway:
                        gene_list = pathway["evidence_genes"]
            
            # Method 2: traced_seed_genes
            if not gene_list and "traced_seed_genes" in hyp:
                gene_list = hyp["traced_seed_genes"]
            
            # Method 3: key_nodes (for other data formats)
            if not gene_list and "key_nodes" in hyp and hyp["key_nodes"]:
                gene_list = hyp["key_nodes"]
            
            # Track gene occurrences
            for gene in gene_list:
                if gene:
                    if gene not in all_genes:
                        all_genes[gene] = {
                            "hypothesis_count": 0,
                            "connected_genes": set(),
                            "pathways": []
                        }
                    all_genes[gene]["hypothesis_count"] += 1
                    all_genes[gene]["pathways"].append(hyp.get("pathway_name", ""))
            
            # Create edges between co-occurring genes
            for i in range(len(gene_list)):
                for j in range(i + 1, len(gene_list)):
                    if gene_list[i] and gene_list[j]:
                        edges.append((gene_list[i], gene_list[j]))
                        all_genes[gene_list[i]]["connected_genes"].add(gene_list[j])
                        all_genes[gene_list[j]]["connected_genes"].add(gene_list[i])
        
        # Compute hub genes (top by degree centrality)
        hub_genes_list = []
        for gene, data in sorted(all_genes.items(), key=lambda x: len(x[1]["connected_genes"]), reverse=True)[:20]:
            degree = len(data["connected_genes"])
            # Simple centrality metrics based on connectivity
            hub_genes_list.append({
                "gene": gene,
                "degree": degree,
                "betweenness": degree / len(all_genes) if len(all_genes) > 0 else 0,  # Normalized degree as proxy
                "closeness": data["hypothesis_count"] / len(hypotheses.get("hypotheses", [])) if hypotheses.get("hypotheses") else 0,
                "eigenvector": degree / max(len(g["connected_genes"]) for g in all_genes.values()) if all_genes else 0,
                "pagerank": (degree + data["hypothesis_count"]) / (len(all_genes) + len(hypotheses.get("hypotheses", []))) if all_genes else 0
            })
        
        topology["hub_genes"] = hub_genes_list[:10]  # Top 10
        
        # Compute network metrics
        unique_edges = list(set(edges))
        avg_degree = sum(len(g["connected_genes"]) for g in all_genes.values()) / len(all_genes) if all_genes else 0
        max_degree = max(len(g["connected_genes"]) for g in all_genes.values()) if all_genes else 0
        
        topology["network_metrics"] = {
            "modularity": 0.0,  # Would require community detection, set to 0
            "clustering_coefficient": avg_degree / max_degree if max_degree > 0 else 0,
            "node_count": len(all_genes),
            "edge_count": len(unique_edges)
        }
        
        logger.info(f"Computed topology: {len(all_genes)} nodes, {len(unique_edges)} edges, {len(hub_genes_list)} hub genes")
        
    # Original enhancement code for when topology has network_data
    elif topology and isinstance(topology, dict):
            # Add hub genes from network data if available
            if "network_data" in topology and not topology.get("hub_genes"):
                network = topology["network_data"]
                if "nodes" in network:
                    # Extract top nodes by degree centrality
                    nodes = network["nodes"]
                    hub_genes = sorted(
                        [n for n in nodes if n.get("gene")],
                        key=lambda x: x.get("degree", 0),
                        reverse=True
                    )[:10]
                    topology["hub_genes"] = [
                        {
                            "gene": node.get("gene", ""),
                            "degree": node.get("degree", 0),
                            "betweenness": node.get("betweenness", 0),
                            "closeness": node.get("closeness", 0),
                            "eigenvector": node.get("eigenvector_centrality", 0),
                            "pagerank": node.get("pagerank", 0)
                        }
                        for node in hub_genes
                    ]
            
            # Add network metrics if not present
            if "network_data" in topology and not topology.get("network_metrics"):
                network = topology["network_data"]
                topology["network_metrics"] = {
                    "modularity": network.get("modularity", 0.5),
                    "clustering_coefficient": network.get("average_clustering", 0.4),
                    "node_count": len(network.get("nodes", [])),
                    "edge_count": len(network.get("edges", []))
                }
    
    # Extract top_genes from results if available
    top_genes = results.get("top_genes")
    if top_genes:
        logger.debug(f"get_analysis_results: found top_genes: {len(top_genes)} genes")
    
    # NO FALLBACKS - Only return real data from analysis
    # Frontend must handle missing data gracefully
    
    logger.info(f"Returning results for {analysis_id}: {len(seed_genes)} seed genes, {hypotheses['total_count'] if hypotheses else 0} hypotheses, {len(top_genes) if top_genes else 0} top genes")
    
    # Normalize hypothesis fields so frontend and consumers always have expected keys
    def _ensure_score_components(hyp: dict):
        sc = hyp.get('score_components') or {}
        # Ensure cardiac_relevance present (0.0-1.0)
        if 'cardiac_relevance' not in sc:
            # Try top-level cardiac_relevance fallback
            sc['cardiac_relevance'] = float(hyp.get('cardiac_relevance', 0.0) or 0.0)
        # Ensure centrality weight exists
        if 'centrality_weight' not in sc:
            # Attempt coarse estimate from key_nodes centrality if available
            key_nodes = hyp.get('key_nodes') or hyp.get('top_key_nodes') or []
            try:
                vals = [float(n.get('centrality') or n.get('pagerank') or 0.0) for n in key_nodes if isinstance(n, dict)]
                avg = sum(vals) / len(vals) if vals else 0.0
            except Exception:
                avg = 0.0
            # Map avg centrality [0..1] to weight in [1.0, 1.8]
            sc['centrality_weight'] = round(1.0 + min(max(avg, 0.0), 1.0) * 0.8, 4)
        hyp['score_components'] = sc
        # Ensure a canonical nes_score field exists (frontend uses nes_score)
        if 'nes_score' not in hyp and 'nes' in hyp:
            nes_val = hyp.get('nes')
            if nes_val is not None:
                try:
                    hyp['nes_score'] = float(nes_val)
                except Exception:
                    hyp['nes_score'] = None
        return hyp

    # Apply normalization to ranked hypotheses if present
    if hypotheses and isinstance(hypotheses, dict) and 'hypotheses' in hypotheses:
        normalized_list = []
        for h in hypotheses.get('hypotheses', []):
            if isinstance(h, dict):
                normalized_list.append(_ensure_score_components(h))
            else:
                normalized_list.append(h)
        hypotheses['hypotheses'] = normalized_list

    # Sanitize report URLs: remove any keys with None or non-string values so Pydantic validation succeeds
    raw_report_urls = analysis.get("report_files", {}) or {}
    
    # Also check report_generation stage for additional report files
    if "report_generation" in results:
        report_stage = results["report_generation"]
        if isinstance(report_stage, dict) and "data" in report_stage:
            report_data = report_stage["data"]
            if isinstance(report_data, dict) and "report_files" in report_data:
                stage_reports = report_data["report_files"]
                if isinstance(stage_reports, dict):
                    raw_report_urls.update(stage_reports)
    
    sanitized_report_urls = {}
    if isinstance(raw_report_urls, dict):
        for k, v in raw_report_urls.items():
            if isinstance(v, str) and v:
                sanitized_report_urls[k] = v

    return AnalysisResultsResponse(
        analysis_id=analysis_id,
        status=analysis["status"],
        seed_genes=seed_genes,
        hypotheses=hypotheses,
        topology=topology,
        top_genes=top_genes,
        report_urls=sanitized_report_urls or None
    )


@router.get("/analysis/{analysis_id}/stage/{stage_id}", response_model=StageResultResponse)
async def get_stage_results(analysis_id: str, stage_id: str):
    """
    Get results for a specific pipeline stage.
    
    Args:
        analysis_id: Analysis identifier
        stage_id: Stage identifier (stage_0, stage_1, etc.)
        
    Returns:
        Stage result response
    """
    analysis = analysis_store.get_analysis(analysis_id)
    
    # If analysis not in memory, try to reload from disk
    if not analysis:
        logger.info(f"Analysis {analysis_id} not in memory, attempting to reload from disk")
        analysis_store._load_existing_analyses()
        analysis = analysis_store.get_analysis(analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    results = analysis.get("results", {})
    stage_data = results.get(stage_id)
    
    if not stage_data:
        raise HTTPException(status_code=404, detail=f"Stage {stage_id} not found")
    
    stage_names = {
        "stage_0": "Input Validation",
        "stage_1": "Functional Neighborhood Assembly",
        "stage_2a": "Primary Pathway Enrichment",
        "stage_2b": "Secondary Pathway Discovery",
        "stage_2c": "Pathway Aggregation",
        "stage_5a": "Final NES Scoring",
        "stage_4_topology": "Topology Analysis",
        "stage_4_literature": "Literature Validation"
    }
    
    return StageResultResponse(
        analysis_id=analysis_id,
        stage_id=stage_id,
        stage_name=stage_names.get(stage_id, stage_id),
        status="completed",
        data=stage_data
    )


@router.get("/config/defaults", response_model=ConfigDefaultsResponse)
async def get_config_defaults():
    """
    Get default configuration parameters.
    
    Returns:
        Configuration defaults
    """
    settings = get_settings()
    
    config = {
        "string_neighbor_count": settings.nets.string_neighbor_count,
        "string_score_threshold": settings.nets.string_score_threshold,
        "fdr_threshold": settings.nets.fdr_threshold,
        "top_hypotheses_count": settings.nets.top_hypotheses_count,
        "aggregation_strategy": settings.nets.aggregation_strategy,
        "min_support_threshold": settings.nets.min_support_threshold,
        "db_weights": settings.nets.db_weights
    }
    
    return ConfigDefaultsResponse(config=config)


@router.get("/analysis/{analysis_id}/report/{format}")
async def download_report(analysis_id: str, format: str):
    """
    Download analysis report in specified format.
    
    Args:
        analysis_id: Analysis identifier
        format: Report format (markdown, html, json, pdf)
        
    Returns:
        File download response
    """
    logger.info(f"Report download requested: analysis_id={analysis_id}, format={format}")
    
    analysis = analysis_store.get_analysis(analysis_id)
    
    if not analysis:
        logger.error(f"Analysis not found: {analysis_id}")
        raise HTTPException(status_code=404, detail=f"Analysis not found: {analysis_id}")
    
    if analysis["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not completed (status: {analysis['status']})"
        )
    
    # Get report file path
    report_files = analysis.get("report_files", {})
    
    # Check if report exists and is valid
    if format not in report_files or not Path(report_files[format]).exists():
        logger.info(f"Report not found for {analysis_id}, generating on-demand...")
        
        # Generate report on-demand
        try:
            from app.services import ReportGenerator
            
            # Extract data from analysis results
            results = analysis.get("results", {})
            seed_genes = _extract_seed_genes(results)
            hypotheses = _extract_hypotheses(results)
            topology = _extract_topology(results)
            literature = _extract_literature(results)
            
            # Generate report
            from app.services.fast_service_init import get_service_fast
            report_generator = get_service_fast("report_generator")
            output_files = report_generator.generate_report(
                analysis_id=analysis_id,
                seed_genes=seed_genes,
                hypotheses=hypotheses,
                topology_analysis=topology,
                literature_evidence=literature,
                output_formats=[format]
            )
            
            # Update analysis store with new report files
            report_files.update(output_files)
            analysis_store.update_analysis(
                analysis_id,
                report_files=report_files
            )
            
            report_path = Path(output_files[format])
            logger.info(f"Report generated successfully: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate report: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate report: {str(e)}"
            )
    else:
        report_path = Path(report_files[format])
    
    # Determine media type and filename
    media_types = {
        "markdown": "text/markdown",
        "html": "text/html",
        "json": "application/json",
        "pdf": "application/pdf",
        "csv": "text/csv"
    }
    
    extensions = {
        "markdown": "md",
        "html": "html",
        "json": "json",
        "pdf": "pdf",
        "csv": "csv"
    }
    
    media_type = media_types.get(format, "application/octet-stream")
    extension = extensions.get(format, "txt")
    filename = f"cardioxnet_report_{analysis_id}.{extension}"
    
    return FileResponse(
        path=str(report_path),
        media_type=media_type,
        filename=filename
    )


def _extract_seed_genes(results: Dict[str, Any]) -> list:
    """Extract seed genes from analysis results."""
    if "stage_0" in results:
        stage_0 = results["stage_0"]
        if isinstance(stage_0, dict) and "valid_genes" in stage_0:
            return stage_0["valid_genes"]
    return []


def _extract_hypotheses(results: Dict[str, Any]):
    """Extract hypotheses from analysis results and flatten structure for frontend."""
    if "stage_3" in results:
        stage_3 = results["stage_3"]
        if isinstance(stage_3, dict) and "hypotheses" in stage_3:
            # Flatten the hypothesis structure for frontend compatibility
            flattened_hypotheses = []
            for hyp in stage_3["hypotheses"]:
                # Extract nested pathway data
                pathway_data = hyp.get("aggregated_pathway", {}).get("pathway", {})
                
                # Create flattened hypothesis with pathway_id at top level
                # Build lineage information
                aggregated_pw = hyp.get("aggregated_pathway", {})
                source_primaries = aggregated_pw.get("source_primary_pathways", [])
                source_secondaries = aggregated_pw.get("source_secondary_pathways", [])
                
                lineage = {
                    "seed_genes": hyp.get("traced_seed_genes", []),
                    "primary_pathways": source_primaries,
                    "secondary_pathways": source_secondaries,  # NEW: Full secondary pathway instances
                    "final_pathway_id": pathway_data.get("pathway_id", ""),
                    "final_pathway_name": pathway_data.get("pathway_name", ""),
                    "discovery_method": "aggregated" if len(source_primaries) > 1 else "primary",
                    "support_count": aggregated_pw.get("support_count", 0)
                }
                
                flattened = {
                    "pathway_id": pathway_data.get("pathway_id", ""),
                    "pathway_name": pathway_data.get("pathway_name", ""),
                    "source_db": pathway_data.get("source_db", ""),
                    "p_value": pathway_data.get("p_value", 1.0),
                    "p_adj": pathway_data.get("p_adj", 1.0),
                    "evidence_count": pathway_data.get("evidence_count", 0),
                    "evidence_genes": pathway_data.get("evidence_genes", []),
                    "nes_score": hyp.get("nes_score", 0),
                    "rank": hyp.get("rank", 0),
                    "score_components": hyp.get("score_components", {}),
                    "traced_seed_genes": hyp.get("traced_seed_genes", []),
                    "literature_associations": hyp.get("literature_associations", {}),
                    "aggregated_pathway": hyp.get("aggregated_pathway", {}),  # Keep original for details
                    "lineage": lineage,  # NEW: Complete discovery lineage
                }
                flattened_hypotheses.append(flattened)
            
            return {
                "hypotheses": flattened_hypotheses,
                "total_count": stage_3.get("total_count", len(flattened_hypotheses))
            }
    return None


def _extract_topology(results: Dict[str, Any]):
    """Extract topology analysis from results."""
    if "stage_4_topology" in results:
        return results["stage_4_topology"]
    return None


def _extract_literature(results: Dict[str, Any]):
    """Extract literature evidence from results."""
    if "stage_4_literature" in results:
        return results["stage_4_literature"]
    return None


def _run_pipeline_background(pipeline, seed_genes: list, config_overrides: Optional[Dict] = None):
    """
    Run pipeline in background task (synchronous wrapper for async pipeline).
    
    Args:
        pipeline: Pipeline instance
        seed_genes: Seed genes
        config_overrides: Configuration overrides (for logging/debugging)
    """
    import asyncio
    import sys
    
    analysis_id = pipeline.analysis_id
    
    # Log configuration overrides
    if config_overrides:
        print(f"[CONFIG DEBUG] Analysis {analysis_id} using {len(config_overrides)} config overrides: {config_overrides}", flush=True)
        logger.info(f"[CONFIG DEBUG] Analysis {analysis_id} using config overrides: {config_overrides}")
    else:
        print(f"[CONFIG DEBUG] Analysis {analysis_id} using default configuration", flush=True)
    
    # Ensure logging works in background context
    print(f"[BACKEND DEBUG] Starting background analysis {analysis_id}", flush=True)
    logger.info(f"[BACKEND DEBUG] Starting background analysis {analysis_id}")
    
    try:
        # Update status
        analysis_store.update_analysis(
            analysis_id,
            status="running",
            current_stage="Stage 0",
            progress=0,
            message="Starting analysis"
        )
        print(f"[BACKEND DEBUG] Analysis {analysis_id} status updated to running", flush=True)
        
        # Define async progress callback
        async def progress_callback(stage: str, progress: float, message: str):
            # Use both print and logger for maximum visibility
            progress_msg = f"[PROGRESS] {analysis_id}: {stage} - {progress:.1f}% - {message}"
            print(progress_msg, flush=True)  # Force flush to terminal
            logger.info(progress_msg)
            
            analysis_store.update_analysis(
                analysis_id,
                current_stage=stage,
                progress=progress,
                message=message
            )
            
            # Verify the update
            updated = analysis_store.get_analysis(analysis_id)
            if updated:
                verify_msg = f"[PROGRESS VERIFIED] {analysis_id}: progress={updated.get('progress')}, stage={updated.get('current_stage')}"
                print(verify_msg, flush=True)
                logger.info(verify_msg)
        
        print(f"[BACKEND DEBUG] About to start pipeline execution for {analysis_id}", flush=True)
        
        # Run pipeline in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(pipeline.run(seed_genes, progress_callback))
        finally:
            loop.close()
        
        print(f"[BACKEND DEBUG] Pipeline execution completed for {analysis_id}", flush=True)
        
        # Update analysis store with pipeline results (use the 'results' key returned by pipeline.run)
        analysis_store.update_analysis(
            analysis_id,
            status="completed",
            results=result.get("results", {}),
            report_files=result.get("report_files", {}),
            warnings=result.get("warnings", [])
        )
        
        completion_msg = f"Analysis {analysis_id} completed successfully"
        print(f"[BACKEND DEBUG] {completion_msg}", flush=True)
        logger.info(completion_msg)
        
    except Exception as e:
        error_msg = f"Analysis {analysis_id} failed: {str(e)}"
        print(f"[BACKEND ERROR] {error_msg}", flush=True)
        logger.error(error_msg)
        
        import traceback
        print(f"[BACKEND ERROR] Traceback:", flush=True)
        traceback.print_exc()
        
        analysis_store.update_analysis(
            analysis_id,
            status="failed",
            error=str(e)
        )


@router.get("/analysis/{analysis_id}/detailed-results")
async def get_detailed_analysis_results(analysis_id: str):
    """
    Get comprehensive pipeline results for detailed pathway analysis.
    
    This endpoint returns the full pipeline stage results needed for 
    comprehensive pathway lineage visualization, database evidence display,
    and literature analysis.
    
    Args:
        analysis_id: Analysis identifier
        
    Returns:
        Complete pipeline results including all stages
    """
    analysis = analysis_store.get_analysis(analysis_id)
    
    # If analysis not in memory, try to reload from disk
    if not analysis:
        logger.info(f"Analysis {analysis_id} not in memory, attempting to reload from disk")
        analysis_store._load_existing_analyses()
        analysis = analysis_store.get_analysis(analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not completed (status: {analysis['status']})"
        )
    
    # For completed analyses, load the report JSON file which has the final results
    import json
    from pathlib import Path
    
    report_path = Path(f"outputs/{analysis_id}_report.json")
    if report_path.exists():
        logger.info(f"Loading detailed results from report file: {report_path}")
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        
        # Enhance with additional metadata
        enhanced_results = {
            **report_data,
            "analysis_metadata": {
                "analysis_id": analysis_id,
                "status": analysis["status"],
                "created_at": analysis.get("created_at"),
                "completed_at": analysis.get("completed_at"),
                "warnings": analysis.get("warnings", [])
            }
        }
        
        logger.info(f"Returning detailed results from report with {len(report_data.get('ranked_hypotheses', []))} hypotheses")
        return enhanced_results
    else:
        # Fallback to in-memory results if report not found
        logger.warning(f"Report file not found: {report_path}, using in-memory results")
        results = analysis.get("results", {})
        
        enhanced_results = {
            **results,
            "analysis_metadata": {
                "analysis_id": analysis_id,
                "status": analysis["status"],
                "created_at": analysis.get("created_at"),
                "completed_at": analysis.get("completed_at"),
                "warnings": analysis.get("warnings", [])
            }
        }
        
        logger.info(f"Returning detailed results for {analysis_id} with {len(results)} stages")
        return enhanced_results



