"""
Epigenomic Data Client for Cardiac Regulatory Elements.

Integrates cardiac-specific epigenomic data from ENCODE and Roadmap Epigenomics
to identify genes under active regulatory control in cardiac tissues.

Data sources:
- ENCODE: Encyclopedia of DNA Elements (enhancers, promoters, TF binding)
- Roadmap Epigenomics: Histone marks and chromatin states in cardiac tissues
- Target genes: Left ventricle, right ventricle, heart tissues

Regulatory features:
- H3K27ac: Active enhancers and promoters
- H3K4me3: Active promoters
- H3K4me1: Enhancers
- DNase-seq: Open chromatin / accessible regions
- Chromatin states: Active TSS, strong enhancers, weak enhancers

Note: This is a simplified implementation. For production, consider using
ENCODE Portal API or pre-downloaded BED files with gene annotations.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Set
import aiohttp
from app.core.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class EpigenomicClient:
    """Client for cardiac epigenomic regulatory data."""
    
    # ENCODE Portal API
    ENCODE_API_BASE = "https://www.encodeproject.org"
    
    # Roadmap Epigenomics cardiac tissue identifiers
    CARDIAC_TISSUE_IDS = {
        'E095': 'Left Ventricle',
        'E096': 'Right Ventricle',  
        'E104': 'Right Atrium',
        'E105': 'Left Atrium'
    }
    
    # Cardiac-specific enhancer/promoter keywords
    CARDIAC_REGULATORY_TERMS = {
        'cardiac', 'heart', 'ventricle', 'atrium', 'myocardium',
        'cardiomyocyte', 'myocyte'
    }
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """
        Initialize epigenomic client.
        
        Args:
            cache_manager: Optional cache manager for caching results
        """
        self.cache_manager = cache_manager or CacheManager()
        logger.info("EpigenomicClient initialized")
    
    async def get_cardiac_regulatory_activity(
        self,
        genes: List[str]
    ) -> Dict[str, Dict]:
        """
        Get cardiac regulatory activity for genes.
        
        Scores genes based on presence of cardiac-specific regulatory elements
        (enhancers, promoters, open chromatin) within gene loci.
        
        Args:
            genes: List of gene symbols
            
        Returns:
            Dictionary mapping gene symbols to regulatory data:
            {
                'gene_symbol': {
                    'has_cardiac_regulatory': bool,
                    'regulatory_score': float,  # 0.0 to 1.0
                    'active_promoter': bool,    # H3K4me3 signal
                    'active_enhancer': bool,    # H3K27ac signal
                    'open_chromatin': bool,     # DNase-seq signal
                    'chromatin_state': str,     # Chromatin state annotation
                    'num_cardiac_enhancers': int,
                    'enhancer_strength': float, # Average H3K27ac signal
                    'tissue_specificity': float # Cardiac vs other tissues
                }
            }
        """
        cache_key = f"epigenomic_cardiac_regulatory_{','.join(sorted(genes))}"
        
        # Check cache
        cached = self.cache_manager.get(cache_key)
        if cached:
            logger.info(f"Epigenomic data cache hit for {len(genes)} genes")
            return cached
        
        logger.info(f"Fetching cardiac regulatory data for {len(genes)} genes")
        
        results = {}
        
        for gene in genes:
            try:
                # Fetch regulatory annotations
                regulatory_data = await self._fetch_gene_regulatory_data(gene)
                
                if regulatory_data:
                    processed_data = self._process_regulatory_data(regulatory_data)
                    results[gene] = processed_data
                else:
                    results[gene] = self._get_no_data_result()
                    
            except Exception as e:
                logger.warning(f"Failed to fetch epigenomic data for {gene}: {e}")
                results[gene] = self._get_no_data_result()
        
        # Cache results for 7 days (epigenomic data is static)
        self.cache_manager.set(cache_key, results, ttl_hours=168)
        
        logger.info(
            f"Epigenomic data fetched: {len(results)} genes, "
            f"{sum(1 for r in results.values() if r['has_cardiac_regulatory'])} with cardiac regulatory activity"
        )
        
        return results
    
    async def _fetch_gene_regulatory_data(self, gene: str) -> Optional[Dict]:
        """
        Fetch regulatory element data for a gene.
        
        This is a simplified implementation that queries ENCODE Portal API
        for regulatory elements overlapping the gene locus in cardiac tissues.
        
        Args:
            gene: Gene symbol
            
        Returns:
            Regulatory data dictionary or None
        """
        # ENCODE API endpoint for gene regulatory annotations
        # Note: This is a simplified query. Production code should include:
        # 1. Gene coordinate lookup (HGNC/Ensembl API)
        # 2. BED file overlap queries for histone marks
        # 3. Chromatin state segmentation data
        
        api_url = f"{self.ENCODE_API_BASE}/search/"
        params = {
            'type': 'Experiment',
            'target.gene_name': gene,
            'biosample_ontology.term_name': 'heart',
            'assay_title': 'Histone ChIP-seq',
            'status': 'released',
            'format': 'json',
            'limit': 50
        }
        
        # Retry logic for transient network issues
        max_retries = 2
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        api_url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data
                        elif response.status == 404:
                            logger.debug(f"No epigenomic data found for gene {gene}")
                            return None
                        else:
                            logger.warning(f"ENCODE API returned status {response.status} for {gene}")
                            return None
                            
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.debug(f"Timeout fetching epigenomic data for {gene}, retrying... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(1)  # Brief delay before retry
                else:
                    logger.warning(f"Timeout fetching epigenomic data for {gene} after {max_retries} attempts")
                return None
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.debug(f"Error fetching epigenomic data for {gene}: {e}, retrying...")
                    await asyncio.sleep(1)
                else:
                    logger.warning(f"Error fetching epigenomic data for {gene} after {max_retries} attempts: {e}")
                return None
        
        return None
    
    def _process_regulatory_data(self, encode_data: Dict) -> Dict:
        """
        Process ENCODE regulatory data into summary metrics.
        
        Args:
            encode_data: Raw ENCODE API response
            
        Returns:
            Processed regulatory metrics
        """
        # Parse ENCODE response for histone mark experiments
        experiments = encode_data.get('@graph', [])
        
        # Count cardiac-specific regulatory features
        has_h3k27ac = False  # Active enhancers/promoters
        has_h3k4me3 = False  # Active promoters
        has_h3k4me1 = False  # Enhancers
        has_dnase = False    # Open chromatin
        
        cardiac_enhancer_count = 0
        enhancer_signal_values = []
        
        for exp in experiments:
            target = exp.get('target', {})
            target_label = target.get('label', '').lower()
            assay = exp.get('assay_title', '').lower()
            biosample = exp.get('biosample_ontology', {}).get('term_name', '').lower()
            
            # Check if experiment is cardiac-specific
            is_cardiac = any(term in biosample for term in self.CARDIAC_REGULATORY_TERMS)
            
            if not is_cardiac:
                continue
            
            # Identify histone marks
            if 'h3k27ac' in target_label:
                has_h3k27ac = True
                cardiac_enhancer_count += 1
                # Extract signal value if available
                signal = exp.get('quality_metrics', {}).get('NSC', 0)
                if signal > 0:
                    enhancer_signal_values.append(signal)
                    
            elif 'h3k4me3' in target_label:
                has_h3k4me3 = True
                
            elif 'h3k4me1' in target_label:
                has_h3k4me1 = True
            
            # Check for DNase-seq
            if 'dnase' in assay:
                has_dnase = True
        
        # Determine chromatin state
        if has_h3k4me3 and has_h3k27ac:
            chromatin_state = 'Active Promoter'
        elif has_h3k27ac and has_h3k4me1:
            chromatin_state = 'Strong Enhancer'
        elif has_h3k4me1:
            chromatin_state = 'Weak Enhancer'
        elif has_dnase:
            chromatin_state = 'Open Chromatin'
        else:
            chromatin_state = 'Unknown'
        
        # Calculate regulatory score
        # Score based on presence of multiple regulatory marks
        score_components = []
        if has_h3k4me3:
            score_components.append(0.30)  # Active promoter (30%)
        if has_h3k27ac:
            score_components.append(0.35)  # Active enhancer (35%)
        if has_h3k4me1:
            score_components.append(0.20)  # Enhancer mark (20%)
        if has_dnase:
            score_components.append(0.15)  # Open chromatin (15%)
        
        regulatory_score = sum(score_components)
        
        # Average enhancer strength
        avg_enhancer_strength = (
            sum(enhancer_signal_values) / len(enhancer_signal_values)
            if enhancer_signal_values else 0.0
        )
        
        # Tissue specificity (placeholder - requires multi-tissue comparison)
        # For now, use binary: cardiac-specific experiments = 1.0
        tissue_specificity = 1.0 if len(experiments) > 0 else 0.0
        
        has_cardiac_regulatory = regulatory_score > 0.3
        
        return {
            'has_cardiac_regulatory': has_cardiac_regulatory,
            'regulatory_score': regulatory_score,
            'active_promoter': has_h3k4me3,
            'active_enhancer': has_h3k27ac,
            'open_chromatin': has_dnase,
            'chromatin_state': chromatin_state,
            'num_cardiac_enhancers': cardiac_enhancer_count,
            'enhancer_strength': avg_enhancer_strength,
            'tissue_specificity': tissue_specificity
        }
    
    def _get_no_data_result(self) -> Dict:
        """Return default result when no epigenomic data available."""
        return {
            'has_cardiac_regulatory': False,
            'regulatory_score': 0.0,
            'active_promoter': False,
            'active_enhancer': False,
            'open_chromatin': False,
            'chromatin_state': 'Unknown',
            'num_cardiac_enhancers': 0,
            'enhancer_strength': 0.0,
            'tissue_specificity': 0.0
        }
    
    async def get_regulatory_enrichment_score(
        self,
        genes: List[str]
    ) -> float:
        """
        Calculate regulatory enrichment score for a gene set.
        
        Score = (genes with cardiac regulatory activity / total genes) * 
                average regulatory score
        
        Args:
            genes: List of gene symbols
            
        Returns:
            Regulatory enrichment score (0.0 to 1.0)
        """
        regulatory_data = await self.get_cardiac_regulatory_activity(genes)
        
        genes_with_regulatory = sum(
            1 for data in regulatory_data.values()
            if data['has_cardiac_regulatory']
        )
        
        if genes_with_regulatory == 0:
            return 0.0
        
        # Calculate average regulatory score
        avg_regulatory_score = sum(
            data['regulatory_score'] for data in regulatory_data.values()
            if data['has_cardiac_regulatory']
        ) / genes_with_regulatory
        
        # Enrichment: proportion with regulatory activity * avg score
        proportion_with_regulatory = genes_with_regulatory / len(genes)
        enrichment_score = proportion_with_regulatory * avg_regulatory_score
        
        logger.info(
            f"Regulatory enrichment score: {enrichment_score:.3f} "
            f"({genes_with_regulatory}/{len(genes)} genes with cardiac regulatory activity, "
            f"avg score = {avg_regulatory_score:.3f})"
        )
        
        return enrichment_score
    
    async def get_genes_with_cardiac_enhancers(
        self,
        genes: List[str],
        min_enhancer_count: int = 1
    ) -> List[str]:
        """
        Get list of genes with cardiac-specific enhancers.
        
        Args:
            genes: List of gene symbols to check
            min_enhancer_count: Minimum number of cardiac enhancers required
            
        Returns:
            List of gene symbols with cardiac enhancers
        """
        regulatory_data = await self.get_cardiac_regulatory_activity(genes)
        
        enhancer_genes = [
            gene for gene, data in regulatory_data.items()
            if data['num_cardiac_enhancers'] >= min_enhancer_count
        ]
        
        logger.info(
            f"Identified {len(enhancer_genes)} / {len(genes)} genes with "
            f">= {min_enhancer_count} cardiac enhancers"
        )
        
        return enhancer_genes
    
    async def close(self):
        """Cleanup resources."""
        # Cache manager doesn't need async cleanup
        logger.info("EpigenomicClient closed")
