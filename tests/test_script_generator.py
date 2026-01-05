"""
Unit tests for ScriptGenerator module.

Tests cover:
- Prompt generation
- Script generation with mocked LLM
- Script cleaning and validation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestPromptGeneration:
    """Tests for prompt generation functions."""
    
    def test_get_script_generation_prompt_structure(self):
        """Test that prompt contains all required elements."""
        from src.script_generator import get_script_generation_prompt
        from src.wikipedia_fetcher import ArticleData
        
        article = ArticleData(
            title="Mumbai Indians",
            summary="Mumbai Indians is an IPL team.",
            full_text="Full text here",
            key_facts=["Won 5 titles"],
            categories=["IPL teams"],
            url="https://example.com"
        )
        
        prompt = get_script_generation_prompt(
            article=article,
            host_1="RAVI",
            host_2="PRIYA",
            duration_minutes=2,
            word_count=300
        )
        
        # Check required elements are present
        assert "RAVI" in prompt
        assert "PRIYA" in prompt
        assert "Mumbai Indians" in prompt
        assert "300" in prompt  # word count
        assert "Hinglish" in prompt.upper() or "hinglish" in prompt.lower()
        
    def test_prompt_includes_fillers(self):
        """Test that prompt mentions required fillers."""
        from src.script_generator import get_script_generation_prompt
        from src.wikipedia_fetcher import ArticleData
        
        article = ArticleData(
            title="Test",
            summary="Test summary",
            full_text="",
            key_facts=[],
            categories=[],
            url=""
        )
        
        prompt = get_script_generation_prompt(
            article=article,
            host_1="RAVI",
            host_2="PRIYA",
            duration_minutes=2,
            word_count=300
        )
        
        # Check fillers are mentioned
        assert "umm" in prompt.lower()
        assert "achcha" in prompt.lower()
        assert "matlab" in prompt.lower()
    
    def test_prompt_includes_interruptions(self):
        """Test that prompt requests interruptions."""
        from src.script_generator import get_script_generation_prompt
        from src.wikipedia_fetcher import ArticleData
        
        article = ArticleData(
            title="Test",
            summary="Test",
            full_text="",
            key_facts=[],
            categories=[],
            url=""
        )
        
        prompt = get_script_generation_prompt(
            article=article,
            host_1="RAVI",
            host_2="PRIYA",
            duration_minutes=2,
            word_count=300
        )
        
        # Check for action markers mentioned in prompt
        assert "[laughs]" in prompt or "laughs" in prompt
        assert "[chuckles]" in prompt or "[excited]" in prompt or "chuckles" in prompt


class TestGeneratedScript:
    """Tests for GeneratedScript dataclass."""
    
    def test_str_method(self):
        """Test string representation."""
        from src.script_generator import GeneratedScript
        
        script = GeneratedScript(
            raw_text="RAVI: Hello yaar!\n\nPRIYA: Hi!",
            topic="Test Topic",
            host_1="RAVI",
            host_2="PRIYA",
            word_count=5
        )
        
        assert str(script) == "RAVI: Hello yaar!\n\nPRIYA: Hi!"


class TestScriptGenerator:
    """Tests for ScriptGenerator class."""
    
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        from src.script_generator import ScriptGenerator
        from src.config import Config
        
        config = Config()
        config.gemini_api_key = None
        
        generator = ScriptGenerator(config)
        
        # Should not raise until generate is called
        assert generator.config.gemini_api_key is None
    
    def test_clean_script_removes_markdown(self):
        """Test script cleaning removes markdown."""
        from src.script_generator import ScriptGenerator
        from src.config import Config
        
        config = Config()
        generator = ScriptGenerator(config)
        
        raw = "```\nRAVI: Hello!\n\nPRIYA: Hi!\n```"
        cleaned = generator._clean_script(raw)
        
        assert "```" not in cleaned
        assert "RAVI: Hello!" in cleaned
    
    def test_clean_script_removes_extra_whitespace(self):
        """Test script cleaning removes extra whitespace."""
        from src.script_generator import ScriptGenerator
        from src.config import Config
        
        config = Config()
        generator = ScriptGenerator(config)
        
        raw = "\n\n\nRAVI: Hello!\n\n\n\n\nPRIYA: Hi!\n\n\n"
        cleaned = generator._clean_script(raw)
        
        # Should have normalized whitespace
        assert cleaned.startswith("RAVI")
        assert "\n\n\n" not in cleaned
    
    @patch('src.script_generator.ScriptGenerator._call_llm')
    def test_generate_calls_llm(self, mock_call_llm):
        """Test that generate method calls LLM."""
        from src.script_generator import ScriptGenerator
        from src.config import Config
        from src.wikipedia_fetcher import ArticleData
        
        mock_call_llm.return_value = "RAVI: Test dialogue\n\nPRIYA: Response"
        
        config = Config()
        generator = ScriptGenerator(config)
        
        article = ArticleData(
            title="Test",
            summary="Test summary",
            full_text="",
            key_facts=[],
            categories=[],
            url=""
        )
        
        script = generator.generate(article, duration_minutes=2)
        
        mock_call_llm.assert_called_once()
        assert script.topic == "Test"
        assert "RAVI" in script.raw_text


class TestSystemPrompt:
    """Tests for the system prompt."""
    
    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        from src.script_generator import SYSTEM_PROMPT
        
        assert len(SYSTEM_PROMPT) > 100
        assert "Hinglish" in SYSTEM_PROMPT or "hinglish" in SYSTEM_PROMPT.lower()
    
    def test_system_prompt_has_examples(self):
        """Test that system prompt includes examples."""
        from src.script_generator import SYSTEM_PROMPT
        
        # Should have Hindi words in examples
        assert "yaar" in SYSTEM_PROMPT.lower()
        assert "achcha" in SYSTEM_PROMPT.lower()


class TestPromptExplanation:
    """Tests for the prompt explanation documentation."""
    
    def test_get_prompt_explanation(self):
        """Test prompt explanation function."""
        from src.script_generator import get_prompt_explanation
        
        explanation = get_prompt_explanation()
        
        assert "Hinglish" in explanation
        assert "filler" in explanation.lower()
        assert "interruption" in explanation.lower()


