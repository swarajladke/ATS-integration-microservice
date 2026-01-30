"""
ATS Adapter Factory.
Returns the appropriate adapter based on configuration.
"""
from typing import Type

from .base import BaseATSAdapter
from .greenhouse import GreenhouseAdapter
from .zoho_recruit import ZohoRecruitAdapter
from .workable import WorkableAdapter
from ..utils.config import get_config
from ..utils.logging import get_logger


logger = get_logger(__name__)


# Registry of available adapters
ADAPTER_REGISTRY: dict[str, Type[BaseATSAdapter]] = {
    "greenhouse": GreenhouseAdapter,
    "zoho_recruit": ZohoRecruitAdapter,
    "workable": WorkableAdapter,
}


def get_adapter() -> BaseATSAdapter:
    """
    Get the configured ATS adapter instance.
    
    Reads the ATS_PROVIDER environment variable and returns
    the corresponding adapter.
    
    Returns:
        Configured ATS adapter instance
        
    Raises:
        ValueError: If the configured provider is not supported
    """
    config = get_config()
    provider = config.ats_provider.lower()
    
    logger.info(f"Creating adapter for provider: {provider}")
    
    if provider not in ADAPTER_REGISTRY:
        supported = ", ".join(ADAPTER_REGISTRY.keys())
        raise ValueError(
            f"Unsupported ATS provider: {provider}. "
            f"Supported providers: {supported}"
        )
    
    adapter_class = ADAPTER_REGISTRY[provider]
    return adapter_class()


def register_adapter(name: str, adapter_class: Type[BaseATSAdapter]) -> None:
    """
    Register a new ATS adapter.
    
    This allows extending the service with new ATS providers
    without modifying the core code.
    
    Args:
        name: Provider name (lowercase)
        adapter_class: Adapter class that extends BaseATSAdapter
    """
    ADAPTER_REGISTRY[name.lower()] = adapter_class
    logger.info(f"Registered adapter: {name}")


def list_adapters() -> list[str]:
    """
    List all available ATS adapters.
    
    Returns:
        List of supported provider names
    """
    return list(ADAPTER_REGISTRY.keys())
