"""
Wikipedia content fetcher for The Synthetic Radio Host.

Extracts and processes Wikipedia article content for script generation.
"""

import re
import ssl
import urllib.request
import urllib3
from dataclasses import dataclass
from typing import List, Optional
import logging

import requests

try:
    import wikipediaapi
except ImportError:
    wikipediaapi = None

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create unverified SSL context for environments with certificate issues
ssl._create_default_https_context = ssl._create_unverified_context

# Patch requests to disable SSL verification (for corporate proxy/firewall environments)
_original_request = requests.Session.request

def _patched_request(self, *args, **kwargs):
    """Patched request method that disables SSL verification."""
    kwargs['verify'] = False
    return _original_request(self, *args, **kwargs)

requests.Session.request = _patched_request

logger = logging.getLogger(__name__)


@dataclass
class ArticleData:
    """Structured Wikipedia article data."""
    
    title: str
    summary: str
    full_text: str
    key_facts: List[str]
    categories: List[str]
    url: str
    
    def get_content_for_script(self, max_words: int = 500) -> str:
        """
        Get optimized content for script generation.
        
        Args:
            max_words: Maximum words to include
            
        Returns:
            Processed content string
        """
        # Start with summary
        content = self.summary
        
        # Add key facts if space allows
        if self.key_facts:
            facts_text = "\n\nKey Facts:\n" + "\n".join(f"- {fact}" for fact in self.key_facts[:5])
            content += facts_text
        
        # Truncate to max words
        words = content.split()
        if len(words) > max_words:
            content = " ".join(words[:max_words]) + "..."
        
        return content


class WikipediaFetcher:
    """
    Fetches and processes Wikipedia articles.
    
    This class handles:
    - Article retrieval by topic
    - Content extraction and cleaning
    - Key fact identification
    - Disambiguation handling
    """
    
    def __init__(self, language: str = "en", user_agent: str = "SyntheticRadioHost/1.0"):
        """
        Initialize the Wikipedia fetcher.
        
        Args:
            language: Wikipedia language code (default: "en")
            user_agent: User agent string for API requests
        """
        if wikipediaapi is None:
            raise ImportError(
                "wikipedia-api is required. Install with: pip install wikipedia-api"
            )
        
        self.wiki = wikipediaapi.Wikipedia(
            user_agent=user_agent,
            language=language,
            extract_format=wikipediaapi.ExtractFormat.WIKI
        )
        self.language = language
    
    def _extract_topic_from_url(self, url: str) -> str:
        """
        Extract topic name from Wikipedia URL.
        
        Args:
            url: Wikipedia URL (e.g., https://en.wikipedia.org/wiki/Mumbai_Indians)
            
        Returns:
            Topic name extracted from URL
        """
        import urllib.parse
        
        # Handle different Wikipedia URL formats
        # https://en.wikipedia.org/wiki/Mumbai_Indians
        # https://en.m.wikipedia.org/wiki/Mumbai_Indians
        
        if '/wiki/' in url:
            # Extract the part after /wiki/
            topic = url.split('/wiki/')[-1]
            # URL decode (convert %20 to spaces, etc.)
            topic = urllib.parse.unquote(topic)
            # Replace underscores with spaces
            topic = topic.replace('_', ' ')
            return topic
        
        raise ValueError(f"Invalid Wikipedia URL format: {url}")
    
    def _is_url(self, input_str: str) -> bool:
        """Check if input is a URL."""
        return input_str.startswith('http://') or input_str.startswith('https://')
    
    def fetch(self, topic_or_url: str) -> ArticleData:
        """
        Fetch Wikipedia article for a given topic or URL.
        
        Args:
            topic_or_url: Either a topic name (e.g., "Mumbai Indians") 
                         or a Wikipedia URL (e.g., https://en.wikipedia.org/wiki/Mumbai_Indians)
            
        Returns:
            ArticleData object with extracted content
            
        Raises:
            ValueError: If article not found or disambiguation needed
        """
        # Check if input is a URL
        if self._is_url(topic_or_url):
            topic = self._extract_topic_from_url(topic_or_url)
            logger.info(f"Extracted topic from URL: {topic}")
        else:
            topic = topic_or_url
        
        logger.info(f"Fetching Wikipedia article: {topic}")
        
        # Get the page
        page = self.wiki.page(topic)
        
        # Check if page exists
        if not page.exists():
            raise ValueError(f"Wikipedia article not found: {topic}")
        
        # Extract content
        full_text = page.text
        summary = page.summary
        
        # Extract key facts from the first few paragraphs
        key_facts = self._extract_key_facts(full_text)
        
        # Get categories
        categories = self._extract_categories(page)
        
        # Build article data
        article = ArticleData(
            title=page.title,
            summary=summary,
            full_text=full_text,
            key_facts=key_facts,
            categories=categories,
            url=page.fullurl
        )
        
        logger.info(f"Successfully fetched: {article.title}")
        return article
    
    def _extract_key_facts(self, text: str, max_facts: int = 10) -> List[str]:
        """
        Extract key facts from article text.
        
        Uses heuristics to identify important statements:
        - Sentences with numbers/dates
        - Sentences with "is", "was", "are" (definitional)
        - First sentence of paragraphs
        
        Args:
            text: Full article text
            max_facts: Maximum number of facts to extract
            
        Returns:
            List of key fact strings
        """
        facts = []
        
        # Split into paragraphs
        paragraphs = text.split("\n\n")
        
        for para in paragraphs[:10]:  # Focus on first 10 paragraphs
            # Skip very short paragraphs
            if len(para) < 50:
                continue
            
            # Split into sentences
            sentences = re.split(r'(?<=[.!?])\s+', para)
            
            for sentence in sentences:
                # Clean the sentence
                sentence = sentence.strip()
                
                # Skip if too short or too long
                if len(sentence) < 30 or len(sentence) > 200:
                    continue
                
                # Check if it contains interesting content
                if self._is_key_fact(sentence):
                    facts.append(sentence)
                    if len(facts) >= max_facts:
                        return facts
        
        return facts
    
    def _is_key_fact(self, sentence: str) -> bool:
        """
        Determine if a sentence is a key fact.
        
        Args:
            sentence: Sentence to evaluate
            
        Returns:
            True if sentence appears to be a key fact
        """
        # Contains numbers (dates, statistics)
        if re.search(r'\d{4}|\d+%|\d+\s*(million|billion|crore|lakh)', sentence, re.I):
            return True
        
        # Definitional sentences
        if re.match(r'^[A-Z][^.]+\s+(is|was|are|were)\s+', sentence):
            return True
        
        # Contains important keywords
        keywords = ['founded', 'established', 'won', 'achieved', 'first', 'largest', 'famous']
        if any(kw in sentence.lower() for kw in keywords):
            return True
        
        return False
    
    def _extract_categories(self, page) -> List[str]:
        """
        Extract relevant categories from a Wikipedia page.
        
        Args:
            page: Wikipedia page object
            
        Returns:
            List of category names
        """
        categories = []
        
        try:
            for cat in page.categories.keys():
                # Skip hidden/maintenance categories
                if 'Hidden' in cat or 'Articles' in cat or 'Pages' in cat:
                    continue
                
                # Clean category name
                cat_name = cat.replace('Category:', '')
                categories.append(cat_name)
                
                if len(categories) >= 5:
                    break
        except Exception as e:
            logger.warning(f"Could not extract categories: {e}")
        
        return categories
    
    def search(self, query: str, limit: int = 5) -> List[str]:
        """
        Search for Wikipedia articles matching a query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching article titles
        """
        # Note: wikipedia-api doesn't have search, using page suggestions
        # In production, you might use the Wikipedia Search API directly
        page = self.wiki.page(query)
        
        if page.exists():
            return [page.title]
        
        # Return empty if not found
        return []


def fetch_article(topic: str) -> ArticleData:
    """
    Convenience function to fetch a Wikipedia article.
    
    Args:
        topic: Article topic to fetch
        
    Returns:
        ArticleData object
    """
    fetcher = WikipediaFetcher()
    return fetcher.fetch(topic)


