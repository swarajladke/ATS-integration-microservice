"""
Unit tests for the Greenhouse adapter.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.adapters.greenhouse import GreenhouseAdapter
from src.models import Job, CandidateCreate, CandidateResponse, Application


class TestGreenhouseAdapter:
    """Tests for GreenhouseAdapter class."""
    
    @pytest.fixture
    def adapter(self):
        """Create adapter with mocked config."""
        with patch("src.adapters.greenhouse.get_config") as mock_config:
            mock_config.return_value = Mock(
                ats_api_key="test_key",
                ats_base_url="https://harvest.greenhouse.io/v1"
            )
            return GreenhouseAdapter()
    
    @pytest.fixture
    def sample_greenhouse_job(self):
        """Sample Greenhouse job data."""
        return {
            "id": 123456,
            "name": "Senior Software Engineer",
            "status": "open",
            "offices": [{"name": "San Francisco, CA"}],
            "job_post": {
                "external_url": "https://boards.greenhouse.io/company/jobs/123456"
            }
        }
    
    @pytest.fixture
    def sample_greenhouse_application(self):
        """Sample Greenhouse application data."""
        return {
            "id": 789012,
            "candidate": {
                "first_name": "John",
                "last_name": "Doe",
                "email_addresses": [{"value": "john@example.com"}]
            },
            "current_stage": {"name": "Phone Screen"},
            "rejected_at": None
        }
    
    def test_normalize_job(self, adapter, sample_greenhouse_job):
        """Test job normalization."""
        job = adapter._normalize_job(sample_greenhouse_job)
        
        assert job.id == "123456"
        assert job.title == "Senior Software Engineer"
        assert job.status == "OPEN"
        assert job.location == "San Francisco, CA"
        assert "123456" in job.external_url
    
    def test_normalize_job_status_mapping(self, adapter):
        """Test all job status mappings."""
        test_cases = [
            ({"id": 1, "name": "Test", "status": "open"}, "OPEN"),
            ({"id": 2, "name": "Test", "status": "closed"}, "CLOSED"),
            ({"id": 3, "name": "Test", "status": "draft"}, "DRAFT"),
            ({"id": 4, "name": "Test", "status": "unknown"}, "DRAFT"),
        ]
        
        for raw_job, expected_status in test_cases:
            job = adapter._normalize_job(raw_job)
            assert job.status == expected_status
    
    def test_extract_location_from_offices(self, adapter):
        """Test location extraction from offices."""
        raw_job = {
            "offices": [
                {"name": "San Francisco"},
                {"name": "New York"}
            ]
        }
        location = adapter._extract_location(raw_job)
        assert location == "San Francisco, New York"
    
    def test_extract_location_fallback(self, adapter):
        """Test location fallback when no offices."""
        raw_job = {"location": {"name": "Remote"}}
        location = adapter._extract_location(raw_job)
        assert location == "Remote"
    
    def test_extract_location_default(self, adapter):
        """Test default location when nothing available."""
        raw_job = {}
        location = adapter._extract_location(raw_job)
        assert location == "Remote"
    
    def test_normalize_application(self, adapter, sample_greenhouse_application):
        """Test application normalization."""
        app = adapter._normalize_application(sample_greenhouse_application)
        
        assert app.id == "789012"
        assert app.candidate_name == "John Doe"
        assert app.email == "john@example.com"
        assert app.status == "SCREENING"
    
    def test_application_status_rejected(self, adapter):
        """Test rejected application status."""
        raw_app = {
            "id": 1,
            "candidate": {
                "first_name": "Test",
                "last_name": "User",
                "email_addresses": [{"value": "test@example.com"}]
            },
            "rejected_at": "2024-01-15T10:00:00Z",
            "current_stage": {"name": "Interview"}
        }
        app = adapter._normalize_application(raw_app)
        assert app.status == "REJECTED"
    
    def test_application_status_hired(self, adapter):
        """Test hired application status."""
        raw_app = {
            "id": 1,
            "candidate": {
                "first_name": "Test",
                "last_name": "User",
                "email_addresses": [{"value": "test@example.com"}]
            },
            "rejected_at": None,
            "current_stage": {"name": "Hired"},
            "status": "hired"
        }
        app = adapter._normalize_application(raw_app)
        assert app.status == "HIRED"
    
    def test_extract_first_name(self, adapter):
        """Test first name extraction."""
        assert adapter._extract_first_name("John Doe") == "John"
        assert adapter._extract_first_name("Jane") == "Jane"
        assert adapter._extract_first_name("Mary Jane Watson") == "Mary"
    
    def test_extract_last_name(self, adapter):
        """Test last name extraction."""
        assert adapter._extract_last_name("John Doe") == "Doe"
        assert adapter._extract_last_name("Jane") == ""
        assert adapter._extract_last_name("Mary Jane Watson") == "Jane Watson"


class TestGreenhouseAdapterIntegration:
    """Integration tests that mock HTTP client."""
    
    @pytest.fixture
    def adapter_with_mock_client(self):
        """Create adapter with mocked HTTP client."""
        with patch("src.adapters.greenhouse.get_config") as mock_config:
            mock_config.return_value = Mock(
                ats_api_key="test_key",
                ats_base_url="https://harvest.greenhouse.io/v1"
            )
            adapter = GreenhouseAdapter()
            adapter.client = Mock()
            return adapter
    
    def test_get_jobs_success(self, adapter_with_mock_client):
        """Test successful job fetching."""
        adapter = adapter_with_mock_client
        
        # Mock client response
        adapter.client.get.return_value = (
            [
                {
                    "id": 1,
                    "name": "Engineer",
                    "status": "open",
                    "offices": [{"name": "NYC"}]
                }
            ],
            {}  # Empty headers (no pagination)
        )
        
        jobs = adapter.get_jobs()
        
        assert len(jobs) == 1
        assert jobs[0].title == "Engineer"
        assert jobs[0].status == "OPEN"
    
    def test_create_candidate_success(self, adapter_with_mock_client):
        """Test successful candidate creation."""
        adapter = adapter_with_mock_client
        
        # Mock client response
        adapter.client.post.return_value = (
            {
                "id": 789,
                "applications": [{"id": 456}]
            },
            {}
        )
        
        candidate_data = CandidateCreate(
            name="John Doe",
            email="john@example.com",
            phone="+1-555-1234",
            job_id="123"
        )
        
        result = adapter.create_candidate(candidate_data)
        
        assert result.candidate_id == "789"
        assert result.application_id == "456"
        assert result.name == "John Doe"
        assert result.status == "APPLIED"
