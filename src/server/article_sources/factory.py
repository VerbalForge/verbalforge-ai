"""
Article Source Factory

Factory for creating and managing article source instances.
Makes it easy to add new sources and select sources dynamically.
"""

from typing import Dict, List, Optional
import logging

from .base import ArticleSource
from .atlantic import AtlanticArticleSource
from .sciencedaily import ScienceDailyArticleSource
from .nationalgeographic import NationalGeographicArticleSource
from .popularscience import PopularScienceArticleSource
from .ancientorigins import AncientOriginsArticleSource
from .psychologytoday import PsychologyTodayArticleSource

logger = logging.getLogger(__name__)


class ArticleSourceFactory:
    """Factory for creating and managing article sources"""

    # Source registry
    _sources = {
        'atlantic': AtlanticArticleSource,
        'sciencedaily': ScienceDailyArticleSource,
        'popularscience': PopularScienceArticleSource,
        'ancientorigins': AncientOriginsArticleSource,
        'psychologytoday': PsychologyTodayArticleSource,
        # 'discover': DiscoverMagazineArticleSource,  # Temporarily disabled - performance issues
        # 'nationalgeographic': NationalGeographicArticleSource,  # Temporarily disabled - needs optimization
    }
    
    # Weights for random selection (higher = more likely)
    # Scientific sources should be favored
    _weights = {
        'sciencedaily': 4,      # Highest weight - pure science
        'popularscience': 3,    # High weight - science/tech magazine
        'psychologytoday': 2,   # Medium weight - psychology/behavioral science
        'ancientorigins': 3,    # High weight - archaeology/history
        'atlantic': 1,          # Lower weight - general journalism (but filtered)
    }

    @classmethod
    def get_source(cls, source_name: str) -> Optional[ArticleSource]:
        """
        Get an article source instance by name

        Args:
            source_name: Name of the source (e.g., 'atlantic', 'newyorker')

        Returns:
            ArticleSource instance or None if not found
        """
        source_class = cls._sources.get(source_name.lower())
        if source_class:
            return source_class()
        else:
            logger.error(f"Unknown article source: {source_name}")
            return None

    @classmethod
    def get_available_sources(cls) -> List[str]:
        """
        Get list of available source names (excluding aliases)

        Returns:
            List of source names
        """
        # Filter out aliases
        return [name for name in cls._sources.keys() if name not in ['natgeo']]
    
    @classmethod
    def get_random_source(cls, exclude_aliases: bool = True) -> Optional[str]:
        """
        Get a weighted random source name
        
        Scientific sources are weighted higher than general journalism.

        Args:
            exclude_aliases: Whether to exclude alias names (default True)

        Returns:
            Source name or None if no sources available
        """
        import random
        
        available = cls.get_available_sources() if exclude_aliases else list(cls._sources.keys())
        if not available:
            return None
        
        # Create weighted list
        weighted_sources = []
        for source in available:
            weight = cls._weights.get(source, 1)
            weighted_sources.extend([source] * weight)
        
        return random.choice(weighted_sources) if weighted_sources else None

    @classmethod
    def register_source(cls, name: str, source_class: type):
        """
        Register a new article source

        This allows for dynamic registration of sources at runtime.

        Args:
            name: Name to register the source under
            source_class: ArticleSource subclass
        """
        if not issubclass(source_class, ArticleSource):
            raise ValueError(f"{source_class} must be a subclass of ArticleSource")
        
        cls._sources[name.lower()] = source_class
        logger.info(f"Registered article source: {name}")

    @classmethod
    def fetch_from_any_source(
        cls, difficulty: str, count: int = 1, preferred_sources: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        Fetch articles from any available source (with optional preferences)

        Args:
            difficulty: Difficulty level
            count: Number of articles to fetch
            preferred_sources: Optional list of source names to try first

        Returns:
            List of article dicts
        """
        import random

        sources_to_try = preferred_sources or cls.get_available_sources()
        articles = []

        # Shuffle to distribute load
        sources_order = sources_to_try.copy()
        random.shuffle(sources_order)

        for source_name in sources_order:
            try:
                source = cls.get_source(source_name)
                if not source:
                    continue

                fetched = source.fetch_articles_for_difficulty(difficulty, count - len(articles))
                articles.extend(fetched)

                if len(articles) >= count:
                    break

            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
                continue

        return articles[:count]
