"""
GET /jobs Lambda handler.
Returns a list of open jobs from the configured ATS.
"""
import time
from typing import Any, Dict

from ..adapters import get_adapter
from ..utils import (
    format_error_response,
    format_success_response,
    get_logger,
    log_request,
    log_response,
)


logger = get_logger(__name__)


def get_jobs(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /jobs endpoint.
    
    Fetches all jobs from the configured ATS, normalizes them,
    and returns a clean JSON response.
    
    Query Parameters:
        status (optional): Filter by job status (OPEN, CLOSED, DRAFT)
    
    Returns:
        JSON response with list of jobs
    """
    start_time = time.time()
    log_request(logger, event)
    
    try:
        # Get query parameters
        query_params = event.get("queryStringParameters") or {}
        status_filter = query_params.get("status")
        
        # Get adapter and fetch jobs
        adapter = get_adapter()
        jobs = adapter.get_jobs(status_filter=status_filter)
        
        # Build response
        response_data = {
            "jobs": [job.model_dump() for job in jobs],
            "total_count": len(jobs)
        }
        
        duration_ms = (time.time() - start_time) * 1000
        log_response(logger, 200, duration_ms)
        
        return format_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}", exc_info=True)
        duration_ms = (time.time() - start_time) * 1000
        log_response(logger, 500, duration_ms)
        return format_error_response(e)
