"""
Hypothesis Enrichment Service

Enriches hypothesis data with real external data from:
- GTEx (tissue expression profiles)
- GWAS Catalog (genetic associations)
- Drug databases (therapeutic targets)
- Clinical trials (clinical evidence)

NO FALLBACKS - Only returns real data from APIs or None.
"""

import asyncio
from typing import List, Dict, Any, Optional
from app.core.logging import logger
from app.services.gtex_client import GTExClient
from app.services.gwas_client import GWASClient
from app.services.druggability_analyzer import DruggabilityAnalyzer
from app.services.clinical_evidence_integrator import ClinicalEvidenceIntegrator


class HypothesisEnricher:
    """Enriches hypotheses with real external data - NO FALLBACKS."""
    
    def __init__(self):
        self.gtex_client = GTExClient()
        self.gwas_client = GWASClient()
        self.druggability_analyzer = DruggabilityAnalyzer()
        self.clinical_integrator = ClinicalEvidenceIntegrator()
    
    async def enrich_hypothesis(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a single hypothesis with external data.
        
        Args:
            hypothesis: Hypothesis dict with aggregated_pathway and score_components
            
        Returns:
            Enriched hypothesis dict with new fields populated (or None if no data)
        """
        # Extract genes from pathway
        genes = self._extract_genes(hypothesis)
        if not genes:
            logger.warning("No genes found in hypothesis for enrichment")
            return hypothesis
        
        logger.info(f"Enriching hypothesis with {len(genes)} genes")
        
        # Enrich score_components with real data (parallel API calls)
        tasks = [
            self._enrich_tissue_expression(genes, hypothesis),
            self._enrich_gwas_associations(genes, hypothesis),
            self._enrich_therapeutic_targets(genes, hypothesis),
            self._enrich_clinical_evidence(genes, hypothesis)
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return hypothesis
    
    def _extract_genes(self, hypothesis: Dict[str, Any]) -> List[str]:
        """Extract gene list from hypothesis."""
        genes = []
        
        # Try multiple sources
        if "aggregated_pathway" in hypothesis:
            agg = hypothesis["aggregated_pathway"]
            if "pathway" in agg and "evidence_genes" in agg["pathway"]:
                genes = agg["pathway"]["evidence_genes"]
        
        if not genes and "traced_seed_genes" in hypothesis:
            genes = hypothesis["traced_seed_genes"]
        
        # Limit to first 20 genes for API efficiency
        return genes[:20] if genes else []
    
    async def _enrich_tissue_expression(self, genes: List[str], hypothesis: Dict[str, Any]) -> None:
        """
        Enrich with GTEx tissue expression data.
        NO FALLBACKS - only real GTEx data or None.
        """
        try:
            # Get tissue expression for each gene
            tissue_data = []
            
            for gene in genes[:10]:  # Limit to avoid rate limiting
                try:
                    expression = await self.gtex_client.get_tissue_expression(gene)
                    if expression:
                        # Format for frontend
                        for tissue_name, tpm_value in expression.items():
                            tissue_data.append({
                                "gene": gene,
                                "tissue": tissue_name,
                                "tpm": tpm_value,
                                "rank": 0  # Will be set after sorting
                            })
                except Exception as e:
                    logger.debug(f"Failed to get tissue expression for {gene}: {e}")
                    continue
            
            # Sort by TPM and assign ranks
            tissue_data.sort(key=lambda x: x["tpm"], reverse=True)
            for idx, item in enumerate(tissue_data[:50]):  # Top 50 tissues
                item["rank"] = idx + 1
            
            # Only add if we got real data
            if tissue_data:
                if "score_components" not in hypothesis:
                    hypothesis["score_components"] = {}
                hypothesis["score_components"]["tissue_expression_data"] = tissue_data
                logger.info(f"Added {len(tissue_data)} tissue expression records")
            
        except Exception as e:
            logger.error(f"Error enriching tissue expression: {e}")
    
    async def _enrich_gwas_associations(self, genes: List[str], hypothesis: Dict[str, Any]) -> None:
        """
        Enrich with GWAS Catalog associations.
        NO FALLBACKS - only real GWAS data or None.
        """
        try:
            gwas_data = []
            
            for gene in genes[:10]:  # Limit API calls
                try:
                    associations = await self.gwas_client.get_associations_for_gene(gene)
                    if associations:
                        for assoc in associations[:5]:  # Top 5 per gene
                            gwas_data.append({
                                "gene": gene,
                                "snp": assoc.get("variant_id", assoc.get("rsid", "Unknown")),
                                "trait": assoc.get("trait", assoc.get("disease", "Unknown")),
                                "p_value": assoc.get("p_value", assoc.get("pvalue", None)),
                                "study": assoc.get("study", assoc.get("pubmed_id", "Unknown")),
                                "chromosome": assoc.get("chromosome"),
                                "position": assoc.get("position")
                            })
                except Exception as e:
                    logger.debug(f"Failed to get GWAS data for {gene}: {e}")
                    continue
            
            # Sort by p-value (most significant first)
            gwas_data.sort(key=lambda x: x["p_value"] if x["p_value"] else 1.0)
            
            # Only add if we got real data
            if gwas_data:
                if "score_components" not in hypothesis:
                    hypothesis["score_components"] = {}
                hypothesis["score_components"]["gwas_associations"] = gwas_data[:20]  # Top 20
                logger.info(f"Added {len(gwas_data[:20])} GWAS associations")
                
        except Exception as e:
            logger.error(f"Error enriching GWAS associations: {e}")
    
    async def _enrich_therapeutic_targets(self, genes: List[str], hypothesis: Dict[str, Any]) -> None:
        """
        Enrich with therapeutic target information.
        NO FALLBACKS - only real drug database data or None.
        """
        try:
            targets_data = []
            
            for gene in genes:
                try:
                    # Get druggability assessment
                    target_info = await self.druggability_analyzer.assess_target(gene)
                    
                    if target_info and target_info.get("druggability_score", 0) > 0:
                        targets_data.append({
                            "gene_symbol": gene,
                            "druggability_score": target_info.get("druggability_score", 0),
                            "tier": target_info.get("tier", "unknown"),
                            "existing_drugs": target_info.get("known_drugs", []),
                            "clinical_trials": target_info.get("clinical_trial_count", 0),
                            "drug_classes": target_info.get("drug_classes", []),
                            "target_class": target_info.get("target_class", "Unknown"),
                            "prioritization_rationale": target_info.get("rationale", "")
                        })
                except Exception as e:
                    logger.debug(f"Failed to get therapeutic target data for {gene}: {e}")
                    continue
            
            # Sort by druggability score
            targets_data.sort(key=lambda x: x["druggability_score"], reverse=True)
            
            # Only add if we got real data
            if targets_data:
                if "score_components" not in hypothesis:
                    hypothesis["score_components"] = {}
                hypothesis["score_components"]["therapeutic_targets"] = targets_data[:15]  # Top 15
                logger.info(f"Added {len(targets_data[:15])} therapeutic targets")
                
        except Exception as e:
            logger.error(f"Error enriching therapeutic targets: {e}")
    
    async def _enrich_clinical_evidence(self, genes: List[str], hypothesis: Dict[str, Any]) -> None:
        """
        Enrich with clinical evidence.
        NO FALLBACKS - only real clinical trial data or None.
        """
        try:
            clinical_data = []
            
            # Get clinical evidence for pathway
            pathway_name = None
            if "aggregated_pathway" in hypothesis:
                pathway_name = hypothesis["aggregated_pathway"].get("pathway", {}).get("pathway_name")
            
            if pathway_name:
                evidence = await self.clinical_integrator.get_clinical_evidence(
                    genes=genes[:5],  # Limit genes
                    pathway_name=pathway_name
                )
                
                if evidence:
                    clinical_data = {
                        "clinical_trials": evidence.get("clinical_trials", []),
                        "publications": evidence.get("publications", []),
                        "drug_indications": evidence.get("drug_indications", []),
                        "safety_data": evidence.get("safety_data", {}),
                        "evidence_level": evidence.get("evidence_level", "unknown")
                    }
            
            # Only add if we got real data
            if clinical_data and clinical_data.get("clinical_trials"):
                hypothesis["stage_3_clinical_evidence"] = clinical_data
                logger.info(f"Added clinical evidence with {len(clinical_data.get('clinical_trials', []))} trials")
                
        except Exception as e:
            logger.error(f"Error enriching clinical evidence: {e}")
    
    async def enrich_hypotheses_batch(self, hypotheses: List[Dict[str, Any]], 
                                     max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """
        Enrich multiple hypotheses with rate limiting.
        
        Args:
            hypotheses: List of hypothesis dicts
            max_concurrent: Maximum concurrent API calls
            
        Returns:
            List of enriched hypotheses
        """
        logger.info(f"Starting enrichment of {len(hypotheses)} hypotheses")
        
        # Process in batches to avoid overwhelming APIs
        enriched = []
        for i in range(0, len(hypotheses), max_concurrent):
            batch = hypotheses[i:i + max_concurrent]
            tasks = [self.enrich_hypothesis(hyp) for hyp in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Enrichment failed: {result}")
                else:
                    enriched.append(result)
            
            # Small delay between batches to respect rate limits
            if i + max_concurrent < len(hypotheses):
                await asyncio.sleep(1)
        
        logger.info(f"Enrichment complete: {len(enriched)} hypotheses processed")
        return enriched
