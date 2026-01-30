"""
Application model representing a job application.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Application(BaseModel):
    """Unified application model normalized across all ATS providers."""
    
    id: str = Field(..., description="Unique application identifier")
    candidate_name: str = Field(..., description="Name of the candidate")
    email: str = Field(..., description="Candidate email address")
    status: Literal["APPLIED", "SCREENING", "REJECTED", "HIRED"] = Field(
        ..., description="Application status"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "345678",
                "candidate_name": "John Doe",
                "email": "john.doe@example.com",
                "status": "SCREENING"
            }
        }


class ApplicationList(BaseModel):
    """Response model for application listings."""
    
    applications: list[Application] = Field(
        default_factory=list, description="List of applications"
    )
    job_id: str = Field(..., description="Job ID these applications are for")
    total_count: int = Field(0, description="Total number of applications")
    
    class Config:
        json_schema_extra = {
            "example": {
                "applications": [
                    {
                        "id": "345678",
                        "candidate_name": "John Doe",
                        "email": "john.doe@example.com",
                        "status": "SCREENING"
                    }
                ],
                "job_id": "123456",
                "total_count": 1
            }
        }
