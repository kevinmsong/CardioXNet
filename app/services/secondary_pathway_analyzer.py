"""Secondary pathway discovery service with literature expansion (Stage 2b)."""

import logging
import math
from typing import List, Set, Dict, Tuple, Optional
from collections import defaultdict

from app.models import (
    GeneInfo,
    ScoredPathwayEntry,
    PrimaryTriageResult,
    SecondaryPathwaySet,
    SecondaryTriageResult,
    PathwayEntry
)
from app.services import (
    GProfilerClient,
    ReactomeClient,
    LiteratureExpander,
    APIClientError
)
from app.services.semantic_filter import SemanticFilter
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SecondaryPathwayAnalyzer:
    """Discovers secondary pathways with literature expansion (Stage 2b)."""
    
    def __init__(self):
        """Initialize secondary pathway analyzer."""
        self.settings = get_settings()
        self.gprofiler_client = GProfilerClient()
        self.reactome_client = ReactomeClient()
        self.literature_expander = LiteratureExpander()
        self.semantic_filter = SemanticFilter()
        
        logger.info("SecondaryPathwayAnalyzer initialized with semantic filtering")
    
    def analyze(
        self,
        primary_result: PrimaryTriageResult,
        seed_genes: List[GeneInfo],
        top_n: Optional[int] = None
    ) -> SecondaryTriageResult:
        """
        Discover secondary pathways by processing each primary pathway separately.
        
        CORRECT NETS METHODOLOGY (Per-Primary Processing):
        
        For EACH primary pathway:
        1. Extract member genes from THIS primary pathway
        2. Perform literature expansion in THIS primary's context
        3. Combine member genes + literature-expanded genes
        4. Query g:Profiler enrichment with combined gene list
        5. Apply FDR correction (P_adj < 0.05)
        6. Calculate preliminary NES scores
        7. Filter out pathways where seed genes are known (Reactome + high overlap)
        8. Store secondary pathways for THIS primary
        
        Then aggregate all secondaries for Stage 2c processing.
        
        Args:
            primary_result: Primary triage result from Stage 2a
            seed_genes: Original seed genes
            top_n: Number of top primary pathways to process (default: config)
            
        Returns:
            SecondaryTriageResult with per-primary secondary pathway mappings
        """
        # Store seed genes for novelty filtering
        self.seed_genes = seed_genes
        
        top_n = top_n or self.settings.nets.top_hypotheses_count
        
        logger.info(
            f"[STAGE 2B] Starting per-primary secondary pathway discovery "
            f"for top {top_n} primary pathways"
        )
        
        # Get known pathways for filtering
        known_pathway_ids = self._get_known_pathways(seed_genes)
        
        # Get top N primary pathways
        primary_pathways = primary_result.primary_pathways[:top_n]
        
        logger.info(f"[STAGE 2B] Processing {len(primary_pathways)} primary pathways:")
        for i, p in enumerate(primary_pathways, 1):
            logger.info(f"[STAGE 2B]   {i}. {p.pathway_name} - {len(p.evidence_genes)} member genes")
        
        # Process each primary pathway separately
        all_secondary_pathways = []
        pathway_to_primaries = {}  # Track which primaries support each secondary
        
        for i, primary_pathway in enumerate(primary_pathways, 1):
            logger.info(
                f"[STAGE 2B] Processing primary {i}/{len(primary_pathways)}: "
                f"{primary_pathway.pathway_name}"
            )
            
            try:
                # Process this primary pathway
                secondary_pathways = self._process_primary_pathway(
                    primary_pathway,
                    known_pathway_ids
                )
                
                all_secondary_pathways.extend(secondary_pathways)
                
                # Track which primaries support each secondary pathway
                for sec_pathway in secondary_pathways:
                    pathway_id = sec_pathway.pathway_id
                    if pathway_id not in pathway_to_primaries:
                        pathway_to_primaries[pathway_id] = []
                    pathway_to_primaries[pathway_id].append(primary_pathway.pathway_id)
                
                logger.info(
                    f"[STAGE 2B] Primary {i} produced {len(secondary_pathways)} "
                    f"secondary pathways"
                )
                
            except Exception as e:
                logger.warning(
                    f"[STAGE 2B] Failed to process primary pathway "
                    f"{primary_pathway.pathway_name}: {str(e)}"
                )
                continue
        
        # Aggregate pathways and calculate support metrics
        logger.info(f"[STAGE 2B] Aggregating {len(all_secondary_pathways)} total secondary pathways")
        
        aggregated_pathways, pathway_support, pathway_frequency = self._aggregate_secondary_pathways(
            all_secondary_pathways,
            pathway_to_primaries
        )
        
        logger.info(
            f"[STAGE 2B] Aggregation complete: {len(aggregated_pathways)} unique pathways, "
            f"max support: {max(pathway_frequency.values()) if pathway_frequency else 0}"
        )
        
        # Build result
        result = SecondaryTriageResult(
            union_genes=[],  # Not used in per-primary approach
            gene_triage_results=[],  # Not used in per-primary approach
            aggregated_pathways=aggregated_pathways,
            pathway_support=pathway_support,
            pathway_frequency=pathway_frequency,
            total_secondary_count=len(aggregated_pathways),
            literature_expansion_stats={
                "primaries_processed": len(primary_pathways),
                "total_secondaries": len(all_secondary_pathways),
                "unique_secondaries": len(aggregated_pathways)
            }
        )
        
        logger.info(
            f"[STAGE 2B] Secondary discovery complete: {len(aggregated_pathways)} unique pathways "
            f"from {len(primary_pathways)} primary pathways"
        )
        
        return result
    
    def _process_primary_pathway(
        self,
        primary_pathway: ScoredPathwayEntry,
        known_pathway_ids: Set[str]
    ) -> List[ScoredPathwayEntry]:
        """
        Process a single primary pathway to discover secondary pathways.
        
        Args:
            primary_pathway: Primary pathway to process
            known_pathway_ids: Set of known pathway IDs to filter
            
        Returns:
            List of secondary pathways for this primary
        """
        # Step 1: Extract member genes
        member_genes = primary_pathway.evidence_genes
        
        logger.debug(
            f"Primary pathway '{primary_pathway.pathway_name}' has {len(member_genes)} member genes"
        )
        
        # Step 1.5: Check if pathway is too generic (skip literature mining for generic pathways)
        if getattr(self.settings.nets, 'filter_generic_pathways', True):
            pathway_desc = getattr(primary_pathway, 'pathway_description', '')
            if self.semantic_filter.is_generic_pathway(
                primary_pathway.pathway_name,
                pathway_desc
            ):
                logger.info(
                    f"Skipping literature mining for generic pathway: '{primary_pathway.pathway_name}'"
                )
                # Skip literature expansion for generic pathways - use only member genes
                expanded_genes = []
            else:
                # Step 2: Expand gene list using literature mining (non-generic pathways only)
                try:
                    literature_expansion = self.literature_expander.expand_genes(
                        pathway_genes=member_genes,
                        pathway_name=primary_pathway.pathway_name
                    )
                    expanded_genes = literature_expansion.expanded_genes
                    logger.debug(
                        f"Literature expansion added {len(expanded_genes)} genes "
                        f"for '{primary_pathway.pathway_name}'"
                    )
                except Exception as e:
                    logger.warning(f"Literature expansion failed: {str(e)}, continuing without expansion")
                    expanded_genes = []
        else:
            # Step 2: Expand gene list using literature mining (filtering disabled)
            try:
                literature_expansion = self.literature_expander.expand_genes(
                    pathway_genes=member_genes,
                    pathway_name=primary_pathway.pathway_name
                )
                expanded_genes = literature_expansion.expanded_genes
                logger.debug(
                    f"Literature expansion added {len(expanded_genes)} genes "
                    f"for '{primary_pathway.pathway_name}'"
                )
            except Exception as e:
                logger.warning(f"Literature expansion failed: {str(e)}, continuing without expansion")
                expanded_genes = []
        
        # Combine member genes with expanded genes
        all_genes = member_genes + expanded_genes
        
        # Convert to GeneInfo objects
        gene_info_list = [
            GeneInfo(
                input_id=gene,
                entrez_id="",
                hgnc_id="",
                symbol=gene,
                species="Homo sapiens"
            )
            for gene in all_genes
        ]
        
        # Step 3-4: Query g:Profiler with expanded gene list
        secondary_pathways = self._query_enrichment(gene_info_list)
        
        # Step 5: Calculate preliminary NES scores
        scored_pathways = self._calculate_nes_scores(
            secondary_pathways, 
            primary_pathway.contributing_seed_genes,
            primary_pathway.pathway_id  # Pass primary pathway ID for lineage tracking
        )
        
        # Step 6: Filter out known pathways
        filtered_pathways = self._filter_known_pathways(
            scored_pathways,
            known_pathway_ids
        )
        
        logger.debug(
            f"Primary '{primary_pathway.pathway_name}': "
            f"{len(secondary_pathways)} enriched → {len(filtered_pathways)} novel"
        )
        
        return filtered_pathways
    
    def _aggregate_secondary_pathways(
        self,
        all_secondary_pathways: List[ScoredPathwayEntry],
        pathway_to_primaries: Dict[str, List[str]]
    ) -> Tuple[List[ScoredPathwayEntry], Dict[str, List[str]], Dict[str, int]]:
        """
        Aggregate secondary pathways across primaries.
        
        Args:
            all_secondary_pathways: All secondary pathways from all primaries
            pathway_to_primaries: Mapping of pathway_id to supporting primary_ids
            
        Returns:
            Tuple of (unique_pathways, pathway_support, pathway_frequency)
        """
        # Group pathways by ID and aggregate their NES scores
        pathway_map = {}  # pathway_id -> ScoredPathwayEntry
        pathway_nes_scores = defaultdict(list)  # pathway_id -> [nes_scores]
        pathway_pvalues = defaultdict(list)  # pathway_id -> [p_values] for Fisher's method
        
        for pathway in all_secondary_pathways:
            pathway_id = pathway.pathway_id
            
            # Track first occurrence
            if pathway_id not in pathway_map:
                pathway_map[pathway_id] = pathway
            
            # Collect NES scores and p-values
            pathway_nes_scores[pathway_id].append(pathway.preliminary_nes)
            pathway_pvalues[pathway_id].append(pathway.p_value)
        
        # Create aggregated pathways with average NES
        aggregated_pathways = []
        pathway_frequency = {}
        
        for pathway_id, pathway in pathway_map.items():
            # Calculate average NES across all primaries that found this pathway
            avg_nes = sum(pathway_nes_scores[pathway_id]) / len(pathway_nes_scores[pathway_id])
            
            # Calculate combined p-value using Fisher's method (NEW - Multi-Database Aggregation)
            combined_pvalue = self._calculate_fisher_combined_pvalue(pathway_pvalues[pathway_id])
            
            # Update pathway with aggregated NES and combined p-value
            pathway.preliminary_nes = avg_nes
            pathway.p_value = combined_pvalue  # Replace single p-value with combined
            # Update p_adj proportionally (combined_pvalue / original_pvalue * original_p_adj)
            if pathway.p_value > 0:
                original_pvalue = pathway_pvalues[pathway_id][0]  # First p-value
                if original_pvalue > 0:
                    pathway.p_adj = (combined_pvalue / original_pvalue) * pathway.p_adj
                else:
                    pathway.p_adj = combined_pvalue  # Fallback if original was 0
            
            # Track frequency (number of primaries that support this pathway)
            frequency = len(pathway_to_primaries.get(pathway_id, []))
            pathway_frequency[pathway_id] = frequency
            
            aggregated_pathways.append(pathway)
        
        # Sort by frequency (support count) then by NES
        aggregated_pathways.sort(
            key=lambda p: (pathway_frequency[p.pathway_id], p.preliminary_nes),
            reverse=True
        )
        
        return aggregated_pathways, pathway_to_primaries, pathway_frequency
    
    def _query_enrichment(
        self,
        genes: List[GeneInfo]
    ) -> List[PathwayEntry]:
        """
        Query g:Profiler for pathway enrichment.
        
        Args:
            genes: List of genes (member + expanded)
            
        Returns:
            List of enriched pathways
        """
        if not genes:
            return []
        
        logger.debug(f"Querying g:Profiler with {len(genes)} genes")
        
        try:
            pathways = self.gprofiler_client.get_enrichment(
                genes=genes,
                sources=["REAC", "KEGG", "WP", "GO:BP"],
                fdr_threshold=self.settings.nets.fdr_threshold
            )
            
            return pathways
            
        except APIClientError as e:
            logger.warning(f"g:Profiler enrichment query failed: {str(e)}")
            
            # If g:Profiler is unavailable, continue with empty results
            if "temporarily unavailable" in str(e).lower() or "503" in str(e):
                print("[GPROFILER FALLBACK] Service unavailable in secondary analysis")
            
            return []
    
    def _calculate_nes_scores(
        self,
        pathways: List[PathwayEntry],
        contributing_seed_genes: List[str],
        source_primary_pathway_id: str = None
    ) -> List[ScoredPathwayEntry]:
        """
        Calculate preliminary NES scores for pathways.
        
        Args:
            pathways: List of enriched pathways
            contributing_seed_genes: Seed genes that contributed
            source_primary_pathway_id: ID of the primary pathway that led to these secondaries
            
        Returns:
            List of pathways with NES scores
        """
        scored_pathways = []
        db_weights = self.settings.nets.db_weights
        
        for pathway in pathways:
            # Calculate -log10(P_adj)
            if pathway.p_adj > 0:
                log_p = -math.log10(pathway.p_adj)
            else:
                # For p-values reported as 0, use equivalent of p_adj = 1e-50
                log_p = 50.0
            
            # Cap at 50 to prevent extreme scores
            log_p = min(log_p, 50.0)
            
            # Get database weight
            db_weight = db_weights.get(pathway.source_db, 1.0)
            
            # Calculate NES
            nes = log_p * pathway.evidence_count * db_weight
            
            # Create scored entry
            scored_pathway = ScoredPathwayEntry(
                pathway_id=pathway.pathway_id,
                pathway_name=pathway.pathway_name,
                source_db=pathway.source_db,
                p_value=pathway.p_value,
                p_adj=pathway.p_adj,
                evidence_count=pathway.evidence_count,
                evidence_genes=pathway.evidence_genes,
                preliminary_nes=nes,
                contributing_seed_genes=contributing_seed_genes,
                literature_support=None,
                source_primary_pathway=source_primary_pathway_id  # Track lineage
            )
            
            scored_pathways.append(scored_pathway)
        
        return scored_pathways
    
    def _get_known_pathways(
        self,
        seed_genes: List[GeneInfo]
    ) -> Set[str]:
        """
        Query Reactome for seed genes' known pathways.
        
        Args:
            seed_genes: List of seed genes
            
        Returns:
            Set of known pathway IDs
        """
        logger.debug(f"Querying known pathways for {len(seed_genes)} seed genes")
        
        known_pathway_ids = set()
        
        try:
            known_pathways = self.reactome_client.get_pathways_for_genes(seed_genes)
            
            for pathway in known_pathways:
                known_pathway_ids.add(pathway.pathway_id)
            
            logger.debug(f"Found {len(known_pathway_ids)} known pathways")
            
        except APIClientError as e:
            logger.warning(f"Failed to query known pathways: {str(e)}")
        
        return known_pathway_ids
    
    def _filter_known_pathways(
        self,
        scored_pathways: List[ScoredPathwayEntry],
        known_pathway_ids: Set[str]
    ) -> List[ScoredPathwayEntry]:
        """
        Filter out pathways with known seed gene annotations.
        
        Enhanced filtering:
        1. Remove pathways in Reactome known pathway list
        2. Remove pathways where >50% of evidence genes are seed genes
        
        Args:
            scored_pathways: List of scored pathways
            known_pathway_ids: Set of known pathway IDs
            
        Returns:
            List of novel pathways
        """
        novel_pathways = []
        
        for pathway in scored_pathways:
            is_known = False
            
            # Check 1: In Reactome known pathways
            if pathway.pathway_id in known_pathway_ids:
                is_known = True
            
            # Check 2: High seed gene overlap (>50% of evidence genes are seeds)
            if not is_known and pathway.evidence_genes and hasattr(self, 'seed_genes'):
                seed_gene_symbols = {gene.symbol for gene in self.seed_genes}
                evidence_gene_set = set(pathway.evidence_genes)
                seed_overlap = evidence_gene_set & seed_gene_symbols
                
                if len(seed_overlap) > 0:
                    overlap_ratio = len(seed_overlap) / len(evidence_gene_set)
                    threshold = self.settings.nets.seed_overlap_threshold
                    if overlap_ratio > threshold:
                        is_known = True
                        logger.debug(
                            f"Filtering {pathway.pathway_name}: {overlap_ratio:.1%} seed gene overlap exceeds threshold {threshold:.1%}"
                        )
            
            if not is_known:
                novel_pathways.append(pathway)
        
        logger.debug(
            f"Filtered pathways: {len(novel_pathways)} novel, "
            f"{len(scored_pathways) - len(novel_pathways)} known"
        )
        
        return novel_pathways
    
    def _calculate_fisher_combined_pvalue(self, pvalues: List[float]) -> float:
        """
        Calculate combined p-value using Fisher's method for meta-analysis.
        
        Fisher's Combined Probability Method:
        χ² = -2 × Σ[ln(p_i)] for i=1 to k databases
        Combined P-value = P(χ²_{2k} > observed χ²)
        
        Example:
        - Pathway in Reactome: p = 1e-10
        - Same pathway in gProfiler: p = 1e-8
        - Same pathway in KEGG: p = 1e-6
        
        Fisher's χ² = -2 × [ln(1e-10) + ln(1e-8) + ln(1e-6)]
                    = -2 × [-23.03 + -18.42 + -13.82]
                    = 110.54
        
        Combined p-value = P(χ²_6 > 110.54) ≈ 1.2e-21 (much stronger!)
        
        Rationale: Properly accounts for independent replication across databases,
        dramatically boosting confidence in cross-validated pathways.
        
        Args:
            pvalues: List of p-values from different databases for the same pathway
            
        Returns:
            Combined p-value using Fisher's method
        """
        if len(pvalues) == 1:
            return pvalues[0]  # Single database, no combination needed
        
        # Filter out zero or negative p-values (shouldn't happen but be defensive)
        valid_pvalues = [p for p in pvalues if p > 0]
        
        if not valid_pvalues:
            return 1.0  # No valid p-values, return non-significant
        
        if len(valid_pvalues) == 1:
            return valid_pvalues[0]
        
        try:
            from scipy import stats
            
            # Calculate Fisher's chi-square statistic
            chi_square = -2 * sum(math.log(p) for p in valid_pvalues)
            degrees_of_freedom = 2 * len(valid_pvalues)
            
            # Calculate combined p-value from chi-square distribution
            combined_pvalue = float(1 - stats.chi2.cdf(chi_square, degrees_of_freedom))
            
            logger.debug(
                f"Fisher's method: {len(valid_pvalues)} p-values combined | "
                f"χ²={chi_square:.2f}, df={degrees_of_freedom}, "
                f"combined_p={combined_pvalue:.2e} (vs single p={valid_pvalues[0]:.2e})"
            )
            
            return combined_pvalue
            
        except Exception as e:
            logger.warning(f"Fisher's method failed: {str(e)}, using minimum p-value")
            return min(valid_pvalues)  # Fallback to most significant p-value
    
    def close(self):
        """Close API client sessions."""
        self.gprofiler_client.close()
        self.reactome_client.close()
        logger.debug("SecondaryPathwayAnalyzer closed API client sessions")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
