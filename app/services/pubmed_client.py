import logging
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
            print(f"[PUBMED HTTP FALLBACK] Searching for: {query[:100]}...", flush=True)
            
            params = {
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'retmode': 'xml',
                'usehistory': 'n'
            }
            
            response = requests.get(self.esearch_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            pmids = []
            
            for id_elem in root.findall('.//Id'):
                if id_elem.text:
                    pmids.append(id_elem.text.strip())
            
            print(f"[PUBMED HTTP FALLBACK] Found {len(pmids)} PMIDs", flush=True)
            return pmids
            
        except Exception as e:
            print(f"[PUBMED HTTP FALLBACK ERROR] Failed: {str(e)}", flush=True)
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
            print(f"[PUBMED HTTP FALLBACK] Fetching {len(pmids)} papers", flush=True)
            
            params = {
                'db': 'pubmed',
                'id': ','.join(pmids),
                'retmode': 'xml',
                'rettype': 'abstract'
            }
            
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
                    print(f"[PUBMED WARNING] Failed to parse article: {str(e)}", flush=True)
                    continue
            
            print(f"[PUBMED HTTP FALLBACK] Parsed {len(papers)} papers", flush=True)
            return papers
            
        except Exception as e:
            print(f"[PUBMED HTTP FALLBACK ERROR] Fetch failed: {str(e)}", flush=True)
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
            print(f"[PUBMED WARNING] Error parsing XML article: {str(e)}", flush=True)
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
        
        # Search PubMed
        pmids = self._search_pubmed(query, max_results)
        
        if not pmids:
            logger.info(f"No results found for gene '{gene_symbol}'")
            return []
        
        logger.info(f"Found {len(pmids)} papers for gene '{gene_symbol}'")
        
        # Fetch paper details
        papers = self._fetch_papers(pmids)
        
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
            print(f"[PUBMED WARNING] Bio.Entrez HTTP error {e.code}: {e.reason}", flush=True)
            if e.code == 502:
                print("[PUBMED DEBUG] 502 error detected, trying HTTP fallback...", flush=True)
                return self._search_pubmed_with_http_fallback(query, max_results)
            raise
        except (URLError, socket.error) as e:
            print(f"[PUBMED WARNING] Bio.Entrez connectivity error: {str(e)}", flush=True)
            print("[PUBMED DEBUG] Trying HTTP fallback...", flush=True)
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
                    time.sleep(0.34)  # ~3 requests per second
                    
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
            
            # Extract title
            title = article.get("ArticleTitle", "")
            
            # Extract abstract
            abstract_parts = article.get("Abstract", {}).get("AbstractText", [])
            if isinstance(abstract_parts, list):
                abstract = " ".join([str(part) for part in abstract_parts])
            else:
                abstract = str(abstract_parts)
            
            # Extract authors
            author_list = article.get("AuthorList", [])
            authors = []
            for author in author_list:
                last_name = author.get("LastName", "")
                initials = author.get("Initials", "")
                if last_name:
                    authors.append(f"{last_name} {initials}".strip())
            
            authors_str = ", ".join(authors) if authors else ""
            
            # Extract publication year
            pub_date = article.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
            year = pub_date.get("Year")
            if not year:
                # Try MedlineDate
                medline_date = pub_date.get("MedlineDate", "")
                if medline_date:
                    year = medline_date.split()[0] if medline_date.split() else None
            
            year = int(year) if year and year.isdigit() else None
            
            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": authors_str,
                "year": year
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse paper record: {str(e)}")
            return None
    
    def fetch_by_pmids(
        self,
        pmids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Fetch papers by PMIDs directly.
        
        Args:
            pmids: List of PMIDs
            
        Returns:
            List of paper dictionaries
        """
        logger.info(f"Fetching {len(pmids)} papers by PMID")
        
        return self._fetch_papers(pmids)
    
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
        
        # Search and fetch
        pmids = self._search_pubmed(query, max_results)
        
        if not pmids:
            logger.info(f"No results found for pathway '{pathway_name}'")
            return []
        
        papers = self._fetch_papers(pmids)
        
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
            handle = Entrez.efetch(
                db="pubmed",
                id=batch_pmids,
                rettype="medline",
                retmode="xml"
            )
            
            records = Entrez.read(handle)
            handle.close()
            
            # Parse records safely
            papers = []
            try:
                # Cast to dict-like for type checker
                records_dict = cast(Dict[str, Any], records)
                pubmed_articles = list(records_dict.get("PubmedArticle", []))
            except (AttributeError, TypeError, KeyError):
                pubmed_articles = []
                
            for record in pubmed_articles:
                paper = self._parse_paper(record)
                if paper:
                    papers.append(paper)
                    
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
    
    async def search_pubmed_async(
        self,
        query: str,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Async version of enhanced PubMed search with HTTP fallback.
        
        Args:
            query: PubMed search query string
            max_results: Maximum number of results
            
        Returns:
            List of paper dictionaries
        """
        if not AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not available, falling back to sync search")
            return self.search_pubmed(query, max_results)
        
        max_results = max_results or self.max_results
        
        logger.debug(f"Async PubMed search: {query}")
        
        # Check cache first
        cache_key = f"{query}:{max_results}"
        if cache_key in self._search_cache:
            logger.debug(f"Using cached PubMed search results for: {query}")
            return self._search_cache[cache_key]
        
        # Search PubMed asynchronously
        pmids = await self._search_pubmed_async(query, max_results)
        
        if not pmids:
            return []
        
        # Check fetch cache
        fetch_key = ",".join(sorted(pmids))
        if fetch_key in self._fetch_cache:
            logger.debug(f"Using cached PubMed fetch results for {len(pmids)} PMIDs")
            papers = self._fetch_cache[fetch_key]
        else:
            # Fetch paper details asynchronously
            papers = await self._fetch_papers_async(pmids)
            # Cache the results
            self._fetch_cache[fetch_key] = papers
        
        # Cache the final results
        self._search_cache[cache_key] = papers
        
        return papers
    
    async def _search_pubmed_async(
        self,
        query: str,
        max_results: int
    ) -> List[str]:
        """
        Async search PubMed and return PMIDs.
        
        Args:
            query: PubMed query string
            max_results: Maximum number of results
            
        Returns:
            List of PMIDs
        """
        if not AIOHTTP_AVAILABLE:
            # Fallback to sync search
            return self._search_pubmed_sync(query, max_results)
        
        try:
            # Use HTTP fallback for async search
            timeout = ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                params = {
                    'db': 'pubmed',
                    'term': query,
                    'retmax': max_results,
                    'retmode': 'xml',
                    'usehistory': 'n'
                }
                
                async with session.get(self.esearch_url, params=params) as response:
                    response.raise_for_status()
                    content = await response.text()
                    
                    # Parse XML response
                    root = ET.fromstring(content)
                    pmids = []
                    
                    for id_elem in root.findall('.//Id'):
                        if id_elem.text:
                            pmids.append(id_elem.text.strip())
                    
                    logger.debug(f"Async PubMed search returned {len(pmids)} PMIDs")
                    return pmids
                    
        except Exception as e:
            logger.warning(f"Async PubMed search failed, falling back to sync: {str(e)}")
            # Fallback to sync version
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._search_pubmed, query, max_results)
    
    async def _fetch_papers_async(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Async fetch paper details from PMIDs.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of paper dictionaries
        """
        if not AIOHTTP_AVAILABLE:
            # Fallback to sync fetch
            return self._fetch_papers_sync(pmids)
        
        if not pmids:
            return []
        
        try:
            # Use HTTP fallback for async fetch
            timeout = ClientTimeout(total=60)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                params = {
                    'db': 'pubmed',
                    'id': ','.join(pmids),
                    'retmode': 'xml',
                    'rettype': 'abstract'
                }
                
                async with session.get(self.efetch_url, params=params) as response:
                    response.raise_for_status()
                    content = await response.text()
                    
                    # Parse XML response
                    root = ET.fromstring(content)
                    papers = []
                    
                    for article in root.findall('.//PubmedArticle'):
                        try:
                            paper = self._parse_xml_article(article)
                            if paper:
                                papers.append(paper)
                        except Exception as e:
                            logger.warning(f"Failed to parse article in async fetch: {str(e)}")
                            continue
                    
                    logger.debug(f"Async PubMed fetch returned {len(papers)} papers")
                    return papers
                    
        except Exception as e:
            logger.warning(f"Async PubMed fetch failed, falling back to sync: {str(e)}")
            # Fallback to sync version
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._fetch_papers, pmids)
    
    def _search_pubmed_sync(self, query: str, max_results: int) -> List[str]:
        """
        Synchronous fallback for PubMed search.
        
        Args:
            query: PubMed query string
            max_results: Maximum number of results
            
        Returns:
            List of PMIDs
        """
        try:
            # Use the existing sync search method
            handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, usehistory="n")
            record = Entrez.read(handle)
            handle.close()
            try:
                return getattr(record, "IdList", [])
            except AttributeError:
                return []
        except Exception as e:
            logger.error(f"Sync PubMed search failed: {str(e)}")
            return []
    
    def _fetch_papers_sync(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Synchronous fallback for paper fetching.
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            List of paper dictionaries
        """
        try:
            # Use the existing sync fetch method
            return self._fetch_papers(pmids)
        except Exception as e:
            logger.error(f"Sync paper fetch failed: {str(e)}")
            return []
