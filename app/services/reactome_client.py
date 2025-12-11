"""Reactome API client for pathway annotation queries."""

import logging
from typing import List, Dict, Any, Set

from app.services.api_client import APIClient, APIClientError
from app.models import GeneInfo, PathwayEntry
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ReactomeClient(APIClient):
    """Client for Reactome pathway database API."""
    
    def __init__(self):
        """Initialize Reactome client."""
        settings = get_settings()
        super().__init__(
            base_url=settings.nets.reactome_api_url,
            name="Reactome"
        )
        self.species = "Homo sapiens"
        self.species_tax_id = "9606"  # Human NCBI taxonomy ID
        # Analysis Service base URL
        self.analysis_base_url = "https://reactome.org/AnalysisService"
    
    def get_pathways_for_genes(
        self,
        genes: List[GeneInfo]
    ) -> List[PathwayEntry]:
        """
        Query Reactome for pathways associated with genes using Analysis Service.
        
        Uses Reactome Analysis Service which accepts gene symbols directly:
        https://reactome.org/AnalysisService/
        
        Args:
            genes: List of genes to query
            
        Returns:
            List of PathwayEntry objects for pathways containing these genes
        """
        if not genes:
            raise ValueError("At least one gene is required")
        
        gene_symbols = [gene.symbol for gene in genes]
        
        logger.info(
            f"Querying Reactome Analysis Service for {len(gene_symbols)} genes"
        )
        
        try:
            # Use Analysis Service to find pathways
            pathways = self._query_analysis_service(gene_symbols)
            
            logger.info(
                f"Retrieved {len(pathways)} pathways from Reactome"
            )
            
            if not pathways:
                logger.debug("No pathways retrieved from Reactome - will use alternative databases")
            
            return pathways
            
        except Exception as e:
            logger.debug(f"Reactome unavailable: {str(e)}")
            logger.debug("Analysis will continue with gProfiler and other databases")
            return []  # Return empty list instead of raising critical error
    
    def _query_analysis_service(
        self,
        gene_symbols: List[str]
    ) -> List[PathwayEntry]:
        """
        Query Reactome Analysis Service for pathway projection.
        
        Per Reactome Analysis Service API:
        POST /AnalysisService/identifiers/projection/
        
        Args:
            gene_symbols: List of gene symbols
            
        Returns:
            List of PathwayEntry objects
        """
        # Prepare gene list as newline-separated text
        gene_list = "\n".join(gene_symbols)
        
        # Use requests directly for Analysis Service (different base URL)
        import requests
        
        url = f"{self.analysis_base_url}/identifiers/projection/"
        params = {
            "pageSize": 500,  # Increased from 100 to maximum allowed (500) for comprehensive results
            "page": 1,
            "species": self.species_tax_id,
            "sortBy": "ENTITIES_PVALUE",
            "order": "ASC"
        }
        
        headers = {
            "Content-Type": "text/plain",
            "Accept": "application/json"
        }
        
        try:
            response = requests.post(
                url,
                params=params,
                headers=headers,
                data=gene_list,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract pathways from response
            pathways = data.get("pathways", [])
            
            # Convert to PathwayEntry objects
            entries = []
            for pathway in pathways:
                # Only include pathways for our species
                species_info = pathway.get("species", {})
                if species_info.get("taxId") != self.species_tax_id:
                    continue
                
                # Get entities information
                entities = pathway.get("entities", {})
                
                entry = PathwayEntry(
                    pathway_id=f"REAC:{pathway['stId']}",
                    pathway_name=pathway["name"],
                    source_db="REAC",
                    p_value=entities.get("pValue", 1.0),
                    p_adj=entities.get("fdr", 1.0),
                    evidence_count=entities.get("found", 0),
                    evidence_genes=gene_symbols  # Simplified - actual genes in pathway
                )
                
                entries.append(entry)
            
            return entries
            
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"Reactome connection failed (server unavailable): {str(e)}")
            return []  # Return empty list - gProfiler will provide pathway coverage
        except requests.exceptions.Timeout as e:
            logger.debug(f"Reactome timeout: {str(e)}")
            return []  # Return empty list - gProfiler will provide pathway coverage
        except requests.exceptions.RequestException as e:
            logger.debug(f"Reactome API error: {str(e)}")
            return []  # Return empty list - gProfiler will provide pathway coverage
        except Exception as e:
            logger.debug(f"Reactome parsing error: {str(e)}")
            logger.info("Continuing analysis without Reactome pathways due to parsing issues")
            return []  # Return empty list instead of raising error
    
    def _query_gene_pathways(self, gene: GeneInfo) -> List[Dict[str, Any]]:
        """
        Query pathways for a single gene.
        
        Per Reactome Content Service API docs:
        https://reactome.org/ContentService/#/
        
        Note: The /data/pathways/low/entity endpoint may return 404 for some genes.
        This is expected behavior - not all genes are in Reactome.
        
        Args:
            gene: Gene to query
            
        Returns:
            List of pathway data (empty list if gene not found)
        """
        # Reactome Content Service - use data/pathways/low/entity endpoint
        # This endpoint returns pathways for a given entity (gene)
        # Accepts: Gene symbols, UniProt IDs, Ensembl IDs, Entrez IDs
        
        # Try with gene symbol first (most common)
        try:
            endpoint = f"data/pathways/low/entity/{gene.symbol}"
            params = {"species": "Homo sapiens"}
            pathways = self.get_json(endpoint, params=params)
            
            if pathways and isinstance(pathways, list):
                logger.debug(f"Found {len(pathways)} pathways for {gene.symbol}")
                return pathways
            
        except APIClientError as e:
            # 404 is expected for genes not in Reactome - don't log as error
            if "404" not in str(e):
                logger.debug(f"Query failed for {gene.symbol}: {str(e)}")
        
        # Try with Entrez ID if available
        if gene.entrez_id:
            try:
                endpoint = f"data/pathways/low/entity/{gene.entrez_id}"
                params = {"species": "Homo sapiens"}
                pathways = self.get_json(endpoint, params=params)
                
                if pathways and isinstance(pathways, list):
                    logger.debug(f"Found {len(pathways)} pathways for Entrez:{gene.entrez_id}")
                    return pathways
                    
            except APIClientError as e:
                # 404 is expected for genes not in Reactome
                if "404" not in str(e):
                    logger.debug(f"Query failed for Entrez:{gene.entrez_id}: {str(e)}")
        
        # No pathways found - this is normal for many genes
        logger.debug(f"No Reactome pathways found for {gene.symbol} (gene may not be in Reactome)")
        return []
    
    def _create_pathway_entries(
        self,
        pathways: List[Dict[str, Any]],
        pathway_genes_map: Dict[str, Set[str]]
    ) -> List[PathwayEntry]:
        """
        Create PathwayEntry objects from Reactome data.
        
        Args:
            pathways: Raw pathway data from Reactome
            pathway_genes_map: Mapping of pathway IDs to gene sets
            
        Returns:
            List of PathwayEntry objects
        """
        entries = []
        
        for pathway in pathways:
            pathway_id = pathway.get("stId")
            pathway_name = pathway.get("displayName")
            
            if not pathway_id or not pathway_name:
                continue
            
            # Get genes for this pathway
            evidence_genes = list(pathway_genes_map.get(pathway_id, set()))
            evidence_count = len(evidence_genes)
            
            # Create entry (p-values not available from this endpoint)
            entry = PathwayEntry(
                pathway_id=f"REAC:{pathway_id}",
                pathway_name=pathway_name,
                source_db="REAC",
                p_value=1.0,  # Not available from annotation query
                p_adj=1.0,    # Not available from annotation query
                evidence_count=evidence_count,
                evidence_genes=evidence_genes
            )
            
            entries.append(entry)
        
        return entries
    
    def get_pathway_details(self, pathway_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a pathway.
        
        Per Reactome Content Service API:
        Endpoint: GET /data/query/{id}
        Returns detailed information about a database object
        
        Args:
            pathway_id: Reactome pathway stable identifier (e.g., R-HSA-1234567)
            
        Returns:
            Pathway details including name, species, summation, etc.
        """
        # Remove REAC: prefix if present
        if pathway_id.startswith("REAC:"):
            pathway_id = pathway_id[5:]
        
        logger.info(f"Querying Reactome for pathway details: {pathway_id}")
        
        # Use data/query endpoint for detailed information
        endpoint = f"data/query/{pathway_id}"
        
        try:
            details = self.get_json(endpoint)
            
            logger.debug(f"Retrieved details for pathway {pathway_id}")
            
            return details
            
        except Exception as e:
            logger.error(f"Failed to get pathway details: {str(e)}")
            raise APIClientError(f"Failed to get pathway details: {str(e)}")
    
    def get_pathway_participants(self, pathway_id: str) -> List[str]:
        """
        Get all participating entities in a pathway.
        
        Per Reactome Content Service API:
        Endpoint: GET /data/participants/{id}
        Returns all PhysicalEntities that participate in a given Event
        
        Args:
            pathway_id: Reactome pathway stable identifier (e.g., R-HSA-1234567)
            
        Returns:
            List of participant gene names/identifiers
        """
        # Remove REAC: prefix if present
        if pathway_id.startswith("REAC:"):
            pathway_id = pathway_id[5:]
        
        logger.info(f"Querying participants for pathway: {pathway_id}")
        
        # Use data/participants endpoint
        endpoint = f"data/participants/{pathway_id}"
        
        try:
            participants = self.get_json(endpoint)
            
            # Extract gene names/identifiers from participants
            # Participants are PhysicalEntity objects with various properties
            gene_names = []
            
            if isinstance(participants, list):
                for participant in participants:
                    if isinstance(participant, dict):
                        # Try different name fields
                        name = (
                            participant.get("displayName") or 
                            participant.get("name") or
                            participant.get("geneName")
                        )
                        if name:
                            gene_names.append(name)
            
            logger.debug(
                f"Retrieved {len(gene_names)} participants for pathway {pathway_id}"
            )
            
            return gene_names
            
        except Exception as e:
            logger.error(f"Failed to get pathway participants: {str(e)}")
            raise APIClientError(f"Failed to get pathway participants: {str(e)}")
    
    def search_pathways(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for pathways by name or keyword.
        
        Per Reactome Content Service API:
        Endpoint: GET /search/query
        Performs full-text search on the Reactome knowledgebase
        
        Args:
            query: Search query string
            
        Returns:
            List of matching pathway objects
        """
        logger.info(f"Searching Reactome for: {query}")
        
        # Use search/query endpoint for full-text search
        endpoint = "search/query"
        
        params = {
            "query": query,
            "species": self.species,
            "types": "Pathway",  # Filter to only Pathway objects
            "cluster": "true"    # Group results by species
        }
        
        try:
            response = self.get_json(endpoint, params=params)
            
            # Extract results from response
            # Response structure: {"results": [...], "facets": [...]}
            results = []
            if isinstance(response, dict):
                results = response.get("results", [])
            elif isinstance(response, list):
                results = response
            
            logger.info(f"Found {len(results)} pathways matching '{query}'")
            
            return results
            
        except Exception as e:
            logger.error(f"Pathway search failed: {str(e)}")
            raise APIClientError(f"Pathway search failed: {str(e)}")
