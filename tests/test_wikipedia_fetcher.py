"""
Unit tests for WikipediaFetcher module.

Tests cover:
- Article fetching
- Key fact extraction
- Error handling for missing articles
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestArticleData:
    """Tests for ArticleData dataclass."""
    
    def test_get_content_for_script_basic(self):
        """Test basic content extraction."""
        from src.wikipedia_fetcher import ArticleData
        
        article = ArticleData(
            title="Test Article",
            summary="This is a test summary with important information.",
            full_text="Full text content here.",
            key_facts=["Fact 1", "Fact 2", "Fact 3"],
            categories=["Category1"],
            url="https://en.wikipedia.org/wiki/Test"
        )
        
        content = article.get_content_for_script(max_words=100)
        
        assert "test summary" in content.lower()
        assert "Fact 1" in content
        assert "Fact 2" in content
    
    def test_get_content_truncation(self):
        """Test content truncation for long articles."""
        from src.wikipedia_fetcher import ArticleData
        
        # Create article with very long summary
        long_summary = " ".join(["word"] * 1000)
        
        article = ArticleData(
            title="Long Article",
            summary=long_summary,
            full_text="",
            key_facts=[],
            categories=[],
            url=""
        )
        
        content = article.get_content_for_script(max_words=50)
        words = content.split()
        
        # Should be truncated with ellipsis
        assert len(words) <= 55  # 50 + some buffer for "..."
        assert content.endswith("...")


class TestWikipediaFetcher:
    """Tests for WikipediaFetcher class."""
    
    @patch('src.wikipedia_fetcher.wikipediaapi')
    def test_fetch_success(self, mock_wiki):
        """Test successful article fetching."""
        from src.wikipedia_fetcher import WikipediaFetcher
        
        # Mock Wikipedia page
        mock_page = MagicMock()
        mock_page.exists.return_value = True
        mock_page.title = "Mumbai Indians"
        mock_page.summary = "Mumbai Indians is an IPL cricket team."
        mock_page.text = "Full article text about Mumbai Indians."
        mock_page.fullurl = "https://en.wikipedia.org/wiki/Mumbai_Indians"
        mock_page.categories = {}
        
        mock_wiki_instance = MagicMock()
        mock_wiki_instance.page.return_value = mock_page
        mock_wiki.Wikipedia.return_value = mock_wiki_instance
        
        fetcher = WikipediaFetcher()
        article = fetcher.fetch("Mumbai Indians")
        
        assert article.title == "Mumbai Indians"
        assert "IPL" in article.summary
    
    @patch('src.wikipedia_fetcher.wikipediaapi')
    def test_fetch_not_found(self, mock_wiki):
        """Test handling of non-existent articles."""
        from src.wikipedia_fetcher import WikipediaFetcher
        
        # Mock non-existent page
        mock_page = MagicMock()
        mock_page.exists.return_value = False
        
        mock_wiki_instance = MagicMock()
        mock_wiki_instance.page.return_value = mock_page
        mock_wiki.Wikipedia.return_value = mock_wiki_instance
        
        fetcher = WikipediaFetcher()
        
        with pytest.raises(ValueError) as excinfo:
            fetcher.fetch("NonExistentArticle12345")
        
        assert "not found" in str(excinfo.value).lower()
    
    def test_is_key_fact_with_numbers(self):
        """Test key fact detection with numbers."""
        from src.wikipedia_fetcher import WikipediaFetcher
        
        fetcher = WikipediaFetcher.__new__(WikipediaFetcher)
        
        # Sentence with year
        assert fetcher._is_key_fact("The team was founded in 2008.")
        
        # Sentence with percentage
        assert fetcher._is_key_fact("The success rate is 75%.")
        
        # Sentence with "million"
        assert fetcher._is_key_fact("The stadium holds 3 million fans annually.")
    
    def test_is_key_fact_with_keywords(self):
        """Test key fact detection with keywords."""
        from src.wikipedia_fetcher import WikipediaFetcher
        
        fetcher = WikipediaFetcher.__new__(WikipediaFetcher)
        
        # Founded keyword
        assert fetcher._is_key_fact("The organization was founded by pioneers.")
        
        # Won keyword
        assert fetcher._is_key_fact("They won the championship decisively.")
        
        # First keyword
        assert fetcher._is_key_fact("It was the first of its kind in India.")
    
    def test_extract_key_facts(self):
        """Test extraction of key facts from text."""
        from src.wikipedia_fetcher import WikipediaFetcher
        
        fetcher = WikipediaFetcher.__new__(WikipediaFetcher)
        
        text = """
        Mumbai Indians is a professional cricket team.
        
        The team was founded in 2008 by Mukesh Ambani.
        They have won 5 IPL titles since their inception.
        The home ground is Wankhede Stadium.
        """
        
        facts = fetcher._extract_key_facts(text, max_facts=3)
        
        assert len(facts) > 0
        assert len(facts) <= 3


class TestFetchArticleFunction:
    """Tests for the convenience fetch_article function."""
    
    @patch('src.wikipedia_fetcher.WikipediaFetcher')
    def test_fetch_article(self, mock_fetcher_class):
        """Test convenience function."""
        from src.wikipedia_fetcher import fetch_article, ArticleData
        
        mock_article = ArticleData(
            title="Test",
            summary="Summary",
            full_text="Text",
            key_facts=[],
            categories=[],
            url=""
        )
        
        mock_instance = MagicMock()
        mock_instance.fetch.return_value = mock_article
        mock_fetcher_class.return_value = mock_instance
        
        result = fetch_article("Test")
        
        assert result.title == "Test"
        mock_instance.fetch.assert_called_once_with("Test")


