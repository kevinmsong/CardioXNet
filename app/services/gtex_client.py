"""GTEx Portal API client for tissue expression data."""

import logging
import requests
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class GTExExpression:
    """GTEx gene expression data."""
    
    gene_symbol: str
    tissue: str
    median_tpm: float
    mean_tpm: float
    tissue_sample_count: int


@dataclass 
class CardiacExpressionProfile:
    """Cardiac-specific expression profile for a gene."""
    
    gene_symbol: str
    cardiac_median_tpm: float
    cardiac_mean_tpm: float
    max_non_cardiac_tpm: float
    cardiac_specificity_ratio: float
    total_tissues: int
    cardiac_rank: int  # Rank among all tissues by expression


class GTExClient:
    """
    Client for querying GTEx Portal API.
    
    GTEx Portal provides tissue-specific gene expression data from 
    54 human tissue types including cardiac tissues.
    
    API Documentation: https://gtexportal.org/api/v2/redoc
    """
    
    def __init__(self):
        """Initialize GTEx client."""
        self.settings = get_settings()
        self.base_url = "https://gtexportal.org/api/v2"
        self.session = requests.Session()
        
        # GTEx cardiac tissue identifiers - focused on heart-specific validation
        self.cardiac_tissues = {
            'Heart_Left_Ventricle': 'Heart - Left Ventricle',
            'Heart_Atrial_Appendage': 'Heart - Atrial Appendage'
        }
        
        # Cardiac-specific tissue IDs for targeted validation
        self.cardiac_tissue_ids = list(self.cardiac_tissues.keys())
        
        # Common non-cardiac reference tissues for specificity calculation
        self.reference_tissues = [
            'Brain_Cortex', 'Liver', 'Lung', 'Kidney_Cortex', 
            'Muscle_Skeletal', 'Adipose_Subcutaneous', 'Skin_Sun_Exposed_Lower_leg'
        ]
        
        # Cache for dynamic lookups to avoid repeated API calls
        self._gencode_cache: Dict[str, Optional[str]] = {}

        # Cache for cardiac specificity profiles — avoids redundant GTEx API calls
        self._cardiac_specificity_cache: Dict[str, CardiacExpressionProfile] = {}

        # Track genes we've already logged warnings for (avoid spam)
        self._logged_warnings: set = set()
        
        logger.info("GTEx client initialized for cardiac expression analysis")
    
    def _get_versioned_gencode_id(self, gene_symbol: str) -> Optional[str]:
        """
        Convert gene symbol to versioned GENCODE ID for GTEx API v2.

        GTEx API v2 ``medianGeneExpression`` requires the *current* versioned
        GENCODE ID (e.g. ENSG00000173020.15). A hardcoded version suffix goes
        stale whenever GTEx bumps the GENCODE patch (e.g. GATA4 was .14, now .17)
        and then silently returns an empty tissue list — which previously zeroed
        out the cardiac tissue score for every gene in the static map. So we
        resolve the live ID first and fall back to the (best-effort, possibly
        stale) static map only when the lookup endpoint is unreachable.
        """
        # Check cache first
        cache_key = gene_symbol.upper()
        if cache_key in self._gencode_cache:
            cached_id = self._gencode_cache[cache_key]
            if cached_id:
                logger.debug(f"Using cached GENCODE ID for {gene_symbol}: {cached_id}")
            return cached_id

        # Offline / API-down fallback only. Versions here may be stale; the live
        # lookup below is authoritative and runs first.
        static_fallback = {
            # Natriuretic peptides and signaling (corrected from API lookup)
            'NPPA': 'ENSG00000175206.10',  # Corrected from API
            'NPPB': 'ENSG00000120937.8',   # BNP - corrected from API
            'NPR1': 'ENSG00000169418.12',
            'NPR2': 'ENSG00000159899.14',
            
            # Cardiac contractile proteins  
            'TTN': 'ENSG00000155657.26',   # Titin - corrected version
            'MYH6': 'ENSG00000197616.16',  # Myosin heavy chain 6 (alpha)
            'MYH7': 'ENSG00000092054.12',  # Myosin heavy chain 7 (beta) - corrected from API
            'MYBPC3': 'ENSG00000134571.10', # Myosin binding protein C3 - corrected version
            'TNNT2': 'ENSG00000118194.11', # Troponin T2
            'TNNI3': 'ENSG00000129991.8', # Troponin I3
            'TPM1': 'ENSG00000140416.16', # Tropomyosin 1
            'ACTC1': 'ENSG00000159251.15', # Actin alpha cardiac 1
            'MYL2': 'ENSG00000111245.14',  # Myosin light chain 2
            'MYL3': 'ENSG00000160808.13',  # Myosin light chain 3
            'ACTN2': 'ENSG00000077522.16', # Actinin alpha 2
            'DES': 'ENSG00000175084.17',   # Desmin
            'VCL': 'ENSG00000035403.17',   # Vinculin
            
            # Cardiac transcription factors
            'NKX2-5': 'ENSG00000183072.13',
            'GATA4': 'ENSG00000136574.14',
            'GATA5': 'ENSG00000102974.12',
            'GATA6': 'ENSG00000141448.15',
            'MEF2C': 'ENSG00000081189.15',
            'MEF2A': 'ENSG00000068305.14',
            'TBX5': 'ENSG00000089225.15',
            'TBX20': 'ENSG00000164532.13',
            'HAND1': 'ENSG00000113196.10',
            'HAND2': 'ENSG00000164107.14',
            'ISL1': 'ENSG00000016082.17',
            'MYOCD': 'ENSG00000141052.12',
            
            # Ion channels and calcium handling
            'SCN5A': 'ENSG00000183873.17',  # Sodium channel
            'KCNQ1': 'ENSG00000053918.18',  # Potassium channel
            'KCNH2': 'ENSG00000055118.15',  # hERG
            'KCNJ2': 'ENSG00000123700.14',  # Kir2.1
            'CACNA1C': 'ENSG00000151067.16', # L-type calcium channel
            'RYR2': 'ENSG00000198626.13',   # Ryanodine receptor 2
            'ATP2A2': 'ENSG00000174437.17', # SERCA2
            'PLN': 'ENSG00000198523.7',     # Phospholamban
            'CASQ2': 'ENSG00000118729.12',  # Calsequestrin 2
            'JPH2': 'ENSG00000149596.12',   # Junctophilin 2
            
            # Adrenergic signaling
            'ADRB1': 'ENSG00000043591.18',  # Beta-1 adrenergic receptor
            'ADRB2': 'ENSG00000169252.7',   # Beta-2 adrenergic receptor
            'GRK2': 'ENSG00000173020.15',   # G protein-coupled receptor kinase 2
            'GRK5': 'ENSG00000198873.11',   # G protein-coupled receptor kinase 5
            
            # Other cardiovascular genes
            'CCNB1': 'ENSG00000134057.14',  # Cyclin B1
            'RET': 'ENSG00000165731.14',    # RET proto-oncogene
            'SMURF1': 'ENSG00000198742.13',
            'SMURF2': 'ENSG00000163584.14',
            'NCOA4': 'ENSG00000138279.9',
            'LRP2': 'ENSG00000081479.20',
            'GPC3': 'ENSG00000147257.15',
            'IFT172': 'ENSG00000138619.13',
        }
        
        # Live lookup is authoritative — it always returns the current versioned
        # ID for the requested symbol. Fall back to the static map only if the
        # endpoint is unreachable.
        gencode_id = self._lookup_gene_id_dynamic(gene_symbol)
        if not gencode_id:
            gencode_id = static_fallback.get(cache_key)
            if gencode_id:
                logger.debug(f"Using static fallback GENCODE ID for {gene_symbol}: {gencode_id}")

        # Cache the result (even if None to avoid repeated failed lookups)
        self._gencode_cache[cache_key] = gencode_id
        if gencode_id:
            logger.info(f"[OK] Resolved GENCODE ID: {gene_symbol} -> {gencode_id}")
        return gencode_id
    
    def _lookup_gene_id_dynamic(self, gene_symbol: str) -> Optional[str]:
        """
        Dynamically lookup GENCODE ID for a gene symbol using GTEx API.
        
        Args:
            gene_symbol: Gene symbol to lookup
            
        Returns:
            Versioned GENCODE ID if found, None otherwise
        """
        try:
            # Use GTEx gene lookup endpoint with increased timeout and retry logic
            url = f"{self.base_url}/reference/gene"
            params = {
                'geneId': gene_symbol,  # Can search by symbol
                'datasetId': 'gtex_v8',
                'pageSize': 10
            }
            
            # Try multiple times with increasing timeout
            for attempt in range(3):
                try:
                    timeout = 15 + (attempt * 5)  # 15s, 20s, 25s
                    response = self.session.get(url, params=params, timeout=timeout)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'data' in data and data['data']:
                            # Look for exact symbol match first
                            for gene_info in data['data']:
                                api_symbol = gene_info.get('geneSymbol', '').upper()
                                if api_symbol == gene_symbol.upper():
                                    gencode_id = gene_info.get('gencodeId')
                                    if gencode_id:
                                        logger.info(f"[OK] Dynamic lookup exact match: {gene_symbol} -> {gencode_id}")
                                        return gencode_id
                            
                            # If no exact match, try the first result (API usually returns most relevant first)
                            if data['data']:
                                first_result = data['data'][0]
                                gencode_id = first_result.get('gencodeId')
                                api_symbol = first_result.get('geneSymbol', '')
                                if gencode_id:
                                    logger.info(f"[OK] Dynamic lookup first result: {gene_symbol} -> {api_symbol} -> {gencode_id}")
                                    return gencode_id
                    
                    # If we got here, no valid data found
                    if attempt < 2:
                        logger.debug(f"Retry {attempt + 1}/3 for {gene_symbol}")
                        continue
                    else:
                        break
                        
                except requests.exceptions.Timeout:
                    if attempt < 2:
                        logger.warning(f"Timeout on attempt {attempt + 1}/3 for {gene_symbol}, retrying...")
                        continue
                    else:
                        logger.warning(f"All timeout attempts failed for {gene_symbol}")
                        return None
            
            logger.warning(f"[FAIL] Dynamic lookup failed for gene symbol: {gene_symbol} (no results after 3 attempts)")
            return None
            
        except Exception as e:
            logger.warning(f"[FAIL] Dynamic gene lookup error for {gene_symbol}: {e}")
            return None
    
    async def get_gene_expression(
        self, 
        gene_symbol: str,
        tissues: Optional[List[str]] = None
    ) -> List[GTExExpression]:
        """
        Get gene expression across tissues from GTEx.
        
        Args:
            gene_symbol: HGNC gene symbol (e.g., 'MYH7', 'MYBPC3')
            tissues: List of tissue identifiers (default: all tissues)
            
        Returns:
            List of GTExExpression objects for each tissue
        """
        # Convert gene symbol to Ensembl ID
        gencode_id = self._get_versioned_gencode_id(gene_symbol)
        if not gencode_id:
            # Only log warning once per gene to avoid spam
            if gene_symbol not in self._logged_warnings:
                logger.warning(f"No versioned GENCODE mapping found for gene symbol: {gene_symbol}")
                self._logged_warnings.add(gene_symbol)
            return []
        
        logger.debug(f"Using GENCODE ID {gencode_id} for gene {gene_symbol}")
        
        try:
            # Try multiple GTEx API approaches
            expressions = []
            
            # Use GTEx v2 medianGeneExpression endpoint - the correct tissue API
            url = f"{self.base_url}/expression/medianGeneExpression"
            
            # Prepare parameters according to GTEx API v2 tissue documentation
            params = {
                'gencodeId': gencode_id,  # Single versioned GENCODE ID required
                'datasetId': 'gtex_v8'
            }
            
            # Get all tissues unless specific tissues are requested
            # This allows proper cardiac specificity calculation
            logger.debug(f"Querying GTEx for {gene_symbol} expression across all tissues")
            
            # Build GTEx API call - get all tissues for proper specificity analysis
            full_url = f"{url}?gencodeId={gencode_id}&datasetId={params['datasetId']}"
            response = self.session.get(full_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    # Parse GTEx v2 median expression API response format
                    for tissue_expr in data['data']:
                        tissue_id = tissue_expr.get('tissueSiteDetailId', '')
                        median_value = tissue_expr.get('median', 0.0)
                        unit = tissue_expr.get('unit', 'TPM')
                        
                        if tissue_id and median_value is not None:
                            expressions.append(GTExExpression(
                                gene_symbol=gene_symbol,
                                tissue=tissue_id,
                                median_tpm=float(median_value),
                                mean_tpm=float(median_value),  # Median approximation for mean
                                tissue_sample_count=1  # Not provided by median endpoint
                            ))
                    
                    if expressions:
                        # Calculate cardiac specificity metrics
                        cardiac_count = len([exp for exp in expressions if exp.tissue in self.cardiac_tissue_ids])
                        logger.info(f"Retrieved GTEx cardiac expression for {gene_symbol}: {cardiac_count}/{len(expressions)} cardiac tissues")
                        return expressions
                else:
                    logger.debug(f"No median expression data returned for {gene_symbol} (GENCODE: {gencode_id})")
            else:
                logger.debug(f"GTEx median expression API returned status {response.status_code} for {gene_symbol}")
            
            # If API call failed, log and return empty list for fallback handling
            logger.debug(f"GTEx API unavailable for {gene_symbol}, using cardiac gene classification fallback")
            return []
            
        except Exception as e:
            logger.debug(f"GTEx expression query error for {gene_symbol}: {e}")
            return []
    
    async def calculate_cardiac_specificity(
        self, 
        gene_symbol: str
    ) -> Optional[CardiacExpressionProfile]:
        """
        Calculate cardiac specificity ratio for a gene.
        
        Cardiac specificity = max(cardiac_expression) / max(non_cardiac_expression)
        
        Args:
            gene_symbol: Gene symbol to analyze
            
        Returns:
            CardiacExpressionProfile with specificity metrics
        """
        try:
            expressions = await self.get_gene_expression(gene_symbol)
            
            if not expressions:
                return None
            
            # Separate cardiac and non-cardiac tissues
            cardiac_expressions = []
            non_cardiac_expressions = []
            
            for exp in expressions:
                if any(cardiac_id in exp.tissue for cardiac_id in self.cardiac_tissues.keys()):
                    cardiac_expressions.append(exp)
                else:
                    non_cardiac_expressions.append(exp)
            
            if not cardiac_expressions:
                logger.warning(f"No cardiac expression data found for {gene_symbol}")
                return None
            
            # Calculate cardiac metrics
            cardiac_median_tpm = max(exp.median_tpm for exp in cardiac_expressions)
            cardiac_mean_tpm = max(exp.mean_tpm for exp in cardiac_expressions)
            
            # Calculate non-cardiac maximum
            if non_cardiac_expressions:
                max_non_cardiac_tpm = max(exp.median_tpm for exp in non_cardiac_expressions)
            else:
                max_non_cardiac_tpm = 0.1  # Avoid division by zero
            
            # Calculate specificity ratio
            cardiac_specificity_ratio = cardiac_median_tpm / max(max_non_cardiac_tpm, 0.1)
            
            # Calculate cardiac rank (how cardiac expression ranks among all tissues)
            all_expressions = sorted(expressions, key=lambda x: x.median_tpm, reverse=True)
            cardiac_rank = len(all_expressions)  # Default to last
            
            for i, exp in enumerate(all_expressions, 1):
                if any(cardiac_id in exp.tissue for cardiac_id in self.cardiac_tissues.keys()):
                    cardiac_rank = i
                    break
            
            return CardiacExpressionProfile(
                gene_symbol=gene_symbol,
                cardiac_median_tpm=cardiac_median_tpm,
                cardiac_mean_tpm=cardiac_mean_tpm,
                max_non_cardiac_tpm=max_non_cardiac_tpm,
                cardiac_specificity_ratio=cardiac_specificity_ratio,
                total_tissues=len(expressions),
                cardiac_rank=cardiac_rank
            )
            
        except Exception as e:
            logger.error(f"Cardiac specificity calculation failed for {gene_symbol}: {e}")
            return None
    
    async def batch_cardiac_specificity(
        self,
        gene_symbols: List[str],
        max_concurrent: int = 5
    ) -> Dict[str, CardiacExpressionProfile]:
        """
        Calculate cardiac specificity for multiple genes in parallel.
        
        Args:
            gene_symbols: List of gene symbols to analyze
            max_concurrent: Maximum concurrent API requests
            
        Returns:
            Dictionary mapping gene symbols to expression profiles
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        # Deduplicate while preserving order; serve cached profiles immediately
        seen: set = set()
        unique_genes = [g for g in gene_symbols if not (g in seen or seen.add(g))]

        profiles: Dict[str, CardiacExpressionProfile] = {}
        to_fetch = []
        for gene in unique_genes:
            if gene in self._cardiac_specificity_cache:
                profiles[gene] = self._cardiac_specificity_cache[gene]
            else:
                to_fetch.append(gene)

        async def _get_specificity_with_semaphore(gene: str):
            async with semaphore:
                try:
                    profile = await self.calculate_cardiac_specificity(gene)
                    return gene, profile
                except Exception as e:
                    logger.warning(f"GTEx query failed for {gene}: {e}")
                    return gene, None

        # Execute concurrent requests only for uncached genes
        tasks = [_get_specificity_with_semaphore(gene) for gene in to_fetch]
        fetch_results = await asyncio.gather(*tasks)

        successful = len(profiles)
        failed = 0

        for gene, profile in fetch_results:
            if profile:
                self._cardiac_specificity_cache[gene] = profile
                profiles[gene] = profile
                successful += 1
            else:
                failed += 1

        logger.info(
            f"GTEx batch cardiac specificity: {successful} successful, "
            f"{failed} failed out of {len(unique_genes)} unique genes"
        )

        return profiles
    