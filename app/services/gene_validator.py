"""Gene identifier validation and normalization service."""

import logging
from typing import List, Optional, Dict, Any
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models import GeneInfo, ValidationResult
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GeneValidator:
    """Validates and normalizes gene identifiers using MyGene.info API."""
    
    MYGENE_API_URL = "https://mygene.info/v3"
    SPECIES = "human"
    
    def __init__(self):
        """Initialize the gene validator."""
        self.settings = get_settings()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"{self.settings.app_name}/1.0"
        })
    
    def validate_genes(self, gene_ids: List[str]) -> ValidationResult:
        """
        Validate a list of gene identifiers.
        
        Args:
            gene_ids: List of gene identifiers to validate
            
        Returns:
            ValidationResult containing valid genes, invalid genes, and warnings
        """
        logger.info(f"Validating {len(gene_ids)} gene identifiers (input count: {len(gene_ids)})")
        logger.info(f"First 10 input genes: {gene_ids[:10]}")
        
        valid_genes: List[GeneInfo] = []
        invalid_genes: List[str] = []
        warnings: List[str] = []
        seen_symbols: Dict[str, str] = {}  # Track symbol -> original input mapping
        
        # Log if there are duplicates in input
        unique_inputs = set(gene_ids)
        if len(unique_inputs) < len(gene_ids):
            dup_count = len(gene_ids) - len(unique_inputs)
            logger.warning(f"Input contains {dup_count} duplicate gene IDs in the input list")
        
        for gene_id in gene_ids:
            try:
                gene_info = self.normalize_identifier(gene_id)
                if gene_info:
                    # Check for duplicates by symbol
                    if gene_info.symbol in seen_symbols:
                        original_input = seen_symbols[gene_info.symbol]
                        if original_input != gene_id:
                            warning_msg = f"Duplicate gene: '{gene_id}' maps to same symbol as '{original_input}' ({gene_info.symbol})"
                            warnings.append(warning_msg)
                            logger.debug(warning_msg)
                        # Skip adding duplicate
                        continue
                    
                    valid_genes.append(gene_info)
                    seen_symbols[gene_info.symbol] = gene_id
                    logger.debug(f"Successfully validated gene: {gene_id} -> {gene_info.symbol}")
                else:
                    invalid_genes.append(gene_id)
                    logger.warning(f"Failed to validate gene: {gene_id}")
            except Exception as e:
                logger.error(f"Error validating gene {gene_id}: {str(e)}")
                invalid_genes.append(gene_id)
                warnings.append(f"Error validating {gene_id}: {str(e)}")
        
        logger.info(
            f"Validation complete: {len(valid_genes)} valid (unique), "
            f"{len(invalid_genes)} invalid, {len(warnings)} warnings"
        )
        
        # Alert if counts don't match
        if len(valid_genes) + len(invalid_genes) != len(unique_inputs):
            logger.warning(
                f"Gene count mismatch! Input: {len(gene_ids)} unique ({len(unique_inputs)}), "
                f"Output: {len(valid_genes)} valid + {len(invalid_genes)} invalid = {len(valid_genes) + len(invalid_genes)}"
            )
        
        if len(warnings) > 0:
            logger.info(f"Duplicate warnings (first 5): {warnings[:5]}")
        
        return ValidationResult(
            valid_genes=valid_genes,
            invalid_genes=invalid_genes,
            warnings=warnings
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10)
    )
    def normalize_identifier(self, gene_id: str) -> Optional[GeneInfo]:
        """
        Normalize gene identifier to standard format using MyGene.info.
        
        ROBUSTNESS:
        - Handles special characters (Greek letters, hyphens, etc.)
        - Maps common alternative names to standard symbols
        - Cleans and normalizes input
        - Provides fallback for API failures
        
        Args:
            gene_id: Gene identifier (symbol, Entrez ID, Ensembl ID, etc.)
            
        Returns:
            GeneInfo object if successful, None otherwise
        """
        try:
            # Clean and normalize input
            cleaned_id = self._clean_gene_id(gene_id)
            
            # Try to map common alternative names
            mapped_id = self._map_common_names(cleaned_id)
            
            # Query MyGene.info API
            response = self._query_mygene(mapped_id)
            
            if not response:
                logger.debug(f"No results from MyGene.info for: {gene_id} (cleaned: {cleaned_id}, mapped: {mapped_id})")
                # Use fallback validation if no API results
                return self._create_fallback_gene_info(gene_id)
            
            # Extract gene information
            gene_info = self._extract_gene_info(gene_id, response)
            
            # Validate species
            if gene_info and gene_info.species != "Homo sapiens":
                logger.warning(
                    f"Gene {gene_id} is not from Homo sapiens: {gene_info.species}"
                )
                return None
            
            return gene_info
            
        except Exception as e:
            # Enhanced error handling for various API failures
            error_str = str(e).lower()
            
            # Check for various types of connectivity/API issues
            connectivity_errors = [
                'connection', 'resolve', 'network', 'timeout', 'timed out',
                'response ended prematurely', 'connection broken', 'read timeout',
                'connection reset', 'connection aborted', 'ssl error', 'certificate'
            ]
            
            if any(err in error_str for err in connectivity_errors):
                logger.warning(f"API connectivity issue for {gene_id}: {str(e)}")
                # Use fallback validation for connectivity issues
                return self._create_fallback_gene_info(gene_id)
            else:
                logger.error(f"Error normalizing identifier {gene_id}: {str(e)}")
                # For non-connectivity errors, use fallback as well to be robust
                return self._create_fallback_gene_info(gene_id)
    
    def _is_valid_gene_symbol(self, gene_id: str) -> bool:
        """
        Check if a string looks like a valid gene symbol.

        Stricter heuristics to prevent invalid symbols like "TTNT2":
        - 2-15 characters (minimum 2 to avoid single letters)
        - Alphanumeric with hyphens allowed
        - Starts with a letter
        - Cannot end with more than 2 consecutive digits
        - Cannot have suspicious patterns (like repeating letters)
        - Must contain at least one vowel (a,e,i,o,u) or be a known abbreviation

        Args:
            gene_id: Gene identifier to check

        Returns:
            True if it looks like a valid gene symbol
        """
        if not gene_id or len(gene_id) < 2 or len(gene_id) > 15:
            return False

        # Must start with a letter
        if not gene_id[0].isalpha():
            return False

        # Only alphanumeric and hyphens
        for char in gene_id:
            if not (char.isalnum() or char == '-'):
                return False

        # Cannot end with more than 2 consecutive digits (rejects "TTNT2", "GENE1234", etc.)
        import re
        if re.search(r'\d{3,}$', gene_id):
            return False

        # Check for suspicious repeating patterns (like "AAAA", "TTT", etc.)
        # Allow some repeats (like "TTN") but reject obvious nonsense
        if len(set(gene_id.upper())) < len(gene_id) * 0.4:  # Less than 40% unique characters
            return False

        # Must contain at least one vowel (unless it's a known abbreviation or short gene)
        vowels = set('aeiouAEIOU')
        has_vowel = any(c in vowels for c in gene_id)

        # Known abbreviations that don't have vowels
        known_abbrevs = {'BRCA', 'TP53', 'MYC', 'SRC', 'JAK', 'STAT', 'MAPK', 'ERK', 'JNK', 'PI3K', 'MTOR', 'ATM', 'ATR', 'CHK', 'CDK', 'GSK', 'PTEN', 'RB1', 'APC', 'NF1', 'NF2', 'VHL', 'WT1', 'MEN1', 'RET', 'PTC', 'TRK', 'ALK', 'ROS', 'MET', 'KIT', 'PDGF', 'VEGF', 'EGF', 'TGF', 'IGF', 'FGF', 'HGF', 'SCF', 'GCSF', 'GMCSF', 'IL1', 'IL2', 'IL3', 'IL4', 'IL5', 'IL6', 'IL7', 'IL8', 'IL9', 'IL10', 'IL11', 'IL12', 'IL13', 'TNF', 'IFN', 'MHC', 'HLA', 'MHC', 'TCR', 'BCR', 'FAS', 'BCL', 'BAK', 'BAX', 'BID', 'BAD', 'NOXA', 'PUMA', 'XIAP', 'SMAC', 'IAP', 'CASP', 'PARP', 'ATM', 'ATR', 'DNA', 'RNA', 'mRNA', 'tRNA', 'rRNA', 'miRNA', 'siRNA', 'lncRNA', 'circRNA'}

        upper_gene = gene_id.upper()

        # Allow genes without vowels if they're short (2-4 chars) or known abbreviations
        if not has_vowel and upper_gene not in known_abbrevs:
            if len(upper_gene) > 4:  # Longer genes should have vowels
                # But allow if it follows common gene naming patterns (like TNNT2, MYBPC3)
                # These are typically [letters][number] patterns
                if not re.match(r'^[A-Z]+[A-Z0-9]*\d+$', upper_gene):
                    return False

        # Additional check: reject genes that look like obvious typos or invalid patterns
        # For example, TTNT2 looks like it should be TNNT2
        suspicious_patterns = [
            r'^TTN.*2$',  # TTN followed by something ending with 2 (should be TNNT2)
        ]
        for pattern in suspicious_patterns:
            if re.match(pattern, upper_gene):
                return False

        return True
    
    def _create_fallback_gene_info(self, gene_id: str) -> Optional[GeneInfo]:
        """
        Create fallback GeneInfo when API validation fails.

        This is now more conservative - only accepts genes that pass strict validation
        and are likely to be real gene symbols.

        Args:
            gene_id: Gene identifier to create fallback for

        Returns:
            GeneInfo object if the gene_id passes strict validation, None otherwise
        """
        # Clean the gene ID
        cleaned_id = self._clean_gene_id(gene_id)

        # Use stricter validation for fallback (don't accept suspicious symbols)
        if self._is_valid_gene_symbol_strict(cleaned_id):
            logger.warning(f"Creating fallback gene info for {gene_id} -> {cleaned_id} (API validation failed)")
            return GeneInfo(
                input_id=gene_id,
                entrez_id="unknown",
                hgnc_id=None,
                symbol=cleaned_id.upper(),
                species="Homo sapiens"
            )
        else:
            logger.warning(f"Rejecting fallback for {gene_id} -> {cleaned_id} (fails strict validation)")
            return None

    def _is_valid_gene_symbol_strict(self, gene_id: str) -> bool:
        """
        Stricter validation for fallback cases - rejects more suspicious symbols.

        Additional checks beyond basic validation:
        - Must be at least 3 characters (most gene symbols are 3+ chars)
        - Cannot have more than 2 consecutive identical letters
        - Cannot be all consonants with no vowels (unless known abbrev)
        - Cannot end with 3+ digits

        Args:
            gene_id: Gene identifier to check strictly

        Returns:
            True if it passes strict validation
        """
        # First pass basic validation
        if not self._is_valid_gene_symbol(gene_id):
            return False

        # Additional strict checks
        if len(gene_id) < 3:
            return False

        # Check for 3+ consecutive identical letters (rejects "AAAT", "TTTT", etc.)
        for i in range(len(gene_id) - 2):
            if gene_id[i] == gene_id[i+1] == gene_id[i+2]:
                return False

        # Check for ending with 3+ digits (very suspicious)
        import re
        if re.search(r'\d{3,}$', gene_id):
            return False

        return True
    
    def _clean_gene_id(self, gene_id: str) -> str:
        """
        Clean and normalize gene identifier.
        
        Args:
            gene_id: Raw gene identifier
            
        Returns:
            Cleaned gene identifier
        """
        # Strip whitespace
        cleaned = gene_id.strip()
        
        # Convert Greek letters to standard names
        greek_map = {
            'α': 'alpha',
            'β': 'beta',
            'γ': 'gamma',
            'δ': 'delta',
            'ε': 'epsilon',
            'ζ': 'zeta',
            'η': 'eta',
            'θ': 'theta',
            'κ': 'kappa',
            'λ': 'lambda',
            'μ': 'mu',
            'ν': 'nu',
            'ξ': 'xi',
            'π': 'pi',
            'ρ': 'rho',
            'σ': 'sigma',
            'τ': 'tau',
            'φ': 'phi',
            'χ': 'chi',
            'ψ': 'psi',
            'ω': 'omega'
        }
        
        for greek, english in greek_map.items():
            if greek in cleaned.lower():
                cleaned = cleaned.replace(greek, english).replace(greek.upper(), english.upper())
        
        return cleaned
    
    def _map_common_names(self, gene_id: str) -> str:
        """
        Map common alternative gene names to standard symbols.
        
        Args:
            gene_id: Gene identifier
            
        Returns:
            Mapped gene identifier
        """
        # Common alternative names mapping
        name_map = {
            'PI3KCA': 'PIK3CA',  # Common typo
            'BETA-CATENIN': 'CTNNB1',
            'β-CATENIN': 'CTNNB1',
            'BETA-ACTIN': 'ACTB',
            'β-ACTIN': 'ACTB',
            'ALPHA-ACTIN': 'ACTA1',
            'α-ACTIN': 'ACTA1',
            'NF-KAPPAB': 'NFKB1',
            'NF-κB': 'NFKB1',
            'P53': 'TP53',
            'P21': 'CDKN1A',
            'P27': 'CDKN1B',
            'P16': 'CDKN2A',
            'MDM-2': 'MDM2',
            'BCL-2': 'BCL2',
            'BAX': 'BAX',
            'CASP-3': 'CASP3',
            'CASP-9': 'CASP9',
        }
        
        # Check uppercase version
        upper_id = gene_id.upper()
        if upper_id in name_map:
            mapped = name_map[upper_id]
            logger.info(f"Mapped alternative name: {gene_id} -> {mapped}")
            return mapped
        
        return gene_id
    
    def _query_mygene(self, gene_id: str) -> Optional[Dict[str, Any]]:
        """
        Query MyGene.info API for gene information with robust error handling.
        
        Args:
            gene_id: Gene identifier
            
        Returns:
            API response data or None
        """
        # Try query endpoint first (supports multiple ID types)
        url = f"{self.MYGENE_API_URL}/query"
        params = {
            "q": gene_id,
            "species": self.SPECIES,
            "fields": "entrezgene,symbol,HGNC,taxid,name",
            "size": 1
        }
        
        try:
            # Use a fresh session for each request to avoid connection issues
            response = requests.get(
                url,
                params=params,
                timeout=(10, 30),  # (connect_timeout, read_timeout)
                headers={
                    "User-Agent": f"{self.settings.app_name}/1.0",
                    "Accept": "application/json",
                    "Connection": "close"  # Prevent connection reuse issues
                }
            )
            response.raise_for_status()
            
            # Handle empty response
            if not response.content:
                logger.warning(f"Empty response from MyGene.info for {gene_id}")
                return None
            
            data = response.json()
            
            # Check if we got results
            if data.get("hits") and len(data["hits"]) > 0:
                return data["hits"][0]
            
            # If query didn't work, try gene endpoint (for Entrez IDs)
            if gene_id.isdigit():
                return self._query_mygene_by_id(gene_id)
            
            return None
            
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            # Specific handling for connectivity issues
            logger.warning(f"MyGene.info connectivity issue for {gene_id}: {str(e)}")
            raise
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors (4xx, 5xx)
            if e.response.status_code >= 500:
                logger.warning(f"MyGene.info server error for {gene_id}: {e.response.status_code}")
            else:
                logger.error(f"MyGene.info client error for {gene_id}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"MyGene.info API request failed for {gene_id}: {str(e)}")
            raise
    
    def _query_mygene_by_id(self, entrez_id: str) -> Optional[Dict[str, Any]]:
        """
        Query MyGene.info by Entrez ID directly with robust error handling.
        
        Args:
            entrez_id: Entrez gene ID
            
        Returns:
            API response data or None
        """
        url = f"{self.MYGENE_API_URL}/gene/{entrez_id}"
        params = {
            "fields": "entrezgene,symbol,HGNC,taxid,name"
        }
        
        try:
            # Use fresh request with robust settings
            response = requests.get(
                url,
                params=params,
                timeout=(10, 30),  # (connect_timeout, read_timeout)
                headers={
                    "User-Agent": f"{self.settings.app_name}/1.0",
                    "Accept": "application/json",
                    "Connection": "close"
                }
            )
            
            if response.status_code == 404:
                logger.debug(f"Gene {entrez_id} not found in MyGene.info")
                return None
            
            response.raise_for_status()
            
            # Handle empty response
            if not response.content:
                logger.warning(f"Empty response from MyGene.info gene endpoint for {entrez_id}")
                return None
            
            return response.json()
            
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            # Specific handling for connectivity issues
            logger.warning(f"MyGene.info gene endpoint connectivity issue for {entrez_id}: {str(e)}")
            raise
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors (4xx, 5xx)
            if e.response.status_code >= 500:
                logger.warning(f"MyGene.info server error for gene {entrez_id}: {e.response.status_code}")
            else:
                logger.error(f"MyGene.info client error for gene {entrez_id}: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"MyGene.info gene endpoint failed for {entrez_id}: {str(e)}")
            raise
    
    def _extract_gene_info(
        self,
        input_id: str,
        api_response: Dict[str, Any]
    ) -> Optional[GeneInfo]:
        """
        Extract GeneInfo from MyGene.info API response.
        
        Args:
            input_id: Original input identifier
            api_response: MyGene.info API response
            
        Returns:
            GeneInfo object or None
        """
        try:
            # Extract required fields
            entrez_id = api_response.get("entrezgene")
            symbol = api_response.get("symbol")
            
            if not entrez_id or not symbol:
                logger.warning(
                    f"Missing required fields for {input_id}: "
                    f"entrez_id={entrez_id}, symbol={symbol}"
                )
                return None
            
            # Extract optional HGNC ID
            hgnc_id = None
            if "HGNC" in api_response:
                hgnc_data = api_response["HGNC"]
                if isinstance(hgnc_data, str):
                    hgnc_id = hgnc_data
                elif isinstance(hgnc_data, int):
                    hgnc_id = f"HGNC:{hgnc_data}"
            
            # Determine species from taxid
            taxid = api_response.get("taxid", 9606)
            species = "Homo sapiens" if taxid == 9606 else f"taxid:{taxid}"
            
            return GeneInfo(
                input_id=input_id,
                entrez_id=str(entrez_id),
                hgnc_id=hgnc_id,
                symbol=symbol,
                species=species
            )
            
        except Exception as e:
            logger.error(f"Error extracting gene info for {input_id}: {str(e)}")
            return None
    
    def batch_validate(
        self,
        gene_ids: List[str],
        batch_size: int = 100
    ) -> ValidationResult:
        """
        Validate genes in batches for better performance.
        
        Args:
            gene_ids: List of gene identifiers
            batch_size: Number of genes per batch
            
        Returns:
            ValidationResult
        """
        logger.info(f"Batch validating {len(gene_ids)} genes (batch_size={batch_size})")
        
        all_valid: List[GeneInfo] = []
        all_invalid: List[str] = []
        all_warnings: List[str] = []
        
        # Process in batches
        for i in range(0, len(gene_ids), batch_size):
            batch = gene_ids[i:i + batch_size]
            logger.debug(f"Processing batch {i // batch_size + 1}")
            
            result = self.validate_genes(batch)
            all_valid.extend(result.valid_genes)
            all_invalid.extend(result.invalid_genes)
            all_warnings.extend(result.warnings)
        
        return ValidationResult(
            valid_genes=all_valid,
            invalid_genes=all_invalid,
            warnings=all_warnings
        )
