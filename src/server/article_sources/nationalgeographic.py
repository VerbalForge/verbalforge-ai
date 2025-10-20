"""
National Geographic Article Source

Implementation of ArticleSource for National Geographic.
Fetches articles about nature, science, exploration, and culture.
"""

import requests
from bs4 import BeautifulSoup
import random
from typing import List, Dict, Optional
from datetime import datetime

from .base import ArticleSource


BASE_URL = "https://www.nationalgeographic.com"

# National Geographic sections (using full paths that work)
NATGEO_SECTIONS = [
    'science', 'animals', 'environment', 'history'
]


class NationalGeographicArticleSource(ArticleSource):
    """Article source implementation for National Geographic"""

    def __init__(self):
        super().__init__("National Geographic")
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
        Fetch random articles from National Geographic

        Args:
            difficulty: Number of articles to fetch
            count: Number of articles to fetch

        Returns:
            List of article dicts
        """
        articles = []
        
        self.logger.info(f"Fetching {count} articles from National Geographic")
        
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
        Fetch a random article from National Geographic

        Returns:
            Article dict or None
        """
        try:
            # Try multiple sections with shorter timeout
            sections_to_try = random.sample(NATGEO_SECTIONS, min(2, len(NATGEO_SECTIONS)))
            
            for section in sections_to_try:
                try:
                    url = f"{self.base_url}/{section}"
                    response = self.session.get(url, timeout=5)  # Shorter timeout
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Find article links - simplified approach
                    article_links = []
                    for link in soup.find_all('a', href=True, limit=100):  # Limit search
                        href = link.get('href', '')
                        # Look for article patterns
                        if '/article/' in href:
                            full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                            
                            # Skip recently fetched URLs and duplicates
                            if (full_url not in self._recent_urls and 
                                full_url not in article_links and
                                'pictures' not in full_url and 
                                'photos' not in full_url and
                                'video' not in full_url):
                                article_links.append(full_url)
                                
                                # Stop early if we have enough
                                if len(article_links) >= 15:
                                    break

                    if article_links:
                        # Try just first 5 random articles (faster)
                        random.shuffle(article_links)
                        for article_url in article_links[:5]:
                            result = self._fetch_article_content(article_url)
                            if result:
                                # Add to recent cache
                                self._recent_urls.append(article_url)
                                if len(self._recent_urls) > self._max_cache_size:
                                    self._recent_urls.pop(0)
                                
                                self.logger.info(f"✓ Fetched NatGeo article: {result['title']}")
                                return result
                                
                except Exception as e:
                    self.logger.debug(f"Error fetching from {section}: {e}")
                    continue

            return None

        except Exception as e:
            self.logger.debug(f"Error in _fetch_random_article: {e}")
            return None

    def _fetch_article_content(self, url: str) -> Optional[Dict[str, str]]:
        """
        Fetch the content of a specific National Geographic article

        Args:
            url: Article URL

        Returns:
            Article dict with content or None if failed
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract title
            title = None
            for selector in [
                ('h1', {'class': 'article__title'}),
                ('h1', {}),
                ('meta', {'property': 'og:title'}),
            ]:
                tag = soup.find(selector[0], selector[1])
                if tag:
                    if selector[0] == 'meta':
                        title = tag.get('content', '').strip()
                    else:
                        title = tag.get_text().strip()
                    if title:
                        break
            
            if not title:
                self.logger.debug(f"No title found at {url}")
                return None

            # Extract article content
            article_body = None
            for selector in [
                ('article', {}),
                ('div', {'class': 'article__body'}),
                ('div', {'class': 'body-text'}),
            ]:
                article_body = soup.find(selector[0], selector[1])
                if article_body:
                    break

            if not article_body:
                self.logger.debug(f"No article body found at {url}")
                return None

            # Extract paragraphs
            content = self.extract_paragraphs(article_body, min_length=50, max_paragraphs=5)

            if not content or len(content.strip()) < 100:
                self.logger.debug(f"Insufficient content extracted from {url}")
                return None

            # Truncate to reasonable length
            content = self.truncate_content(content, max_words=450, min_words=200)

            if not content:
                self.logger.debug(f"Content too short after truncation from {url}")
                return None

            return {
                'url': url,
                'title': title,
                'section': 'General',
                'content': content,
                'author': 'National Geographic',
                'source': self.source_name,
                'fetched_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.debug(f"Error fetching article content from {url}: {e}")
            return None
