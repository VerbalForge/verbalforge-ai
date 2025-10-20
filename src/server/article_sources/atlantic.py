"""
Atlantic Article Source

Implementation of ArticleSource for The Atlantic magazine.
Fetches random articles from the latest page.
"""

import requests
from bs4 import BeautifulSoup
import random
from typing import List, Dict, Optional
from datetime import datetime

from .base import ArticleSource


BASE_URL = "https://www.theatlantic.com"

# Preferred topics - articles matching these keywords get priority
PREFERRED_TOPICS = [
    # Sciences (expanded)
    'science', 'scientific', 'biology', 'biological', 'physics', 'physical', 
    'chemistry', 'chemical', 'research', 'study', 'studies', 'experiment',
    'genetics', 'genetic', 'neuroscience', 'molecular', 'cellular', 'organism',
    'species', 'evolution', 'evolutionary', 'ecology', 'ecological', 'climate',
    'medicine', 'medical', 'disease', 'pandemic', 'virus', 'bacteria',
    'technology', 'engineering', 'innovation', 'discovery', 'invention',
    # Astronomy & Space
    'astronomy', 'astronomical', 'space', 'planet', 'planetary', 'star', 'stellar',
    'galaxy', 'galaxies', 'universe', 'cosmic', 'cosmology', 'telescope', 'nasa',
    'solar system', 'exoplanet', 'black hole', 'nebula', 'asteroid', 'comet',
    # Economics
    'economy', 'economics', 'economic', 'market', 'markets', 'finance', 'financial',
    'industry', 'industrial', 'trade', 'commerce', 'capitalism', 'labor', 'employment',
    # US History
    'history', 'historical', 'american history', 'civil war', 'revolution', 'colonial',
    'century', 'era', 'period', 'founding', 'constitution', 'amendment', 'reconstruction',
    # Psychology
    'psychology', 'psychological', 'mental', 'cognitive', 'cognition', 'behavior', 
    'behavioral', 'brain', 'mind', 'consciousness', 'memory', 'perception', 'emotion',
    # Sociology & Anthropology
    'sociology', 'sociological', 'society', 'societies', 'social structure', 
    'anthropology', 'anthropological', 'human evolution', 'archaeology', 'archaeological',
    'ancient', 'civilization', 'culture', 'cultural anthropology', 'ethnography'
]

# Non-academic indicators - filter out news/opinion/entertainment articles
NON_ACADEMIC_INDICATORS = [
    # Current events/news commentary (not informational)
    'trump', 'biden', 'israel', 'hamas', 'ukraine', 'russia', 'putin',
    'fentanyl', 'border', 'immigration', 'election', 'political',
    # Opinion/personal narratives
    'i watched', 'i don\'t want', 'my experience', 'what i learned',
    # Casual/entertainment
    'lamentations', 'fan', 'fans', 'burning man', 'terminally online', 'stand-up',
    # Lists and recommendations
    'books to read', 'must read', 'best of', 'top 10', 'you should',
    # Very short opinion pieces
    'hot take', 'rant', 'confession',
    # Pop culture fluff
    'celebrity', 'gossip', 'viral',
    # Current affairs/policy debates (too newsy)
    'can\'t go on like this', 'doesn\'t understand', 'pushed to', 
    'just the beginning', 'doesn\'t come through',
]


class AtlanticArticleSource(ArticleSource):
    """Article source implementation for The Atlantic"""

    def __init__(self):
        super().__init__("The Atlantic")
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; VerbalForge/1.0; +https://verbalforge.ai)'
        })
        # Cache to avoid recent duplicates (keeps last 50 URLs)
        self._recent_urls = []
        self._max_cache_size = 50

    def fetch_articles(self, count: int = 3) -> List[Dict[str, str]]:
        """
        Fetch random articles from The Atlantic

        Args:
            count: Number of articles to fetch

        Returns:
            List of article dicts
        """
        articles = []
        
        self.logger.info(f"Fetching {count} articles from The Atlantic")
        
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
        Fetch a random article from The Atlantic.
        Prioritizes articles matching preferred topics.
        Avoids recently fetched URLs for better diversity.

        Returns:
            Article dict or None
        """
        try:
            # Try multiple pages for better diversity
            # Prioritize sections most likely to have informational/scientific content
            priority_pages = [
                f"{self.base_url}/science/",
                f"{self.base_url}/health/",
                f"{self.base_url}/planet/",
                f"{self.base_url}/technology/",
            ]
            
            secondary_pages = [
                f"{self.base_url}/ideas/",
                f"{self.base_url}/books/",
                f"{self.base_url}/culture/",
                f"{self.base_url}/global/",
            ]
            
            # Shuffle each group separately, then combine with priority first
            random.shuffle(priority_pages)
            random.shuffle(secondary_pages)
            pages_to_try = priority_pages + secondary_pages
            
            for url in pages_to_try:
                try:
                    response = self.session.get(url, timeout=10)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Find all article links
                    article_links = soup.find_all('a', href=True)
                    preferred_articles = []
                    other_articles = []

                    for link in article_links:
                        href = link.get('href', '')
                        
                        # Check if it's an article URL
                        if '/archive/' in href:
                            full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                            
                            # Skip recently fetched URLs
                            if full_url in self._recent_urls:
                                continue
                            
                            # Get article text for keyword matching
                            link_text = link.get_text().lower()
                            
                            # Check if article matches preferred topics
                            matches_preferred = any(keyword in link_text or keyword in full_url.lower() 
                                                   for keyword in PREFERRED_TOPICS)
                            
                            if matches_preferred:
                                if full_url not in preferred_articles:
                                    preferred_articles.append(full_url)
                            else:
                                if full_url not in other_articles:
                                    other_articles.append(full_url)

                    # Prioritize preferred articles
                    all_articles = []
                    if preferred_articles:
                        random.shuffle(preferred_articles)
                        all_articles.extend(preferred_articles)
                        self.logger.info(f"Found {len(preferred_articles)} preferred topic articles (sciences, astronomy, economics, history, psychology, sociology)")
                    
                    if other_articles:
                        random.shuffle(other_articles)
                        all_articles.extend(other_articles)
                        self.logger.debug(f"Found {len(other_articles)} other articles")
                    
                    if all_articles:
                        # Try articles until one works
                        for article_url in all_articles[:20]:  # Try more articles
                            result = self._fetch_article_content(article_url)
                            if result:
                                # Add to recent cache
                                self._recent_urls.append(article_url)
                                if len(self._recent_urls) > self._max_cache_size:
                                    self._recent_urls.pop(0)
                                
                                # Log if we got a preferred topic
                                is_preferred = article_url in preferred_articles
                                if is_preferred:
                                    self.logger.info(f"✓ Fetched preferred topic article: {result['title']}")
                                return result

                except Exception as e:
                    self.logger.debug(f"Error fetching from {url}: {e}")
                    continue

            return None

        except Exception as e:
            self.logger.debug(f"Error in _fetch_random_article: {e}")
            return None

    def _fetch_article_content(self, url: str) -> Optional[Dict[str, str]]:
        """
        Fetch the content of a specific Atlantic article

        Args:
            url: Article URL

        Returns:
            Article dict with content or None if failed
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract title - try multiple selectors
            title = None
            for selector in [
                ('h1', {'class': 'article-title'}),
                ('h1', {'data-testid': 'headline'}),
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

            # Extract author - try multiple patterns
            author = "The Atlantic"
            for selector in [
                ('a', {'rel': 'author'}),
                ('span', {'class': 'author'}),
                ('div', {'class': 'author-name'}),
                ('meta', {'name': 'author'}),
            ]:
                tag = soup.find(selector[0], selector[1])
                if tag:
                    if selector[0] == 'meta':
                        author = tag.get('content', '').strip()
                    else:
                        author = tag.get_text().strip()
                    if author and author != "The Atlantic":
                        break

            # Extract article content - try multiple selectors
            article_body = None
            for selector in [
                ('article', {}),
                ('div', {'class': 'article-body'}),
                ('div', {'class': 'l-article__body'}),
                ('div', {'data-testid': 'article-content'}),
                ('section', {'class': 'article-content'}),
            ]:
                article_body = soup.find(selector[0], selector[1])
                if article_body:
                    break

            if not article_body:
                self.logger.debug(f"No article body found at {url}")
                return None

            # Extract and clean paragraphs
            content = self.extract_paragraphs(article_body, min_length=50, max_paragraphs=5)

            if not content or len(content.strip()) < 100:
                self.logger.debug(f"Insufficient content extracted from {url}")
                return None

            # Truncate to reasonable length
            content = self.truncate_content(content, max_words=350, min_words=150)

            if not content:
                self.logger.debug(f"Content too short after truncation from {url}")
                return None

            # Validate academic quality
            if not self._is_academically_appropriate(title, content):
                self.logger.debug(f"Article filtered out (not academically appropriate): {title}")
                return None

            return {
                'url': url,
                'title': title,
                'section': 'General',  # No section-based categorization
                'content': content,
                'author': author,
                'source': self.source_name,
                'fetched_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.debug(f"Error fetching article content from {url}: {e}")
            return None

    def _is_academically_appropriate(self, title: str, content: str) -> bool:
        """
        Check if article is academically appropriate for GRE passages.
        
        GRE passages are informational, analytical, and explanatory - not news commentary
        or opinion pieces about current events.
        
        Filters out:
        - News articles and current event commentary
        - Personal narratives and opinion pieces
        - Casual entertainment pieces
        - Simple listicles
        - Pop culture content
        
        Args:
            title: Article title
            content: Article content
            
        Returns:
            True if appropriate, False otherwise
        """
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Filter out non-academic titles
        for indicator in NON_ACADEMIC_INDICATORS:
            if indicator in title_lower:
                return False
        
        # Filter out very short titles (single words) - likely not substantive
        if len(title.split()) <= 1:
            return False
        
        # Check content length - must be substantial
        words = content.split()
        if len(words) < 150:
            return False
        
        # Calculate average word length (academic articles use more complex vocabulary)
        avg_word_length = sum(len(word.strip('.,!?;:')) for word in words[:100]) / min(100, len(words))
        
        # Reject articles with very simple vocabulary (avg word length < 4.2)
        if avg_word_length < 4.2:
            return False
        
        # Check for informational/analytical content markers (not news/opinion)
        informational_markers = [
            'research', 'study', 'studies', 'scientists', 'researchers', 'scholars',
            'evidence', 'data', 'findings', 'analysis', 'examined', 'investigated',
            'discovered', 'theory', 'hypothesis', 'experiment', 'observation',
            'according to', 'suggests', 'indicates', 'demonstrates', 'reveals',
            'phenomenon', 'process', 'mechanism', 'system', 'structure', 'function',
            'century', 'historical', 'evolution', 'development', 'origins',
            'understanding', 'explain', 'explains', 'explanation', 'explore',
            'nature', 'natural', 'scientific', 'species', 'human', 'world'
        ]
        
        # Count informational markers in first 1000 characters
        marker_count = sum(1 for marker in informational_markers 
                          if marker in content_lower[:1000])
        
        # Require at least 1 informational marker (very relaxed)
        # Most articles should pass this - the real filtering is done by title/opinion checks
        if marker_count < 1:
            return False
        
        # Reject if it has too many opinion/news indicators
        news_opinion_indicators = [
            'should', 'must', 'need to', 'have to', 'we need', 'we must',
            'crisis', 'disaster', 'controversial', 'debate', 'argues that',
            'critics say', 'supporters claim'
        ]
        
        opinion_count = sum(1 for indicator in news_opinion_indicators 
                           if indicator in content_lower[:1000])
        
        # Reject if too opinion-heavy (more than 3 opinion markers, relaxed from 2)
        if opinion_count > 3:
            return False
        
        return True

