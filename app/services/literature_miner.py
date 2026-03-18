"""Literature validation service for pathway hypotheses (Stage 4)."""

import logging
import asyncio
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models import (
    GeneInfo,
    ScoredPathway,
    CardiacContext,
    Citation,
    LiteratureEvidence
)
from app.services.pubmed_client import PubMedClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LiteratureMiner:
    """Mines literature to validate pathway hypotheses (Stage 4)."""
    
    def __init__(self):
        """Initialize literature miner."""
        self.settings = get_settings()
        self.pubmed_client = PubMedClient()
        self.cardiac_context = CardiacContext()
        
        logger.info("LiteratureMiner initialized")

    @staticmethod
    def _console_safe(text: str, limit: Optional[int] = None) -> str:
        """Normalize external text for Windows console output."""
        safe_text = (text or "").replace("\r", " ").replace("\n", " ")
        if limit is not None and len(safe_text) > limit:
            safe_text = safe_text[:limit]
        return safe_text.encode("ascii", errors="replace").decode("ascii")
    
    def validate_hypotheses(
        self,
        hypotheses: List[ScoredPathway],
        seed_genes: List[GeneInfo],
        top_n: Optional[int] = None,
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None
    ) -> LiteratureEvidence:
        """
        Validate top N hypotheses using literature mining focused on contributing seed genes.
        
        Args:
            hypotheses: Scored pathway hypotheses with traced seed genes
            seed_genes: Original seed genes (for fallback)
            top_n: Number of top hypotheses to validate (default from config)
            disease_context: Optional disease context for targeted literature search
            disease_synonyms: Optional list of disease synonyms for enhanced matching
            
        Returns:
            LiteratureEvidence with citations for each hypothesis
        """
        # If top_n is None, process ALL hypotheses; otherwise use specified limit or config default
        if top_n is None:
            hypotheses_to_process = hypotheses
            literature_msg = f"Validating ALL {len(hypotheses)} hypotheses using seed gene-specific literature mining"
        else:
            top_n = top_n or self.settings.nets.top_hypotheses_count
            hypotheses_to_process = hypotheses[:top_n]
            literature_msg = f"Validating top {top_n} hypotheses using seed gene-specific literature mining"
        
        logger.info(literature_msg)
        pass
        pass
        
        hypothesis_citations = {}
        
        # Validate hypotheses with seed gene-specific literature search
        for i, hypothesis in enumerate(hypotheses_to_process, 1):
            pathway_id = hypothesis.aggregated_pathway.pathway.pathway_id
            pathway_name = hypothesis.aggregated_pathway.pathway.pathway_name
            
            # Get contributing seed genes for this specific hypothesis
            contributing_seed_symbols = getattr(hypothesis, 'traced_seed_genes', [])
            if not contributing_seed_symbols:
                # Fallback to all seed genes if tracing not available
                contributing_seed_symbols = [gene.symbol for gene in seed_genes]
                pass
            else:
                pass
            
            # Convert symbols back to GeneInfo objects for the contributing genes
            contributing_genes = [
                gene for gene in seed_genes 
                if gene.symbol in contributing_seed_symbols
            ]
            
            # Detailed progress output
            progress_msg = f"Hypothesis {i} of {top_n}: Literature search for '{pathway_name}' + {len(contributing_genes)} contributing seed genes"
            logger.info(progress_msg)
            pass
            pass
            
            try:
                citations = self._mine_hypothesis_literature(
                    pathway_name,
                    contributing_genes,
                    hypothesis_id=pathway_id,
                    disease_context=disease_context,
                    disease_synonyms=disease_synonyms
                )
                
                hypothesis_citations[pathway_id] = citations
                
                result_msg = f"Hypothesis {i}/{len(hypotheses_to_process)} complete: Found {len(citations)} citations for '{pathway_name}' + {len(contributing_genes)} seed genes"
                logger.info(result_msg)
                pass
                
            except Exception as e:
                error_msg = f"Hypothesis {i}/{len(hypotheses_to_process)} failed: Literature mining failed for '{pathway_name}': {str(e)}"
                logger.error(error_msg)
                pass
                hypothesis_citations[pathway_id] = []
        
        result = LiteratureEvidence(
            hypothesis_citations=hypothesis_citations
        )
        
        # Summary statistics
        total_citations = sum(len(citations) for citations in hypothesis_citations.values())
        hypotheses_with_citations = sum(1 for citations in hypothesis_citations.values() if citations)
        
        completion_msg = f"Literature validation complete for {len(hypothesis_citations)} hypotheses"
        logger.info(completion_msg)
        pass
        pass
        pass
        
        if hypotheses_with_citations > 0:
            avg_citations = total_citations / hypotheses_with_citations
            pass
        
        return result
    
    async def validate_hypotheses_async(
        self,
        hypotheses: List[ScoredPathway],
        seed_genes: List[GeneInfo],
        top_n: Optional[int] = None,
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None,
        max_concurrent: int = 3
    ) -> LiteratureEvidence:
        """
        Validate top N hypotheses using seed gene-specific literature mining (async version).
        
        Args:
            hypotheses: Scored pathway hypotheses with traced seed genes
            seed_genes: Original seed genes (for fallback)
            top_n: Number of top hypotheses to validate (default from config)
            disease_context: Optional disease context for targeted literature search
            disease_synonyms: Optional list of disease synonyms for enhanced matching
            max_concurrent: Maximum number of concurrent literature searches
            
        Returns:
            LiteratureEvidence with citations for each hypothesis
        """
        # If top_n is None, process ALL hypotheses; otherwise use specified limit or config default
        if top_n is None:
            hypotheses_to_process = hypotheses
            literature_msg = f"Validating ALL {len(hypotheses)} hypotheses using parallel seed gene-specific literature mining"
        else:
            top_n = top_n or self.settings.nets.top_hypotheses_count
            hypotheses_to_process = hypotheses[:top_n]
            literature_msg = f"Validating top {top_n} hypotheses using parallel seed gene-specific literature mining"
        
        logger.info(literature_msg)
        pass
        pass
        pass
        
        hypothesis_citations = {}
        
        # Prepare tasks for hypotheses
        tasks = []
        for i, hypothesis in enumerate(hypotheses_to_process, 1):
            pathway_id = hypothesis.aggregated_pathway.pathway.pathway_id
            pathway_name = hypothesis.aggregated_pathway.pathway.pathway_name
            
            # Get contributing seed genes for this specific hypothesis
            contributing_seed_symbols = getattr(hypothesis, 'traced_seed_genes', [])
            if not contributing_seed_symbols:
                # Fallback to all seed genes if tracing not available
                contributing_seed_symbols = [gene.symbol for gene in seed_genes]
                pass
            else:
                pass
            
            # Convert symbols back to GeneInfo objects for the contributing genes
            contributing_genes = [
                gene for gene in seed_genes 
                if gene.symbol in contributing_seed_symbols
            ]
            
            tasks.append((i, pathway_id, pathway_name, contributing_genes))
        
        # Process tasks in parallel with semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_hypothesis(task_data: Tuple[int, str, str, List[GeneInfo]]) -> Tuple[str, List[Citation]]:
            i, pathway_id, pathway_name, contributing_genes = task_data
            
            async with semaphore:
                progress_msg = f"Hypothesis {i} of {len(hypotheses_to_process)}: Literature search for '{pathway_name}' + {len(contributing_genes)} contributing seed genes"
                logger.info(progress_msg)
                pass
                pass
                
                try:
                    # Run the synchronous literature mining in a thread pool
                    loop = asyncio.get_event_loop()
                    citations = await loop.run_in_executor(
                        None,
                        self._mine_hypothesis_literature,
                        pathway_name,
                        contributing_genes,
                        pathway_id,
                        disease_context,
                        disease_synonyms
                    )
                    
                    result_msg = f"Hypothesis {i}/{len(hypotheses_to_process)} complete: Found {len(citations)} citations for '{pathway_name}' + {len(contributing_genes)} seed genes"
                    logger.info(result_msg)
                    pass
                    
                    return pathway_id, citations
                    
                except Exception as e:
                    error_msg = f"Hypothesis {i}/{len(hypotheses_to_process)} failed: Literature mining failed for '{pathway_name}': {str(e)}"
                    logger.error(error_msg)
                    pass
                    return pathway_id, []
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*[process_hypothesis(task) for task in tasks])
        
        # Collect results
        for pathway_id, citations in results:
            hypothesis_citations[pathway_id] = citations
        
        result = LiteratureEvidence(
            hypothesis_citations=hypothesis_citations
        )
        
        # Summary statistics
        total_citations = sum(len(citations) for citations in hypothesis_citations.values())
        hypotheses_with_citations = sum(1 for citations in hypothesis_citations.values() if citations)
        
        completion_msg = f"Parallel literature validation complete for {len(hypothesis_citations)} hypotheses"
        logger.info(completion_msg)
        pass
        pass
        pass
        
        if hypotheses_with_citations > 0:
            avg_citations = total_citations / hypotheses_with_citations
            pass
        
        return result
    
    def _mine_pathway_literature(
        self,
        pathway_name: str,
        seed_genes: List[GeneInfo],
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None
    ) -> List[Citation]:
        """
        Mine literature for a pathway hypothesis.
        
        Args:
            pathway_name: Pathway name
            seed_genes: Seed genes
            disease_context: Optional disease context for targeted search
            disease_synonyms: Optional list of disease synonyms
            
        Returns:
            List of Citation objects
        """
        # Show gene context for this pathway search
        gene_symbols = [gene.symbol for gene in seed_genes[:5]]  # Show up to 5 genes
        pass
        
        # Construct search query with seed genes + pathway terms
        query = self._construct_query(pathway_name, seed_genes, disease_context, disease_synonyms)
        
        pass
        logger.debug(f"Literature query: {query}")
        
        # Search PubMed
        pass
        papers = self._search_pubmed(query)
        
        pass
        
        # Calculate relevance scores and create citations
        pass
        citations = self._create_citations(papers, pathway_name, seed_genes)
        
        # Sort by relevance score
        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        
        if citations:
            top_score = citations[0].relevance_score
            pass
        else:
            pass
        
        return citations
    
    def _mine_hypothesis_literature(
        self,
        pathway_name: str,
        contributing_seed_genes: List[GeneInfo],
        hypothesis_id: str,
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None
    ) -> List[Citation]:
        """
        Mine literature for a specific hypothesis using its contributing seed genes.
        
        This provides more targeted literature evidence by focusing only on the seed genes
        that actually contributed to discovering this specific pathway hypothesis.
        
        Args:
            pathway_name: Pathway name
            contributing_seed_genes: Only the seed genes that contributed to this hypothesis
            hypothesis_id: Hypothesis identifier for logging
            disease_context: Optional disease context for targeted search
            disease_synonyms: Optional list of disease synonyms for enhanced matching
            
        Returns:
            List of Citation objects relevant to this specific hypothesis
        """
        # Show which seed genes are being used for this specific hypothesis
        gene_symbols = [gene.symbol for gene in contributing_seed_genes]
        pass
        
        # Construct targeted query with only contributing seed genes
        query = self._construct_hypothesis_query(pathway_name, contributing_seed_genes, disease_context, disease_synonyms)
        
        pass
        logger.debug(f"Hypothesis literature query for {hypothesis_id}: {query}")
        
        # Search PubMed with hypothesis-specific query
        pass
        papers = self._search_pubmed(query)
        
        pass
        
        # Calculate relevance scores with hypothesis-specific context
        pass
        citations = self._create_hypothesis_citations(papers, pathway_name, contributing_seed_genes, hypothesis_id)
        
        # Sort by relevance score
        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        
        if citations:
            top_score = citations[0].relevance_score
            pass
        else:
            pass
        
        return citations
    
    def _construct_hypothesis_query(
        self,
        pathway_name: str,
        contributing_seed_genes: List[GeneInfo],
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None
    ) -> str:
        """
        Construct PubMed search query focused on specific contributing seed genes.
        
        Args:
            pathway_name: Pathway name
            contributing_seed_genes: Only the seed genes that contributed to this hypothesis
            disease_context: Optional disease context for targeted search
            disease_synonyms: Optional list of disease synonyms for enhanced matching
            
        Returns:
            PubMed query string optimized for this specific hypothesis
        """
        # Extract gene symbols from contributing genes only (up to 8 for broader coverage)
        gene_symbols = [gene.symbol for gene in contributing_seed_genes]

        if gene_symbols:
            gene_query = " OR ".join([f'{gene}[Title/Abstract]' for gene in gene_symbols[:8]])
        else:
            gene_query = "gene[Title/Abstract]"

        # Search only by gene — cardiac relevance ranking handles prioritisation.
        # Adding an AND cardiac-keyword clause is too restrictive for genes that
        # are not primarily annotated as cardiac in the literature.
        return gene_query
    
    def _create_hypothesis_citations(
        self,
        papers: List[Dict],
        pathway_name: str,
        contributing_seed_genes: List[GeneInfo],
        hypothesis_id: str
    ) -> List[Citation]:
        """
        Create Citation objects with hypothesis-specific relevance scoring.
        
        Args:
            papers: List of paper dictionaries
            pathway_name: Pathway name
            contributing_seed_genes: Only the seed genes that contributed to this hypothesis
            hypothesis_id: Hypothesis identifier for logging
            
        Returns:
            List of Citation objects with enhanced relevance for this specific hypothesis
        """
        citations = []
        
        pass
        
        for i, paper in enumerate(papers, 1):
            # Show progress for citation creation
            if i <= 3 or i % 10 == 0 or i == len(papers):
                title_preview = self._console_safe(paper.get("title", "No title"), limit=50)
                pass
            
            # Calculate hypothesis-specific relevance score
            relevance_score = self._calculate_hypothesis_relevance(
                paper,
                pathway_name,
                contributing_seed_genes,
                hypothesis_id
            )
            
            # Create citation with enhanced metadata
            citation = Citation(
                pmid=paper.get("pmid", ""),
                title=paper.get("title", ""),
                authors=paper.get("authors", ""),
                year=paper.get("year", 0),
                relevance_score=relevance_score,
                journal=paper.get("journal", "") or None,
                abstract=paper.get("abstract", "") or None,
            )
            
            citations.append(citation)
            
            # Show high relevance papers with hypothesis context
            if relevance_score > 0.7:
                contributing_genes_str = ", ".join([g.symbol for g in contributing_seed_genes])
                title_preview = self._console_safe(paper.get("title", ""), limit=60)
                pass
        
        pass
        return citations
    
    def _calculate_hypothesis_relevance(
        self,
        paper: Dict,
        pathway_name: str,
        contributing_seed_genes: List[GeneInfo],
        hypothesis_id: str
    ) -> float:
        """
        Calculate enhanced relevance score specifically for a hypothesis and its contributing genes.
        
        Enhanced scoring that gives higher weight to papers mentioning the specific
        seed genes that contributed to this pathway discovery.
        
        Args:
            paper: Paper dictionary
            pathway_name: Pathway name
            contributing_seed_genes: Only the seed genes that contributed to this hypothesis
            hypothesis_id: Hypothesis identifier for debugging
            
        Returns:
            Relevance score (0-1) optimized for this specific hypothesis
        """
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        score = 0.0
        
        # 1. Pathway name mention (weight: 0.25)
        pathway_terms = pathway_name.lower().split()
        pathway_matches = sum(1 for term in pathway_terms if len(term) > 3 and term in text)
        if pathway_matches > 0:
            score += 0.25 * min(pathway_matches / len(pathway_terms), 1.0)
        
        # 2. Contributing seed gene mentions (weight: 0.35 - INCREASED for hypothesis specificity)
        contributing_gene_mentions = sum(
            1 for gene in contributing_seed_genes
            if gene.symbol.lower() in text
        )
        if contributing_gene_mentions > 0 and len(contributing_seed_genes) > 0:
            # Higher weight for papers mentioning the specific contributing genes
            gene_coverage = contributing_gene_mentions / len(contributing_seed_genes)
            score += 0.35 * gene_coverage
            
            if contributing_gene_mentions > 1:
                # Bonus for mentioning multiple contributing genes
                score += 0.05 * min((contributing_gene_mentions - 1) / 3, 1.0)
        
        # 3. Cardiac keyword matches (weight: 0.2)
        high_priority_matches = sum(
            1 for kw in self.cardiac_context.high_priority_keywords
            if kw.lower() in text
        )
        
        medium_priority_matches = sum(
            1 for kw in self.cardiac_context.medium_priority_keywords
            if kw.lower() in text
        )
        
        if high_priority_matches > 0 or medium_priority_matches > 0:
            keyword_score = (high_priority_matches * 1.0 + medium_priority_matches * 0.5) / 3.0
            score += 0.2 * min(keyword_score, 1.0)
        
        # 4. Recency bonus (weight: 0.1)
        year = paper.get('year', 0)
        if year >= 2020:
            score += 0.1
        elif year >= 2015:
            score += 0.05
        
        # 5. Citation impact (weight: 0.1)
        citation_count = paper.get('citation_count', 0)
        if citation_count > 0:
            citation_score = min(citation_count / 20.0, 1.0)  # 20+ citations = full score
            score += 0.1 * citation_score
        
        return min(score, 1.0)
    
    def _construct_query(
        self,
        pathway_name: str,
        seed_genes: List[GeneInfo],
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None
    ) -> str:
        """
        Construct PubMed search query.
        
        Args:
            pathway_name: Pathway name
            seed_genes: Seed genes
            disease_context: Optional disease context for targeted search
            disease_synonyms: Optional list of disease synonyms
            
        Returns:
            PubMed query string
        """
        import re as _re
        _STOP = {
            'pathway', 'signaling', 'signal', 'by', 'in', 'of', 'via', 'the',
            'a', 'an', 'and', 'or', 'with', 'for', 'from', 'to', 'regulation',
            'regulated', 'process', 'processing', 'response', 'activity',
            'activation', 'complex', 'system', 'biosynthesis', 'metabolism',
            'metabolic', 'disease', 'diseases', 'type', 'class',
        }
        tokens = _re.split(r'[\s\-_/,;:()\[\]]+', pathway_name)
        key_terms = [
            t for t in tokens
            if len(t) >= 3 and t.lower() not in _STOP and _re.search(r'[A-Za-z]', t)
        ][:3]

        gene_symbols = [gene.symbol for gene in seed_genes[:8]]
        gene_query = " OR ".join([f'{g}[Title/Abstract]' for g in gene_symbols])

        cardiac_keywords = ["cardiovascular", "cardiac", "heart", "myocardial", "cardiomyopathy"]
        keyword_query = " OR ".join([f'{kw}[Title/Abstract]' for kw in cardiac_keywords])

        if key_terms:
            term_clause = " OR ".join([f'{t}[Title/Abstract]' for t in key_terms])
            query = f"({gene_query}) AND ({keyword_query} OR {term_clause})"
        else:
            query = f"({gene_query}) AND ({keyword_query})"

        return query
    
    def _search_pubmed(self, query: str) -> List[Dict]:
        """
        Search PubMed with constructed query.
        
        Args:
            query: PubMed query string
            
        Returns:
            List of paper dictionaries
        """
        try:
            max_results = 100

            papers = self.pubmed_client._search_pubmed(query, max_results=max_results)
            
            if papers:
                pass
                # Fetch paper details
                paper_details = self.pubmed_client._fetch_papers(papers)
                pass
                return paper_details
            else:
                pass
                return []
            
        except Exception as e:
            error_msg = f"PubMed search failed: {str(e)}"
            logger.warning(error_msg)
            pass
            return []
    
    def _create_citations(
        self,
        papers: List[Dict],
        pathway_name: str,
        seed_genes: List[GeneInfo]
    ) -> List[Citation]:
        """
        Create Citation objects with relevance scores.
        
        Args:
            papers: List of paper dictionaries
            pathway_name: Pathway name
            seed_genes: Seed genes
            
        Returns:
            List of Citation objects
        """
        citations = []
        
        pass
        
        for i, paper in enumerate(papers, 1):
            # Show progress for citation creation
            if i <= 5 or i % 10 == 0 or i == len(papers):
                title_preview = self._console_safe(paper.get("title", "No title"), limit=60)
                pass
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance(
                paper,
                pathway_name,
                seed_genes
            )
            
            # Create citation
            citation = Citation(
                pmid=paper.get("pmid", ""),
                title=paper.get("title", ""),
                authors=paper.get("authors", ""),
                year=paper.get("year", 0),
                relevance_score=relevance_score,
                journal=paper.get("journal", "") or None,
                abstract=paper.get("abstract", "") or None,
            )
            
            citations.append(citation)
            
            # Show high relevance papers
            if relevance_score > 0.7:
                title_preview = self._console_safe(paper.get("title", ""), limit=80)
                pass
        
        pass
        return citations
    
    def _calculate_relevance(
        self,
        paper: Dict,
        pathway_name: str,
        seed_genes: List[GeneInfo]
    ) -> float:
        """
        Calculate enhanced relevance score for a paper.
        
        Score based on:
        - Pathway name mentions (0.3)
        - Seed gene mentions (0.25)
        - Cardiac keyword matches (0.25)
        - Recency bonus (0.1)
        - Citation impact (0.1)
        
        Args:
            paper: Paper dictionary
            pathway_name: Pathway name
            seed_genes: Seed genes
            
        Returns:
            Relevance score (0-1)
        """
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        
        score = 0.0
        
        # 1. Pathway name mention (weight: 0.3)
        pathway_terms = pathway_name.lower().split()
        pathway_matches = sum(1 for term in pathway_terms if len(term) > 3 and term in text)
        if pathway_matches > 0:
            score += 0.3 * min(pathway_matches / len(pathway_terms), 1.0)
        
        # 2. Seed gene mentions (weight: 0.25)
        gene_mentions = sum(
            1 for gene in seed_genes
            if gene.symbol.lower() in text
        )
        if gene_mentions > 0:
            score += 0.25 * min(gene_mentions / len(seed_genes), 1.0)
        
        # 3. Cardiac keyword matches (weight: 0.25)
        keyword_weights = self.cardiac_context.keyword_weights
        
        high_priority_matches = sum(
            1 for kw in self.cardiac_context.high_priority_keywords
            if kw.lower() in text
        )
        
        medium_priority_matches = sum(
            1 for kw in self.cardiac_context.medium_priority_keywords
            if kw.lower() in text
        )
        
        low_priority_matches = sum(
            1 for kw in self.cardiac_context.low_priority_keywords
            if kw.lower() in text
        )
        
        total_matches = high_priority_matches + medium_priority_matches + low_priority_matches
        
        if total_matches > 0:
            weighted_keyword_score = (
                high_priority_matches * keyword_weights["high_priority"] +
                medium_priority_matches * keyword_weights["medium_priority"] +
                low_priority_matches * keyword_weights["low_priority"]
            ) / (total_matches * 2.0)  # Normalize by max weight
            
            score += 0.25 * weighted_keyword_score
        
        # 4. Recency bonus (weight: 0.1) - favor recent papers
        year = paper.get('year', 0)
        if year >= 2020:
            score += 0.1
        elif year >= 2015:
            score += 0.05
        
        # 5. Citation impact (weight: 0.1) - if available from Semantic Scholar
        citation_count = paper.get('citation_count', 0)
        if citation_count > 0:
            # Logarithmic scale: 10+ citations = full score
            citation_score = min(citation_count / 10.0, 1.0)
            score += 0.1 * citation_score
        
        return min(score, 1.0)
