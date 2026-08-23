import logging
import os
import threading
import time
from typing import List, Dict, Any, Optional, cast
from Bio import Entrez
from urllib.error import HTTPError, URLError
import socket
import requests
import xml.etree.ElementTree as ET
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    import aiohttp
    from aiohttp import ClientTimeout
    import asyncio
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    ClientTimeout = None
    asyncio = None
    AIOHTTP_AVAILABLE = False

from app.models import CardiacContext
from app.core.config import get_settings

logger = logging.getLogger(__name__)

if not AIOHTTP_AVAILABLE:
    logger.warning("aiohttp not available - async functionality will be disabled")


class PubMedClient:
    """Enhanced PubMed client with HTTP fallback for API failures."""
    
    def __init__(self, email: Optional[str] = None):
        """
        Initialize PubMed client.
        
        Args:
            email: Email for NCBI Entrez (required by NCBI)
        """
        self.settings = get_settings()
        
        # Set Entrez email (required by NCBI)
        Entrez.email = email or f"{self.settings.app_name}@example.com"
        Entrez.tool = self.settings.app_name
        
        self.max_results = self.settings.nets.pubmed_max_results
        
        # HTTP API endpoints for fallback
        self.esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        
        # Simple in-memory cache for API responses
        self._search_cache = {}
        self._fetch_cache = {}
        
        logger.info(f"PubMedClient initialized (email: {Entrez.email}, max_results: {self.max_results})")

    # ---- NCBI E-utilities rate limiting -------------------------------------
    # NCBI permits 3 requests/second without an API key and 10/second with one.
    # The limiter is process-wide because several PubMedClient instances and the
    # async mining path share the same NCBI quota.
    _rate_lock = threading.Lock()
    _last_request_ts = 0.0

    @classmethod
    def _throttle(cls) -> None:
        """Block until the next E-utilities request is allowed."""
        # NCBI allows 3 req/s without a key and 10 with one. The unkeyed
        # interval sits deliberately below the 0.334 s that 3/s implies:
        # E-utilities measures bursts, and pacing exactly at the limit returned
        # HTTP 429 often enough to corrupt the literature-saturation metric,
        # which silently degrades to "no records found".
        min_interval = 0.12 if os.environ.get("NCBI_API_KEY") else 0.40
        with cls._rate_lock:
            now = time.monotonic()
            wait = cls._last_request_ts + min_interval - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            cls._last_request_ts = now

    def count_hits(
        self,
        query: str,
        mindate: Optional[str] = None,
        maxdate: Optional[str] = None,
    ) -> int:
        """Return the total number of PubMed records matching ``query``.

        This is the ``<Count>`` field of an esearch response and is *not*
        capped by ``retmax``. Literature saturation must be derived from this
        number rather than from the number of records actually downloaded,
        otherwise saturation is bounded by the retrieval limit and becomes
        constant across pathways.

        Args:
            query: PubMed query string.
            mindate: Inclusive lower publication-date bound, e.g. "2021".
            maxdate: Inclusive upper publication-date bound, e.g. "2020".

        Returns -1 when the count could not be determined, so callers can
        distinguish "no papers" (0) from "lookup failed".
        """
        cache_key = ("count", query, mindate, maxdate)
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        params_base = {
            "db": "pubmed",
            "term": query,
            "rettype": "count",
            "retmode": "json",
            "tool": self.settings.app_name,
            "email": Entrez.email,
        }
        # Publication-date bounds, used by the temporal-holdout benchmark to ask
        # what the literature looked like as of a cutoff year.
        if mindate or maxdate:
            params_base["datetype"] = "pdat"
            params_base["mindate"] = mindate or "1800"
            params_base["maxdate"] = maxdate or "3000"
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            params_base["api_key"] = api_key

        # Retry on throttling. A dropped count is not a neutral failure: it makes
        # the pathway look unstudied, which is the strongest novelty signal the
        # scorer has, so a 429 would promote exactly the wrong pathways.
        count = -1
        for attempt in range(4):
            try:
                self._throttle()
                response = requests.get(self.esearch_url, params=params_base, timeout=30)
                if response.status_code == 429:
                    raise requests.HTTPError("429 Too Many Requests")
                response.raise_for_status()
                count = int(response.json()["esearchresult"]["count"])
                break
            except Exception as e:
                if attempt == 3:
                    logger.warning(
                        f"PubMed count lookup failed after {attempt + 1} attempts: {str(e)}"
                    )
                    return -1
                backoff = 1.5 * (2 ** attempt)
                logger.debug(f"PubMed count retry {attempt + 1} in {backoff:.1f}s: {str(e)}")
                time.sleep(backoff)

        self._search_cache[cache_key] = count
        return count
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((HTTPError, requests.RequestException, Exception))
    )
    def _search_pubmed_with_http_fallback(self, query: str, max_results: int) -> List[str]:
        """
        HTTP fallback search when Bio.Entrez fails with 502 or other errors.
        
        Args:
            query: PubMed search query
            max_results: Maximum results to return
            
        Returns:
            List of PMIDs as strings
        """
        try:
            
            params = {
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'retmode': 'xml',
                'usehistory': 'n'
            }
            
            self._throttle()
            response = requests.get(self.esearch_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            pmids = []
            
            for id_elem in root.findall('.//Id'):
                if id_elem.text:
                    pmids.append(id_elem.text.strip())
            
            return pmids
            
        except Exception as e:
            return []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((HTTPError, requests.RequestException))
    )
    def _fetch_papers_with_http_fallback(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        HTTP fallback fetch when Bio.Entrez fails.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of paper dictionaries
        """
        if not pmids:
            return []
            
        try:
            
            params = {
                'db': 'pubmed',
                'id': ','.join(pmids),
                'retmode': 'xml',
                'rettype': 'abstract'
            }
            
            self._throttle()
            response = requests.get(self.efetch_url, params=params, timeout=60)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            papers = []
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    paper = self._parse_xml_article(article)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    continue
            
            return papers
            
        except Exception as e:
            return []
    
    def _parse_xml_article(self, article_elem) -> Optional[Dict[str, Any]]:
        """
        Parse XML article element into paper dictionary.
        
        Args:
            article_elem: XML element containing article data
            
        Returns:
            Paper dictionary or None if parsing fails
        """
        try:
            # Extract PMID
            pmid_elem = article_elem.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else None
            
            # Extract title
            title_elem = article_elem.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "No title available"
            
            # Extract abstract
            abstract_elem = article_elem.find('.//AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None else "No abstract available"
            
            # Extract publication year
            year_elem = article_elem.find('.//PubDate/Year')
            year = int(year_elem.text) if year_elem is not None and year_elem.text else None
            
            # Extract journal
            journal_elem = article_elem.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else "Unknown journal"
            
            # Extract authors
            authors = []
            for author_elem in article_elem.findall('.//Author'):
                last_name_elem = author_elem.find('LastName')
                first_name_elem = author_elem.find('ForeName')
                
                if last_name_elem is not None:
                    last_name = last_name_elem.text or ""
                    first_name = first_name_elem.text if first_name_elem is not None else ""
                    authors.append(f"{first_name} {last_name}".strip())
            
            return {
                'pmid': pmid,
                'title': title,
                'abstract': abstract,
                'year': year,
                'journal': journal,
                'authors': authors,
                'relevance_score': 0.5  # Default relevance
            }
            
        except Exception as e:
            return None
    
    def search(
        self,
        query: str,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Enhanced PubMed search with HTTP fallback for API failures.
        
        Args:
            query: PubMed search query string
            max_results: Maximum number of results
            
        Returns:
            List of paper dictionaries
        """
        max_results = max_results or self.max_results
        
        logger.debug(f"Generic PubMed search: {query}")
        
        # Check cache first
        cache_key = f"{query}:{max_results}"
        if cache_key in self._search_cache:
            logger.debug(f"Using cached PubMed search results for: {query}")
            return self._search_cache[cache_key]
        
        # Search PubMed
        pmids = self._search_pubmed(query, max_results)
        
        if not pmids:
            return []
        
        # Check fetch cache
        fetch_key = ",".join(sorted(pmids))
        if fetch_key in self._fetch_cache:
            logger.debug(f"Using cached PubMed fetch results for {len(pmids)} PMIDs")
            papers = self._fetch_cache[fetch_key]
        else:
            # Fetch paper details
            papers = self._fetch_papers(pmids)
            # Cache the results
            self._fetch_cache[fetch_key] = papers
        
        # Cache the final results
        self._search_cache[cache_key] = papers
        
        return papers
    
    def search_gene_literature(
        self,
        gene_symbol: str,
        cardiac_context: CardiacContext,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search PubMed for literature about a gene in cardiac context.
        
        Args:
            gene_symbol: Gene symbol to search
            cardiac_context: Cardiac context with keywords
            max_results: Maximum number of results (default from config)
            
        Returns:
            List of paper dictionaries with PMIDs, titles, and abstracts
        """
        max_results = max_results or self.max_results
        
        logger.info(
            f"Searching PubMed for gene '{gene_symbol}' in cardiac context "
            f"(max_results={max_results})"
        )
        
        # Build search query
        query = self._build_query(gene_symbol, cardiac_context)
        
        logger.debug(f"PubMed query: {query}")
        
        papers = self.search(query, max_results)

        if not papers:
            logger.info(f"No results found for gene '{gene_symbol}'")
            return []
        
        logger.info(f"Found {len(papers)} papers for gene '{gene_symbol}'")
        
        return papers
    
    def _build_query(
        self,
        gene_symbol: str,
        cardiac_context: CardiacContext
    ) -> str:
        """
        Build PubMed search query with gene and cardiac keywords.
        
        Args:
            gene_symbol: Gene symbol
            cardiac_context: Cardiac context
            
        Returns:
            PubMed query string
        """
        # Start with gene symbol
        gene_query = f'"{gene_symbol}"[Title/Abstract]'
        
        # Add cardiac keywords with OR logic
        cardiac_keywords = cardiac_context.keywords
        
        if cardiac_keywords:
            # Group keywords with OR
            keyword_parts = [f'"{kw}"[Title/Abstract]' for kw in cardiac_keywords]
            keyword_query = " OR ".join(keyword_parts)
            
            # Combine gene and keywords with AND
            query = f"({gene_query}) AND ({keyword_query})"
        else:
            query = gene_query
        
        # Add species filter
        if cardiac_context.species:
            query += f' AND "{cardiac_context.species}"[Organism]'
        
        return query
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((HTTPError, URLError, socket.error, ConnectionError))
    )
    def _search_pubmed(
        self,
        query: str,
        max_results: int
    ) -> List[str]:
        """
        Search PubMed and return PMIDs with robust error handling.
        
        Args:
            query: PubMed query string
            max_results: Maximum number of results
            
        Returns:
            List of PMIDs
        """
        try:
            # Search PubMed with timeout handling
            self._throttle()
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="relevance"
            )
            
            record = Entrez.read(handle)
            handle.close()
            
            # Safely extract PMIDs from Entrez record
            try:
                # Cast to dict-like for type checker
                record_dict = cast(Dict[str, Any], record)
                pmids = list(record_dict.get("IdList", []))
            except (AttributeError, TypeError, KeyError):
                pmids = []
            
            logger.debug(f"PubMed search returned {len(pmids)} PMIDs")
            
            return pmids
            
        except HTTPError as e:
            if e.code == 502:
                return self._search_pubmed_with_http_fallback(query, max_results)
            raise
        except (URLError, socket.error) as e:
            return self._search_pubmed_with_http_fallback(query, max_results)
        except Exception as e:
            error_str = str(e).lower()
            connectivity_errors = [
                'connection', 'timeout', 'remote end closed',
                'connection reset', 'connection broken', 'ssl error'
            ]
            
            if any(err in error_str for err in connectivity_errors):
                logger.warning(f"PubMed connection error (will retry): {str(e)}")
                raise ConnectionError(f"PubMed connection failed: {str(e)}")
            else:
                logger.error(f"PubMed search failed: {str(e)}")
                return []
    
    def _fetch_papers(
        self,
        pmids: List[str],
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch paper details from PubMed.
        
        Args:
            pmids: List of PMIDs
            batch_size: Number of papers to fetch per request
            
        Returns:
            List of paper dictionaries
        """
        papers = []
        
        # Fetch in batches to avoid overwhelming the API
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            
            try:
                # Fetch paper details with robust error handling
                batch_papers = self._fetch_papers_batch_with_retry(batch_pmids)
                papers.extend(batch_papers)
                
                # Be nice to NCBI - rate limit
                if i + batch_size < len(pmids):
                    pass  # pacing handled by the shared _throttle() limiter
                    
            except Exception as e:
                logger.error(f"Failed to fetch batch {i}-{i+batch_size}: {str(e)}")
                # Continue with next batch instead of failing completely
                continue
        
        logger.info(f"Fetched details for {len(papers)} papers")
        
        return papers
    
    def _parse_paper(self, record: Any) -> Optional[Dict[str, Any]]:
        """
        Parse PubMed record into paper dictionary.
        
        Args:
            record: PubMed record (Bio.Entrez record object)
            
        Returns:
            Paper dictionary or None if parsing fails
        """
        try:
            # Cast to dict-like for type checker
            record_dict = cast(Dict[str, Any], record)
            medline_citation = cast(Dict[str, Any], record_dict.get("MedlineCitation", {}))
            article = cast(Dict[str, Any], medline_citation.get("Article", {}))
            
            # Extract PMID
            pmid = str(medline_citation.get("PMID", ""))
            
            # Extract title — Biopython may return StringElement, dict, or plain str
            title_raw = article.get("ArticleTitle", "")
            if isinstance(title_raw, str):
                title = title_raw
            elif isinstance(title_raw, dict):
                # Structured title (e.g. with markup) — join all text values
                title = " ".join(str(v) for v in title_raw.values() if v)
            else:
                title = str(title_raw) if title_raw else ""

            # Extract abstract
            abstract_parts = article.get("Abstract", {}).get("AbstractText", [])
            if isinstance(abstract_parts, list):
                abstract = " ".join([str(part) for part in abstract_parts])
            elif abstract_parts:
                abstract = str(abstract_parts)
            else:
                abstract = ""
            
            # Extract authors
            author_list = article.get("AuthorList", [])
            authors = []
            for author in author_list:
                last_name = author.get("LastName", "")
                initials = author.get("Initials", "")
                if last_name:
                    authors.append(f"{last_name} {initials}".strip())
            
            authors_str = ", ".join(authors) if authors else ""
            
            # Extract publication year and journal
            journal_info = article.get("Journal", {})
            pub_date = journal_info.get("JournalIssue", {}).get("PubDate", {})
            year = pub_date.get("Year")
            if not year:
                # Try MedlineDate
                medline_date = pub_date.get("MedlineDate", "")
                if medline_date:
                    year = medline_date.split()[0] if medline_date.split() else None

            year = int(year) if year and year.isdigit() else None

            journal = journal_info.get("Title", "") or journal_info.get("ISOAbbreviation", "") or ""

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors_str,
                "year": year,
                "journal": journal,
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse paper record: {str(e)}")
            return None
    
    
    def search_pathway_literature(
        self,
        pathway_name: str,
        cardiac_context: CardiacContext,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search PubMed for literature about a pathway in cardiac context.
        
        Args:
            pathway_name: Pathway name to search
            cardiac_context: Cardiac context with keywords
            max_results: Maximum number of results
            
        Returns:
            List of paper dictionaries
        """
        max_results = max_results or self.max_results
        
        logger.info(
            f"Searching PubMed for pathway '{pathway_name}' in cardiac context"
        )
        
        # Build query with pathway name
        pathway_query = f'"{pathway_name}"[Title/Abstract]'
        
        # Add cardiac keywords
        cardiac_keywords = cardiac_context.keywords
        if cardiac_keywords:
            keyword_parts = [f'"{kw}"[Title/Abstract]' for kw in cardiac_keywords]
            keyword_query = " OR ".join(keyword_parts)
            query = f"({pathway_query}) AND ({keyword_query})"
        else:
            query = pathway_query
        
        # Add species filter
        if cardiac_context.species:
            query += f' AND "{cardiac_context.species}"[Organism]'
        
        logger.debug(f"PubMed query: {query}")
        
        papers = self.search(query, max_results)

        if not papers:
            logger.info(f"No results found for pathway '{pathway_name}'")
            return []
        
        logger.info(f"Found {len(papers)} papers for pathway '{pathway_name}'")
        
        return papers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((HTTPError, URLError, socket.error, ConnectionError))
    )
    def _fetch_papers_batch_with_retry(self, batch_pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch a batch of papers with robust error handling and retry logic.
        
        Args:
            batch_pmids: List of PMIDs to fetch
            
        Returns:
            List of paper dictionaries
        """
        try:
            # Fetch paper details
            self._throttle()
            handle = Entrez.efetch(
                db="pubmed",
                id=",".join(batch_pmids),
                rettype="abstract",
                retmode="xml",
                retmax=len(batch_pmids)
            )

            records = Entrez.read(handle)
            handle.close()

            # Parse records safely
            papers = []
            try:
                records_dict = cast(Dict[str, Any], records)
                pubmed_articles = list(records_dict.get("PubmedArticle", []))
            except (AttributeError, TypeError, KeyError):
                pubmed_articles = []

            for record in pubmed_articles:
                paper = self._parse_paper(record)
                if paper:
                    papers.append(paper)

            # If biopython parse produced nothing, fall back to HTTP XML parser
            if not papers and batch_pmids:
                logger.warning(f"Biopython parse returned 0 papers for {len(batch_pmids)} PMIDs — falling back to HTTP fetch")
                papers = self._fetch_papers_with_http_fallback(batch_pmids)

            return papers
            
        except (HTTPError, URLError, socket.error) as e:
            logger.warning(f"PubMed batch fetch connectivity issue (will retry): {str(e)}")
            raise
        except Exception as e:
            error_str = str(e).lower()
            connectivity_errors = [
                'connection', 'timeout', 'remote end closed',
                'connection reset', 'connection broken', 'ssl error'
            ]
            
            if any(err in error_str for err in connectivity_errors):
                logger.warning(f"PubMed batch fetch connection error (will retry): {str(e)}")
                raise ConnectionError(f"PubMed batch fetch failed: {str(e)}")
            else:
                logger.error(f"PubMed batch fetch failed: {str(e)}")
                return []
    
    
    
    
    
