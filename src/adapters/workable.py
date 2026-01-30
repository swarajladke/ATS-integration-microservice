"""
Workable ATS adapter implementation.
"""
from typing import List, Dict, Any, Optional

from .base import BaseATSAdapter
from ..models import Job, CandidateCreate, CandidateResponse, Application
from ..utils.config import get_config
from ..utils.logging import get_logger
from ..utils.errors import (
    ATSAuthenticationError,
    ATSError,
    ValidationError
)
from ..client.http_client import HTTPClient


logger = get_logger(__name__)


class WorkableAdapter(BaseATSAdapter):
    """
    Adapter for Workable ATS.
    Uses Bearer Token authentication.
    """
    
    def __init__(self):
        self.config = get_config()
        self.client = HTTPClient(
            base_url=self.config.ats_base_url,
            api_key="", # Not used for Basic Auth
        )
        # Override _get_auth to use Bearer Token
        self.client._get_auth = lambda: None
        self.client.session.headers.update({
            "Authorization": f"Bearer {self.config.workable_api_key}"
        })
    
    def get_jobs(self, status_filter: str = None) -> List[Job]:
        """Fetch jobs from Workable."""
        # Workable states: published, draft, closed, archived
        params = {}
        if status_filter:
            # Map unified status to Workable state
            state_map = {
                "OPEN": "published",
                "CLOSED": "closed",
                "DRAFT": "draft"
            }
            if status_filter in state_map:
                params["state"] = state_map[status_filter]

        response_data, _ = self.client.get("jobs", params=params)
        
        raw_jobs = response_data.get("jobs", [])
        return [self._normalize_job(j) for j in raw_jobs]

    def create_candidate(self, candidate: CandidateCreate) -> CandidateResponse:
        """Create a candidate for a specific job in Workable."""
        # Workable uses 'shortcode' as the job identifier
        endpoint = f"jobs/{candidate.job_id}/candidates"
        
        candidate_data = {
            "candidate": {
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone or "",
                # Workable accepts resume_url or file, but for unified API we use URL
            }
        }
        
        response_data, _ = self.client.post(endpoint, data=candidate_data)
        
        cand = response_data.get("candidate", {})
        candidate_id = cand.get("id")
        
        # In Workable, creating a candidate at the job level automatically creates the application
        return CandidateResponse(
            candidate_id=str(candidate_id),
            application_id=str(candidate_id), # Application ID is often tied to candidate ID in this context
            name=candidate.name,
            email=candidate.email,
            job_id=candidate.job_id,
            status="APPLIED"
        )

    def get_applications(self, job_id: str) -> List[Application]:
        """Fetch candidates (applications) for a job in Workable."""
        endpoint = f"jobs/{job_id}/candidates"
        response_data, _ = self.client.get(endpoint)
        
        raw_candidates = response_data.get("candidates", [])
        return [self._normalize_application(c) for c in raw_candidates]

    def _normalize_job(self, raw_job: Dict[str, Any]) -> Job:
        """Map Workable job to unified Job model."""
        state = raw_job.get("state", "published")
        status_map = {
            "published": "OPEN",
            "closed": "CLOSED",
            "archived": "CLOSED",
            "draft": "DRAFT"
        }
        
        return Job(
            id=raw_job.get("shortcode"), # shortcode is the unique identifier for jobs in Workable
            title=raw_job.get("title"),
            location=raw_job.get("location", {}).get("city", "Remote"),
            status=status_map.get(state, "OPEN"),
            external_url=raw_job.get("url")
        )

    def _normalize_application(self, raw_cand: Dict[str, Any]) -> Application:
        """Map Workable candidate to unified Application model."""
        # Workable stages: 'Applied', 'Screening', 'Interview', 'Offer', 'Hired', 'Rejected'
        stage = raw_cand.get("stage", "Applied")
        
        status_map = {
            "Applied": "APPLIED",
            "Screening": "SCREENING",
            "Interview": "SCREENING",
            "Offer": "SCREENING",
            "Hired": "HIRED",
            "Rejected": "REJECTED"
        }
        
        return Application(
            id=str(raw_cand.get("id")),
            candidate_name=raw_cand.get("name"),
            email=raw_cand.get("email"),
            status=status_map.get(stage, "APPLIED")
        )

    def health_check(self) -> bool:
        """Check Workable connection."""
        try:
            # Try a simple root jobs call
            self.client.get("jobs", params={"limit": 1})
            return True
        except Exception:
            return False
