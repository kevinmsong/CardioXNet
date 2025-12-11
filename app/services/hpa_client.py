"""
Human Protein Atlas (HPA) API Client.

Retrieves tissue-specific protein expression data from the Human Protein Atlas
to validate cardiac expression patterns and tissue specificity.

Data sources:
- RNA-seq tissue expression (consensus normalized expression)
- Immunohistochemistry protein expression
- Single-cell RNA-seq cardiac data

Website: https://www.proteinatlas.org/
API: https://www.proteinatlas.org/about/download
"""

import logging
import asyncio
from typing import Dict, List, Optional, Set
import aiohttp
from app.core.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class HPAClient:
    """Client for Human Protein Atlas tissue expression data."""
    
    # HPA normal tissue RNA expression data (TSV format)
    HPA_RNA_URL = "https://www.proteinatlas.org/download/rna_tissue_consensus.tsv.zip"
    HPA_PROTEIN_URL = "https://www.proteinatlas.org/download/normal_tissue.tsv.zip"
    
    # Cardiac tissue names in HPA
    CARDIAC_TISSUES = {
        'heart muscle',
        'heart',
        'cardiac muscle',
        'left ventricle',
        'right ventricle',
        'atrium',
        'myocardium'
    }
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """
        Initialize HPA client.
        
        Args:
            cache_manager: Optional cache manager for caching results
        """
        self.cache_manager = cache_manager or CacheManager()
        self._expression_data: Optional[Dict] = None
        self._protein_data: Optional[Dict] = None
        logger.info("HPAClient initialized")
    
    async def get_cardiac_expression(
        self,
        genes: List[str],
        expression_threshold: float = 1.0
    ) -> Dict[str, Dict]:
        """
        Get cardiac tissue expression data for genes.
        
        Args:
            genes: List of gene symbols
            expression_threshold: Minimum nTPM for cardiac expression (default: 1.0)
            
        Returns:
            Dictionary mapping gene symbols to expression data:
            {
                'gene_symbol': {
                    'cardiac_expression': float,  # nTPM in cardiac tissue
                    'median_expression': float,   # Median nTPM across all tissues
                    'cardiac_specificity': float, # Ratio: cardiac / median
                    'is_cardiac_enriched': bool,  # True if specificity > 2.0
                    'expression_level': str,      # 'High', 'Medium', 'Low', 'Not detected'
                    'tissues': List[Dict],        # Expression in all tissues
                    'protein_evidence': Optional[str]  # IHC evidence level
                }
            }
        """
        cache_key = f"hpa_cardiac_expression_{','.join(sorted(genes))}_{expression_threshold}"
        
        # Check cache
        cached = self.cache_manager.get(cache_key)
        if cached:
            logger.info(f"HPA cardiac expression cache hit for {len(genes)} genes")
            return cached
        
        logger.info(f"Fetching HPA cardiac expression for {len(genes)} genes")
        
        results = {}
        
        for gene in genes:
            try:
                # Query HPA API for gene expression
                expression_data = await self._fetch_gene_expression(gene)
                
                if expression_data:
                    cardiac_expr = self._extract_cardiac_expression(
                        expression_data,
                        expression_threshold
                    )
                    results[gene] = cardiac_expr
                else:
                    results[gene] = self._get_no_data_result()
                    
            except Exception as e:
                logger.warning(f"Failed to fetch HPA data for {gene}: {e}")
                results[gene] = self._get_no_data_result()
        
        # Cache results for 24 hours
        self.cache_manager.set(cache_key, results, ttl_hours=24)
        
        logger.info(
            f"HPA cardiac expression fetched: {len(results)} genes, "
            f"{sum(1 for r in results.values() if r['is_cardiac_enriched'])} cardiac-enriched"
        )
        
        return results
    
    async def _fetch_gene_expression(self, gene: str) -> Optional[Dict]:
        """
        Fetch expression data for a single gene from HPA API.
        
        Note: HPA provides bulk download files. For production, we use the
        programmatic API endpoint when available, or parse downloaded TSV files.
        
        Args:
            gene: Gene symbol
            
        Returns:
            Expression data dictionary or None
        """
        # HPA programmatic access endpoint
        api_url = f"https://www.proteinatlas.org/{gene}.json"
        
        # Retry logic for transient network issues
        max_retries = 2
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data
                        elif response.status == 404:
                            logger.debug(f"Gene {gene} not found in HPA")
                            return None
                        else:
                            logger.warning(f"HPA API returned status {response.status} for {gene}")
                            return None
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.debug(f"Timeout fetching HPA data for {gene}, retrying... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(1)  # Brief delay before retry
                else:
                    logger.warning(f"Timeout fetching HPA data for {gene} after {max_retries} attempts")
                return None
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.debug(f"Error fetching HPA data for {gene}: {e}, retrying...")
                    await asyncio.sleep(1)
                else:
                    logger.warning(f"Error fetching HPA data for {gene} after {max_retries} attempts: {e}")
                return None
        
        return None
    
    def _extract_cardiac_expression(
        self,
        hpa_data: Dict,
        threshold: float
    ) -> Dict:
        """
        Extract cardiac-specific expression metrics from HPA data.
        
        Args:
            hpa_data: Raw HPA JSON data
            threshold: Expression threshold (nTPM)
            
        Returns:
            Processed cardiac expression metrics
        """
        # Extract RNA expression data
        rna_tissues = {}
        
        # HPA JSON structure: data['rna']['tissue']
        if 'rna' in hpa_data and 'tissue' in hpa_data['rna']:
            for tissue_data in hpa_data['rna']['tissue']:
                tissue_name = tissue_data.get('name', '').lower()
                expr_value = tissue_data.get('value', 0.0)
                rna_tissues[tissue_name] = float(expr_value)
        
        # Find cardiac expression
        cardiac_expr = 0.0
        for tissue_name, expr in rna_tissues.items():
            if any(cardiac_term in tissue_name for cardiac_term in self.CARDIAC_TISSUES):
                cardiac_expr = max(cardiac_expr, expr)
        
        # Calculate median expression across all tissues
        if rna_tissues:
            tissue_values = list(rna_tissues.values())
            tissue_values.sort()
            n = len(tissue_values)
            median_expr = tissue_values[n // 2] if n % 2 == 1 else (tissue_values[n // 2 - 1] + tissue_values[n // 2]) / 2
        else:
            median_expr = 0.0
        
        # Calculate cardiac specificity
        if median_expr > 0:
            cardiac_specificity = cardiac_expr / median_expr
        else:
            cardiac_specificity = 0.0
        
        # Determine expression level
        if cardiac_expr >= 10.0:
            expression_level = 'High'
        elif cardiac_expr >= threshold:
            expression_level = 'Medium'
        elif cardiac_expr > 0:
            expression_level = 'Low'
        else:
            expression_level = 'Not detected'
        
        # Check if cardiac-enriched (>2x median expression)
        is_cardiac_enriched = cardiac_specificity > 2.0 and cardiac_expr >= threshold
        
        # Extract protein evidence (immunohistochemistry)
        protein_evidence = None
        if 'protein' in hpa_data and 'tissue' in hpa_data['protein']:
            for tissue_data in hpa_data['protein']['tissue']:
                tissue_name = tissue_data.get('name', '').lower()
                if any(cardiac_term in tissue_name for cardiac_term in self.CARDIAC_TISSUES):
                    protein_evidence = tissue_data.get('level', 'Not available')
                    break
        
        return {
            'cardiac_expression': cardiac_expr,
            'median_expression': median_expr,
            'cardiac_specificity': cardiac_specificity,
            'is_cardiac_enriched': is_cardiac_enriched,
            'expression_level': expression_level,
            'tissues': [
                {'name': name, 'expression': expr}
                for name, expr in sorted(rna_tissues.items(), key=lambda x: x[1], reverse=True)
            ][:10],  # Top 10 tissues
            'protein_evidence': protein_evidence
        }
    
    def _get_no_data_result(self) -> Dict:
        """Return default result when no HPA data available."""
        return {
            'cardiac_expression': 0.0,
            'median_expression': 0.0,
            'cardiac_specificity': 0.0,
            'is_cardiac_enriched': False,
            'expression_level': 'Not detected',
            'tissues': [],
            'protein_evidence': None
        }
    
    async def get_cardiac_enriched_genes(
        self,
        genes: List[str],
        specificity_threshold: float = 2.0,
        expression_threshold: float = 1.0
    ) -> List[str]:
        """
        Get list of genes with cardiac-enriched expression.
        
        Args:
            genes: List of gene symbols to check
            specificity_threshold: Minimum cardiac specificity ratio (default: 2.0)
            expression_threshold: Minimum cardiac nTPM (default: 1.0)
            
        Returns:
            List of gene symbols with cardiac-enriched expression
        """
        expression_data = await self.get_cardiac_expression(genes, expression_threshold)
        
        cardiac_genes = [
            gene for gene, data in expression_data.items()
            if data['is_cardiac_enriched'] and data['cardiac_specificity'] >= specificity_threshold
        ]
        
        logger.info(
            f"Identified {len(cardiac_genes)} / {len(genes)} genes with "
            f"cardiac-enriched expression (specificity > {specificity_threshold})"
        )
        
        return cardiac_genes
    
    async def close(self):
        """Cleanup resources."""
        # Cache manager doesn't need async cleanup
        logger.info("HPAClient closed")
