"""STRING database client for protein-protein interactions using direct API calls."""

import logging
from typing import List, Dict, Any, Optional
import time

import requests
import pandas as pd
from app.models import GeneInfo
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class STRINGClient:
    """Client for STRING protein-protein interaction database using direct API calls."""
    
    def __init__(self):
        """Initialize STRING client."""
        self.settings = get_settings()
        self.species = 9606  # Human NCBI taxonomy ID
        self.base_url = "https://version-12-0.string-db.org/api"
        self.session = requests.Session()
    
    def get_interactions(
        self,
        genes: List[GeneInfo],
        score_threshold: Optional[float] = None,
        neighbor_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Query STRING for protein-protein interactions using direct API calls.
        
        Args:
            genes: List of seed genes
            score_threshold: Minimum combined score (0-1, default from config)
            neighbor_count: Number of additional neighbors to add (default from config)
            
        Returns:
            Dictionary containing:
                - neighbors: List of interacting proteins
                - interactions: List of interaction edges with scores
                - contributions: Per-gene contribution counts
        """
        if not genes:
            raise ValueError("At least one gene is required")
        
        score_threshold = score_threshold or self.settings.nets.string_score_threshold
        neighbor_count = neighbor_count or getattr(self.settings.nets, 'string_neighbor_count', 50)
        
        # Extract gene symbols for query
        gene_symbols = [gene.symbol for gene in genes]
        
        logger.info(
            f"Querying STRING for {len(gene_symbols)} genes, "
            f"score threshold: {score_threshold}"
        )
        
        try:
            # Validate genes before querying
            if not gene_symbols or len(gene_symbols) == 0:
                logger.warning("No genes provided to STRING, returning empty result")
                return {
                    "neighbors": [],
                    "interactions": [],
                    "contributions": {},
                    "total_interactions": 0,
                    "score_threshold": score_threshold
                }
            
            # Get network using direct API call
            network_df = self._get_network_data(
                gene_symbols, score_threshold, neighbor_count or 50
            )
            
            logger.debug(f"STRING returned: {type(network_df)}, shape: {network_df.shape if network_df is not None else 'None'}")
            
            # Check if DataFrame is empty
            if network_df is None or network_df.empty:
                logger.warning(f"No interactions found for genes: {gene_symbols}")
                return {
                    "neighbors": [],
                    "interactions": [],
                    "contributions": {gene.symbol: 0 for gene in genes},
                    "total_interactions": 0,
                    "score_threshold": score_threshold
                }
            
            # Parse and filter response
            result = self._parse_network(network_df, genes, score_threshold)
            
            logger.info(
                f"Retrieved {len(result['neighbors'])} interacting proteins from STRING"
            )
            
            return result
            
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            # Only log warning, not error - STRING API is unreliable but non-critical
            logger.warning(f"STRING API unavailable: {error_msg}. Continuing without STRING interactions.")
            
            # Return empty result instead of failing - pipeline can continue
            return {
                "neighbors": [],
                "interactions": [],
                "contributions": {gene.symbol: 0 for gene in genes},
                "total_interactions": 0,
                "score_threshold": score_threshold,
                "error": error_msg
            }
    
    def _get_network_data(
        self,
        gene_symbols: List[str],
        score_threshold: float,
        neighbor_count: int
    ) -> Optional[pd.DataFrame]:
        """
        Get network data from STRING API directly.
        
        Args:
            gene_symbols: List of gene symbols
            score_threshold: Score threshold (0-1)
            neighbor_count: Number of neighbors to add
            
        Returns:
            DataFrame with network data or None if failed
        """
        # Convert score threshold to STRING scale (0-1000)
        required_score = int(score_threshold * 1000)
        
        # Prepare identifiers (separated by %0d which is URL-encoded \r)
        identifiers = "%0d".join(gene_symbols)
        
        # Build API URL with parameters
        url = f"{self.base_url}/tsv/network"
        
        params = {
            "identifiers": identifiers,
            "species": self.species,
            "required_score": required_score,
            "add_nodes": neighbor_count,
            "caller_identity": "CardioXNet"
        }
        
        logger.debug(f"Calling STRING API: {url} with params: {params}")
        
        try:
            # Make API request with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.session.get(url, params=params, timeout=30)
                    response.raise_for_status()
                    
                    # Parse TSV response into DataFrame
                    # Skip the first line (header) and read TSV
                    lines = response.text.strip().split('\n')
                    if len(lines) <= 1:  # Only header or empty
                        return pd.DataFrame()
                    
                    # Parse TSV data
                    data_lines = lines[1:]  # Skip header
                    if not data_lines:
                        return pd.DataFrame()
                    
                    # Parse each line
                    parsed_data = []
                    for line in data_lines:
                        if line.strip():
                            parts = line.split('\t')
                            if len(parts) >= 10:  # Ensure we have all required columns
                                parsed_data.append({
                                    'stringId_A': parts[0],
                                    'stringId_B': parts[1],
                                    'preferredName_A': parts[2],
                                    'preferredName_B': parts[3],
                                    'ncbiTaxonId': parts[4],
                                    'score': float(parts[5]),
                                    'nscore': float(parts[6]) if parts[6] else 0.0,
                                    'fscore': float(parts[7]) if parts[7] else 0.0,
                                    'pscore': float(parts[8]) if parts[8] else 0.0,
                                    'ascore': float(parts[9]) if parts[9] else 0.0,
                                    'escore': float(parts[10]) if len(parts) > 10 and parts[10] else 0.0,
                                    'dscore': float(parts[11]) if len(parts) > 11 and parts[11] else 0.0,
                                    'tscore': float(parts[12]) if len(parts) > 12 and parts[12] else 0.0
                                })
                    
                    if not parsed_data:
                        return pd.DataFrame()
                    
                    return pd.DataFrame(parsed_data)
                    
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"STRING API attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
            
        except Exception as e:
            logger.error(f"Failed to get network data from STRING API: {e}")
            return None
    
    def _parse_network(
        self,
        network_df,
        seed_genes: List[GeneInfo],
        score_threshold: float
    ) -> Dict[str, Any]:
        """
        Parse STRING network DataFrame from direct API response.
        
        Args:
            network_df: DataFrame from STRING API
            seed_genes: Original seed genes
            score_threshold: Score threshold used
            
        Returns:
            Parsed result dictionary
        """
        # Create seed gene symbol set
        seed_symbols = {gene.symbol for gene in seed_genes}
        
        # Track unique proteins and interactions
        protein_map = {}  # protein name -> gene info
        interactions = []
        contributions = {gene.symbol: 0 for gene in seed_genes}
        
        # Parse network DataFrame
        for _, row in network_df.iterrows():
            protein_a = row.get("preferredName_A")
            protein_b = row.get("preferredName_B")
            score = row.get("score", 0.0)
            
            if not protein_a or not protein_b:
                continue
            
            # Add proteins to map
            for protein_name in [protein_a, protein_b]:
                if protein_name not in protein_map:
                    # Create GeneInfo
                    protein_map[protein_name] = GeneInfo(
                        input_id=protein_name,
                        entrez_id="",  # STRING uses Ensembl IDs
                        symbol=protein_name,
                        species="Homo sapiens"
                    )
            
            # Add interaction with all evidence scores
            interactions.append({
                "from": protein_a,
                "to": protein_b,
                "score": score,
                "nscore": row.get("nscore", 0.0),
                "fscore": row.get("fscore", 0.0),
                "pscore": row.get("pscore", 0.0),
                "ascore": row.get("ascore", 0.0),
                "escore": row.get("escore", 0.0),
                "dscore": row.get("dscore", 0.0),
                "tscore": row.get("tscore", 0.0)
            })
            
            # Track contributions from seed genes
            if protein_a in seed_symbols:
                contributions[protein_a] += 1
            if protein_b in seed_symbols:
                contributions[protein_b] += 1
        
        # Extract neighbors (exclude seed genes)
        neighbors = [
            gene_info for symbol, gene_info in protein_map.items()
            if symbol not in seed_symbols
        ]
        
        return {
            "neighbors": neighbors,
            "interactions": interactions,
            "contributions": contributions,
            "total_interactions": len(interactions),
            "score_threshold": score_threshold
        }
