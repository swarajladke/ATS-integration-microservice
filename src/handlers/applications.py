"""
GET /applications Lambda handler.
Returns applications for a specific job.
"""
import time
from typing import Any, Dict

from ..adapters import get_adapter
from ..utils import (
    ValidationError,
    format_error_response,
    format_success_response,
    get_logger,
    log_request,
    log_response,
)


logger = get_logger(__name__)


def get_applications(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /applications endpoint.
    
    Fetches all applications for a specific job from the configured ATS,
    normalizes them, and returns a clean JSON response.
    
    Query Parameters:
        job_id (required): Job ID to fetch applications for
    
    Returns:
        JSON response with list of applications
    """
    start_time = time.time()
    log_request(logger, event)
    
    try:
        # Get query parameters
        query_params = event.get("queryStringParameters") or {}
        job_id = query_params.get("job_id")
        
        # Validate required parameter
        if not job_id:
            raise ValidationError(
                "job_id query parameter is required",
                details={"job_id": "This field is required"}
            )
        
        # Get adapter and fetch applications
        adapter = get_adapter()
        applications = adapter.get_applications(job_id)
        
        # Build response
        response_data = {
            "applications": [app.model_dump() for app in applications],
            "job_id": job_id,
            "total_count": len(applications)
        }
        
        duration_ms = (time.time() - start_time) * 1000
        log_response(logger, 200, duration_ms)
        
        return format_success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error fetching applications: {e}", exc_info=True)
        duration_ms = (time.time() - start_time) * 1000
        log_response(logger, 500, duration_ms)
        return format_error_response(e)
