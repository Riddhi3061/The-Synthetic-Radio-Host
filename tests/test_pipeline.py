"""
Unit tests for the main Pipeline module.

Tests cover:
- Pipeline initialization
- End-to-end generation with mocks
- Script-only generation
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""
    
    def test_summary(self, tmp_path):
        """Test summary generation."""
        from src.pipeline import PipelineResult
        from src.wikipedia_fetcher import ArticleData
        from src.script_generator import GeneratedScript
        
        result = PipelineResult(
            topic="Mumbai Indians",
            article=ArticleData(
                title="Mumbai Indians",
                summary="Test",
                full_text="",
                key_facts=[],
                categories=[],
                url=""
            ),
            script=GeneratedScript(
                raw_text="RAVI: Hello",
                topic="Mumbai Indians",
                host_1="RAVI",
                host_2="PRIYA",
                word_count=2
            ),
            dialogues=[],
            audio_segments=[],
            output_path=tmp_path / "test.mp3",
            duration_seconds=120.0
        )
        
        summary = result.summary()
        
        assert "Mumbai Indians" in summary
        assert "120" in summary  # duration


class TestSyntheticRadioHost:
    """Tests for SyntheticRadioHost class."""
    
    def test_init(self):
        """Test pipeline initialization."""
        from src.pipeline import SyntheticRadioHost
        from src.config import Config
        
        config = Config()
        pipeline = SyntheticRadioHost(config)
        
        assert pipeline.fetcher is not None
        assert pipeline.generator is not None
        assert pipeline.parser is not None
        assert pipeline.tts is not None
        assert pipeline.audio_processor is not None
    
    @patch('src.pipeline.WikipediaFetcher')
    @patch('src.pipeline.ScriptGenerator')
    @patch('src.pipeline.TTSConverter')
    @patch('src.pipeline.AudioProcessor')
    def test_generate_calls_all_components(
        self,
        mock_audio_processor,
        mock_tts,
        mock_generator,
        mock_fetcher,
        tmp_path
    ):
        """Test that generate calls all pipeline components."""
        from src.pipeline import SyntheticRadioHost
        from src.config import Config
        from src.wikipedia_fetcher import ArticleData
        from src.script_generator import GeneratedScript
        from src.tts_converter import AudioSegment
        
        # Setup mocks
        mock_article = ArticleData(
            title="Test",
            summary="Summary",
            full_text="Text",
            key_facts=[],
            categories=[],
            url=""
        )
        mock_fetcher.return_value.fetch.return_value = mock_article
        
        mock_script = GeneratedScript(
            raw_text="RAVI: Hello yaar!\n\nPRIYA: Hi!",
            topic="Test",
            host_1="RAVI",
            host_2="PRIYA",
            word_count=5
        )
        mock_generator.return_value.generate.return_value = mock_script
        
        mock_segment = AudioSegment(
            file_path=tmp_path / "segment.mp3",
            speaker="RAVI",
            text="Hello"
        )
        mock_tts.return_value.convert_dialogues.return_value = [mock_segment]
        
        output_file = tmp_path / "output.mp3"
        output_file.touch()
        mock_audio_processor.return_value.stitch_segments.return_value = output_file
        mock_audio_processor.return_value.get_duration.return_value = 60.0
        
        # Run pipeline
        config = Config()
        config.output_dir = tmp_path
        pipeline = SyntheticRadioHost(config)
        
        result = pipeline.generate(
            topic="Test Topic",
            duration_minutes=2,
            output_path=str(output_file)
        )
        
        # Verify all components were called
        mock_fetcher.return_value.fetch.assert_called_once()
        mock_generator.return_value.generate.assert_called_once()
        mock_tts.return_value.convert_dialogues.assert_called_once()
        mock_audio_processor.return_value.stitch_segments.assert_called_once()
    
    @patch('src.pipeline.WikipediaFetcher')
    @patch('src.pipeline.ScriptGenerator')
    def test_generate_script_only(
        self,
        mock_generator,
        mock_fetcher
    ):
        """Test script-only generation."""
        from src.pipeline import SyntheticRadioHost
        from src.config import Config
        from src.wikipedia_fetcher import ArticleData
        from src.script_generator import GeneratedScript
        
        # Setup mocks
        mock_article = ArticleData(
            title="Test",
            summary="Summary",
            full_text="",
            key_facts=[],
            categories=[],
            url=""
        )
        mock_fetcher.return_value.fetch.return_value = mock_article
        
        mock_script = GeneratedScript(
            raw_text="RAVI: Test",
            topic="Test",
            host_1="RAVI",
            host_2="PRIYA",
            word_count=2
        )
        mock_generator.return_value.generate.return_value = mock_script
        
        config = Config()
        pipeline = SyntheticRadioHost(config)
        
        script = pipeline.generate_script_only("Test", 2.0)
        
        assert script.raw_text == "RAVI: Test"
        mock_fetcher.return_value.fetch.assert_called_once()
        mock_generator.return_value.generate.assert_called_once()
    
    def test_validate_script(self):
        """Test script validation."""
        from src.pipeline import SyntheticRadioHost
        from src.config import Config
        
        config = Config()
        pipeline = SyntheticRadioHost(config)
        
        valid_script = """RAVI: Arey yaar, umm, let me explain!

PRIYA: [laughs] Achcha, tell me more!

RAVI: [interrupts] Wait, matlab—

PRIYA: [chuckles] Okay okay!"""
        
        is_valid, errors = pipeline.validate_script(valid_script)
        
        # Should pass validation
        assert is_valid is True


class TestGenerateRadioShowFunction:
    """Tests for convenience function."""
    
    @patch('src.pipeline.SyntheticRadioHost')
    def test_generate_radio_show(self, mock_pipeline_class, tmp_path):
        """Test convenience function."""
        from src.pipeline import generate_radio_show, PipelineResult
        from src.wikipedia_fetcher import ArticleData
        from src.script_generator import GeneratedScript
        
        output_path = tmp_path / "show.mp3"
        output_path.touch()
        
        mock_result = PipelineResult(
            topic="Test",
            article=ArticleData("", "", "", [], [], ""),
            script=GeneratedScript("", "", "", "", 0),
            dialogues=[],
            audio_segments=[],
            output_path=output_path,
            duration_seconds=60.0
        )
        
        mock_pipeline_class.return_value.generate.return_value = mock_result
        
        result = generate_radio_show("Test", 2.0, str(output_path))
        
        assert result == output_path


class TestPipelineErrorHandling:
    """Tests for error handling in pipeline."""
    
    @patch('src.pipeline.WikipediaFetcher')
    def test_handles_fetch_error(self, mock_fetcher):
        """Test handling of Wikipedia fetch errors."""
        from src.pipeline import SyntheticRadioHost
        from src.config import Config
        
        mock_fetcher.return_value.fetch.side_effect = ValueError("Article not found")
        
        config = Config()
        pipeline = SyntheticRadioHost(config)
        
        with pytest.raises(ValueError) as excinfo:
            pipeline.generate("NonexistentTopic12345")
        
        assert "not found" in str(excinfo.value).lower()


