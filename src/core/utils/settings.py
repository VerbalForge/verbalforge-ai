"""Settings management using pydantic-settings"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


# Find the .env file - it's in the project root
def find_env_file() -> str:
    """Find .env file by searching up the directory tree"""
    current = Path(__file__).resolve()
    for parent in [current.parent] + list(current.parents):
        env_path = parent / ".env"
        if env_path.exists():
            return str(env_path)
    return ".env"  # fallback to current directory


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # OpenAI settings
    openai_api_key: Optional[str] = None

    # Azure OpenAI settings
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_deployment_name: Optional[str] = None

    # LLM configuration
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.7

    # MongoDB configuration
    mongodb_uri: str = "mongodb://localhost:27017/"
    mongodb_database: str = "verbalforge"

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/verbalforge.log"

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Create singleton instance
settings = Settings()
