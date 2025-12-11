"""Scientifically rigorous pathway aggregation service (Stage 2c)."""

import logging
import math
from typing import List, Dict, Tuple
from collections import defaultdict
import numpy as np
from scipy import stats

from app.models import (
    SecondaryTriageResult,
    ScoredPathwayEntry,
    PathwayEntry,
    AggregatedPathway,
    FinalPathwayResult
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RigorousPathwayAggregator:
    """
    Aggregates secondary pathways with statistical rigor (Stage 2c).
    
    Uses multiple statistical methods:
    - Fisher's combined probability test for p-values
    - Weighted NES aggregation
    - Consistency scoring
    - Confidence scoring
    """
    
    def __init__(self):
        """Initialize rigorous pathway aggregator."""
        self.settings = get_settings()
        logger.info("RigorousPathwayAggregator initialized")
    
    def aggregate(
        self,
        secondary_result: SecondaryTriageResult,
        strategy: str = None,
        primary_result = None
    ) -> FinalPathwayResult:
        """
        Aggregate secondary pathways using rigorous statistical methods.
        
        Args:
            secondary_result: Secondary triage result from Stage 2b
            strategy: Aggregation strategy (ignored - always uses rigorous method)
            primary_result: Optional primary result (for fallback)
            
        Returns:
            FinalPathwayResult with statistically aggregated pathways
        """
        logger.info(
            f"[STAGE 2C] Starting rigorous aggregation of "
            f"{secondary_result.total_secondary_count} secondary pathways"
        )
        
        # Fallback: If no secondary pathways, use primary pathways
        if secondary_result.total_secondary_count == 0:
            logger.warning("No secondary pathways found. Using primary pathways as fallback.")
            return self._use_primary_pathways_as_final(secondary_result, primary_result)
        
        # Stage 2b already aggregated pathways, so we just need to add statistical rigor
        # Use the pathway_frequency to get support counts
        
        logger.info(f"[STAGE 2C] Processing {len(secondary_result.aggregated_pathways)} unique pathways")
        
        # Pre-filter pathways by statistical significance (scientific optimization)
        pre_filtered_pathways = self._pre_filter_pathways(secondary_result.aggregated_pathways)
        logger.info(f"[STAGE 2C] After pre-filtering: {len(pre_filtered_pathways)} pathways")
        
        # Step 2: Calculate total number of primaries
        total_primaries = len(set(
            primary_id 
            for primary_ids in secondary_result.pathway_support.values() 
            for primary_id in primary_ids
        ))
        
        if total_primaries == 0:
            total_primaries = 1  # Avoid division by zero
        
        logger.info(f"[STAGE 2C] Total primaries processed: {total_primaries}")
        
        # Step 3: Add statistical rigor to each pathway
        aggregated_pathways = []
        
        for pathway in pre_filtered_pathways:
            try:
                # Get support information from Stage 2b
                pathway_id = pathway.pathway_id
                support_count = secondary_result.pathway_frequency.get(pathway_id, 1)
                supporting_primary_ids = secondary_result.pathway_support.get(pathway_id, [])
                
                # Create list with single instance (already aggregated in Stage 2b)
                agg_pathway = self._aggregate_pathway_instances(
                    pathway_id,
                    [pathway],  # Single instance
                    total_primaries,
                    supporting_primary_ids
                )
                
                # Override support_count with the actual count from Stage 2b
                agg_pathway.support_count = support_count
                agg_pathway.support_fraction = support_count / total_primaries
                
                # Recalculate confidence with correct support
                agg_pathway.confidence_score = self._calculate_confidence_score(
                    agg_pathway.support_fraction,
                    agg_pathway.combined_p_value or pathway.p_adj,
                    agg_pathway.aggregated_nes or pathway.preliminary_nes,
                    agg_pathway.consistency_score or 1.0
                )
                agg_pathway.aggregation_score = agg_pathway.confidence_score
                
                aggregated_pathways.append(agg_pathway)
            except Exception as e:
                logger.warning(f"Failed to aggregate pathway {pathway_id}: {str(e)}")
                continue
        
        # Step 4: Sort by confidence score (descending)
        aggregated_pathways.sort(
            key=lambda p: p.confidence_score if p.confidence_score else 0,
            reverse=True
        )
        
        # Step 5: Apply filtering
        logger.info(
            f"[STAGE 2C] Before filtering: {len(aggregated_pathways)} pathways, "
            f"min_support={self.settings.nets.min_support_threshold}"
        )
        
        # Debug: Check support counts
        if aggregated_pathways:
            support_counts = [p.support_count for p in aggregated_pathways[:10]]
            logger.info(f"[STAGE 2C] Sample support counts: {support_counts}")
        
        final_pathways = self._apply_filters(
            aggregated_pathways,
            min_support=self.settings.nets.min_support_threshold
        )
        
        logger.info(
            f"[STAGE 2C] Aggregation complete: {len(final_pathways)} final pathways "
            f"(filtered from {len(aggregated_pathways)})"
        )
        
        result = FinalPathwayResult(
            final_pathways=final_pathways,
            aggregation_strategy="rigorous_statistical",
            total_count=len(final_pathways),
            min_support_threshold=self.settings.nets.min_support_threshold
        )
        
        return result
    
    def _group_pathways_by_id(
        self,
        secondary_result: SecondaryTriageResult
    ) -> Dict[str, List[ScoredPathwayEntry]]:
        """
        Group pathway instances by pathway ID.
        
        Args:
            secondary_result: Secondary triage result
            
        Returns:
            Dictionary mapping pathway_id to list of instances
        """
        pathway_groups = defaultdict(list)
        
        for pathway in secondary_result.aggregated_pathways:
            pathway_groups[pathway.pathway_id].append(pathway)
        
        return dict(pathway_groups)
    
    def _aggregate_pathway_instances(
        self,
        pathway_id: str,
        instances: List[ScoredPathwayEntry],
        total_primaries: int,
        supporting_primary_ids: List[str]
    ) -> AggregatedPathway:
        """
        Aggregate multiple instances of the same pathway with statistical rigor.
        
        Args:
            pathway_id: Pathway identifier
            instances: List of pathway instances from different primaries
            total_primaries: Total number of primary pathways processed
            supporting_primary_ids: IDs of primaries that support this pathway
            
        Returns:
            AggregatedPathway with statistical metrics
        """
        # Use first instance as template
        template = instances[0]
        
        # Calculate support metrics
        support_count = len(instances)
        support_fraction = support_count / total_primaries
        
        # Extract p-values and NES scores
        p_values = [inst.p_adj for inst in instances if inst.p_adj > 0]
        nes_values = [inst.preliminary_nes for inst in instances]
        
        # Calculate combined p-value using Fisher's method
        combined_p = self._fishers_combined_probability(p_values) if p_values else 1.0
        
        # Calculate weighted NES aggregation
        weights = self._calculate_weights(instances)
        aggregated_nes = self._weighted_average(nes_values, weights)
        
        # Calculate consistency score
        consistency = self._calculate_consistency(nes_values)
        
        # Calculate overall confidence score
        confidence = self._calculate_confidence_score(
            support_fraction,
            combined_p,
            aggregated_nes,
            consistency
        )
        
        # Aggregate contributing seed genes from all instances
        all_contributing_seeds = set()
        for inst in instances:
            all_contributing_seeds.update(inst.contributing_seed_genes)
        contributing_seed_genes = sorted(list(all_contributing_seeds))
        
        # Create list of secondary pathway instances for lineage tracking
        source_secondary_pathways = [
            {
                "pathway_id": inst.pathway_id,
                "pathway_name": inst.pathway_name,
                "source_db": inst.source_db,
                "p_adj": inst.p_adj,
                "preliminary_nes": inst.preliminary_nes,
                "evidence_count": inst.evidence_count,
                "contributing_seed_genes": inst.contributing_seed_genes,
                "source_primary_pathway": inst.source_primary_pathway if hasattr(inst, 'source_primary_pathway') else None
            }
            for inst in instances
        ]
        
        # Create aggregated pathway
        agg_pathway = AggregatedPathway(
            pathway=PathwayEntry(
                pathway_id=template.pathway_id,
                pathway_name=template.pathway_name,
                source_db=template.source_db,
                p_value=template.p_value,
                p_adj=combined_p,  # Use combined p-value
                evidence_count=template.evidence_count,
                evidence_genes=template.evidence_genes
            ),
            support_count=support_count,
            source_primary_pathways=supporting_primary_ids,
            source_secondary_pathways=source_secondary_pathways,
            aggregation_score=confidence,  # Use confidence as aggregation score
            combined_p_value=combined_p,
            aggregated_nes=aggregated_nes,
            consistency_score=consistency,
            confidence_score=confidence,
            support_fraction=support_fraction,
            contributing_seed_genes=contributing_seed_genes
        )
        
        return agg_pathway
    
    def _fishers_combined_probability(self, p_values: List[float]) -> float:
        """
        Combine p-values using Fisher's method.
        
        Formula: χ² = -2 * Σ ln(p_i), df = 2k
        
        Args:
            p_values: List of p-values to combine
            
        Returns:
            Combined p-value
        """
        if not p_values:
            return 1.0
        
        # Filter out zero p-values (use small value instead)
        p_values = [max(p, 1e-300) for p in p_values]
        
        # Calculate chi-squared statistic
        chi_squared = -2 * sum(math.log(p) for p in p_values)
        df = 2 * len(p_values)
        
        # Calculate combined p-value from chi-squared distribution
        combined_p = 1 - stats.chi2.cdf(chi_squared, df)
        
        return combined_p
    
    def _calculate_weights(self, instances: List[ScoredPathwayEntry]) -> List[float]:
        """
        Calculate quality-based weights for each pathway instance.
        
        Weights based on:
        - Statistical significance (lower p = higher weight)
        - Evidence count (more genes = higher weight)
        - Database quality (from config)
        
        Args:
            instances: List of pathway instances
            
        Returns:
            List of normalized weights
        """
        weights = []
        
        for inst in instances:
            # Weight by statistical significance
            p_weight = -math.log10(inst.p_adj) if inst.p_adj > 0 else 10
            
            # Weight by evidence count
            evidence_weight = math.log(inst.evidence_count + 1)
            
            # Weight by database quality
            db_weight = self.settings.nets.db_weights.get(inst.source_db, 1.0)
            
            # Combined weight
            weight = p_weight * evidence_weight * db_weight
            weights.append(weight)
        
        # Normalize weights to sum to 1
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(weights)] * len(weights)
        
        return weights
    
    def _weighted_average(self, values: List[float], weights: List[float]) -> float:
        """
        Calculate weighted average.
        
        Args:
            values: List of values
            weights: List of weights (should sum to 1)
            
        Returns:
            Weighted average
        """
        if not values:
            return 0.0
        
        return sum(v * w for v, w in zip(values, weights))
    
    def _calculate_consistency(self, values: List[float]) -> float:
        """
        Calculate consistency score (inverse coefficient of variation).
        
        High consistency = values are similar across primaries
        Low consistency = values vary widely
        
        Args:
            values: List of NES values
            
        Returns:
            Consistency score (0-1, higher = more consistent)
        """
        if len(values) < 2:
            return 1.0  # Single value is perfectly consistent
        
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        if mean_val == 0:
            return 0.0
        
        # Coefficient of variation
        cv = std_val / mean_val
        
        # Convert to consistency score (0-1)
        # Lower CV = higher consistency
        consistency = max(0, 1 - cv)
        
        return consistency
    
    def _calculate_confidence_score(
        self,
        support_fraction: float,
        combined_p: float,
        aggregated_nes: float,
        consistency: float
    ) -> float:
        """
        Calculate overall confidence score combining multiple factors.
        
        Factors:
        - Replication (support_fraction): 30% weight
        - Statistical significance (1 - combined_p): 30% weight
        - Effect size (normalized NES): 25% weight
        - Consistency: 15% weight
        
        Args:
            support_fraction: Fraction of primaries supporting this (0-1)
            combined_p: Combined p-value (0-1)
            aggregated_nes: Aggregated NES score
            consistency: Consistency score (0-1)
            
        Returns:
            Confidence score (0-1)
        """
        # Normalize NES to 0-1 range (assuming max NES ~ 100)
        norm_nes = min(aggregated_nes / 100.0, 1.0)
        
        # Weighted combination
        confidence = (
            0.30 * support_fraction +      # 30% weight on replication
            0.30 * (1 - combined_p) +      # 30% weight on significance
            0.25 * norm_nes +              # 25% weight on effect size
            0.15 * consistency             # 15% weight on consistency
        )
        
        return confidence
    
    def _apply_filters(
        self,
        pathways: List[AggregatedPathway],
        min_support: int = 2,
        max_combined_p: float = 0.05,
        min_confidence: float = 0.1
    ) -> List[AggregatedPathway]:
        """
        Apply filtering criteria to aggregated pathways.
        
        Args:
            pathways: List of aggregated pathways
            min_support: Minimum number of supporting primaries
            max_combined_p: Maximum combined p-value
            min_confidence: Minimum confidence score
            
        Returns:
            Filtered list of pathways
        """
        filtered = []
        
        for pathway in pathways:
            # Filter by support count
            if pathway.support_count < min_support:
                continue
            
            # Filter by combined p-value
            if pathway.combined_p_value and pathway.combined_p_value > max_combined_p:
                continue
            
            # Filter by confidence score
            if pathway.confidence_score and pathway.confidence_score < min_confidence:
                continue
            
            filtered.append(pathway)
        
        logger.debug(
            f"Filtering: {len(filtered)}/{len(pathways)} pathways passed "
            f"(min_support={min_support}, max_p={max_combined_p}, min_conf={min_confidence})"
        )
        
        return filtered
    
    def _pre_filter_pathways(self, pathways: List[ScoredPathwayEntry]) -> List[ScoredPathwayEntry]:
        """
        Pre-filter pathways by statistical significance to reduce computational load.
        
        Scientific optimization: Removes pathways with insufficient statistical support
        early in the pipeline to focus computational resources on promising candidates.
        
        Args:
            pathways: List of pathway entries to filter
            
        Returns:
            Filtered list of pathway entries
        """
        logger.info(f"Pre-filtering {len(pathways)} pathways by statistical significance")
        
        filtered_pathways = []
        min_p_value = 0.05  # Configurable threshold
        min_nes_score = 1.0  # Minimum NES score for consideration
        
        for pathway in pathways:
            # Apply statistical filters
            p_value_ok = pathway.p_adj is None or pathway.p_adj <= min_p_value
            nes_ok = pathway.preliminary_nes is None or abs(pathway.preliminary_nes) >= min_nes_score
            
            if p_value_ok and nes_ok:
                filtered_pathways.append(pathway)
            else:
                logger.debug(
                    f"Filtered pathway {pathway.pathway_name}: "
                    f"p_adj={pathway.p_adj}, nes={pathway.preliminary_nes}"
                )
        
        logger.info(
            f"Pre-filtering complete: {len(filtered_pathways)}/{len(pathways)} pathways retained "
            f"(p≤{min_p_value}, |NES|≥{min_nes_score})"
        )
        
        return filtered_pathways
    
    def _use_primary_pathways_as_final(
        self,
        secondary_result: SecondaryTriageResult,
        primary_result
    ) -> FinalPathwayResult:
        """
        Fallback: Use primary pathways when no secondaries are found.
        
        Args:
            secondary_result: Secondary triage result (empty)
            primary_result: Primary triage result
            
        Returns:
            FinalPathwayResult with primary pathways
        """
        if not primary_result or not primary_result.primary_pathways:
            logger.warning("No primary or secondary pathways available")
            return FinalPathwayResult(
                final_pathways=[],
                aggregation_strategy="fallback_empty",
                total_count=0,
                min_support_threshold=self.settings.nets.min_support_threshold
            )
        
        # Convert primary pathways to aggregated pathways
        final_pathways = []
        top_n = self.settings.nets.top_hypotheses_count
        
        for primary in primary_result.primary_pathways[:top_n]:
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
                support_count=1,
                source_primary_pathways=[],
                aggregation_score=primary.preliminary_nes,
                combined_p_value=primary.p_adj,
                aggregated_nes=primary.preliminary_nes,
                consistency_score=1.0,
                confidence_score=0.5,  # Lower confidence for fallback
                support_fraction=1.0
            )
            final_pathways.append(agg_pathway)
        
        logger.info(f"Using {len(final_pathways)} primary pathways as fallback")
        
        return FinalPathwayResult(
            final_pathways=final_pathways,
            aggregation_strategy="fallback_primary",
            total_count=len(final_pathways),
            min_support_threshold=self.settings.nets.min_support_threshold
        )
