"""
Base Article Source

Abstract base class for all article sources.
Defines the interface that all sources must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ArticleSource(ABC):
    """Abstract base class for article sources"""

    def __init__(self, source_name: str):
        """
        Initialize article source

        Args:
            source_name: Name of the source (e.g., "The Atlantic", "ScienceDaily")
        """
        self.source_name = source_name
        self.logger = logging.getLogger(f"{__name__}.{source_name}")

    @abstractmethod
    def fetch_articles(self, count: int = 3) -> List[Dict[str, str]]:
        """
        Fetch articles from the source

        This is the main public method that must be implemented by all sources.

        Args:
            count: Number of articles to fetch

        Returns:
            List of article dicts with keys: url, title, section, content, author, source, fetched_at
        """
        pass

    def format_for_rc_generation(self, article: Dict[str, str]) -> str:
        """
        Format article data into a topic instruction for RC generation

        Can be overridden for source-specific formatting, but provides
        a sensible default.

        Args:
            article: Article dict

        Returns:
            Formatted topic instruction string
        """
        topic_instruction = f"""
            Use the following article as the basis for creating the passage:
            **Source Article**:
            - Title: {article['title']}
            - Author: {article.get('author', 'Unknown')}
            - Source: {self.source_name}
            - URL: {article['url']}

            **Article Content**:
            {article['content']}

            **Instructions for passage creation**:
            - Adapt this article's content into a coherent GRE-style passage
            - Maintain the academic tone and key concepts from the source
            - Ensure the passage is self-contained and comprehensive
            - In the JSON response:
            * Set "source": "{self.source_name}"
            * Set "title": "{article['title']}" 
  """

        return topic_instruction

    @staticmethod
    def truncate_content(content: str, max_words: int = 350, min_words: int = 150) -> Optional[str]:
        """
        Truncate content to appropriate length

        Args:
            content: Full content text
            max_words: Maximum word count (default 350 to stay under 2000 char passage limit)
            min_words: Minimum word count for content to be valid

        Returns:
            Truncated content or None if too short
        """
        if len(content) < min_words:
            return None

        words = content.split()
        if len(words) > max_words:
            content = ' '.join(words[:max_words]) + '...'

        return content

    @staticmethod
    def extract_paragraphs(soup_element, min_length: int = 50, max_paragraphs: int = 5) -> str:
        """
        Extract and clean paragraphs from a BeautifulSoup element

        Args:
            soup_element: BeautifulSoup element containing article body
            min_length: Minimum paragraph length to include
            max_paragraphs: Maximum number of paragraphs to extract

        Returns:
            Joined paragraph text
        """
        paragraphs = soup_element.find_all('p')
        content_paragraphs = []

        for p in paragraphs:
            text = p.get_text().strip()
            # Filter out short paragraphs and common navigation/promotional elements
            if (len(text) > min_length and 
                not text.startswith(('Sign up', 'Subscribe', 'Read more', 'Advertisement'))):
                content_paragraphs.append(text)

        return ' '.join(content_paragraphs[:max_paragraphs])
