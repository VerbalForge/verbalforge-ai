"""
Article Sources Package

Modular architecture for fetching articles from various sources for Reading Comprehension.

Available sources:
- The Atlantic: Long-form journalism and analysis
- ScienceDaily: Science news and research summaries
- Popular Science: Science and technology
- Ancient Origins: Archaeology, ancient civilizations, and history
- Psychology Today: Psychology, mental health, and behavioral science
"""

from .base import ArticleSource
from .atlantic import AtlanticArticleSource
from .sciencedaily import ScienceDailyArticleSource
from .nationalgeographic import NationalGeographicArticleSource
from .discover import DiscoverMagazineArticleSource
from .popularscience import PopularScienceArticleSource
from .ancientorigins import AncientOriginsArticleSource
from .discovery import DiscoveryArticleSource
from .psychologytoday import PsychologyTodayArticleSource
from .factory import ArticleSourceFactory

__all__ = [
    'ArticleSource',
    'AtlanticArticleSource',
    'ScienceDailyArticleSource',
    'NationalGeographicArticleSource',
    'DiscoverMagazineArticleSource',
    'PopularScienceArticleSource',
    'AncientOriginsArticleSource',
    'DiscoveryArticleSource',
    'PsychologyTodayArticleSource',
    'ArticleSourceFactory',
]
