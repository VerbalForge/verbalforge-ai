"""
Popular Science Article Source

Implementation of ArticleSource for Popular Science.
Fetches science and technology articles.
"""

import requests
from bs4 import BeautifulSoup
import random
from typing import List, Dict, Optional
from datetime import datetime

from .base import ArticleSource


BASE_URL = "https://www.popsci.com"

# Popular Science topics
POPSCI_TOPICS = [
    'science', 'technology', 'space', 'health', 'environment', 'diy'
]


class PopularScienceArticleSource(ArticleSource):
    """Article source implementation for Popular Science"""

    def __init__(self):
        super().__init__("Popular Science")
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; VerbalForge/1.0; +https://verbalforge.ai)'
        })
        # Cache to avoid recent duplicates
        self._recent_urls = []
        self._max_cache_size = 50

    def fetch_articles(self, count: int = 3) -> List[Dict[str, str]]:
        """
        Fetch random articles from Popular Science

        Args:
            count: Number of articles to fetch

        Returns:
            List of article dicts
        """
        articles = []
        
        self.logger.info(f"Fetching {count} articles from Popular Science")
        
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
        Fetch a random article from Popular Science

        Returns:
            Article dict or None
        """
        try:
            # Randomly select topic
            topic = random.choice(POPSCI_TOPICS)
            url = f"{self.base_url}/{topic}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find article links
            article_links = []
            for link in soup.find_all('a', href=True, limit=100):
                href = link.get('href', '')
                # PopSci article URLs
                if any(topic in href for topic in POPSCI_TOPICS) and '/article/' not in href:
                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    
                    # Skip recently fetched URLs
                    if (full_url not in self._recent_urls and 
                        full_url not in article_links and
                        full_url != url):  # Don't fetch the category page itself
                        article_links.append(full_url)
                        
                        if len(article_links) >= 15:
                            break

            if not article_links:
                return None

            # Try random articles
            random.shuffle(article_links)
            for article_url in article_links[:5]:
                result = self._fetch_article_content(article_url)
                if result:
                    # Add to recent cache
                    self._recent_urls.append(article_url)
                    if len(self._recent_urls) > self._max_cache_size:
                        self._recent_urls.pop(0)
                    
                    self.logger.info(f"✓ Fetched PopSci article: {result['title']}")
                    return result

            return None

        except Exception as e:
            self.logger.debug(f"Error in _fetch_random_article: {e}")
            return None

    def _fetch_article_content(self, url: str) -> Optional[Dict[str, str]]:
        """
        Fetch the content of a specific Popular Science article

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
                ('h1', {'class': 'article-title'}),
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
                ('div', {'class': 'article-body'}),
                ('div', {'class': 'content'}),
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
            content = self.truncate_content(content, max_words=350, min_words=150)

            if not content:
                self.logger.debug(f"Content too short after truncation from {url}")
                return None

            return {
                'url': url,
                'title': title,
                'section': 'Science',
                'content': content,
                'author': 'Popular Science',
                'source': self.source_name,
                'fetched_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.debug(f"Error fetching article content from {url}: {e}")
            return None
