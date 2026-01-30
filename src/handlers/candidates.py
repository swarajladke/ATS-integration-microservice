"""
POST /candidates Lambda handler.
Creates a new candidate and attaches them to a job.
"""
import json
import time
from typing import Any, Dict

from pydantic import ValidationError as PydanticValidationError

from ..adapters import get_adapter
from ..models import CandidateCreate
from ..utils import (
    ValidationError,
    format_error_response,
    format_success_response,
    get_logger,
    log_request,
    log_response,
)


logger = get_logger(__name__)


def create_candidate(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for POST /candidates endpoint.
    
    Creates a new candidate in the configured ATS and attaches
    them to the specified job.
    
    Request Body:
        {
            "name": "string",
            "email": "string",
            "phone": "string (optional)",
            "resume_url": "string (optional)",
            "job_id": "string"
        }
    
    Returns:
        JSON response with candidate and application IDs
    """
    start_time = time.time()
    log_request(logger, event)
    
    try:
        # Parse request body
        body = event.get("body")
        if not body:
            raise ValidationError("Request body is required")
        
        # Handle both string and dict body
        if isinstance(body, str):
            try:
                body_data = json.loads(body)
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON in request body")
        else:
            body_data = body
        
        # Validate request data
        try:
            candidate_data = CandidateCreate(**body_data)
        except PydanticValidationError as e:
            errors = e.errors()
            details = {err["loc"][0]: err["msg"] for err in errors}
            raise ValidationError("Validation failed", details=details)
        
        # Get adapter and create candidate
        adapter = get_adapter()
        result = adapter.create_candidate(candidate_data)
        
        # Build response
        response_data = result.model_dump()
        
        duration_ms = (time.time() - start_time) * 1000
        log_response(logger, 201, duration_ms)
        
        return format_success_response(response_data, status_code=201)
        
    except Exception as e:
        logger.error(f"Error creating candidate: {e}", exc_info=True)
        duration_ms = (time.time() - start_time) * 1000
        log_response(logger, 500, duration_ms)
        return format_error_response(e)
