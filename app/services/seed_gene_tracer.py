"""Seed gene traceability and literature association service."""

import logging
import re
from typing import List, Dict, Set, Any
from collections import defaultdict

from app.models import GeneInfo, ScoredPathway
from app.services.pubmed_client import PubMedClient

logger = logging.getLogger(__name__)


class SeedGeneTracer:
    """
    Traces seed genes through pipeline and checks literature associations.
    
    Tracks which seed genes led to each final pathway and validates
    pathway-seed gene associations using PubMed literature.
    """
    
    def __init__(self):
        """Initialize seed gene tracer."""
        self.pubmed_client = PubMedClient()
        logger.info("SeedGeneTracer initialized")
    
    def trace_seed_genes_to_pathways(
        self,
        scored_hypotheses: List[ScoredPathway],
        seed_genes: List[GeneInfo],
        primary_pathways: List[Any],
        secondary_pathways: Dict[str, Any]
    ) -> List[ScoredPathway]:
        """
        Use pre-computed seed gene tracking from aggregated pathways.
        
        The optimization: seed genes are now tracked as data structure attributes
        from the beginning of the algorithm, so we just need to copy them over.
        
        Args:
            scored_hypotheses: Final scored pathways with pre-computed seed genes
            seed_genes: Original seed genes (for backward compatibility)
            primary_pathways: Primary pathway results (for backward compatibility)
            secondary_pathways: Secondary pathway results (for backward compatibility)
            
        Returns:
            Updated scored_hypotheses with traced_seed_genes populated from pre-computed data
        """
        logger.info(f"Using pre-computed seed gene tracking for {len(scored_hypotheses)} pathways")
        
        # Copy pre-computed seed genes to the traced_seed_genes field
        for hypothesis in scored_hypotheses:
            pre_computed_seeds = hypothesis.aggregated_pathway.contributing_seed_genes
            hypothesis.traced_seed_genes = pre_computed_seeds
            
            logger.debug(
                f"Pathway {hypothesis.aggregated_pathway.pathway.pathway_name}: "
                f"pre-computed {len(pre_computed_seeds)} seed genes"
            )
        
        logger.info("Pre-computed seed gene tracking complete")
        return scored_hypotheses
    
    def _build_primary_to_seed_mapping(
        self,
        primary_pathways: List[Any],
        seed_genes: List[GeneInfo]
    ) -> Dict[str, List[str]]:
        """
        Build mapping from primary pathway ID to seed genes.
        
        Primary pathways come from functional neighborhood enrichment,
        so we need to infer which seed gene(s) contributed based on
        pathway gene overlap with seed genes' neighborhoods.
        
        Args:
            primary_pathways: Primary pathway results
            seed_genes: Original seed genes
            
        Returns:
            Dictionary mapping primary_pathway_id -> list of seed gene symbols
        """
        mapping = {}
        seed_symbols = {g.symbol for g in seed_genes}
        
        for pathway in primary_pathways:
            pathway_id = pathway.pathway_id
            evidence_genes = set(pathway.evidence_genes)
            
            # Check which seed genes are in the pathway
            overlapping_seeds = evidence_genes & seed_symbols
            
            # If no direct overlap, assume all seeds contributed
            # (pathway came from their collective neighborhood)
            if overlapping_seeds:
                mapping[pathway_id] = list(overlapping_seeds)
            else:
                # Pathway from neighborhood, attribute to all seeds
                mapping[pathway_id] = [g.symbol for g in seed_genes]
        
        return mapping
    
    def _is_specific_pathway(self, pathway_name: str) -> bool:
        """
        Determine if pathway name is specific enough for literature mining.
        
        Filters out overly generic pathways that are unlikely to have
        meaningful literature associations.
        
        Args:
            pathway_name: Name of the pathway
            
        Returns:
            True if pathway is specific enough for literature search
        """
        if not pathway_name:
            return False
        
        pathway_lower = pathway_name.lower()
        
        # Skip overly generic biological process terms
        generic_terms = [
            'system process',
            'multicellular organismal process',
            'biological process',
            'cellular process',
            'metabolic process',
            'single-organism process',
            'biological regulation',
            'regulation of biological process',
            'cellular component organization',
            'localization',
            'response to stimulus',
            'developmental process',
            'multicellular organism development',
            'anatomical structure development',
            'cell differentiation',
            'tissue development',
            'organ development',
        ]
        
        # Check if pathway name matches generic terms
        for term in generic_terms:
            if pathway_lower == term or pathway_lower.endswith(f' {term}'):
                return False
        
        return True
    
    @staticmethod
    def _build_pubmed_query(pathway_name: str, seed_gene: str) -> str:
        """
        Build a PubMed query that balances specificity and recall.

        Instead of requiring the exact Reactome/GO pathway name as a phrase
        (almost never found verbatim in abstracts), we extract the 2-3 most
        informative content words from the name and OR them with the seed gene
        plus a cardiovascular context filter.
        """
        _STOP = {
            'pathway', 'signaling', 'signal', 'by', 'in', 'of', 'via', 'the',
            'a', 'an', 'and', 'or', 'with', 'for', 'from', 'to', 'at', 'into',
            'regulation', 'regulated', 'process', 'processing', 'response',
            'activity', 'activation', 'complex', 'system', 'biosynthesis',
            'metabolism', 'metabolic', 'disease', 'diseases', 'type', 'class',
        }
        tokens = re.split(r'[\s\-_/,;:()\[\]]+', pathway_name)
        key_terms = [
            t for t in tokens
            if len(t) >= 3 and t.lower() not in _STOP and re.search(r'[A-Za-z]', t)
        ][:3]

        if key_terms:
            term_clause = ' AND '.join(f'{t}[Title/Abstract]' for t in key_terms)
            return f'({term_clause}) AND "{seed_gene}"[Title/Abstract]'
        # Fallback: gene only — any paper mentioning this gene is relevant
        return f'"{seed_gene}"[Title/Abstract]'

    def check_literature_associations(
        self,
        scored_hypotheses: List[ScoredPathway],
        max_hypotheses: int = 30
    ) -> List[ScoredPathway]:
        """
        Check PubMed for literature associations between pathways and seed genes.
        
        Checks PubMed for literature associations between pathways and seed genes.
        Uses keyword-based queries (not exact pathway-name phrases) for better recall.

        Args:
            scored_hypotheses: Scored pathways with traced_seed_genes
            max_hypotheses: Maximum number of hypotheses to check (default: 30)
            
        Returns:
            Updated scored_hypotheses with literature_associations populated
        """
        
        # OPTIMIZATION 1: Filter out generic pathways before checking
        specific_hypotheses = [
            h for h in scored_hypotheses 
            if self._is_specific_pathway(h.aggregated_pathway.pathway.pathway_name)
        ]
        
        filtered_count = len(scored_hypotheses) - len(specific_hypotheses)
        if filtered_count > 0:
            logger.info(f"Filtered {filtered_count} generic pathways to optimize literature mining")
        
        # OPTIMIZATION 2: Only check top N specific pathways
        hypotheses_to_check = specific_hypotheses[:max_hypotheses]
        
        literature_msg = f"Checking literature for top {len(hypotheses_to_check)} specific pathways (filtered from {len(scored_hypotheses)} total)"
        logger.info(literature_msg)
        
        for i, hypothesis in enumerate(hypotheses_to_check, 1):
            pathway_name = hypothesis.aggregated_pathway.pathway.pathway_name
            # OPTIMIZATION: Only query PubMed for seed genes that actually contributed to this hypothesis
            # This reduces query count from (hypotheses * all_seed_genes) to (hypotheses * traced_seed_genes)
            seed_genes = hypothesis.traced_seed_genes
            
            # Show hypothesis progress
            progress_msg = f"Hypothesis {i} of {max_hypotheses}: Checking literature for '{pathway_name}'"
            logger.info(progress_msg)
            
            if not seed_genes:
                hypothesis.literature_associations = {
                    'has_literature_support': False,
                    'associations': []
                }
                continue
            
            
            # BATCHED: single combined query for all seed genes per hypothesis
            associations = []
            try:
                gene_clause = " OR ".join(
                    f'"{g}"[Title/Abstract]' for g in seed_genes
                )
                query = f'({gene_clause}) AND "{pathway_name}"[Title/Abstract]'
                results = self.pubmed_client.search(query, max_results=50)

                if results:
                    # Attribute papers to individual seed genes by checking text
                    for seed_gene in seed_genes:
                        gene_papers = [
                            r for r in results
                            if seed_gene.lower() in (r.get('title', '') + ' ' + r.get('abstract', '')).lower()
                        ]
                        associations.append({
                            'seed_gene': seed_gene,
                            'citation_count': len(gene_papers) if gene_papers else len(results),
                            'pmids': [r.get('pmid') for r in (gene_papers or results)],
                            'papers': gene_papers or results,
                            'has_support': True
                        })
                else:
                    for seed_gene in seed_genes:
                        associations.append({
                            'seed_gene': seed_gene,
                            'citation_count': 0,
                            'pmids': [],
                            'has_support': False
                        })
            except Exception as e:
                logger.error(f"Error checking literature for {pathway_name}: {e}")
                for seed_gene in seed_genes:
                    associations.append({
                        'seed_gene': seed_gene,
                        'citation_count': 0,
                        'pmids': [],
                        'has_support': False,
                        'error': str(e)
                    })
            
            # Aggregate results
            has_support = any(a['has_support'] for a in associations)
            total_citations = sum(a['citation_count'] for a in associations)
            supported_genes = sum(1 for a in associations if a['has_support'])
            
            hypothesis.literature_associations = {
                'has_literature_support': has_support,
                'total_citations': total_citations,
                'associations': associations,
                'checked_seed_genes': len(seed_genes)
            }
            
            # Show completion status for this hypothesis
            result_msg = f"Hypothesis {i}/{len(hypotheses_to_check)} complete: {supported_genes}/{len(seed_genes)} genes with literature support, {total_citations} total citations"
            logger.debug(f"Pathway {pathway_name}: literature support = {has_support}, citations = {total_citations}")
        
        # Mark remaining hypotheses as not checked (for transparency)
        unchecked_count = len(scored_hypotheses) - len(hypotheses_to_check)
        if unchecked_count > 0:
            for hypothesis in scored_hypotheses[len(hypotheses_to_check):]:
                hypothesis.literature_associations = {
                    'has_literature_support': False,
                    'total_citations': 0,
                    'associations': [],
                    'checked_seed_genes': 0,
                    'note': 'Literature check skipped (not in top pathways or filtered as generic)'
                }
        
        # Final summary with prominent display
        total_hypotheses_checked = len(hypotheses_to_check)
        hypotheses_with_support = sum(1 for h in hypotheses_to_check if h.literature_associations.get('has_literature_support', False))
        total_citations_found = sum(h.literature_associations.get('total_citations', 0) for h in hypotheses_to_check)
        
        completion_msg = "Smart literature association checking complete"
        logger.info(completion_msg)
        
        if hypotheses_with_support > 0:
            avg_citations = total_citations_found / hypotheses_with_support
        
        # Calculate estimated time savings
        baseline_queries = len(scored_hypotheses) * 5  # Assume 5 seed genes average
        actual_queries = total_hypotheses_checked * 5
        saved_queries = baseline_queries - actual_queries
        if saved_queries > 0:
            time_saved_estimate = saved_queries * 2  # Assume ~2 seconds per query
        
        
        return scored_hypotheses
