"""
Greenhouse ATS adapter implementation.
Maps Greenhouse API to the unified data models.
"""
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseATSAdapter
from ..models import Job, CandidateCreate, CandidateResponse, Application
from ..client import HTTPClient, PaginationHandler
from ..utils.config import get_config
from ..utils.errors import ATSNotFoundError, ATSError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class GreenhouseAdapter(BaseATSAdapter):
    """
    Adapter for Greenhouse ATS (Harvest API).
    
    Greenhouse API Documentation: https://developers.greenhouse.io/harvest.html
    """
    
    # Status mapping from Greenhouse to unified format
    JOB_STATUS_MAP = {
        "open": "OPEN",
        "closed": "CLOSED",
        "draft": "DRAFT",
    }
    
    # Application status mapping
    # Greenhouse uses stages, we map common stage names to our unified statuses
    APPLICATION_STATUS_MAP = {
        # Initial stages
        "application review": "APPLIED",
        "applied": "APPLIED",
        "new": "APPLIED",
        
        # Screening stages
        "phone screen": "SCREENING",
        "screening": "SCREENING",
        "recruiter screen": "SCREENING",
        "phone interview": "SCREENING",
        "technical screen": "SCREENING",
        
        # Interview stages (also mapped to SCREENING in our simplified model)
        "interview": "SCREENING",
        "onsite": "SCREENING",
        "onsite interview": "SCREENING",
        "final interview": "SCREENING",
        
        # Offer stages (mapped to SCREENING before acceptance)
        "offer": "SCREENING",
        "reference check": "SCREENING",
        "background check": "SCREENING",
        
        # Final statuses
        "hired": "HIRED",
        "rejected": "REJECTED",
    }
    
    def __init__(self):
        """Initialize Greenhouse adapter with configuration."""
        config = get_config()
        self.client = HTTPClient(
            base_url=config.ats_base_url,
            api_key=config.ats_api_key
        )
        self.paginator = PaginationHandler(page_size=100)
    
    def get_jobs(self, status_filter: str = None) -> List[Job]:
        """
        Fetch all jobs from Greenhouse.
        
        Uses the Harvest API /jobs endpoint with pagination.
        """
        logger.info("Fetching jobs from Greenhouse")
        
        def fetch_page(params: Dict[str, Any]) -> Tuple[List[Dict], Dict[str, str]]:
            response, headers = self.client.get("jobs", params=params)
            return response if isinstance(response, list) else [], headers
        
        params = {"per_page": 100}
        if status_filter:
            params["status"] = status_filter.lower()
        
        raw_jobs = self.paginator.paginate(fetch_page, params)
        
        jobs = []
        for raw_job in raw_jobs:
            try:
                job = self._normalize_job(raw_job)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to normalize job {raw_job.get('id')}: {e}")
                continue
        
        logger.info(f"Fetched and normalized {len(jobs)} jobs")
        return jobs
    
    def _normalize_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        """Convert Greenhouse job to unified Job model."""
        job_id = str(raw_job.get("id", ""))
        
        # Extract location from offices or location field
        location = self._extract_location(raw_job)
        
        # Map status
        raw_status = raw_job.get("status", "draft").lower()
        status = self.JOB_STATUS_MAP.get(raw_status, "DRAFT")
        
        # Get external URL
        external_url = self._get_job_url(raw_job)
        
        return Job(
            id=job_id,
            title=raw_job.get("name", "Untitled Position"),
            location=location,
            status=status,
            external_url=external_url
        )
    
    def _extract_location(self, raw_job: Dict[str, Any]) -> str:
        """Extract location string from Greenhouse job data."""
        offices = raw_job.get("offices", [])
        if offices:
            office_names = [o.get("name", "") for o in offices if o.get("name")]
            if office_names:
                return ", ".join(office_names)
        
        # Fallback to location field if present
        location = raw_job.get("location", {})
        if isinstance(location, dict):
            return location.get("name", "Remote")
        elif isinstance(location, str):
            return location
        
        return "Remote"
    
    def _get_job_url(self, raw_job: Dict[str, Any]) -> str:
        """Get the public-facing job URL."""
        # Check for job board URL
        job_post = raw_job.get("job_post")
        if job_post and job_post.get("external_url"):
            return job_post["external_url"]
        
        # Construct from ID
        job_id = raw_job.get("id", "")
        return f"https://boards.greenhouse.io/jobs/{job_id}"
    
    def create_candidate(self, candidate: CandidateCreate) -> CandidateResponse:
        """
        Create a candidate in Greenhouse and add to job.
        
        Greenhouse requires:
        1. POST /candidates - Create candidate
        2. POST /candidates/{id}/applications - Add to job (creates application)
        """
        logger.info(f"Creating candidate: {candidate.email}")
        
        # Prepare candidate payload
        candidate_payload = {
            "first_name": self._extract_first_name(candidate.name),
            "last_name": self._extract_last_name(candidate.name),
            "email_addresses": [
                {"value": candidate.email, "type": "personal"}
            ],
            "applications": [
                {
                    "job_id": int(candidate.job_id)
                }
            ]
        }
        
        # Add phone if provided
        if candidate.phone:
            candidate_payload["phone_numbers"] = [
                {"value": candidate.phone, "type": "mobile"}
            ]
        
        # Add resume if provided
        if candidate.resume_url:
            candidate_payload["attachments"] = [
                {
                    "filename": "resume.pdf",
                    "type": "resume",
                    "url": candidate.resume_url
                }
            ]
        
        # Create candidate
        response, _ = self.client.post("candidates", candidate_payload)
        
        candidate_id = str(response.get("id", ""))
        
        # Get application ID from response
        applications = response.get("applications", [])
        application_id = str(applications[0]["id"]) if applications else ""
        
        if not application_id:
            raise ATSError(
                message="Failed to create application for candidate",
                status_code=500
            )
        
        return CandidateResponse(
            candidate_id=candidate_id,
            application_id=application_id,
            name=candidate.name,
            email=candidate.email,
            job_id=candidate.job_id,
            status="APPLIED"
        )
    
    def _extract_first_name(self, full_name: str) -> str:
        """Extract first name from full name."""
        parts = full_name.strip().split()
        return parts[0] if parts else full_name
    
    def _extract_last_name(self, full_name: str) -> str:
        """Extract last name from full name."""
        parts = full_name.strip().split()
        return " ".join(parts[1:]) if len(parts) > 1 else ""
    
    def get_applications(self, job_id: str) -> List[Application]:
        """
        Fetch all applications for a specific job.
        
        Uses the Harvest API /applications endpoint with job_id filter.
        """
        logger.info(f"Fetching applications for job {job_id}")
        
        def fetch_page(params: Dict[str, Any]) -> Tuple[List[Dict], Dict[str, str]]:
            response, headers = self.client.get("applications", params=params)
            return response if isinstance(response, list) else [], headers
        
        params = {
            "job_id": job_id,
            "per_page": 100
        }
        
        raw_applications = self.paginator.paginate(fetch_page, params)
        
        applications = []
        for raw_app in raw_applications:
            try:
                app = self._normalize_application(raw_app)
                if app:
                    applications.append(app)
            except Exception as e:
                logger.warning(f"Failed to normalize application {raw_app.get('id')}: {e}")
                continue
        
        logger.info(f"Fetched and normalized {len(applications)} applications")
        return applications
    
    def _normalize_application(self, raw_app: Dict[str, Any]) -> Optional[Application]:
        """Convert Greenhouse application to unified Application model."""
        app_id = str(raw_app.get("id", ""))
        
        # Get candidate info
        candidate = raw_app.get("candidate", {})
        candidate_name = self._format_candidate_name(candidate)
        
        # Get email
        emails = candidate.get("email_addresses", [])
        email = emails[0]["value"] if emails else ""
        
        # Determine status from current stage and rejection
        status = self._determine_application_status(raw_app)
        
        return Application(
            id=app_id,
            candidate_name=candidate_name,
            email=email,
            status=status
        )
    
    def _format_candidate_name(self, candidate: Dict[str, Any]) -> str:
        """Format candidate name from first_name and last_name."""
        first_name = candidate.get("first_name", "")
        last_name = candidate.get("last_name", "")
        return f"{first_name} {last_name}".strip() or "Unknown"
    
    def _determine_application_status(self, raw_app: Dict[str, Any]) -> str:
        """
        Determine unified application status from Greenhouse data.
        
        Checks rejection status first, then stage name.
        """
        # Check if rejected
        rejected_at = raw_app.get("rejected_at")
        if rejected_at:
            return "REJECTED"
        
        # Check current stage
        current_stage = raw_app.get("current_stage", {})
        stage_name = current_stage.get("name", "").lower() if current_stage else ""
        
        # Check for hired status
        status = raw_app.get("status", "").lower()
        if status == "hired" or "hired" in stage_name:
            return "HIRED"
        
        # Map stage to status
        for pattern, unified_status in self.APPLICATION_STATUS_MAP.items():
            if pattern in stage_name:
                return unified_status
        
        # Default to APPLIED
        return "APPLIED"
    
    def health_check(self) -> bool:
        """Check Greenhouse API connectivity."""
        try:
            # Simple request to verify credentials
            self.client.get("jobs", params={"per_page": 1})
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
