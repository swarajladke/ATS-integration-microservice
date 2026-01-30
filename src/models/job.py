"""
Job model representing a unified job posting.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Job(BaseModel):
    """Unified job model normalized across all ATS providers."""
    
    id: str = Field(..., description="Unique job identifier")
    title: str = Field(..., description="Job title")
    location: str = Field(..., description="Job location")
    status: Literal["OPEN", "CLOSED", "DRAFT"] = Field(..., description="Job status")
    external_url: str = Field(..., description="Public-facing job URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123456",
                "title": "Senior Software Engineer",
                "location": "San Francisco, CA",
                "status": "OPEN",
                "external_url": "https://boards.greenhouse.io/company/jobs/123456"
            }
        }


class JobList(BaseModel):
    """Response model for job listings."""
    
    jobs: list[Job] = Field(default_factory=list, description="List of jobs")
    total_count: int = Field(0, description="Total number of jobs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [
                    {
                        "id": "123456",
                        "title": "Senior Software Engineer",
                        "location": "San Francisco, CA",
                        "status": "OPEN",
                        "external_url": "https://boards.greenhouse.io/company/jobs/123456"
                    }
                ],
                "total_count": 1
            }
        }
