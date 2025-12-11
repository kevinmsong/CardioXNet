"""Consolidated base API client with shared functionality."""

import logging
import asyncio
import time
from typing import Optional, Dict, Any, List, Union
from abc import ABC, abstractmethod
import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BaseAPIError(Exception):
    """Base exception for API errors."""
    pass


class TimeoutError(BaseAPIError):
    """Raised when API request times out."""
    pass


class RateLimitError(BaseAPIError):
    """Raised when API rate limit is exceeded."""
    pass


class BaseAPIClient(ABC):
    """
    Consolidated base API client with shared functionality.
    
    This provides common patterns for:
    - HTTP session management
    - Retry logic with exponential backoff
    - Rate limiting
    - Error handling
    - Caching
    - Async support
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        name: str = "BaseAPIClient",
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_delay: float = 1.0
    ):
        """
        Initialize base API client.
        
        Args:
            base_url: Base URL for the API (optional for library-based clients)
            name: Client name for logging
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            rate_limit_delay: Delay between requests for rate limiting
        """
        self.base_url = base_url.rstrip('/') if base_url else None
        self.name = name
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_delay = rate_limit_delay
        
        self.settings = get_settings()
        self._session = None
        self._last_request_time = 0
        
        logger.debug(f"Initialized {self.name} API client")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize the client (create sessions, etc.)."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        logger.debug(f"{self.name} client initialized")
    
    async def cleanup(self):
        """Clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.debug(f"{self.name} client cleaned up")
    
    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make HTTP request with retry logic and rate limiting.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object
            
        Raises:
            TimeoutError: On timeout
            RateLimitError: On rate limit
            BaseAPIError: On other errors
        """
        if not self._session:
            await self.initialize()
        
        # Rate limiting
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
            before_sleep=before_sleep_log(logger, logging.WARNING)
        )
        async def _do_request():
            try:
                self._last_request_time = time.time()
                async with self._session.request(method, url, **kwargs) as response:
                    response.raise_for_status()
                    return response
            except asyncio.TimeoutError:
                raise TimeoutError(f"{self.name} request timeout: {url}")
            except aiohttp.ClientResponseError as e:
                if e.status == 429:
                    raise RateLimitError(f"{self.name} rate limit exceeded: {url}")
                raise BaseAPIError(f"{self.name} HTTP {e.status}: {e.message}")
            except aiohttp.ClientError as e:
                raise BaseAPIError(f"{self.name} request failed: {str(e)}")
        
        return await _do_request()
    
    async def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Make GET request.
        
        Args:
            endpoint: API endpoint (appended to base_url if set)
            params: Query parameters
            **kwargs: Additional request options
            
        Returns:
            JSON response data
        """
        url = f"{self.base_url}/{endpoint}" if self.base_url else endpoint
        
        async with self._make_request("GET", url, params=params, **kwargs) as response:
            return await response.json()
    
    async def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Make POST request.
        
        Args:
            endpoint: API endpoint
            data: Request data
            **kwargs: Additional request options
            
        Returns:
            JSON response data
        """
        url = f"{self.base_url}/{endpoint}" if self.base_url else endpoint
        
        async with self._make_request("POST", url, json=data, **kwargs) as response:
            return await response.json()
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the API/service is available.
        
        Returns:
            True if healthy
        """
        pass


class LibraryBasedClient(BaseAPIClient):
    """
    Base client for library-based APIs (not HTTP).
    
    Examples: STRING, BioPython, etc.
    """
    
    def __init__(self, name: str = "LibraryClient", **kwargs):
        super().__init__(base_url=None, name=name, **kwargs)
    
    async def initialize(self):
        """No session needed for library clients."""
        pass
    
    async def cleanup(self):
        """No cleanup needed for library clients."""
        pass
    
    async def health_check(self) -> bool:
        """Check if required libraries are available."""
        try:
            # Basic import check - subclasses should override for specific checks
            return True
        except Exception:
            return False


class CachedAPIClient(BaseAPIClient):
    """
    API client with built-in caching support.
    """
    
    def __init__(self, cache_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.cache_manager = cache_manager or get_settings().cache_manager
    
    async def get_cached(self, key: str, ttl: int = 3600) -> Optional[Any]:
        """
        Get cached value.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            Cached value or None
        """
        if self.cache_manager:
            return await self.cache_manager.get(key, ttl)
        return None
    
    async def set_cached(self, key: str, value: Any, ttl: int = 3600):
        """
        Set cached value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        if self.cache_manager:
            await self.cache_manager.set(key, value, ttl)
