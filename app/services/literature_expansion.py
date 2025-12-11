"""Literature-based gene expansion service."""

import logging
import re
from typing import List, Dict, Set, Optional
from collections import Counter

from app.models import CardiacContext, LiteratureExpansion
from app.services.pubmed_client import PubMedClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LiteratureExpander:
    """Expands gene sets using literature mining and NER."""
    
    def __init__(self):
        """Initialize literature expander."""
        self.settings = get_settings()
        self.pubmed_client = PubMedClient()
        self.cardiac_context = CardiacContext()
        
        # Common gene symbol pattern (simplified)
        self.gene_pattern = re.compile(r'\b[A-Z][A-Z0-9]{1,9}\b')
        
        logger.info("LiteratureExpander initialized")
    
    def expand_genes(
        self,
        pathway_genes: List[str],
        pathway_name: str,
        min_relevance: Optional[float] = None
    ) -> LiteratureExpansion:
        """
        Expand gene list using literature mining.
        
        Steps:
        1. Search PubMed for papers about pathway genes in cardiac context
        2. Extract gene symbols from abstracts (Named Entity Recognition)
        3. Perform co-occurrence analysis
        4. Calculate cardiac relevance scores with keyword weighting
        5. Filter by minimum relevance threshold
        
        Args:
            pathway_genes: Original pathway member genes
            pathway_name: Pathway name for context
            min_relevance: Minimum relevance threshold (default from config)
            
        Returns:
            LiteratureExpansion with expanded genes and evidence
        """
        min_relevance = min_relevance or self.settings.nets.literature_relevance_threshold
        
        logger.info(
            f"Expanding {len(pathway_genes)} genes for pathway '{pathway_name}' "
            f"(min_relevance={min_relevance})"
        )
        
        # Step 1: Search literature for pathway genes
        all_papers = self._search_literature(pathway_genes, pathway_name)
        
        if not all_papers:
            logger.warning("No literature found for pathway genes")
            return LiteratureExpansion(
                original_genes=pathway_genes,
                expanded_genes=[],
                literature_evidence={},
                cardiac_relevance_scores={}
            )
        
        logger.info(f"Retrieved {len(all_papers)} papers from literature")
        
        # Step 2-3: Extract genes and perform co-occurrence analysis
        candidate_genes = self._extract_and_analyze_genes(
            all_papers,
            pathway_genes
        )
        
        # Step 4: Calculate cardiac relevance scores
        relevance_scores = self._calculate_relevance_scores(
            candidate_genes,
            all_papers
        )
        
        # Step 5: Filter by relevance threshold
        expanded_genes = [
            gene for gene, score in relevance_scores.items()
            if score >= min_relevance and gene not in pathway_genes
        ]
        
        # Build literature evidence map
        literature_evidence = self._build_evidence_map(
            expanded_genes,
            all_papers
        )
        
        logger.info(
            f"Literature expansion complete: {len(expanded_genes)} genes added "
            f"(from {len(candidate_genes)} candidates)"
        )
        
        return LiteratureExpansion(
            original_genes=pathway_genes,
            expanded_genes=expanded_genes,
            literature_evidence=literature_evidence,
            cardiac_relevance_scores=relevance_scores
        )
    
    def _search_literature(
        self,
        genes: List[str],
        pathway_name: str
    ) -> List[Dict]:
        """
        Search PubMed for literature about genes and pathway.
        
        Args:
            genes: List of gene symbols
            pathway_name: Pathway name
            
        Returns:
            List of paper dictionaries
        """
        all_papers = []
        seen_pmids = set()
        
        # Search for each gene (limit to avoid too many queries)
        genes_to_search = genes[:10]  # Limit to top 10 genes
        
        for gene in genes_to_search:
            try:
                papers = self.pubmed_client.search_gene_literature(
                    gene_symbol=gene,
                    cardiac_context=self.cardiac_context,
                    max_results=20  # Limit per gene
                )
                
                # Deduplicate by PMID
                for paper in papers:
                    pmid = paper.get("pmid")
                    if pmid and pmid not in seen_pmids:
                        all_papers.append(paper)
                        seen_pmids.add(pmid)
                
            except Exception as e:
                logger.warning(f"Failed to search literature for {gene}: {str(e)}")
                continue
        
        # Also search for pathway name
        try:
            pathway_papers = self.pubmed_client.search_pathway_literature(
                pathway_name=pathway_name,
                cardiac_context=self.cardiac_context,
                max_results=30
            )
            
            for paper in pathway_papers:
                pmid = paper.get("pmid")
                if pmid and pmid not in seen_pmids:
                    all_papers.append(paper)
                    seen_pmids.add(pmid)
                    
        except Exception as e:
            logger.warning(f"Failed to search pathway literature: {str(e)}")
        
        return all_papers
    
    def _extract_and_analyze_genes(
        self,
        papers: List[Dict],
        known_genes: List[str]
    ) -> Dict[str, int]:
        """
        Extract gene symbols from papers and count co-occurrences.
        
        Args:
            papers: List of paper dictionaries
            known_genes: Known pathway genes
            
        Returns:
            Dictionary mapping gene symbols to co-occurrence counts
        """
        gene_counts = Counter()
        known_gene_set = set(known_genes)
        
        for paper in papers:
            # Extract text from title and abstract
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            
            # Extract potential gene symbols using pattern matching
            potential_genes = self._extract_gene_symbols(text)
            
            # Count co-occurrences with known genes
            has_known_gene = any(gene in text.upper() for gene in known_genes)
            
            if has_known_gene:
                for gene in potential_genes:
                    if gene not in known_gene_set:
                        gene_counts[gene] += 1
        
        logger.debug(f"Extracted {len(gene_counts)} candidate genes from literature")
        
        return dict(gene_counts)
    
    def _extract_gene_symbols(self, text: str) -> Set[str]:
        """
        Extract potential gene symbols from text using pattern matching.
        
        This is a simplified NER approach. A production system would use
        a proper NER model or gene recognition tool.
        
        Args:
            text: Text to extract from
            
        Returns:
            Set of potential gene symbols
        """
        # Find all matches
        matches = self.gene_pattern.findall(text)
        
        # Filter out common false positives
        false_positives = {
            "THE", "AND", "FOR", "WITH", "FROM", "THAT", "THIS",
            "ARE", "WAS", "WERE", "BEEN", "HAVE", "HAS", "HAD",
            "BUT", "NOT", "ALL", "CAN", "MAY", "WILL", "ALSO",
            "SUCH", "THESE", "THOSE", "THAN", "THEN", "WHEN",
            "WHERE", "WHO", "WHY", "HOW", "WHAT", "WHICH"
        }
        
        genes = {
            match for match in matches
            if match not in false_positives and len(match) >= 2
        }
        
        return genes
    
    def _calculate_relevance_scores(
        self,
        candidate_genes: Dict[str, int],
        papers: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate cardiac relevance scores for candidate genes.
        
        Score = (co-occurrence_count / max_count) * keyword_weight_avg
        
        Args:
            candidate_genes: Gene symbols with co-occurrence counts
            papers: List of papers
            
        Returns:
            Dictionary mapping genes to relevance scores (0-1)
        """
        if not candidate_genes:
            return {}
        
        max_count = max(candidate_genes.values())
        relevance_scores = {}
        
        # Get keyword weights
        keyword_weights = self.cardiac_context.keyword_weights
        
        for gene, count in candidate_genes.items():
            # Normalize co-occurrence count
            count_score = count / max_count if max_count > 0 else 0
            
            # Calculate average keyword weight for papers mentioning this gene
            gene_papers = [
                p for p in papers
                if gene in f"{p.get('title', '')} {p.get('abstract', '')}".upper()
            ]
            
            if gene_papers:
                keyword_score = self._calculate_keyword_score(gene_papers)
            else:
                keyword_score = 0.5  # Default
            
            # Combined score
            relevance_score = count_score * keyword_score
            relevance_scores[gene] = relevance_score
        
        return relevance_scores
    
    def _calculate_keyword_score(self, papers: List[Dict]) -> float:
        """
        Calculate average keyword weight score for papers.
        
        Args:
            papers: List of papers
            
        Returns:
            Average keyword weight score (0-1)
        """
        keyword_weights = self.cardiac_context.keyword_weights
        
        total_weight = 0
        count = 0
        
        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
            
            # Check for high priority keywords
            high_priority_matches = sum(
                1 for kw in self.cardiac_context.high_priority_keywords
                if kw.lower() in text
            )
            
            # Check for medium priority keywords
            medium_priority_matches = sum(
                1 for kw in self.cardiac_context.medium_priority_keywords
                if kw.lower() in text
            )
            
            # Check for low priority keywords
            low_priority_matches = sum(
                1 for kw in self.cardiac_context.low_priority_keywords
                if kw.lower() in text
            )
            
            # Calculate weighted score
            if high_priority_matches + medium_priority_matches + low_priority_matches > 0:
                paper_weight = (
                    high_priority_matches * keyword_weights["high_priority"] +
                    medium_priority_matches * keyword_weights["medium_priority"] +
                    low_priority_matches * keyword_weights["low_priority"]
                ) / (high_priority_matches + medium_priority_matches + low_priority_matches)
                
                total_weight += paper_weight
                count += 1
        
        # Normalize to 0-1 range
        if count > 0:
            avg_weight = total_weight / count
            # Normalize by max weight (2.0)
            return min(avg_weight / 2.0, 1.0)
        
        return 0.5  # Default
    
    def _build_evidence_map(
        self,
        expanded_genes: List[str],
        papers: List[Dict]
    ) -> Dict[str, List[str]]:
        """
        Build evidence map of PMIDs for each expanded gene.
        
        Args:
            expanded_genes: List of expanded gene symbols
            papers: List of papers
            
        Returns:
            Dictionary mapping genes to lists of PMIDs
        """
        evidence_map = {}
        
        for gene in expanded_genes:
            pmids = []
            
            for paper in papers:
                text = f"{paper.get('title', '')} {paper.get('abstract', '')}".upper()
                
                if gene in text:
                    pmid = paper.get("pmid")
                    if pmid:
                        pmids.append(pmid)
            
            evidence_map[gene] = pmids
        
        return evidence_map
