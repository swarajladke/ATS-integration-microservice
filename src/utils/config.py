"""
Configuration management module.
Loads environment variables securely with validation.
"""
import os
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""
    
    def __init__(self):
        self._ats_provider: str = os.getenv("ATS_PROVIDER", "greenhouse").lower()
        self._ats_api_key: Optional[str] = os.getenv("ATS_API_KEY")
        
        # Zoho specific
        self._zoho_client_id: Optional[str] = os.getenv("ZOHO_CLIENT_ID")
        self._zoho_client_secret: Optional[str] = os.getenv("ZOHO_CLIENT_SECRET")
        self._zoho_refresh_token: Optional[str] = os.getenv("ZOHO_REFRESH_TOKEN")
        self._zoho_region: str = os.getenv("ZOHO_REGION", "com").lower()
        
        # Workable specific
        self._workable_api_key: Optional[str] = os.getenv("WORKABLE_API_KEY")
        self._workable_subdomain: Optional[str] = os.getenv("WORKABLE_SUBDOMAIN")
        
        self._ats_base_url: str = os.getenv("ATS_BASE_URL", self._get_default_base_url())
        self._log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    def _get_default_base_url(self) -> str:
        """Get default base URL based on ATS provider."""
        if self._ats_provider == "greenhouse":
            return "https://harvest.greenhouse.io/v1"
        elif self._ats_provider == "zoho_recruit":
            return f"https://recruit.zoho.{self._zoho_region}/recruit/v2"
        elif self._ats_provider == "workable":
            return f"https://{self._workable_subdomain}.workable.com/spi/v3" if self._workable_subdomain else ""
        return ""
    
    @property
    def ats_provider(self) -> str:
        """Get the configured ATS provider name."""
        return self._ats_provider
    
    @property
    def ats_api_key(self) -> str:
        """Get the ATS API key. Raises if not configured."""
        if not self._ats_api_key:
            raise ValueError("ATS_API_KEY environment variable is not set")
        return self._ats_api_key
    
    @property
    def ats_base_url(self) -> str:
        """Get the ATS base URL."""
        return self._ats_base_url
    
    @property
    def log_level(self) -> str:
        """Get the logging level."""
        return self._log_level

    @property
    def zoho_client_id(self) -> str:
        if not self._zoho_client_id:
            raise ValueError("ZOHO_CLIENT_ID is not set")
        return self._zoho_client_id

    @property
    def zoho_client_secret(self) -> str:
        if not self._zoho_client_secret:
            raise ValueError("ZOHO_CLIENT_SECRET is not set")
        return self._zoho_client_secret

    @property
    def zoho_refresh_token(self) -> str:
        if not self._zoho_refresh_token:
            raise ValueError("ZOHO_REFRESH_TOKEN is not set")
        return self._zoho_refresh_token
    
    @property
    def zoho_region(self) -> str:
        return self._zoho_region

    def get_zoho_accounts_url(self) -> str:
        """Get Zoho accounts URL based on region."""
        return f"https://accounts.zoho.{self._zoho_region}"

    @property
    def workable_api_key(self) -> str:
        if not self._workable_api_key:
            raise ValueError("WORKABLE_API_KEY is not set")
        return self._workable_api_key

    @property
    def workable_subdomain(self) -> str:
        if not self._workable_subdomain:
            raise ValueError("WORKABLE_SUBDOMAIN is not set")
        return self._workable_subdomain
    
    def is_api_key_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self._ats_api_key)


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get cached configuration instance."""
    return Config()
