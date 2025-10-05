"""Configuration management for VerbalForge MCP (import aggregator for backward compatibility)"""

# Import all configuration components from the new modular structure
from .settings import settings, Settings
from .providers_config import (
    get_api_key,
    validate_api_keys,
    get_model_config,
    get_supported_providers,
)

# Re-export everything for backward compatibility
__all__ = [
    "settings",
    "Settings",
    "get_api_key",
    "validate_api_keys",
    "get_model_config",
    "get_supported_providers",
]
