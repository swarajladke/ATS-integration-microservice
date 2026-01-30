"""
Unit tests for Lambda handlers.
"""
import json
import pytest
from unittest.mock import Mock, patch

from src.handlers.jobs import get_jobs
from src.handlers.candidates import create_candidate
from src.handlers.applications import get_applications
from src.models import Job, CandidateResponse, Application


class TestGetJobsHandler:
    """Tests for GET /jobs handler."""
    
    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter."""
        adapter = Mock()
        adapter.get_jobs.return_value = [
            Job(
                id="123",
                title="Engineer",
                location="NYC",
                status="OPEN",
                external_url="https://example.com/jobs/123"
            )
        ]
        return adapter
    
    def test_get_jobs_success(self, mock_adapter):
        """Test successful job retrieval."""
        with patch("src.handlers.jobs.get_adapter", return_value=mock_adapter):
            event = {"queryStringParameters": None}
            result = get_jobs(event, None)
            
            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert len(body["jobs"]) == 1
            assert body["jobs"][0]["title"] == "Engineer"
            assert body["total_count"] == 1
    
    def test_get_jobs_with_status_filter(self, mock_adapter):
        """Test job retrieval with status filter."""
        with patch("src.handlers.jobs.get_adapter", return_value=mock_adapter):
            event = {"queryStringParameters": {"status": "OPEN"}}
            result = get_jobs(event, None)
            
            assert result["statusCode"] == 200
            mock_adapter.get_jobs.assert_called_with(status_filter="OPEN")
    
    def test_get_jobs_error_handling(self):
        """Test error handling in jobs handler."""
        with patch("src.handlers.jobs.get_adapter") as mock_get_adapter:
            mock_get_adapter.side_effect = Exception("Test error")
            
            event = {"queryStringParameters": None}
            result = get_jobs(event, None)
            
            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert "error" in body


class TestCreateCandidateHandler:
    """Tests for POST /candidates handler."""
    
    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter."""
        adapter = Mock()
        adapter.create_candidate.return_value = CandidateResponse(
            candidate_id="789",
            application_id="456",
            name="John Doe",
            email="john@example.com",
            job_id="123",
            status="APPLIED"
        )
        return adapter
    
    def test_create_candidate_success(self, mock_adapter):
        """Test successful candidate creation."""
        with patch("src.handlers.candidates.get_adapter", return_value=mock_adapter):
            event = {
                "body": json.dumps({
                    "name": "John Doe",
                    "email": "john@example.com",
                    "job_id": "123"
                })
            }
            result = create_candidate(event, None)
            
            assert result["statusCode"] == 201
            body = json.loads(result["body"])
            assert body["candidate_id"] == "789"
            assert body["application_id"] == "456"
    
    def test_create_candidate_missing_body(self):
        """Test error when body is missing."""
        with patch("src.handlers.candidates.get_adapter"):
            event = {"body": None}
            result = create_candidate(event, None)
            
            assert result["statusCode"] == 400
            body = json.loads(result["body"])
            assert body["error"] == "VALIDATION_ERROR"
    
    def test_create_candidate_invalid_json(self):
        """Test error when body is invalid JSON."""
        with patch("src.handlers.candidates.get_adapter"):
            event = {"body": "not valid json"}
            result = create_candidate(event, None)
            
            assert result["statusCode"] == 400
    
    def test_create_candidate_missing_required_fields(self):
        """Test error when required fields are missing."""
        with patch("src.handlers.candidates.get_adapter"):
            event = {
                "body": json.dumps({
                    "name": "John Doe"
                    # Missing email and job_id
                })
            }
            result = create_candidate(event, None)
            
            assert result["statusCode"] == 400
            body = json.loads(result["body"])
            assert body["error"] == "VALIDATION_ERROR"


class TestGetApplicationsHandler:
    """Tests for GET /applications handler."""
    
    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter."""
        adapter = Mock()
        adapter.get_applications.return_value = [
            Application(
                id="456",
                candidate_name="John Doe",
                email="john@example.com",
                status="SCREENING"
            )
        ]
        return adapter
    
    def test_get_applications_success(self, mock_adapter):
        """Test successful application retrieval."""
        with patch("src.handlers.applications.get_adapter", return_value=mock_adapter):
            event = {"queryStringParameters": {"job_id": "123"}}
            result = get_applications(event, None)
            
            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert len(body["applications"]) == 1
            assert body["job_id"] == "123"
    
    def test_get_applications_missing_job_id(self):
        """Test error when job_id is missing."""
        with patch("src.handlers.applications.get_adapter"):
            event = {"queryStringParameters": None}
            result = get_applications(event, None)
            
            assert result["statusCode"] == 400
            body = json.loads(result["body"])
            assert body["error"] == "VALIDATION_ERROR"
            assert "job_id" in body["message"]
