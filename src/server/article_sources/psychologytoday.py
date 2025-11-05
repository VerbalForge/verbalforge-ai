"""
Psychology Today Article Source

Implementation of ArticleSource for Psychology Today.
Fetches articles about psychology, mental health, and behavioral science.
"""

import requests
from bs4 import BeautifulSoup
import random
from typing import List, Dict, Optional
from datetime import datetime

from .base import ArticleSource


BASE_URL = "https://www.psychologytoday.com"

# We'll fetch from the main blog listing page
BLOG_URL = f"{BASE_URL}/us"


class PsychologyTodayArticleSource(ArticleSource):
    """Article source implementation for Psychology Today"""

    def __init__(self):
        super().__init__("Psychology Today")
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        # Cache to avoid recent duplicates
        self._recent_urls = []
        self._max_cache_size = 50

    def fetch_articles(
        self, count: int = 3
    ) -> List[Dict[str, str]]:
        """
        Fetch random articles from Psychology Today

        Args:
            count: Number of articles to fetch

        Returns:
            List of article dicts
        """
        articles = []
        
        self.logger.info(f"Fetching {count} articles from Psychology Today")
        
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
        Fetch a random article from Psychology Today

        Returns:
            Article dict or None
        """
        try:
            # Fetch the main US homepage which has recent blog articles
            url = BLOG_URL
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find article links
            # Psychology Today blog URLs: /us/blog/{blog-name}/{YYYYMM}/{article-slug}
            article_links = []
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                
                # Look for blog post URLs with the pattern /us/blog/*
                if '/us/blog/' in href:
                    # Must have at least 5 path components: /, us, blog, blog-name, article
                    if href.count('/') >= 5:
                        full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                        
                        # Skip recently fetched URLs and non-article pages
                        if (full_url not in self._recent_urls and 
                            full_url not in article_links and
                            not any(skip in full_url for skip in ['/about', '/contact', '/author', '/tag', '/archive'])):
                            article_links.append(full_url)

            if not article_links:
                self.logger.warning("No article links found on Psychology Today homepage")
                return None

            # Select random article
            article_url = random.choice(article_links)

            # Fetch full article
            article_response = self.session.get(article_url, timeout=10)
            article_response.raise_for_status()

            article_soup = BeautifulSoup(article_response.text, 'html.parser')

            # Extract title
            title = None
            # Try multiple title selectors
            title_tag = (article_soup.find('h1', class_='blog-entry-title') or 
                        article_soup.find('h1', class_='title') or
                        article_soup.find('h1') or 
                        article_soup.find('meta', property='og:title'))
            
            if title_tag:
                if title_tag.name == 'meta':
                    title = title_tag.get('content', '').strip()
                else:
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
        # Psychology Today uses various content containers
        article_body = (soup.find('div', class_='blog-entry-content') or
                       soup.find('div', class_='article-body') or
                       soup.find('div', class_='entry-content') or
                       soup.find('article') or
                       soup.find('div', {'itemprop': 'articleBody'}))

        if article_body:
            # Get all paragraphs
            paragraphs = article_body.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                # Filter out very short paragraphs, captions, and boilerplate
                if (len(text) > 50 and 
                    not text.startswith('Image:') and
                    not text.startswith('Photo:') and
                    'advertisement' not in text.lower()):
                    content_parts.append(text)

        content = ' '.join(content_parts)
        
        # Validate minimum length
        if len(content) < 200:
            return ''

        return content
