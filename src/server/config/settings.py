"""
Settings Management

Loads and manages environment-based configuration settings.
"""

import sys
from pathlib import Path

# Add project root to path to enable absolute imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.utils.settings import settings as core_settings


def get_settings():
    """Get application settings from core configuration"""
    return core_settings


# Export for convenience
settings = get_settings()
