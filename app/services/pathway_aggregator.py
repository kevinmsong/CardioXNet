"""Pathway aggregation service (Stage 2c)."""

import logging
from typing import List, Dict, Set, Any
from collections import Counter

from app.models import (
    SecondaryTriageResult,
    SecondaryPathwaySet,
    ScoredPathwayEntry,
    PathwayEntry,
    AggregatedPathway,
    FinalPathwayResult
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PathwayAggregator:
    """Aggregates secondary pathways across primary pathways (Stage 2c)."""
    
    def __init__(self):
        """Initialize pathway aggregator."""
        self.settings = get_settings()
        logger.info("PathwayAggregator initialized")
    
    def aggregate(
        self,
        secondary_result: SecondaryTriageResult,
        strategy: str = None,
        primary_result = None
    ) -> FinalPathwayResult:
        """
        Aggregate secondary pathways using specified strategy.
        
        With gene union approach, aggregation is already done in Stage 2b.
        This stage applies additional filtering based on strategy.
        
        Args:
            secondary_result: Secondary triage result from Stage 2b (already aggregated)
            strategy: Aggregation strategy (intersection, frequency, weighted)
                     Default from config
            primary_result: Optional primary result to use as fallback
            
        Returns:
            FinalPathwayResult with final pathways
        """
        strategy = strategy or self.settings.nets.aggregation_strategy
        
        print(f"[AGGREGATOR DEBUG] Starting aggregation with strategy: {strategy}")
        print(f"[AGGREGATOR DEBUG] Input: {secondary_result.total_secondary_count} pathways")
        
        logger.info(
            f"Processing {secondary_result.total_secondary_count} secondary pathways "
            f"using '{strategy}' strategy"
        )
        
        # Fallback: If no secondary pathways, use primary pathways directly
        if secondary_result.total_secondary_count == 0:
            logger.warning(
                "No secondary pathways found. Using primary pathways as final pathways."
            )
            return self._use_primary_pathways_as_final(secondary_result, primary_result)
        
        # With gene union approach, pathways are already aggregated
        # Apply strategy-specific filtering
        if strategy == "intersection":
            # Filter by minimum support threshold
            final_pathways = self._filter_by_support(
                secondary_result,
                min_support=self.settings.nets.min_support_threshold
            )
        elif strategy == "frequency":
            # Use all pathways, ranked by frequency (already done in Stage 2b)
            final_pathways = self._convert_to_aggregated_pathways(
                secondary_result
            )
        elif strategy == "weighted":
            # Weight by support count and NES
            final_pathways = self._weighted_conversion(
                secondary_result
            )
        else:
            raise ValueError(f"Unknown aggregation strategy: {strategy}")
        
        print(f"[AGGREGATOR DEBUG] Creating FinalPathwayResult with {len(final_pathways)} pathways")
        
        result = FinalPathwayResult(
            final_pathways=final_pathways,
            aggregation_strategy=strategy,
            total_count=len(final_pathways),
            min_support_threshold=self.settings.nets.min_support_threshold
        )
        
        print(f"[AGGREGATOR DEBUG] FinalPathwayResult created successfully")
        
        logger.info(
            f"Aggregation complete: {len(final_pathways)} final pathways "
            f"using '{strategy}' strategy"
        )
        
        return result
    
    def _collect_secondary_instances(
        self,
        pathway_id: str,
        secondary_result: SecondaryTriageResult
    ) -> List[Dict[str, Any]]:
        """
        Collect all secondary pathway instances for a given pathway_id.
        
        Args:
            pathway_id: The pathway ID to collect instances for
            secondary_result: Secondary triage result containing all pathways
            
        Returns:
            List of secondary pathway instance dictionaries with lineage info
        """
        instances = []
        
        for pathway in secondary_result.aggregated_pathways:
            if pathway.pathway_id == pathway_id:
                instance = {
                    "pathway_id": pathway.pathway_id,
                    "pathway_name": pathway.pathway_name,
                    "source_db": pathway.source_db,
                    "p_value": pathway.p_value,
                    "p_adj": pathway.p_adj,
                    "evidence_count": pathway.evidence_count,
                    "evidence_genes": pathway.evidence_genes,
                    "preliminary_nes": pathway.preliminary_nes,
                    "source_primary_pathway": pathway.source_primary_pathway,
                    "contributing_seed_genes": pathway.contributing_seed_genes
                }
                instances.append(instance)
        
        return instances
    
    def _filter_by_support(
        self,
        secondary_result: SecondaryTriageResult,
        min_support: int
    ) -> List[AggregatedPathway]:
        """
        Filter pathways by minimum support count (intersection strategy).
        
        Args:
            secondary_result: Secondary triage result
            min_support: Minimum number of genes that must support pathway
            
        Returns:
            List of aggregated pathways meeting threshold
        """
        print(f"[AGGREGATOR DEBUG] Filter by support: min_support={min_support}")
        print(f"[AGGREGATOR DEBUG] Input: {len(secondary_result.aggregated_pathways)} aggregated pathways")
        print(f"[AGGREGATOR DEBUG] pathway_frequency dict size: {len(secondary_result.pathway_frequency)}")
        print(f"[AGGREGATOR DEBUG] pathway_support dict size: {len(secondary_result.pathway_support)}")
        
        aggregated_pathways = []
        
        for i, pathway in enumerate(secondary_result.aggregated_pathways):
            pathway_id = pathway.pathway_id
            support_count = secondary_result.pathway_frequency.get(pathway_id, 0)
            
            if i < 3:  # Log first 3 pathways
                print(f"[AGGREGATOR DEBUG] Pathway {i+1}: {pathway.pathway_name}, support={support_count}")
            
            if support_count >= min_support:
                supporting_genes = secondary_result.pathway_support.get(pathway_id, [])
                
                # Collect all secondary pathway instances for this pathway_id
                secondary_instances = self._collect_secondary_instances(pathway_id, secondary_result)
                
                agg_pathway = AggregatedPathway(
                    pathway=PathwayEntry(
                        pathway_id=pathway.pathway_id,
                        pathway_name=pathway.pathway_name,
                        source_db=pathway.source_db,
                        p_value=pathway.p_value,
                        p_adj=pathway.p_adj,
                        evidence_count=pathway.evidence_count,
                        evidence_genes=pathway.evidence_genes
                    ),
                    support_count=support_count,
                    source_primary_pathways=supporting_genes,  # Using genes as sources
                    source_secondary_pathways=secondary_instances,  # Full lineage tracking
                    aggregation_score=float(support_count),
                    combined_p_value=pathway.p_value,
                    aggregated_nes=None,
                    consistency_score=None,
                    confidence_score=None,
                    support_fraction=float(support_count) / max(len(secondary_result.aggregated_pathways), 1)
                )
                aggregated_pathways.append(agg_pathway)
        
        print(f"[AGGREGATOR DEBUG] After filtering: {len(aggregated_pathways)} pathways with support >= {min_support}")
        
        logger.debug(
            f"Intersection strategy: {len(aggregated_pathways)} pathways "
            f"with support >= {min_support}"
        )
        
        return aggregated_pathways
    
    def _convert_to_aggregated_pathways(
        self,
        secondary_result: SecondaryTriageResult
    ) -> List[AggregatedPathway]:
        """
        Convert secondary pathways to aggregated pathways (frequency strategy).
        
        Args:
            secondary_result: Secondary triage result
            
        Returns:
            List of aggregated pathways
        """
        aggregated_pathways = []
        
        for pathway in secondary_result.aggregated_pathways:
            pathway_id = pathway.pathway_id
            support_count = secondary_result.pathway_frequency.get(pathway_id, 1)
            supporting_genes = secondary_result.pathway_support.get(pathway_id, [])
            
            # Calculate frequency score
            total_genes = len(secondary_result.union_genes)
            frequency_score = support_count / total_genes if total_genes > 0 else 0
            
            # Collect all secondary pathway instances for this pathway_id
            secondary_instances = self._collect_secondary_instances(pathway_id, secondary_result)
            
            agg_pathway = AggregatedPathway(
                pathway=PathwayEntry(
                    pathway_id=pathway.pathway_id,
                    pathway_name=pathway.pathway_name,
                    source_db=pathway.source_db,
                    p_value=pathway.p_value,
                    p_adj=pathway.p_adj,
                    evidence_count=pathway.evidence_count,
                    evidence_genes=pathway.evidence_genes
                ),
                support_count=support_count,
                source_primary_pathways=supporting_genes,
                source_secondary_pathways=secondary_instances,  # Full lineage tracking
                aggregation_score=frequency_score,
                combined_p_value=pathway.p_value,
                aggregated_nes=None,
                consistency_score=None,
                confidence_score=None,
                support_fraction=frequency_score
            )
            aggregated_pathways.append(agg_pathway)
        
        logger.debug(f"Frequency strategy: {len(aggregated_pathways)} pathways")
        
        return aggregated_pathways
    
    def _weighted_conversion(
        self,
        secondary_result: SecondaryTriageResult
    ) -> List[AggregatedPathway]:
        """
        Convert with weighted scoring (weighted strategy).
        
        Args:
            secondary_result: Secondary triage result
            
        Returns:
            List of aggregated pathways with weighted scores
        """
        aggregated_pathways = []
        
        for pathway in secondary_result.aggregated_pathways:
            pathway_id = pathway.pathway_id
            support_count = secondary_result.pathway_frequency.get(pathway_id, 1)
            supporting_genes = secondary_result.pathway_support.get(pathway_id, [])
            
            # Weighted score: NES * support_count
            weighted_score = pathway.preliminary_nes * support_count
            
            # Collect all secondary pathway instances for this pathway_id
            secondary_instances = self._collect_secondary_instances(pathway_id, secondary_result)
            
            agg_pathway = AggregatedPathway(
                pathway=PathwayEntry(
                    pathway_id=pathway.pathway_id,
                    pathway_name=pathway.pathway_name,
                    source_db=pathway.source_db,
                    p_value=pathway.p_value,
                    p_adj=pathway.p_adj,
                    evidence_count=pathway.evidence_count,
                    evidence_genes=pathway.evidence_genes
                ),
                support_count=support_count,
                source_primary_pathways=supporting_genes,
                source_secondary_pathways=secondary_instances,  # Full lineage tracking
                aggregation_score=weighted_score,
                combined_p_value=pathway.p_value,
                aggregated_nes=pathway.preliminary_nes,
                consistency_score=None,
                confidence_score=None,
                support_fraction=float(support_count) / max(len(secondary_result.aggregated_pathways), 1)
            )
            aggregated_pathways.append(agg_pathway)
        
        logger.debug(f"Weighted strategy: {len(aggregated_pathways)} pathways")
        
        return aggregated_pathways
    
    def _use_primary_pathways_as_final(
        self,
        secondary_result: SecondaryTriageResult,
        primary_result
    ) -> FinalPathwayResult:
        """
        Use primary pathways as final pathways when no secondaries found.
        
        Args:
            secondary_result: Empty secondary result
            primary_result: Primary result to use
            
        Returns:
            FinalPathwayResult with primary pathways
        """
        if primary_result is None:
            logger.warning("No primary result provided for fallback")
            return FinalPathwayResult(
                final_pathways=[],
                aggregation_strategy="fallback",
                total_count=0,
                min_support_threshold=0
            )
        
        # Convert primary pathways to aggregated pathways
        final_pathways = []
        for primary in primary_result.primary_pathways[:self.settings.nets.top_hypotheses_count]:
            agg_pathway = AggregatedPathway(
                pathway=PathwayEntry(
                    pathway_id=primary.pathway_id,
                    pathway_name=primary.pathway_name,
                    source_db=primary.source_db,
                    p_value=primary.p_value,
                    p_adj=primary.p_adj,
                    evidence_count=primary.evidence_count,
                    evidence_genes=primary.evidence_genes
                ),
                support_count=1,  # Supported by itself
                source_primary_pathways=[primary.pathway_id],
                source_secondary_pathways=[],  # No secondaries in fallback
                aggregation_score=1.0,
                combined_p_value=primary.p_value,
                aggregated_nes=primary.preliminary_nes,
                consistency_score=None,
                confidence_score=None,
                support_fraction=1.0
            )
            final_pathways.append(agg_pathway)
        
        logger.info(f"Using {len(final_pathways)} primary pathways as final pathways")
        
        return FinalPathwayResult(
            final_pathways=final_pathways,
            aggregation_strategy="primary_fallback",
            total_count=len(final_pathways),
            min_support_threshold=1
        )
    

