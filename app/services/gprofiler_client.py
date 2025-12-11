"""g:Profiler API client for pathway enrichment analysis."""

import logging
import time
from typing import List, Dict, Any, Optional

from gprofiler import GProfiler

from app.services.api_client import APIClientError
from app.models import GeneInfo, PathwayEntry
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GProfilerClient:
    """Client for g:Profiler functional enrichment analysis using official library."""
    
    def __init__(self):
        """Initialize g:Profiler client."""
        self.settings = get_settings()
        self.gp = GProfiler(return_dataframe=False)
        self.organism = "hsapiens"
        logger.info("GProfilerClient initialized with official library")
    
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
        fdr_threshold = fdr_threshold or self.settings.nets.fdr_threshold
        
        gene_symbols = [gene.symbol for gene in genes]
        
        logger.info(
            f"Querying g:Profiler for {len(gene_symbols)} genes, "
            f"sources: {sources}, FDR threshold: {fdr_threshold}"
        )
        print(f"[GPROFILER] Querying with genes: {gene_symbols[:10] if len(gene_symbols) > 10 else gene_symbols}")
        
        # Retry logic for 503 errors
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"[GPROFILER] Retry attempt {attempt + 1}/{max_retries}...")
                    logger.info(f"g:Profiler retry attempt {attempt + 1}/{max_retries}")
                
                # Query using official g:Profiler library
                results = self.gp.profile(
                    organism=self.organism,
                    query=gene_symbols,
                    sources=sources,
                    user_threshold=fdr_threshold,
                    significance_threshold_method='fdr',
                    no_evidences=False
                )
                
                # Parse results
                pathways = self._parse_library_response(results, fdr_threshold)
                
                logger.info(
                    f"Retrieved {len(pathways)} significant pathways from g:Profiler"
                )
                print(f"[GPROFILER] Retrieved {len(pathways)} pathways")
                if pathways:
                    print(f"[GPROFILER] First pathway genes: {pathways[0].evidence_genes[:5] if len(pathways[0].evidence_genes) > 5 else pathways[0].evidence_genes}")
                
                return pathways
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a 503 error (service unavailable)
                if "503" in error_msg or "Service Unavailable" in error_msg or "timed out" in error_msg.lower():
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        logger.warning(
                            f"g:Profiler returned 503 (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {wait_time}s..."
                        )
                        print(f"\n[GPROFILER RETRY] Service unavailable (attempt {attempt + 1}/{max_retries})")
                        print(f"[GPROFILER RETRY] Waiting {wait_time} seconds before retry...\n")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"g:Profiler unavailable after {max_retries} attempts")
                        print(f"[GPROFILER ERROR] Service unavailable after {max_retries} attempts")
                        raise APIClientError(
                            f"g:Profiler service temporarily unavailable. Please try again in a few minutes."
                        )
                else:
                    # Non-503 error, don't retry
                    logger.error(f"g:Profiler query failed: {error_msg}")
                    print(f"[GPROFILER ERROR] {error_msg}")
                    raise APIClientError(f"g:Profiler query failed: {error_msg}")
    
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
            
            # Create PathwayEntry
            pathway = PathwayEntry(
                pathway_id=term_id,
                pathway_name=term_name,
                source_db=source_db,
                p_value=p_value,
                p_adj=p_adj,
                evidence_count=evidence_count,
                evidence_genes=intersection  # Actual gene symbols from library!
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
    
    def convert_ids(
        self,
        gene_ids: List[str],
        source_namespace: str = "ENTREZGENE_ACC",
        target_namespace: str = "ENSG"
    ) -> Dict[str, str]:
        """
        Convert gene identifiers between namespaces.
        
        Args:
            gene_ids: List of gene identifiers
            source_namespace: Source namespace
            target_namespace: Target namespace
            
        Returns:
            Mapping of source IDs to target IDs
        """
        logger.info(
            f"Converting {len(gene_ids)} IDs from {source_namespace} "
            f"to {target_namespace}"
        )
        
        endpoint = "convert/convert"
        
        payload = {
            "organism": self.organism,
            "query": gene_ids,
            "target_namespace": target_namespace
        }
        
        try:
            response_data = self.post_json(endpoint, json=payload)
            
            # Parse conversion results
            result = response_data.get("result", [])
            
            id_map = {}
            for entry in result:
                incoming = entry.get("incoming")
                converted = entry.get("converted")
                if incoming and converted:
                    id_map[incoming] = converted
            
            logger.info(f"Converted {len(id_map)} IDs successfully")
            
            return id_map
            
        except Exception as e:
            logger.error(f"ID conversion failed: {str(e)}")
            raise APIClientError(f"ID conversion failed: {str(e)}")

    def close(self):
        """Close client connections (no-op for library-based client)."""
        # The official g:Profiler library doesn't require explicit cleanup
        logger.debug("GProfilerClient closed (no-op)")
