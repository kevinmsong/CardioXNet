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
        print(f"[LITERATURE DEBUG] {literature_msg}", flush=True)
        print(f"[LITERATURE DEBUG] Processing {len(hypotheses_to_process)} of {len(hypotheses)} total hypotheses", flush=True)
        
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
                print(f"[LITERATURE DEBUG] No traced seed genes for hypothesis {i}, using all {len(contributing_seed_symbols)} seed genes", flush=True)
            else:
                print(f"[LITERATURE DEBUG] Hypothesis {i} contributed by {len(contributing_seed_symbols)} specific seed genes: {', '.join(contributing_seed_symbols)}", flush=True)
            
            # Convert symbols back to GeneInfo objects for the contributing genes
            contributing_genes = [
                gene for gene in seed_genes 
                if gene.symbol in contributing_seed_symbols
            ]
            
            # Detailed progress output
            progress_msg = f"Hypothesis {i} of {top_n}: Literature search for '{pathway_name}' + {len(contributing_genes)} contributing seed genes"
            logger.info(progress_msg)
            print(f"[LITERATURE DEBUG] {progress_msg}", flush=True)
            print(f"[LITERATURE DEBUG] Pathway ID: {pathway_id}", flush=True)
            
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
                print(f"[LITERATURE SUCCESS] {result_msg}", flush=True)
                
            except Exception as e:
                error_msg = f"Hypothesis {i}/{len(hypotheses_to_process)} failed: Literature mining failed for '{pathway_name}': {str(e)}"
                logger.error(error_msg)
                print(f"[LITERATURE ERROR] {error_msg}", flush=True)
                hypothesis_citations[pathway_id] = []
        
        result = LiteratureEvidence(
            hypothesis_citations=hypothesis_citations
        )
        
        # Summary statistics
        total_citations = sum(len(citations) for citations in hypothesis_citations.values())
        hypotheses_with_citations = sum(1 for citations in hypothesis_citations.values() if citations)
        
        completion_msg = f"Literature validation complete for {len(hypothesis_citations)} hypotheses"
        logger.info(completion_msg)
        print(f"[LITERATURE COMPLETE] {completion_msg}", flush=True)
        print(f"[LITERATURE SUMMARY] Total citations found: {total_citations}", flush=True)
        print(f"[LITERATURE SUMMARY] Hypotheses with citations: {hypotheses_with_citations}/{len(hypothesis_citations)}", flush=True)
        
        if hypotheses_with_citations > 0:
            avg_citations = total_citations / hypotheses_with_citations
            print(f"[LITERATURE SUMMARY] Average citations per supported hypothesis: {avg_citations:.1f}", flush=True)
        
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
        print(f"[LITERATURE DEBUG] {literature_msg}", flush=True)
        print(f"[LITERATURE DEBUG] Processing {len(hypotheses_to_process)} of {len(hypotheses)} total hypotheses", flush=True)
        print(f"[LITERATURE DEBUG] Using max_concurrent={max_concurrent} parallel searches", flush=True)
        
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
                print(f"[LITERATURE DEBUG] No traced seed genes for hypothesis {i}, using all {len(contributing_seed_symbols)} seed genes", flush=True)
            else:
                print(f"[LITERATURE DEBUG] Hypothesis {i} contributed by {len(contributing_seed_symbols)} specific seed genes: {', '.join(contributing_seed_symbols)}", flush=True)
            
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
                print(f"[LITERATURE DEBUG] {progress_msg}", flush=True)
                print(f"[LITERATURE DEBUG] Pathway ID: {pathway_id}", flush=True)
                
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
                    print(f"[LITERATURE SUCCESS] {result_msg}", flush=True)
                    
                    return pathway_id, citations
                    
                except Exception as e:
                    error_msg = f"Hypothesis {i}/{len(hypotheses_to_process)} failed: Literature mining failed for '{pathway_name}': {str(e)}"
                    logger.error(error_msg)
                    print(f"[LITERATURE ERROR] {error_msg}", flush=True)
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
        print(f"[LITERATURE COMPLETE] {completion_msg}", flush=True)
        print(f"[LITERATURE SUMMARY] Total citations found: {total_citations}", flush=True)
        print(f"[LITERATURE SUMMARY] Hypotheses with citations: {hypotheses_with_citations}/{len(hypothesis_citations)}", flush=True)
        
        if hypotheses_with_citations > 0:
            avg_citations = total_citations / hypotheses_with_citations
            print(f"[LITERATURE SUMMARY] Average citations per supported hypothesis: {avg_citations:.1f}", flush=True)
        
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
        print(f"[LITERATURE SEARCH] Searching with genes: {', '.join(gene_symbols)}", flush=True)
        
        # Construct search query with seed genes + pathway terms
        query = self._construct_query(pathway_name, seed_genes, disease_context, disease_synonyms)
        
        print(f"[LITERATURE SEARCH] PubMed query: {query[:100]}{'...' if len(query) > 100 else ''}", flush=True)
        logger.debug(f"Literature query: {query}")
        
        # Search PubMed
        print(f"[LITERATURE SEARCH] Querying PubMed...", flush=True)
        papers = self._search_pubmed(query)
        
        print(f"[LITERATURE SEARCH] Retrieved {len(papers)} papers from PubMed", flush=True)
        
        # Calculate relevance scores and create citations
        print(f"[LITERATURE SEARCH] Creating citations and calculating relevance scores...", flush=True)
        citations = self._create_citations(papers, pathway_name, seed_genes)
        
        # Sort by relevance score
        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        
        if citations:
            top_score = citations[0].relevance_score
            print(f"[LITERATURE SEARCH] Citations created: {len(citations)}, top relevance score: {top_score:.3f}", flush=True)
        else:
            print(f"[LITERATURE SEARCH] No citations created from {len(papers)} papers", flush=True)
        
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
        print(f"[HYPOTHESIS LITERATURE] Hypothesis {hypothesis_id}: Searching literature for '{pathway_name}' + {len(gene_symbols)} contributing genes: {', '.join(gene_symbols)}", flush=True)
        
        # Construct targeted query with only contributing seed genes
        query = self._construct_hypothesis_query(pathway_name, contributing_seed_genes, disease_context, disease_synonyms)
        
        print(f"[HYPOTHESIS LITERATURE] Targeted PubMed query: {query[:150]}{'...' if len(query) > 150 else ''}", flush=True)
        logger.debug(f"Hypothesis literature query for {hypothesis_id}: {query}")
        
        # Search PubMed with hypothesis-specific query
        print(f"[HYPOTHESIS LITERATURE] Querying PubMed for hypothesis {hypothesis_id}...", flush=True)
        papers = self._search_pubmed(query)
        
        print(f"[HYPOTHESIS LITERATURE] Retrieved {len(papers)} papers for hypothesis {hypothesis_id}", flush=True)
        
        # Calculate relevance scores with hypothesis-specific context
        print(f"[HYPOTHESIS LITERATURE] Creating citations with hypothesis-specific relevance scoring...", flush=True)
        citations = self._create_hypothesis_citations(papers, pathway_name, contributing_seed_genes, hypothesis_id)
        
        # Sort by relevance score
        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        
        if citations:
            top_score = citations[0].relevance_score
            print(f"[HYPOTHESIS LITERATURE] Hypothesis {hypothesis_id}: {len(citations)} citations created, top relevance: {top_score:.3f}", flush=True)
        else:
            print(f"[HYPOTHESIS LITERATURE] Hypothesis {hypothesis_id}: No citations created from {len(papers)} papers", flush=True)
        
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
        # Extract gene symbols from contributing genes only
        gene_symbols = [gene.symbol for gene in contributing_seed_genes]
        
        # Build more focused query with pathway name and contributing genes
        if len(gene_symbols) > 0:
            # If we have specific contributing genes, focus on them
            gene_query = " OR ".join([f'"{gene}"[Title/Abstract]' for gene in gene_symbols[:5]])  # Limit to 5 genes max
        else:
            # Fallback if no contributing genes identified
            gene_query = "gene[Title/Abstract]"
        
        pathway_query = f'"{pathway_name}"[Title/Abstract]'
        
        # Add disease context if provided
        disease_query = ""
        if disease_context and disease_synonyms:
            # Include disease synonyms in the search
            disease_terms = [disease_context] + disease_synonyms[:3]  # Limit to 4 terms max
            disease_query = " OR ".join([f'"{term}"[Title/Abstract]' for term in disease_terms])
            disease_query = f" AND ({disease_query})"
        
        # Simplified query: genes + cardiac terms (no mandatory pathway requirement)
        # This is more flexible and will return more results
        cardiac_keywords = ["cardiovascular", "cardiac", "heart"]  # Simple cardiac terms
        keyword_query = " OR ".join([f'"{kw}"[Title/Abstract]' for kw in cardiac_keywords])
        
        # Build flexible query: genes AND (cardiac terms OR pathway)
        # This ensures we get papers about the genes in cardiac context
        query = f"({gene_query}) AND ({keyword_query} OR {pathway_query})"
        
        # Add species filter (optional, commented out to increase results)
        # query += f' AND "{self.cardiac_context.species}"[Organism]'
        
        return query
    
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
        
        print(f"[HYPOTHESIS CITATIONS] Processing {len(papers)} papers for hypothesis {hypothesis_id}...", flush=True)
        
        for i, paper in enumerate(papers, 1):
            # Show progress for citation creation
            if i <= 3 or i % 10 == 0 or i == len(papers):
                print(f"[HYPOTHESIS CITATIONS] Hypothesis {hypothesis_id} paper {i}/{len(papers)}: {paper.get('title', 'No title')[:50]}...", flush=True)
            
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
                relevance_score=relevance_score
            )
            
            citations.append(citation)
            
            # Show high relevance papers with hypothesis context
            if relevance_score > 0.7:
                contributing_genes_str = ", ".join([g.symbol for g in contributing_seed_genes])
                print(f"[HIGH HYPOTHESIS RELEVANCE] {hypothesis_id}: Score {relevance_score:.3f} (genes: {contributing_genes_str}) - {paper.get('title', '')[:60]}...", flush=True)
        
        print(f"[HYPOTHESIS CITATIONS] Hypothesis {hypothesis_id}: Created {len(citations)} citations", flush=True)
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
        # Extract gene symbols
        gene_symbols = [gene.symbol for gene in seed_genes[:5]]  # Limit to 5 genes
        
        # Build query with pathway name and genes
        gene_query = " OR ".join([f'"{gene}"[Title/Abstract]' for gene in gene_symbols])
        pathway_query = f'"{pathway_name}"[Title/Abstract]'
        
        # Add cardiac keywords
        cardiac_keywords = self.cardiac_context.high_priority_keywords[:3]
        
        # Add disease context to cardiac keywords if provided
        if disease_context and disease_synonyms:
            # Add disease-specific terms to cardiac keywords
            disease_terms = [term.lower() for term in disease_synonyms[:2]]  # Limit to 2
            cardiac_keywords.extend(disease_terms)
            cardiac_keywords = list(set(cardiac_keywords))  # Remove duplicates
        
        keyword_query = " OR ".join([f'"{kw}"[Title/Abstract]' for kw in cardiac_keywords])
        
        # Combine with AND logic
        query = f"({pathway_query}) AND ({gene_query}) AND ({keyword_query})"
        
        # Add species filter
        query += f' AND "{self.cardiac_context.species}"[Organism]'
        
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
            # Further reduced limit for speed optimization (from 50 to 25)
            max_results = 25
            print(f"[PUBMED SEARCH] Searching for up to {max_results} papers...", flush=True)
            
            papers = self.pubmed_client._search_pubmed(query, max_results=max_results)
            
            if papers:
                print(f"[PUBMED SEARCH] Found {len(papers)} PMIDs, fetching paper details...", flush=True)
                # Fetch paper details
                paper_details = self.pubmed_client._fetch_papers(papers)
                print(f"[PUBMED SEARCH] Successfully fetched details for {len(paper_details)} papers", flush=True)
                return paper_details
            else:
                print(f"[PUBMED SEARCH] No papers found for this query", flush=True)
                return []
            
        except Exception as e:
            error_msg = f"PubMed search failed: {str(e)}"
            logger.warning(error_msg)
            print(f"[PUBMED ERROR] {error_msg}", flush=True)
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
        
        print(f"[CITATION CREATION] Processing {len(papers)} papers to create citations...", flush=True)
        
        for i, paper in enumerate(papers, 1):
            # Show progress for citation creation
            if i <= 5 or i % 10 == 0 or i == len(papers):
                print(f"[CITATION CREATION] Processing paper {i}/{len(papers)}: {paper.get('title', 'No title')[:60]}...", flush=True)
            
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
                relevance_score=relevance_score
            )
            
            citations.append(citation)
            
            # Show high relevance papers
            if relevance_score > 0.7:
                print(f"[HIGH RELEVANCE] Paper {i}: Score {relevance_score:.3f} - {paper.get('title', '')[:80]}...", flush=True)
        
        print(f"[CITATION CREATION] Created {len(citations)} citations", flush=True)
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
