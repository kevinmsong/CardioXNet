"""Base API client with retry logic and error handling."""

import logging
from typing import Optional, Dict, Any
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """Base exception for API client errors."""
    pass


class APITimeoutError(APIClientError):
    """Raised when API request times out."""
    pass


class APIRateLimitError(APIClientError):
    """Raised when API rate limit is exceeded."""
    pass


class APIClient:
    """Base API client with retry logic and error handling."""
    
    def __init__(self, base_url: str, name: str = "APIClient"):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL for the API
            name: Client name for logging
        """
        self.base_url = base_url.rstrip('/')
        self.name = name
        self.settings = get_settings()
        
        # Create session with default headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"{self.settings.app_name}/1.0",
            "Accept": "application/json"
        })
        
        logger.info(f"Initialized {self.name} client with base URL: {self.base_url}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
        retry=retry_if_exception_type((
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            APIRateLimitError
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            data: Form data
            json: JSON data
            timeout: Request timeout in seconds
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            APIClientError: On API errors
            APITimeoutError: On timeout
            APIRateLimitError: On rate limit
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        timeout = timeout or self.settings.nets.request_timeout
        
        logger.debug(
            f"{self.name} {method} {url} "
            f"(params={params}, timeout={timeout})"
        )
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                timeout=timeout,
                **kwargs
            )
            
            # Log response
            logger.debug(
                f"{self.name} response: {response.status_code} "
                f"({len(response.content)} bytes)"
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning(f"{self.name} rate limit exceeded")
                raise APIRateLimitError(f"Rate limit exceeded for {self.name}")
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            return response
            
        except requests.exceptions.Timeout as e:
            logger.error(f"{self.name} request timeout: {str(e)}")
            raise APITimeoutError(f"Request timeout for {self.name}: {str(e)}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"{self.name} request failed: {str(e)}")
            raise APIClientError(f"Request failed for {self.name}: {str(e)}")
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make GET request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            **kwargs: Additional arguments
            
        Returns:
            Response object
        """
        return self._request("GET", endpoint, params=params, **kwargs)
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make POST request.
        
        Args:
            endpoint: API endpoint
            data: Form data
            json: JSON data
            **kwargs: Additional arguments
            
        Returns:
            Response object
        """
        return self._request("POST", endpoint, data=data, json=json, **kwargs)
    
    def get_json(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make GET request and return JSON response.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            **kwargs: Additional arguments
            
        Returns:
            Parsed JSON response
        """
        response = self.get(endpoint, params=params, **kwargs)
        try:
            return response.json()
        except ValueError as e:
            logger.error(f"{self.name} failed to parse JSON response: {str(e)}")
            raise APIClientError(f"Invalid JSON response from {self.name}")
    
    def post_json(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make POST request and return JSON response.
        
        Args:
            endpoint: API endpoint
            data: Form data
            json: JSON data
            **kwargs: Additional arguments
            
        Returns:
            Parsed JSON response
        """
        response = self.post(endpoint, data=data, json=json, **kwargs)
        try:
            return response.json()
        except ValueError as e:
            logger.error(f"{self.name} failed to parse JSON response: {str(e)}")
            raise APIClientError(f"Invalid JSON response from {self.name}")
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.debug(f"{self.name} session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
