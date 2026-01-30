"""
Pagination handler for ATS APIs.
Supports multiple pagination styles: link-based, cursor-based, and offset-based.
"""
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from ..utils.logging import get_logger


logger = get_logger(__name__)


class PaginationHandler:
    """
    Handles pagination for ATS API responses.
    Automatically detects pagination style and fetches all pages.
    """
    
    def __init__(self, max_pages: int = 100, page_size: int = 100):
        """
        Initialize pagination handler.
        
        Args:
            max_pages: Maximum number of pages to fetch (safety limit)
            page_size: Default page size for requests
        """
        self.max_pages = max_pages
        self.page_size = page_size
    
    def paginate(
        self,
        fetch_func: Callable[[Dict[str, Any]], Tuple[List[Any], Dict[str, str]]],
        initial_params: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Fetch all pages of results from an API endpoint.
        
        Args:
            fetch_func: Function that takes params and returns (items, headers)
            initial_params: Initial query parameters
            
        Returns:
            Combined list of all items across all pages
        """
        all_items: List[Any] = []
        params = initial_params.copy() if initial_params else {}
        params.setdefault("per_page", self.page_size)
        
        page_count = 0
        next_url = None
        
        while page_count < self.max_pages:
            page_count += 1
            logger.info(f"Fetching page {page_count}")
            
            # Fetch current page
            items, headers = fetch_func(params)
            
            if isinstance(items, list):
                all_items.extend(items)
            
            # Check for next page
            next_url = self._get_next_page_url(headers)
            
            if not next_url:
                logger.info(f"No more pages. Total items: {len(all_items)}")
                break
            
            # Update params for next page
            params = self._parse_url_params(next_url)
            params.setdefault("per_page", self.page_size)
        
        if page_count >= self.max_pages:
            logger.warning(f"Reached max page limit ({self.max_pages})")
        
        return all_items
    
    def _get_next_page_url(self, headers: Dict[str, str]) -> Optional[str]:
        """
        Extract the next page URL from response headers.
        Supports Link header (RFC 5988) pagination style.
        """
        link_header = headers.get("Link", headers.get("link", ""))
        
        if not link_header:
            return None
        
        # Parse Link header: <url>; rel="next", <url>; rel="last"
        links = link_header.split(",")
        
        for link in links:
            parts = link.strip().split(";")
            if len(parts) >= 2:
                url_part = parts[0].strip()
                rel_part = parts[1].strip()
                
                if 'rel="next"' in rel_part or "rel='next'" in rel_part:
                    # Extract URL from angle brackets
                    match = re.match(r'<(.+)>', url_part)
                    if match:
                        return match.group(1)
        
        return None
    
    def _parse_url_params(self, url: str) -> Dict[str, Any]:
        """Parse query parameters from a URL."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Convert list values to single values
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}


def paginate_with_offset(
    fetch_func: Callable[[int, int], Tuple[List[Any], int]],
    page_size: int = 100,
    max_items: int = 10000
) -> List[Any]:
    """
    Helper for offset-based pagination.
    
    Args:
        fetch_func: Function that takes (offset, limit) and returns (items, total_count)
        page_size: Number of items per page
        max_items: Maximum total items to fetch
        
    Returns:
        Combined list of all items
    """
    all_items: List[Any] = []
    offset = 0
    
    while offset < max_items:
        items, total = fetch_func(offset, page_size)
        
        if not items:
            break
        
        all_items.extend(items)
        offset += len(items)
        
        if offset >= total:
            break
    
    return all_items
