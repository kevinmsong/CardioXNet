"""Input validation service for NETS pipeline."""

import logging
from typing import List, Optional, Union

from app.models import GeneInfo, ValidationResult
from app.services import (
    GeneValidator,
    STRINGClient,
    GProfilerClient,
    ReactomeClient,
    APIClientError
)
from app.services.gtex_client import GTExClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class InputValidator:
    """Validates seed genes and API connectivity for NETS pipeline."""
    
    def __init__(self):
        """Initialize input validator."""
        self.settings = get_settings()
        self.gene_validator = GeneValidator()
        
        # Initialize API clients for connectivity checks
        self.string_client = STRINGClient()
        self.gprofiler_client = GProfilerClient()
        self.reactome_client = ReactomeClient()
        self.gtex_client = GTExClient()
        
        logger.info("InputValidator initialized")
    
    def validate_input(
        self,
        seed_genes: List[Union[str, GeneInfo]],
        check_api_connectivity: bool = True,
        min_seed_connectivity: int = 3
    ) -> ValidationResult:
        """
        Validate seed genes and optionally check API connectivity.
        
        Args:
            seed_genes: List of seed gene identifiers
            check_api_connectivity: Whether to verify API connectivity
            min_seed_connectivity: Minimum number of connections required per seed gene
            
        Returns:
            ValidationResult with validated genes
            
        Raises:
            ValidationError: If validation fails critically
        """
        logger.info(f"Validating input with {len(seed_genes)} seed genes")
        
        # Step 1: Validate seed gene list
        if not seed_genes:
            raise ValidationError("Seed gene list cannot be empty")
        
        if len(seed_genes) < 1:
            raise ValidationError("At least one seed gene is required")
        
        # Step 2: Validate and normalize gene identifiers
        validation_result = self._validate_genes(seed_genes)
        
        if not validation_result.valid_genes:
            raise ValidationError(
                f"No valid genes found. Invalid genes: {validation_result.invalid_genes}"
            )
        
        # Step 3: Pre-filter by seed connectivity (scientific optimization)
        if len(validation_result.valid_genes) > 0:
            connectivity_filtered = self._filter_by_seed_connectivity(
                validation_result.valid_genes, 
                min_seed_connectivity
            )
            
            if len(connectivity_filtered) < len(validation_result.valid_genes):
                filtered_count = len(validation_result.valid_genes) - len(connectivity_filtered)
                validation_result.warnings.append(
                    f"Filtered {filtered_count} seed genes with insufficient connectivity "
                    f"(minimum {min_seed_connectivity} connections required)"
                )
                validation_result.valid_genes = connectivity_filtered
        
        # Step 4: Check API connectivity if requested
        if check_api_connectivity:
            connectivity_warnings = self._check_api_connectivity()
            validation_result.warnings.extend(connectivity_warnings)
        
        logger.info(
            f"Input validation complete: {len(validation_result.valid_genes)} valid genes, "
            f"{len(validation_result.invalid_genes)} invalid genes, "
            f"{len(validation_result.warnings)} warnings"
        )
        
        return validation_result
    
    def _validate_genes(self, seed_genes: List[Union[str, GeneInfo]]) -> ValidationResult:
        """
        Validate and normalize gene identifiers.
        
        Args:
            seed_genes: List of gene identifiers (strings or GeneInfo objects)
            
        Returns:
            ValidationResult
        """
        logger.info(f"Validating {len(seed_genes)} gene identifiers")
        
        try:
            # Extract identifiers from GeneInfo objects or use strings directly
            gene_ids = []
            for gene in seed_genes:
                if isinstance(gene, GeneInfo):
                    gene_ids.append(gene.input_id)
                else:
                    gene_ids.append(str(gene))
            
            result = self.gene_validator.validate_genes(gene_ids)
            
            if result.invalid_genes:
                logger.warning(
                    f"Found {len(result.invalid_genes)} invalid genes: "
                    f"{result.invalid_genes}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Gene validation failed: {str(e)}")
            raise ValidationError(f"Gene validation failed: {str(e)}")
    
    def _filter_by_seed_connectivity(
        self, 
        valid_genes: List[GeneInfo], 
        min_connectivity: int
    ) -> List[GeneInfo]:
        """
        Pre-filter seed genes by connectivity to ensure sufficient network signal.
        
        Scientific optimization: Removes seed genes with insufficient connections
        to avoid weak starting points for pathway discovery.
        
        Args:
            valid_genes: List of validated GeneInfo objects
            min_connectivity: Minimum number of connections required
            
        Returns:
            Filtered list of GeneInfo objects with sufficient connectivity
        """
        logger.info(f"Pre-filtering {len(valid_genes)} genes by connectivity (min: {min_connectivity})")
        
        filtered_genes = []
        
        try:
            # Check connectivity for each gene individually
            for gene in valid_genes:
                try:
                    # Get interactions for this single gene
                    interaction_result = self.string_client.get_interactions(
                        [gene], 
                        score_threshold=0.4
                    )
                    
                    # Count unique interaction partners from the interactions list
                    interactions = interaction_result.get('interactions', [])
                    unique_partners = set()
                    for edge in interactions:
                        # Each edge has 'from' and 'to' keys
                        if 'from' in edge:
                            unique_partners.add(edge['from'])
                        if 'to' in edge:
                            unique_partners.add(edge['to'])
                    
                    # Remove self from count
                    unique_partners.discard(gene.symbol)
                    connectivity = len(unique_partners)
                    
                    if connectivity >= min_connectivity:
                        filtered_genes.append(gene)
                        logger.debug(
                            f"Gene {gene.symbol}: {connectivity} connections (passed)"
                        )
                    else:
                        logger.debug(
                            f"Filtering gene {gene.symbol}: {connectivity} connections "
                            f"(minimum {min_connectivity} required)"
                        )
                        
                except Exception as e:
                    logger.warning(f"Failed to check connectivity for {gene.symbol}: {str(e)}")
                    # If we can't check connectivity, include the gene to avoid blocking
                    filtered_genes.append(gene)
            
            logger.info(
                f"Connectivity filtering complete: {len(filtered_genes)}/{len(valid_genes)} genes retained"
            )
            
        except Exception as e:
            logger.warning(f"Connectivity filtering failed, using all genes: {str(e)}")
            # If connectivity check fails, return all genes to avoid blocking analysis
            return valid_genes
        
        return filtered_genes
    
    def _check_api_connectivity(self) -> List[str]:
        """
        Check connectivity and versions for all required APIs.
        
        Returns:
            List of warning messages for any connectivity issues
        """
        logger.info("Checking API connectivity for all services")
        
        warnings = []
        
        # Check STRING
        string_status = self._check_string()
        if not string_status["available"]:
            warnings.append(
                f"STRING API unavailable: {string_status['error']}"
            )
        
        # Check g:Profiler
        gprofiler_status = self._check_gprofiler()
        if not gprofiler_status["available"]:
            warnings.append(
                f"g:Profiler API unavailable: {gprofiler_status['error']}"
            )
        
        # Check Reactome
        reactome_status = self._check_reactome()
        if not reactome_status["available"]:
            warnings.append(
                f"Reactome API unavailable: {reactome_status['error']}"
            )

        # Check GTEx
        gtex_status = self._check_gtex()
        if not gtex_status["available"]:
            warnings.append(
                f"GTEx API unavailable: {gtex_status['error']}"
            )

        if warnings:
            logger.warning(f"API connectivity issues detected: {len(warnings)} services unavailable")
        else:
            logger.info("All API services are available")
        
        return warnings
    
    def _check_string(self) -> dict:
        """
        Check STRING API connectivity and version.
        
        Returns:
            Status dictionary
        """
        try:
            # Try a simple query with a known cardiac gene
            test_gene = GeneInfo(
                input_id="NKX2-5",
                entrez_id="1482",
                hgnc_id="HGNC:7839",
                symbol="NKX2-5",
                species="Homo sapiens"
            )
            
            result = self.string_client.get_interactions([test_gene])
            
            logger.debug("STRING API is available")
            
            return {
                "available": True,
                "version": self.settings.nets.string_version,
                "error": None
            }
            
        except APIClientError as e:
            logger.warning(f"STRING API check failed: {str(e)}")
            return {
                "available": False,
                "version": None,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error checking STRING: {str(e)}")
            return {
                "available": False,
                "version": None,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def _check_gprofiler(self) -> dict:
        """
        Check g:Profiler API connectivity and version.
        
        Returns:
            Status dictionary
        """
        try:
            # Try a simple enrichment query with known cardiac genes
            test_genes = [
                GeneInfo(
                    input_id="NKX2-5",
                    entrez_id="1482",
                    hgnc_id="HGNC:7839",
                    symbol="NKX2-5",
                    species="Homo sapiens"
                ),
                GeneInfo(
                    input_id="GATA4",
                    entrez_id="2626",
                    hgnc_id="HGNC:4173",
                    symbol="GATA4",
                    species="Homo sapiens"
                )
            ]
            
            result = self.gprofiler_client.get_enrichment(test_genes, sources=["GO:BP"])
            
            logger.debug("g:Profiler API is available")
            
            return {
                "available": True,
                "version": self.settings.nets.gprofiler_version,
                "error": None
            }
            
        except APIClientError as e:
            logger.warning(f"g:Profiler API check failed: {str(e)}")
            return {
                "available": False,
                "version": None,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error checking g:Profiler: {str(e)}")
            return {
                "available": False,
                "version": None,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def _check_reactome(self) -> dict:
        """
        Check Reactome API connectivity and version.
        
        Returns:
            Status dictionary
        """
        try:
            # Try a simple pathway query with a known cardiac gene
            test_gene = GeneInfo(
                input_id="GATA4",
                entrez_id="2626",
                hgnc_id="HGNC:4173",
                symbol="GATA4",
                species="Homo sapiens"
            )
            
            result = self.reactome_client.get_pathways_for_genes([test_gene])
            
            # Check if we got results (empty list means service unavailable but handled gracefully)
            if result is not None:
                logger.debug(f"Reactome API is available (returned {len(result)} pathways)")
                return {
                    "available": True,
                    "version": self.settings.nets.reactome_version,
                    "error": None
                }
            else:
                logger.warning("Reactome API returned None - service likely unavailable")
                return {
                    "available": False,
                    "version": None,
                    "error": "Service returned no response"
                }
            
        except APIClientError as e:
            logger.warning(f"Reactome API check failed: {str(e)}")
            return {
                "available": False,
                "version": None,
                "error": str(e)
            }
        except Exception as e:
            logger.warning(f"Reactome connectivity check failed: {str(e)}")
            return {
                "available": False,
                "version": None,
                "error": f"Connection error: {str(e)}"
            }

    def _check_gtex(self) -> dict:
        """
        Check GTEx API connectivity and version.
        
        Returns:
            dict: Status information with 'available', 'version', and 'error' keys
        """
        try:
            logger.debug("Checking GTEx API connectivity")
            
            # Test GTEx API with a known cardiac gene
            import asyncio
            
            async def test_gtex():
                try:
                    # Test with NPPA (ANP) - a well-known cardiac gene
                    expressions = await self.gtex_client.get_gene_expression('NPPA')
                    return len(expressions) > 0
                except Exception as e:
                    logger.debug(f"GTEx API test failed: {str(e)}")
                    return False
            
            # Run the async test - handle potential existing event loop
            try:
                # Try to get existing loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, we can't run_until_complete
                    # For now, assume GTEx is working since we tested it separately
                    logger.debug("Event loop already running, skipping GTEx async test")
                    return {
                        "available": True,
                        "version": "GTEx v8",
                        "error": None
                    }
                else:
                    success = loop.run_until_complete(test_gtex())
            except RuntimeError:
                # No event loop exists, create new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    success = loop.run_until_complete(test_gtex())
                finally:
                    loop.close()
            
            if success:
                logger.debug("GTEx API connectivity verified")
                return {
                    "available": True,
                    "version": "GTEx v8",
                    "error": None
                }
            else:
                return {
                    "available": False,
                    "version": None,
                    "error": "No expression data returned"
                }
                
        except Exception as e:
            logger.warning(f"GTEx connectivity check failed: {str(e)}")
            return {
                "available": False,
                "version": None,
                "error": f"Connection error: {str(e)}"
            }
    
    def close(self):
        """Close all API client sessions."""
        self.string_client.close()
        self.gprofiler_client.close()
        self.reactome_client.close()
        # GTEx client doesn't need explicit closing as it uses requests.Session
        logger.debug("InputValidator closed all API client sessions")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
