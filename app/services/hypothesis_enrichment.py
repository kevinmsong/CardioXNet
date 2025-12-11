"""
Hypothesis enrichment service to populate detailed clinical data.

This service enriches scored hypotheses with:
- GTEx tissue expression profiles
- GWAS associations from GWAS Catalog
- Therapeutic targets from drug databases
- Clinical trial evidence
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from app.services.gtex_client import GTExClient
from app.services.gwas_client import GWASClient
from app.services.druggability_analyzer import DruggabilityAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class TissueExpressionData:
    """Tissue-specific expression data for visualization."""
    tissue: str
    tpm: float
    rank: int


@dataclass
class GWASAssociation:
    """GWAS association for a gene/variant."""
    snp: str
    trait: str
    p_value: float
    study: str
    genes: List[str]
    beta: Optional[float] = None
    odds_ratio: Optional[float] = None


@dataclass
class TherapeuticTarget:
    """Therapeutic target information."""
    gene: str
    druggability_score: float
    existing_drugs: List[str]
    clinical_trials: int
    prioritization_rationale: str


class HypothesisEnrichmentService:
    """
    Service to enrich hypotheses with detailed clinical data.
    
    Populates:
    - score_components.tissue_expression_data
    - score_components.gwas_associations
    - score_components.therapeutic_targets
    - stage_3_clinical_evidence
    """
    
    def __init__(self):
        """Initialize enrichment service."""
        self.gtex_client = GTExClient()
        self.gwas_client = GWASClient()
        self.druggability_analyzer = DruggabilityAnalyzer()
        logger.info("Hypothesis enrichment service initialized")
    
    async def enrich_hypothesis(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a single hypothesis with detailed clinical data.
        
        Args:
            hypothesis: Hypothesis dict with aggregated_pathway and score_components
            
        Returns:
            Enriched hypothesis dict
        """
        try:
            # Extract genes from pathway
            genes = self._extract_genes(hypothesis)
            if not genes:
                logger.warning("No genes found in hypothesis, skipping enrichment")
                return hypothesis
            
            # Run enrichment tasks in parallel
            tissue_task = self._get_tissue_expression(genes)
            gwas_task = self._get_gwas_associations(genes)
            therapeutic_task = self._get_therapeutic_targets(genes, hypothesis)
            
            tissue_data, gwas_data, therapeutic_data = await asyncio.gather(
                tissue_task, gwas_task, therapeutic_task, return_exceptions=True
            )
            
            # Add to score_components
            score_components = hypothesis.get('score_components', {})
            
            if not isinstance(tissue_data, Exception) and tissue_data:
                score_components['tissue_expression_data'] = tissue_data
            
            if not isinstance(gwas_data, Exception) and gwas_data:
                score_components['gwas_associations'] = gwas_data
            
            if not isinstance(therapeutic_data, Exception) and therapeutic_data:
                score_components['therapeutic_targets'] = therapeutic_data
            
            # Add clinical evidence summary
            hypothesis['stage_3_clinical_evidence'] = {
                'has_tissue_data': bool(tissue_data and not isinstance(tissue_data, Exception)),
                'has_gwas_data': bool(gwas_data and not isinstance(gwas_data, Exception)),
                'has_therapeutic_data': bool(therapeutic_data and not isinstance(therapeutic_data, Exception)),
                'enrichment_timestamp': asyncio.get_event_loop().time()
            }
            
            logger.info(f"Enriched hypothesis with {len(tissue_data or [])} tissues, "
                       f"{len(gwas_data or [])} GWAS hits, {len(therapeutic_data or [])} targets")
            
            return hypothesis
            
        except Exception as e:
            logger.error(f"Error enriching hypothesis: {e}")
            return hypothesis
    
    def _extract_genes(self, hypothesis: Dict[str, Any]) -> List[str]:
        """Extract gene list from hypothesis."""
        genes = []
        
        # Try aggregated_pathway.pathway.evidence_genes
        agg_pathway = hypothesis.get('aggregated_pathway', {})
        if isinstance(agg_pathway, dict):
            pathway = agg_pathway.get('pathway', {})
            if isinstance(pathway, dict):
                evidence_genes = pathway.get('evidence_genes', [])
                if evidence_genes:
                    genes = evidence_genes
        
        # Fallback to traced_seed_genes
        if not genes:
            genes = hypothesis.get('traced_seed_genes', [])
        
        # Fallback to cardiac_expressed_genes
        if not genes:
            score_components = hypothesis.get('score_components', {})
            genes = score_components.get('cardiac_expressed_genes', [])
        
        return genes[:50]  # Limit to top 50 genes to avoid API overload
    
    async def _get_tissue_expression(self, genes: List[str]) -> List[Dict[str, Any]]:
        """
        Get GTEx tissue expression data for genes.
        
        Returns top 10 tissues by median expression.
        """
        try:
            all_tissue_data = {}
            
            # Query GTEx for each gene (limit to first 10 for performance)
            for gene in genes[:10]:
                try:
                    expression_data = await asyncio.to_thread(
                        self.gtex_client.get_gene_expression,
                        gene
                    )
                    
                    if expression_data:
                        for exp in expression_data:
                            tissue = exp.tissue
                            tpm = exp.median_tpm
                            
                            if tissue not in all_tissue_data:
                                all_tissue_data[tissue] = []
                            all_tissue_data[tissue].append(tpm)
                
                except Exception as e:
                    logger.debug(f"Error getting GTEx data for {gene}: {e}")
                    continue
            
            # Calculate median TPM per tissue across all genes
            tissue_summary = []
            for tissue, tpm_values in all_tissue_data.items():
                median_tpm = sum(tpm_values) / len(tpm_values) if tpm_values else 0
                tissue_summary.append({
                    'tissue': tissue,
                    'tpm': round(median_tpm, 2),
                    'rank': 0  # Will be filled after sorting
                })
            
            # Sort by TPM and assign ranks
            tissue_summary.sort(key=lambda x: x['tpm'], reverse=True)
            for idx, tissue in enumerate(tissue_summary):
                tissue['rank'] = idx + 1
            
            return tissue_summary[:10]  # Top 10 tissues
            
        except Exception as e:
            logger.error(f"Error getting tissue expression: {e}")
            return []
    
    async def _get_gwas_associations(self, genes: List[str]) -> List[Dict[str, Any]]:
        """
        Get GWAS Catalog associations for genes.
        
        Returns cardiovascular-relevant GWAS hits.
        """
        try:
            gwas_results = []
            
            # Query GWAS Catalog (limit to first 20 genes for performance)
            for gene in genes[:20]:
                try:
                    associations = await asyncio.to_thread(
                        self.gwas_client.get_associations_for_gene,
                        gene
                    )
                    
                    if associations:
                        for assoc in associations[:3]:  # Top 3 per gene
                            gwas_results.append({
                                'snp': assoc.get('variant_id', f'rs{assoc.get("rsid", "unknown")}'),
                                'trait': assoc.get('trait', 'Unknown trait'),
                                'p_value': float(assoc.get('p_value', 1.0)),
                                'study': assoc.get('study', 'GWAS Catalog'),
                                'genes': [gene],
                                'beta': assoc.get('beta'),
                                'odds_ratio': assoc.get('odds_ratio')
                            })
                
                except Exception as e:
                    logger.debug(f"Error getting GWAS data for {gene}: {e}")
                    continue
            
            # Sort by p-value and return top 10
            gwas_results.sort(key=lambda x: x['p_value'])
            return gwas_results[:10]
            
        except Exception as e:
            logger.error(f"Error getting GWAS associations: {e}")
            return []
    
    async def _get_therapeutic_targets(self, genes: List[str], 
                                      hypothesis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get therapeutic target information for druggable genes.
        
        Uses existing druggability analysis and enhances with drug data.
        """
        try:
            # Get druggable genes from score_components
            score_components = hypothesis.get('score_components', {})
            druggable_genes = score_components.get('druggable_genes', [])
            druggability_tier = score_components.get('druggability_tier', 'unknown')
            
            if not druggable_genes:
                return []
            
            targets = []
            for gene in druggable_genes[:10]:  # Top 10 druggable genes
                try:
                    # Get druggability score
                    score_result = await asyncio.to_thread(
                        self.druggability_analyzer.analyze_gene,
                        gene
                    )
                    
                    targets.append({
                        'gene': gene,
                        'druggability_score': score_result.get('score', 0.5) if isinstance(score_result, dict) else 0.5,
                        'existing_drugs': score_result.get('known_drugs', []) if isinstance(score_result, dict) else [],
                        'clinical_trials': score_result.get('clinical_trials', 0) if isinstance(score_result, dict) else 0,
                        'prioritization_rationale': f"Druggability tier: {druggability_tier}, in pathway network"
                    })
                
                except Exception as e:
                    logger.debug(f"Error getting therapeutic data for {gene}: {e}")
                    # Add basic entry
                    targets.append({
                        'gene': gene,
                        'druggability_score': 0.5,
                        'existing_drugs': [],
                        'clinical_trials': 0,
                        'prioritization_rationale': f"Druggability tier: {druggability_tier}"
                    })
            
            return targets
            
        except Exception as e:
            logger.error(f"Error getting therapeutic targets: {e}")
            return []
    
    async def enrich_hypotheses_batch(self, hypotheses: List[Dict[str, Any]], 
                                     max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """
        Enrich multiple hypotheses in parallel with concurrency limit.
        
        Args:
            hypotheses: List of hypothesis dicts
            max_concurrent: Maximum concurrent enrichment tasks
            
        Returns:
            List of enriched hypothesis dicts
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def enrich_with_semaphore(hyp):
            async with semaphore:
                return await self.enrich_hypothesis(hyp)
        
        enriched = await asyncio.gather(
            *[enrich_with_semaphore(hyp) for hyp in hypotheses],
            return_exceptions=True
        )
        
        # Filter out exceptions
        result = []
        for i, hyp in enumerate(enriched):
            if isinstance(hyp, Exception):
                logger.error(f"Error enriching hypothesis {i}: {hyp}")
                result.append(hypotheses[i])  # Return original
            else:
                result.append(hyp)
        
        return result
