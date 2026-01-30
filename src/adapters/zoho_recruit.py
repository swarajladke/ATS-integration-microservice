"""
Zoho Recruit ATS adapter implementation.
"""
import time
from typing import List, Dict, Any, Optional

from .base import BaseATSAdapter
from ..models import Job, CandidateCreate, CandidateResponse, Application
from ..utils.config import get_config
from ..utils.logging import get_logger
from ..utils.errors import (
    ATSAuthenticationError,
    ATSConnectionError,
    ATSError,
    ValidationError
)
from ..client.http_client import HTTPClient


logger = get_logger(__name__)


class ZohoRecruitAdapter(BaseATSAdapter):
    """
    Adapter for Zoho Recruit ATS.
    Handles OAuth 2.0 token refreshing and API mapping.
    """
    
    def __init__(self):
        self.config = get_config()
        self.access_token = None
        self.token_expiry = 0
        
        # Initialize client with empty key, we'll handle headers manually
        self.client = HTTPClient(
            base_url=self.config.ats_base_url,
            api_key="",
        )
        # Override _get_auth for Zoho
        self.client._get_auth = lambda: None
    
    def _refresh_access_token(self):
        """Fetch a new access token using the refresh token."""
        if self.access_token and time.time() < self.token_expiry - 60:
            return

        logger.info("Refreshing Zoho access token")
        accounts_url = self.config.get_zoho_accounts_url()
        
        try:
            import requests
            response = requests.post(
                f"{accounts_url}/oauth/v2/token",
                data={
                    "refresh_token": self.config.zoho_refresh_token,
                    "client_id": self.config.zoho_client_id,
                    "client_secret": self.config.zoho_client_secret,
                    "grant_type": "refresh_token"
                },
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to refresh Zoho token: {response.text}")
                raise ATSAuthenticationError("Failed to refresh Zoho access token")
            
            data = response.json()
            if "access_token" not in data:
                logger.error(f"Invalid response from Zoho token endpoint: {data}")
                raise ATSAuthenticationError("Invalid response from Zoho token endpoint")
            
            self.access_token = data["access_token"]
            # Set expiry (usually 3600s, use 3500 to be safe)
            self.token_expiry = time.time() + data.get("expires_in", 3600)
            
            # Update client session headers
            self.client.session.headers.update({
                "Authorization": f"Zoho-oauthtoken {self.access_token}"
            })
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error while refreshing Zoho token: {str(e)}")
            raise ATSConnectionError(f"Failed to connect to Zoho token service: {str(e)}")

    def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        self._refresh_access_token()

    def get_jobs(self, status_filter: str = None) -> List[Job]:
        """Fetch all Job Openings from Zoho Recruit."""
        self._ensure_authenticated()
        
        # Zoho module name is 'Job_Openings'
        response_data, _ = self.client.get("Job_Openings")
        
        raw_jobs = response_data.get("data", [])
        jobs = []
        
        for raw_job in raw_jobs:
            job = self._normalize_job(raw_job)
            if not status_filter or job.status == status_filter:
                jobs.append(job)
        
        return jobs

    def create_candidate(self, candidate: CandidateCreate) -> CandidateResponse:
        """Create a candidate in Zoho Recruit and associate with a job."""
        self._ensure_authenticated()
        
        # 1. Create Candidate
        candidate_data = {
            "data": [{
                "First_Name": self._extract_first_name(candidate.name),
                "Last_Name": self._extract_last_name(candidate.name),
                "Email": candidate.email,
                "Phone": candidate.phone or "",
                # Custom fields or resume URL would go here if defined in Zoho
            }]
        }
        
        cand_resp, _ = self.client.post("Candidates", data=candidate_data)
        
        if not cand_resp.get("data") or cand_resp["data"][0].get("code") != "SUCCESS":
            error_msg = cand_resp.get("data", [{}])[0].get("message", "Unknown error")
            raise ATSError(f"Failed to create candidate in Zoho: {error_msg}")
            
        candidate_id = cand_resp["data"][0]["details"]["id"]
        
        # 2. Associate with Job (Create Application)
        # In Zoho Recruit, this often means creating a record in the 'Applications' module
        # or updating a subform. Standard practice is the 'Applications' module.
        app_data = {
            "data": [{
                "Candidate_ID": candidate_id,
                "Job_Opening_ID": candidate.job_id,
                "Application_Status": "Applied"
            }]
        }
        
        # Module name might be 'Applications' or 'JobOpenings_Candidates' 
        # based on Zoho Recruit's specific configuration. Using 'Applications' as default.
        try:
            app_resp, _ = self.client.post("Applications", data=app_data)
            application_id = app_resp["data"][0]["details"]["id"] if app_resp.get("data") else "N/A"
        except ATSError:
            logger.warning("Failed to create Application record, candidate created but association might be manual.")
            application_id = "MANUAL_ASSOC_REQUIRED"

        return CandidateResponse(
            candidate_id=candidate_id,
            application_id=application_id,
            name=candidate.name,
            email=candidate.email,
            job_id=candidate.job_id,
            status="APPLIED"
        )

    def get_applications(self, job_id: str) -> List[Application]:
        """Fetch applications for a job from Zoho Recruit."""
        self._ensure_authenticated()
        
        # Fetch from Applications module with criteria
        params = {"criteria": f"(Job_Opening_ID:equals:{job_id})"}
        response_data, _ = self.client.get("Applications", params=params)
        
        raw_apps = response_data.get("data", [])
        return [self._normalize_application(app) for app in raw_apps]

    def _normalize_job(self, raw_job: Dict[str, Any]) -> Job:
        """Map Zoho Job_Opening record to unified Job model."""
        status_map = {
            "In-progress": "OPEN",
            "Filled": "CLOSED",
            "Cancelled": "CLOSED",
            "Draft": "DRAFT",
            "On-hold": "DRAFT"
        }
        
        return Job(
            id=raw_job.get("id"),
            title=raw_job.get("Posting_Title"),
            location=raw_job.get("City", "Remote"),
            status=status_map.get(raw_job.get("Job_Opening_Status"), "OPEN"),
            external_url=f"https://recruit.zoho.{self.config.zoho_region}/recruit/JobOpenings.do?id={raw_job.get('id')}"
        )

    def _normalize_application(self, raw_app: Dict[str, Any]) -> Application:
        """Map Zoho Application record to unified Application model."""
        # Note: raw_app often contains partial Candidate info or we might need another fetch
        candidate = raw_app.get("Candidate_ID", {})
        
        status_map = {
            "Applied": "APPLIED",
            "Screening": "SCREENING",
            "Rejected": "REJECTED",
            "Hired": "HIRED"
        }
        
        return Application(
            id=raw_app.get("id"),
            candidate_name=candidate.get("name") or "Unknown",
            email=candidate.get("email") or "Unknown",
            status=status_map.get(raw_app.get("Application_Status"), "APPLIED")
        )

    def _extract_first_name(self, name: str) -> str:
        return name.split(" ", 1)[0] if " " in name else name

    def _extract_last_name(self, name: str) -> str:
        return name.split(" ", 1)[1] if " " in name else "."  # Zoho often requires Last Name

    def health_check(self) -> bool:
        """Check Zoho connection."""
        try:
            self._ensure_authenticated()
            # Try a simple modules list
            self.client.get("settings/modules")
            return True
        except Exception:
            return False
