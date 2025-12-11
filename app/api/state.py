"""Analysis state management."""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)


class AnalysisStore:
    """In-memory storage for analysis state."""
    
    def __init__(self):
        """Initialize analysis store."""
        self.analyses: Dict[str, Dict[str, Any]] = {}
        self.lock = Lock()
        
        # Load existing analyses from outputs directory
        self._load_existing_analyses()
        
        logger.info(f"AnalysisStore initialized with {len(self.analyses)} existing analyses")
    
    def _load_existing_analyses(self):
        """Load existing analyses from outputs directory."""
        try:
            outputs_dir = Path("outputs")
            if not outputs_dir.exists():
                logger.info("No outputs directory found, starting with empty analysis store")
                return
            
            # Look for analysis directories and report files
            analysis_dirs = [d for d in outputs_dir.iterdir() if d.is_dir() and d.name.startswith("analysis_")]
            
            for analysis_dir in analysis_dirs:
                analysis_id = analysis_dir.name
                
                # Try to load the results.json file first (has full pipeline data)
                results_file = analysis_dir / "results.json"
                report_file = outputs_dir / f"{analysis_id}_report.json"
                
                results_data = None
                seed_genes = []
                timestamp = None
                
                # Prefer results.json for full pipeline data with GTEx
                if results_file.exists():
                    try:
                        with open(results_file, 'r') as f:
                            results_data = json.load(f)
                        
                        # Extract seed genes from stage_0
                        stage_0 = results_data.get("stage_0", {})
                        valid_genes = stage_0.get("valid_genes", [])
                        seed_genes = [g.get("symbol", g.get("input_id", "")) for g in valid_genes]
                        
                        logger.info(f"Loaded full results from results.json for {analysis_id}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to load results.json for {analysis_id}: {e}")
                        results_data = None
                
                # Fallback to report JSON if results.json failed
                if results_data is None and report_file.exists():
                    try:
                        with open(report_file, 'r') as f:
                            results_data = json.load(f)
                        
                        # Extract seed genes from report
                        seed_genes = results_data.get("input_summary", {}).get("gene_list", [])
                        timestamp = results_data.get("timestamp")
                        
                        logger.info(f"Loaded report data for {analysis_id}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to load report for {analysis_id}: {e}")
                
                # Create analysis entry if we have data
                if results_data:
                    self.analyses[analysis_id] = {
                        "analysis_id": analysis_id,
                        "seed_genes": seed_genes,
                        "status": "completed",
                        "current_stage": "completed", 
                        "progress": 100,
                        "message": "Analysis completed (loaded from disk)",
                        "error": None,
                        "results": results_data,
                        "report_files": {
                            "json": str(report_file) if report_file.exists() else None,
                            "pdf": str(outputs_dir / f"{analysis_id}_report.pdf") if (outputs_dir / f"{analysis_id}_report.pdf").exists() else None
                        },
                        "warnings": [],
                        "created_at": timestamp or datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    logger.info(f"Loaded existing analysis: {analysis_id}")
                    
                else:
                    # No results data found - mark as failed
                    self.analyses[analysis_id] = {
                        "analysis_id": analysis_id,
                        "seed_genes": [],
                        "status": "failed",
                        "current_stage": "unknown",
                        "progress": 0,
                        "message": "Analysis failed or incomplete",
                        "error": "No results data found",
                        "results": {},
                        "report_files": {},
                        "warnings": [],
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    logger.warning(f"No results data found for {analysis_id}")
            
            # Also scan for standalone report JSON files (e.g. fast_analysis_..._report.json)
            # Some pipelines write reports as files instead of creating an analysis_<id>/ directory.
            report_files = list(outputs_dir.glob("*_report.json"))
            for rf in report_files:
                # Derive analysis_id from filename (strip trailing _report.json)
                try:
                    analysis_id = rf.name.rsplit('_report.json', 1)[0]
                except Exception:
                    continue

                # Skip if already loaded from a directory
                if analysis_id in self.analyses:
                    continue

                try:
                    with open(rf, 'r', encoding='utf-8') as f:
                        results_data = json.load(f)

                    seed_genes = results_data.get('input_summary', {}).get('gene_list', [])
                    timestamp = results_data.get('timestamp')

                    self.analyses[analysis_id] = {
                        "analysis_id": analysis_id,
                        "seed_genes": seed_genes,
                        "status": "completed",
                        "current_stage": "completed",
                        "progress": 100,
                        "message": "Analysis completed (loaded from disk - report file)",
                        "error": None,
                        "results": results_data,
                        "report_files": {
                            "json": str(rf),
                            "pdf": str(outputs_dir / f"{analysis_id}_report.pdf") if (outputs_dir / f"{analysis_id}_report.pdf").exists() else None
                        },
                        "warnings": [],
                        "created_at": timestamp or datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    logger.info(f"Loaded standalone report analysis: {analysis_id}")
                except Exception as e:
                    logger.warning(f"Failed to load standalone report {rf}: {e}")

            logger.info(f"Loaded {len(analysis_dirs)} existing analysis directories and {len(report_files)} standalone report files from outputs directory")
            
        except Exception as e:
            logger.error(f"Error loading existing analyses: {e}")
    
    def create_analysis(self, analysis_id: str, seed_genes: list):
        """
        Create new analysis entry.
        
        Args:
            analysis_id: Analysis identifier
            seed_genes: Seed genes
        """
        with self.lock:
            self.analyses[analysis_id] = {
                "analysis_id": analysis_id,
                "seed_genes": seed_genes,
                "status": "pending",
                "current_stage": None,
                "progress": 0,
                "message": None,
                "error": None,
                "results": {},
                "report_files": {},
                "warnings": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        
        logger.info(f"Created analysis: {analysis_id}")
    
    def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analysis by ID.
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            Analysis data or None
        """
        with self.lock:
            return self.analyses.get(analysis_id)
    
    def update_analysis(self, analysis_id: str, **kwargs):
        """
        Update analysis fields.
        
        Args:
            analysis_id: Analysis identifier
            **kwargs: Fields to update
        """
        with self.lock:
            if analysis_id in self.analyses:
                self.analyses[analysis_id].update(kwargs)
                self.analyses[analysis_id]["updated_at"] = datetime.now().isoformat()
                
                logger.debug(f"Updated analysis {analysis_id}: {list(kwargs.keys())}")
    
    def list_analyses(self) -> list:
        """
        List all analyses.
        
        Returns:
            List of analysis summaries
        """
        with self.lock:
            return [
                {
                    "analysis_id": a["analysis_id"],
                    "status": a["status"],
                    "created_at": a["created_at"]
                }
                for a in self.analyses.values()
            ]


# Global analysis store instance
analysis_store = AnalysisStore()
