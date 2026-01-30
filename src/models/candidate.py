"""
Candidate models for creating and managing candidates.
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class CandidateCreate(BaseModel):
    """Request model for creating a new candidate."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Candidate full name")
    email: str = Field(..., description="Candidate email address")
    phone: Optional[str] = Field(None, max_length=50, description="Candidate phone number")
    resume_url: Optional[str] = Field(None, description="URL to candidate's resume")
    job_id: str = Field(..., description="Job ID to apply for")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1-555-123-4567",
                "resume_url": "https://example.com/resumes/johndoe.pdf",
                "job_id": "123456"
            }
        }


class CandidateResponse(BaseModel):
    """Response model after creating a candidate."""
    
    candidate_id: str = Field(..., description="Created candidate ID")
    application_id: str = Field(..., description="Created application/job association ID")
    name: str = Field(..., description="Candidate name")
    email: str = Field(..., description="Candidate email")
    job_id: str = Field(..., description="Associated job ID")
    status: str = Field(default="APPLIED", description="Initial application status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "789012",
                "application_id": "345678",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "job_id": "123456",
                "status": "APPLIED"
            }
        }
