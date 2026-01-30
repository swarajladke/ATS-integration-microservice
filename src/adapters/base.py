"""
Base ATS adapter interface.
Defines the contract that all ATS adapters must implement.
"""
from abc import ABC, abstractmethod
from typing import List

from ..models import Job, CandidateCreate, CandidateResponse, Application


class BaseATSAdapter(ABC):
    """
    Abstract base class for ATS adapters.
    
    All ATS-specific adapters must inherit from this class and implement
    the required methods. This ensures a consistent interface regardless
    of the underlying ATS provider.
    """
    
    @abstractmethod
    def get_jobs(self, status_filter: str = None) -> List[Job]:
        """
        Fetch all jobs from the ATS.
        
        Args:
            status_filter: Optional filter for job status (OPEN, CLOSED, DRAFT)
            
        Returns:
            List of normalized Job objects
        """
        pass
    
    @abstractmethod
    def create_candidate(self, candidate: CandidateCreate) -> CandidateResponse:
        """
        Create a new candidate in the ATS and attach to a job.
        
        Args:
            candidate: Candidate creation data including job_id
            
        Returns:
            CandidateResponse with created candidate and application IDs
        """
        pass
    
    @abstractmethod
    def get_applications(self, job_id: str) -> List[Application]:
        """
        Fetch all applications for a specific job.
        
        Args:
            job_id: The job ID to fetch applications for
            
        Returns:
            List of normalized Application objects
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the ATS connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        pass
