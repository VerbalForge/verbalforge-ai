"""
Settings Management

Loads and manages environment-based configuration settings.
"""

import sys
from pathlib import Path

# Ensure verbalforge package is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.utils.settings import settings as core_settings


def get_settings():
    """Get application settings from core configuration"""
    return core_settings


# Export for convenience
settings = get_settings()
