"""Provider-specific configuration utilities"""

from typing import Optional, Dict, Any

from .settings import settings
from ..models.enums import LLMProvider


def get_api_key(provider: str) -> Optional[str]:
    """Get API key for the specified provider"""
    provider_lower = provider.lower()

    if provider_lower == LLMProvider.OPENAI:
        return settings.openai_api_key
    elif provider_lower == LLMProvider.AZURE_OPENAI:
        return settings.azure_openai_api_key
    else:
        raise ValueError(f"Unknown provider: {provider}")


def validate_api_keys() -> bool:
    """Validate that at least one API key is configured"""
    return bool(settings.openai_api_key or settings.azure_openai_api_key)


def get_model_config(provider: str) -> Dict[str, Any]:
    """Get model configuration for the specified provider"""
    base_config = {
        "temperature": settings.llm_temperature,
        # Removed max_tokens to let models use their default limits
    }

    provider_lower = provider.lower()

    if provider_lower == LLMProvider.OPENAI:
        base_config["model"] = settings.llm_model
    elif provider_lower == LLMProvider.AZURE_OPENAI:
        base_config["model"] = settings.llm_model
        base_config["azure_endpoint"] = settings.azure_openai_endpoint
        base_config["api_version"] = settings.azure_openai_api_version
        base_config["azure_deployment"] = settings.azure_openai_deployment_name

    return base_config


def get_supported_providers() -> list[str]:
    """Get list of supported LLM providers"""
    return [provider.value for provider in LLMProvider]
