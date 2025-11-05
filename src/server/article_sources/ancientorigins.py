"""
Ancient Origins Article Source

Implementation of ArticleSource for Ancient Origins.
Fetches articles about ancient civilizations, archaeology, and history.
"""

import requests
from bs4 import BeautifulSoup
import random
from typing import List, Dict, Optional
from datetime import datetime

from .base import ArticleSource


BASE_URL = "https://www.ancient-origins.net"

# Ancient Origins sections/categories
ANCIENT_ORIGINS_SECTIONS = [
    'ancient-places',
    'unexplained-phenomena',
    'artifacts-other-artifacts',
    'human-origins',
    'myths-legends',
    'ancient-technology',
    'history-famous-people',
]


class AncientOriginsArticleSource(ArticleSource):
    """Article source implementation for Ancient Origins"""

    def __init__(self):
        super().__init__("Ancient Origins")
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; VerbalForge/1.0; +https://verbalforge.ai)'
        })
        # Cache to avoid recent duplicates
        self._recent_urls = []
        self._max_cache_size = 50

    def fetch_articles(
        self, count: int = 3
    ) -> List[Dict[str, str]]:
        """
        Fetch random articles from Ancient Origins

        Args:
            count: Number of articles to fetch

        Returns:
            List of article dicts
        """
        articles = []
        
        self.logger.info(f"Fetching {count} articles from Ancient Origins")
        
        # Try multiple times to get enough articles
        for _ in range(count * 3):
            article = self._fetch_random_article()
            if article:
                # Avoid duplicates
                if not any(a['url'] == article['url'] for a in articles):
                    articles.append(article)
                    if len(articles) >= count:
                        break
        
        self.logger.info(f"Fetched {len(articles)}/{count} articles from {self.source_name}")
        return articles

    def _fetch_random_article(self) -> Optional[Dict[str, str]]:
        """
        Fetch a random article from Ancient Origins

        Returns:
            Article dict or None
        """
        try:
            # Randomly select section
            section = random.choice(ANCIENT_ORIGINS_SECTIONS)
            url = f"{self.base_url}/{section}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find article links
            article_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                # Ancient Origins article URLs typically have sections in them
                if any(sec in href for sec in ANCIENT_ORIGINS_SECTIONS):
                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    
                    # Skip recently fetched URLs
                    if full_url not in self._recent_urls and full_url not in article_links:
                        article_links.append(full_url)

            if not article_links:
                return None

            # Select random article
            article_url = random.choice(article_links)

            # Fetch full article
            article_response = self.session.get(article_url, timeout=10)
            article_response.raise_for_status()

            article_soup = BeautifulSoup(article_response.text, 'html.parser')

            # Extract title
            title = None
            title_tag = article_soup.find('h1')
            if title_tag:
                title = title_tag.get_text(strip=True)

            # Extract content
            content = self._extract_content(article_soup)

            if not title or not content:
                return None

            # Update recent URLs cache
            self._recent_urls.append(article_url)
            if len(self._recent_urls) > self._max_cache_size:
                self._recent_urls.pop(0)

            return {
                'title': title,
                'content': content,
                'url': article_url,
                'source': self.source_name,
                'fetched_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to fetch article: {e}")
            return None

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """
        Extract article content from Beautiful Soup object

        Args:
            soup: BeautifulSoup object

        Returns:
            Article content as string
        """
        content_parts = []

        # Try to find main article content
        article_body = soup.find('div', class_='field-name-body') or \
                      soup.find('div', class_='article-body') or \
                      soup.find('article')

        if article_body:
            # Get all paragraphs
            paragraphs = article_body.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                # Filter out very short paragraphs
                if len(text) > 50:
                    content_parts.append(text)

        content = ' '.join(content_parts)
        
        # Validate minimum length
        if len(content) < 200:
            return ''

        return content
