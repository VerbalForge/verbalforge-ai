"""
Article Sources Package

Modular architecture for fetching articles from various sources for Reading Comprehension.

Available sources:
- The Atlantic: Long-form journalism and analysis
- ScienceDaily: Science news and research summaries
- Popular Science: Science and technology
"""

from .base import ArticleSource
from .atlantic import AtlanticArticleSource
from .sciencedaily import ScienceDailyArticleSource
from .nationalgeographic import NationalGeographicArticleSource
from .discover import DiscoverMagazineArticleSource
from .popularscience import PopularScienceArticleSource
from .factory import ArticleSourceFactory

__all__ = [
    'ArticleSource',
    'AtlanticArticleSource',
    'ScienceDailyArticleSource',
    'NationalGeographicArticleSource',
    'DiscoverMagazineArticleSource',
    'PopularScienceArticleSource',
    'ArticleSourceFactory',
]
