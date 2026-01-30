"""
HTTP client with retry logic, rate limiting, and authentication.
"""
import time
from typing import Any, Dict, Optional, Tuple
import requests
from requests.auth import HTTPBasicAuth
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from ..utils.config import get_config
from ..utils.errors import (
    ATSConnectionError,
    ATSAuthenticationError,
    ATSRateLimitError,
    ATSError,
)
from ..utils.logging import get_logger


logger = get_logger(__name__)


class RetryableError(Exception):
    """Exception that indicates the request should be retried."""
    pass


class HTTPClient:
    """
    HTTP client for making requests to ATS APIs.
    Includes retry logic, rate limiting, and authentication handling.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a configured requests session."""
        session = requests.Session()
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ATS-Integration-Microservice/1.0"
        })
        return session
    
    def _get_auth(self) -> Optional[HTTPBasicAuth]:
        """Get authentication for requests (Greenhouse uses Basic Auth)."""
        if self.api_key:
            return HTTPBasicAuth(self.api_key, "")
        return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RetryableError),
        reraise=True
    )
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Make an HTTP request with retry logic.
        
        Returns:
            Tuple of (response_data, response_headers)
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        logger.info(f"Making {method} request to {url}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                auth=self._get_auth(),
                timeout=self.timeout
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited. Retry after {retry_after}s")
                raise ATSRateLimitError(retry_after=retry_after)
            
            # Handle authentication errors
            if response.status_code == 401:
                raise ATSAuthenticationError("Invalid API credentials")
            
            if response.status_code == 403:
                raise ATSAuthenticationError("Access forbidden - check API permissions")
            
            # Handle server errors (retryable)
            if response.status_code >= 500:
                logger.warning(f"Server error {response.status_code}, will retry")
                raise RetryableError(f"Server error: {response.status_code}")
            
            # Raise for other 4xx errors
            if response.status_code >= 400:
                error_detail = response.text[:200] if response.text else "Unknown error"
                raise ATSError(
                    message=f"Request failed with status {response.status_code}",
                    status_code=response.status_code
                )
            
            # Parse successful response
            if response.content:
                return response.json(), dict(response.headers)
            return {}, dict(response.headers)
            
        except requests.exceptions.Timeout:
            raise RetryableError("Request timed out")
        except requests.exceptions.ConnectionError:
            raise ATSConnectionError("Failed to connect to ATS service")
        except requests.exceptions.RequestException as e:
            raise ATSConnectionError(f"Request failed: {str(e)}")
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, Dict[str, str]]:
        """Make a GET request."""
        return self._make_request("GET", endpoint, params=params)
    
    def post(
        self,
        endpoint: str,
        data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, Dict[str, str]]:
        """Make a POST request."""
        return self._make_request("POST", endpoint, params=params, json_data=data)
    
    def put(
        self,
        endpoint: str,
        data: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, Dict[str, str]]:
        """Make a PUT request."""
        return self._make_request("PUT", endpoint, params=params, json_data=data)
    
    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, Dict[str, str]]:
        """Make a DELETE request."""
        return self._make_request("DELETE", endpoint, params=params)
