"""
ScienceDaily Article Source

Implementation of ArticleSource for ScienceDaily.
Fetches science news and research summaries.
"""

import requests
from bs4 import BeautifulSoup
import random
from typing import List, Dict, Optional
from datetime import datetime

from .base import ArticleSource


BASE_URL = "https://www.sciencedaily.com"

# Science topics available on ScienceDaily
SCIENCE_TOPICS = [
    'space', 'matter_energy', 'computers_math', 'plants_animals',
    'earth_climate', 'fossils_ruins', 'health_medicine', 'mind_brain',
]


class ScienceDailyArticleSource(ArticleSource):
    """Article source implementation for ScienceDaily"""

    def __init__(self):
        super().__init__("ScienceDaily")
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
        Fetch random science articles from ScienceDaily

        Args:
            difficulty: Number of articles to fetch
            count: Number of articles to fetch

        Returns:
            List of article dicts
        """
        articles = []
        
        self.logger.info(f"Fetching {count} articles from ScienceDaily")
        
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
        Fetch a random article from ScienceDaily

        Returns:
            Article dict or None
        """
        try:
            # Randomly select topic
            topic = random.choice(SCIENCE_TOPICS)
            url = f"{self.base_url}/news/{topic}/"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find article links (ScienceDaily uses specific structure)
            article_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/releases/' in href:
                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    
                    # Skip recently fetched URLs
                    if full_url not in self._recent_urls and full_url not in article_links:
                        article_links.append(full_url)

            if not article_links:
                return None

            # Try random articles
            random.shuffle(article_links)
            for article_url in article_links[:10]:
                result = self._fetch_article_content(article_url)
                if result:
                    # Add to recent cache
                    self._recent_urls.append(article_url)
                    if len(self._recent_urls) > self._max_cache_size:
                        self._recent_urls.pop(0)
                    
                    self.logger.info(f"✓ Fetched ScienceDaily article: {result['title']}")
                    return result

            return None

        except Exception as e:
            self.logger.debug(f"Error in _fetch_random_article: {e}")
            return None

    def _fetch_article_content(self, url: str) -> Optional[Dict[str, str]]:
        """
        Fetch the content of a specific ScienceDaily article

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
            title_tag = soup.find('h1', {'id': 'headline'})
            if not title_tag:
                title_tag = soup.find('h1')
            
            if not title_tag:
                self.logger.debug(f"No title found at {url}")
                return None
            
            title = title_tag.get_text().strip()

            # Extract article content
            article_body = soup.find('div', {'id': 'story_text'})
            if not article_body:
                article_body = soup.find('div', {'class': 'story-text'})
            
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

            # ScienceDaily articles are all academic/scientific
            return {
                'url': url,
                'title': title,
                'section': 'Science',
                'content': content,
                'author': 'ScienceDaily',
                'source': self.source_name,
                'fetched_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.debug(f"Error fetching article content from {url}: {e}")
            return None
