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
    
    # Disease-context PubMed search terms (top 3-5 high-signal terms per context)
    DISEASE_QUERY_TERMS: Dict[str, List[str]] = {
        "heart_failure": [
            "heart failure", "cardiac failure", "ventricular dysfunction",
            "ejection fraction", "cardiac remodeling",
        ],
        "myocardial_infarction": [
            "myocardial infarction", "ischemia reperfusion",
            "cardiac ischemia", "coronary artery disease",
        ],
        "cardiomyopathy": [
            "cardiomyopathy", "dilated cardiomyopathy",
            "hypertrophic cardiomyopathy", "arrhythmogenic cardiomyopathy",
        ],
        "diabetic_cardiomyopathy": [
            "diabetic cardiomyopathy", "diabetic heart disease",
            "cardiac insulin resistance", "glucose metabolism heart",
        ],
        "arrhythmia": [
            "cardiac arrhythmia", "atrial fibrillation",
            "ventricular tachycardia", "ion channel heart",
        ],
        "cardiac_regeneration": [
            "cardiac regeneration", "cardiomyocyte proliferation",
            "cardiac repair", "cardiac reprogramming", "heart regeneration",
        ],
    }

    def __init__(self):
        """Initialize literature miner."""
        self.settings = get_settings()
        self.pubmed_client = PubMedClient()
        self.cardiac_context = CardiacContext()

        # Per-run records keyed by pathway id, populated during mining and
        # harvested into the LiteratureEvidence result.
        self._last_hit_counts: Dict[str, int] = {}
        self._last_query_tier: Dict[str, str] = {}
        # Corpus size of the pathway concept on its own, recorded only when the
        # full intersection returns nothing, to tell a real gap from a pathway
        # name that PubMed cannot match at all.
        self._last_concept_counts: Dict[str, int] = {}

        logger.info("LiteratureMiner initialized")

    @staticmethod
    def _console_safe(text: str, limit: Optional[int] = None) -> str:
        """Normalize external text for Windows console output."""
        safe_text = (text or "").replace("\r", " ").replace("\n", " ")
        if limit is not None and len(safe_text) > limit:
            safe_text = safe_text[:limit]
        return safe_text.encode("ascii", errors="replace").decode("ascii")
    
    
    async def validate_hypotheses_async(
        self,
        hypotheses: List[ScoredPathway],
        seed_genes: List[GeneInfo],
        top_n: Optional[int] = None,
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None,
        max_concurrent: int = 8
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
                    
                    return pathway_id, citations
                    
                except Exception as e:
                    error_msg = f"Hypothesis {i}/{len(hypotheses_to_process)} failed: Literature mining failed for '{pathway_name}': {str(e)}"
                    logger.error(error_msg)
                    return pathway_id, []
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*[process_hypothesis(task) for task in tasks])
        
        # Collect results
        for pathway_id, citations in results:
            hypothesis_citations[pathway_id] = citations
        
        result = LiteratureEvidence(
            hypothesis_citations=hypothesis_citations,
            hypothesis_hit_counts={
                pid: self._last_hit_counts.get(pid, -1) for pid in hypothesis_citations
            },
            query_tier={
                pid: self._last_query_tier.get(pid, "unknown") for pid in hypothesis_citations
            },
            concept_hit_counts={
                pid: self._last_concept_counts[pid]
                for pid in hypothesis_citations if pid in self._last_concept_counts
            },
        )
        
        # Summary statistics
        total_citations = sum(len(citations) for citations in hypothesis_citations.values())
        hypotheses_with_citations = sum(1 for citations in hypothesis_citations.values() if citations)
        
        completion_msg = f"Parallel literature validation complete for {len(hypothesis_citations)} hypotheses"
        logger.info(completion_msg)
        
        if hypotheses_with_citations > 0:
            avg_citations = total_citations / hypotheses_with_citations
        
        return result
    
    
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
        
        # Construct targeted query with only contributing seed genes.
        # The strict query is the intersection (genes x pathway x disease). When
        # the pathway name carries no distinctive concept the clause comes back
        # empty and the constructor degrades to the broad query on its own,
        # which is the correct answer for a generic pathway.
        query = self._construct_hypothesis_query(
            pathway_name, contributing_seed_genes, disease_context, disease_synonyms
        )

        logger.debug(f"Hypothesis literature query for {hypothesis_id}: {query}")

        # Total corpus size for this intersection. Recorded before retrieval
        # because it is the basis of the literature-saturation metric and is not
        # bounded by the retrieval cap.
        hit_count = self.pubmed_client.count_hits(query)
        self._last_hit_counts[hypothesis_id] = hit_count
        self._last_query_tier[hypothesis_id] = (
            "strict" if " AND " in query and query.count(" AND ") >= 2 else "broad"
        )

        # A zero-record intersection is ambiguous. It can mean a genuine gap --
        # nobody has connected this pathway to these genes in this disease -- or
        # simply that the pathway name has no lexical footprint in PubMed (an
        # identifier-heavy Reactome label such as "TGFBR3 PTM regulation" will
        # never match an abstract). Treating both as maximally novel puts
        # unsearchable pathway names at the top of the ranking.
        #
        # Asking how much literature the pathway concept has on its own separates
        # the two: a concept with a substantial corpus but an empty intersection
        # is a real gap; a concept with no corpus means the query cannot measure
        # anything and the novelty must be marked unverified.
        if hit_count == 0:
            concept_clause = self._pathway_clause(pathway_name)
            concept_hits = (
                self.pubmed_client.count_hits(f"({concept_clause})")
                if concept_clause else 0
            )
            if concept_hits >= 0:
                self._last_concept_counts[hypothesis_id] = concept_hits
            logger.info(
                f"Hypothesis {hypothesis_id}: 0 records at the intersection; "
                f"pathway concept alone has {concept_hits} records"
            )

        # Search PubMed with hypothesis-specific query
        papers = self._search_pubmed(query)
        
        
        # Calculate relevance scores with hypothesis-specific context
        citations = self._create_hypothesis_citations(
            papers, pathway_name, contributing_seed_genes, hypothesis_id,
            disease_context=disease_context,
        )

        # Sort by relevance score
        citations.sort(key=lambda c: c.relevance_score, reverse=True)

        # --- Filter by relevance threshold ---
        # Keep only papers with meaningful relevance (>= 0.10).
        # This eliminates papers returned by PubMed that have no real connection
        # to the hypothesis, pathway, or disease context.
        RELEVANCE_THRESHOLD = 0.10
        filtered = [c for c in citations if c.relevance_score >= RELEVANCE_THRESHOLD]

        if filtered:
            logger.info(
                f"Hypothesis {hypothesis_id}: {len(filtered)}/{len(citations)} "
                f"citations above relevance threshold {RELEVANCE_THRESHOLD} "
                f"(top={filtered[0].relevance_score:.2f})"
            )
        else:
            logger.info(
                f"Hypothesis {hypothesis_id}: 0/{len(citations)} citations "
                f"above threshold — keeping top 5 as fallback"
            )
            # Fallback: keep at least top 5 so hypotheses aren't left empty
            filtered = citations[:5]

        return filtered
    
    def _construct_hypothesis_query(
        self,
        pathway_name: str,
        contributing_seed_genes: List[GeneInfo],
        disease_context: Optional[str] = None,
        disease_synonyms: Optional[List[str]] = None,
        specificity: str = "strict",
    ) -> str:
        """
        Construct a PubMed query for the *intersection* of
        (seed genes x pathway concept x disease context).

        The three clauses are combined with AND, not OR. An earlier version OR-ed
        the pathway terms into the same clause as a broad cardiac fallback, which
        made the pathway term inert: every pathway resolved to the same
        "(genes) AND (cardiac OR heart OR ...)" query and therefore returned the
        same ~30 papers. Novelty was consequently constant across pathways and
        carried no signal.

        specificity:
            "strict"  -> (genes) AND (pathway terms) AND (disease terms)
            "relaxed" -> (genes) AND (pathway terms)
            "broad"   -> (genes) AND (disease terms)   [pathway concept dropped]
        """
        gene_clause = self._gene_clause(contributing_seed_genes)
        pathway_clause = self._pathway_clause(pathway_name)
        disease_clause = self._disease_clause(disease_context, disease_synonyms)

        if specificity == "strict" and pathway_clause and disease_clause:
            return f"({gene_clause}) AND ({pathway_clause}) AND ({disease_clause})"
        if specificity in ("strict", "relaxed") and pathway_clause:
            return f"({gene_clause}) AND ({pathway_clause})"
        if disease_clause:
            return f"({gene_clause}) AND ({disease_clause})"
        return f"({gene_clause})"

    # Tokens that carry no discriminative meaning in a pathway name.
    _PATHWAY_STOPWORDS = {
        'pathway', 'pathways', 'signaling', 'signalling', 'signal', 'by', 'in', 'of',
        'via', 'the', 'a', 'an', 'and', 'or', 'with', 'for', 'from', 'to',
        'regulation', 'regulated', 'regulating', 'process', 'processes', 'response',
        'activity', 'activation', 'complex', 'system', 'disease', 'diseases',
        'type', 'class', 'positive', 'negative', 'cellular', 'cell', 'biological',
        'involved', 'related', 'other', 'general', 'multicellular', 'organism',
        'anatomical', 'structure', 'development', 'developmental', 'organization',
    }

    @staticmethod
    def _gene_clause(genes: List[GeneInfo]) -> str:
        symbols = [g.symbol for g in genes][:8]
        if not symbols:
            return "gene[Title/Abstract]"
        return " OR ".join(f'{sym}[Title/Abstract]' for sym in symbols)

    # Unigrams that are technically informative but match so much of the
    # cardiovascular corpus that OR-ing them dissolves the pathway clause.
    _GENERIC_UNIGRAMS = {
        'heart', 'cardiac', 'cardiovascular', 'muscle', 'rate', 'blood', 'vessel',
        'cell', 'cells', 'cellular', 'protein', 'proteins', 'gene', 'genes',
        'factor', 'factors', 'receptor', 'receptors', 'binding', 'transport',
        'membrane', 'nuclear', 'tissue', 'organ', 'body', 'human', 'animal',
        'molecule', 'molecular', 'transcription', 'translation', 'expression',
    }

    @classmethod
    def _pathway_clause(cls, pathway_name: str, level: int = 1) -> str:
        """Match the pathway concept in title/abstract.

        ``level`` controls precision/recall:
          0 -- quoted phrases only (the informative core of the name and its
               contiguous informative bigrams). Highest precision.
          1 -- phrases plus *distinctive* unigrams, i.e. informative tokens that
               are not in :attr:`_GENERIC_UNIGRAMS`. This is the default.

        Bare generic unigrams are never emitted at any level. OR-ing tokens such
        as "heart", "muscle" or "rate" re-admits the whole cardiovascular corpus
        and collapses the pathway clause back into the disease clause, which is
        exactly the defect this method exists to prevent.

        A pathway whose name is entirely generic ("multicellular organism
        development") yields an empty clause. The caller then falls back to the
        broad query, which correctly records such a pathway as saturated rather
        than novel.
        """
        import re as _re
        name = (pathway_name or "").strip()
        if not name:
            return ""
        raw_tokens = [
            t for t in _re.split(r'[\s\-_/,;:()\[\]]+', name)
            if t and _re.search(r'[A-Za-z]', t)
        ]
        informative = [
            t for t in raw_tokens
            if len(t) >= 3 and t.lower() not in cls._PATHWAY_STOPWORDS
        ]
        if not informative:
            return ""

        phrases: List[str] = []
        if len(informative) >= 2:
            phrases.append(" ".join(informative[:5]))
        for a, b in zip(raw_tokens, raw_tokens[1:]):
            if a.lower() in cls._PATHWAY_STOPWORDS or b.lower() in cls._PATHWAY_STOPWORDS:
                continue
            if len(a) >= 3 and len(b) >= 3:
                phrases.append(f"{a} {b}")

        if level >= 1:
            for t in informative:
                if t.lower() not in cls._GENERIC_UNIGRAMS and len(t) >= 5:
                    phrases.append(t)

        seen, uniq = set(), []
        for ph in phrases:
            key = ph.lower()
            if key not in seen:
                seen.add(key)
                uniq.append(ph)
        if not uniq:
            return ""
        return " OR ".join(
            (f'"{ph}"[Title/Abstract]' if " " in ph else f'{ph}[Title/Abstract]')
            for ph in uniq[:8]
        )

    def _disease_clause(
        self,
        disease_context: Optional[str],
        disease_synonyms: Optional[List[str]] = None,
    ) -> str:
        parts: List[str] = []
        if disease_context and disease_context in self.DISEASE_QUERY_TERMS:
            for term in self.DISEASE_QUERY_TERMS[disease_context]:
                parts.append(f'"{term}"[Title/Abstract]')
        for syn in (disease_synonyms or [])[:5]:
            parts.append(f'"{syn}"[Title/Abstract]')
        if not parts:
            # Generic cardiovascular context only when nothing specific was given.
            for kw in ("cardiovascular", "cardiac", "heart", "myocardial"):
                parts.append(f'{kw}[Title/Abstract]')
        return " OR ".join(parts)

    def _create_hypothesis_citations(
        self,
        papers: List[Dict],
        pathway_name: str,
        contributing_seed_genes: List[GeneInfo],
        hypothesis_id: str,
        disease_context: Optional[str] = None,
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
        
        
        for i, paper in enumerate(papers, 1):
            # Show progress for citation creation
            if i <= 3 or i % 10 == 0 or i == len(papers):
                title_preview = self._console_safe(paper.get("title", "No title"), limit=50)
            
            # Calculate hypothesis-specific relevance score
            relevance_score = self._calculate_hypothesis_relevance(
                paper,
                pathway_name,
                contributing_seed_genes,
                hypothesis_id,
                disease_context=disease_context,
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
        
        return citations
    
    def _calculate_hypothesis_relevance(
        self,
        paper: Dict,
        pathway_name: str,
        contributing_seed_genes: List[GeneInfo],
        hypothesis_id: str,
        disease_context: Optional[str] = None,
    ) -> float:
        """
        Calculate enhanced relevance score for a hypothesis, its contributing
        genes, and the selected disease context.

        Scoring weights (sum to 1.0):
            1. Pathway name mention        0.20
            2. Contributing seed genes      0.30
            3. Cardiac keyword matches      0.15
            4. Disease-context match        0.15
            5. Recency bonus                0.10
            6. Citation impact              0.10
        """
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        score = 0.0

        # 1. Pathway name mention (weight: 0.20)
        pathway_terms = pathway_name.lower().split()
        pathway_matches = sum(1 for term in pathway_terms if len(term) > 3 and term in text)
        if pathway_matches > 0:
            score += 0.20 * min(pathway_matches / max(len(pathway_terms), 1), 1.0)

        # 2. Contributing seed gene mentions (weight: 0.30)
        contributing_gene_mentions = sum(
            1 for gene in contributing_seed_genes
            if gene.symbol.lower() in text
        )
        if contributing_gene_mentions > 0 and len(contributing_seed_genes) > 0:
            gene_coverage = contributing_gene_mentions / len(contributing_seed_genes)
            score += 0.30 * gene_coverage
            # Bonus for mentioning multiple contributing genes
            if contributing_gene_mentions > 1:
                score += 0.05 * min((contributing_gene_mentions - 1) / 3, 1.0)

        # 3. Cardiac keyword matches (weight: 0.15)
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
            score += 0.15 * min(keyword_score, 1.0)

        # 4. Disease-context match (weight: 0.15)
        if disease_context and disease_context in self.DISEASE_QUERY_TERMS:
            disease_terms = self.DISEASE_QUERY_TERMS[disease_context]
            disease_hits = sum(1 for dt in disease_terms if dt.lower() in text)
            if disease_hits > 0:
                score += 0.15 * min(disease_hits / max(len(disease_terms), 1), 1.0)

        # 5. Recency bonus (weight: 0.10)
        year = paper.get('year', 0)
        if year >= 2020:
            score += 0.10
        elif year >= 2015:
            score += 0.05

        # 6. Citation impact (weight: 0.10)
        citation_count = paper.get('citation_count', 0)
        if citation_count > 0:
            citation_score = min(citation_count / 20.0, 1.0)
            score += 0.10 * citation_score

        return min(score, 1.0)
    
    
    def _search_pubmed(self, query: str, max_results: int = 30) -> List[Dict]:
        """
        Search PubMed with constructed query.

        Args:
            query: PubMed query string
            max_results: Maximum papers to retrieve (default 30)

        Returns:
            List of paper dictionaries
        """
        try:
            papers = self.pubmed_client._search_pubmed(query, max_results=max_results)
            
            if papers:
                pass
                # Fetch paper details
                paper_details = self.pubmed_client._fetch_papers(papers)
                return paper_details
            else:
                pass
                return []
            
        except Exception as e:
            error_msg = f"PubMed search failed: {str(e)}"
            logger.warning(error_msg)
            return []
    
    
