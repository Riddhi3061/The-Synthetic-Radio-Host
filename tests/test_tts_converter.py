"""
Unit tests for TTSConverter module.

Tests cover:
- Audio segment creation
- Voice selection for speakers
- Mock TTS conversion
- Cleanup functionality
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
import tempfile
import asyncio


class TestAudioSegment:
    """Tests for AudioSegment dataclass."""
    
    def test_exists_with_existing_file(self, tmp_path):
        """Test exists() with actual file."""
        from src.tts_converter import AudioSegment
        
        # Create temp file
        temp_file = tmp_path / "test.mp3"
        temp_file.touch()
        
        segment = AudioSegment(
            file_path=temp_file,
            speaker="RAVI",
            text="Hello"
        )
        
        assert segment.exists() is True
    
    def test_exists_with_missing_file(self, tmp_path):
        """Test exists() with non-existent file."""
        from src.tts_converter import AudioSegment
        
        segment = AudioSegment(
            file_path=tmp_path / "nonexistent.mp3",
            speaker="RAVI",
            text="Hello"
        )
        
        assert segment.exists() is False


class TestTTSConverter:
    """Tests for TTSConverter class."""
    
    def test_init(self):
        """Test basic initialization."""
        from src.tts_converter import TTSConverter
        from src.config import Config
        
        config = Config()
        converter = TTSConverter(config)
        
        assert converter.config is config
        assert converter._edge_tts is None
    
    def test_get_temp_dir(self, tmp_path):
        """Test temporary directory creation."""
        from src.tts_converter import TTSConverter
        from src.config import Config
        
        config = Config()
        config.temp_dir = tmp_path
        
        converter = TTSConverter(config)
        temp_dir = converter._get_temp_dir()
        
        assert temp_dir.exists()
        assert temp_dir.parent == tmp_path
    
    def test_cleanup(self, tmp_path):
        """Test cleanup removes temp directory."""
        from src.tts_converter import TTSConverter
        from src.config import Config
        
        config = Config()
        config.temp_dir = tmp_path
        
        converter = TTSConverter(config)
        temp_dir = converter._get_temp_dir()
        
        # Create a file in temp dir
        (temp_dir / "test.mp3").touch()
        
        converter.cleanup()
        
        assert not temp_dir.exists()


class TestMockTTSConverter:
    """Tests for MockTTSConverter."""
    
    def test_mock_conversion(self, tmp_path):
        """Test mock TTS creates empty files."""
        from src.tts_converter import MockTTSConverter
        from src.config import Config
        
        config = Config()
        config.temp_dir = tmp_path
        
        converter = MockTTSConverter(config)
        
        # Convert some text
        segment = converter.convert_single("Hello world", "RAVI")
        
        assert segment.file_path.exists()
        assert segment.speaker == "RAVI"
        assert segment.text == "Hello world"
        assert len(converter.calls) == 1
    
    def test_mock_conversion_logs_calls(self, tmp_path):
        """Test mock logs all conversion calls."""
        from src.tts_converter import MockTTSConverter
        from src.config import Config
        from src.dialogue_parser import DialogueTurn
        
        config = Config()
        config.temp_dir = tmp_path
        
        converter = MockTTSConverter(config)
        
        dialogues = [
            DialogueTurn(speaker="RAVI", text="Hello"),
            DialogueTurn(speaker="PRIYA", text="Hi"),
        ]
        
        segments = converter.convert_dialogues(dialogues)
        
        assert len(segments) == 2
        assert len(converter.calls) == 2


class TestVoiceSelection:
    """Tests for voice selection functionality."""
    
    def test_get_indian_voices(self):
        """Test getting available Indian voices."""
        from src.tts_converter import get_indian_voices
        
        voices = get_indian_voices()
        
        assert "male" in voices
        assert "female" in voices
        assert len(voices["male"]) > 0
        assert len(voices["female"]) > 0
    
    def test_config_voice_selection(self):
        """Test voice selection from config."""
        from src.config import Config
        
        config = Config()
        
        ravi_voice = config.get_voice_for_speaker("RAVI")
        priya_voice = config.get_voice_for_speaker("PRIYA")
        
        assert "Prabhat" in ravi_voice  # Male voice
        assert "Neerja" in priya_voice  # Female voice
    
    def test_config_voice_case_insensitive(self):
        """Test voice selection is case insensitive."""
        from src.config import Config
        
        config = Config()
        
        voice1 = config.get_voice_for_speaker("RAVI")
        voice2 = config.get_voice_for_speaker("ravi")
        voice3 = config.get_voice_for_speaker("Ravi")
        
        assert voice1 == voice2 == voice3


class TestTTSConverterIntegration:
    """Integration-style tests (still mocked, but test full flow)."""
    
    @pytest.mark.asyncio
    @patch('edge_tts.Communicate')
    async def test_convert_single_async(self, mock_communicate, tmp_path):
        """Test async single conversion with mocked edge_tts."""
        from src.tts_converter import TTSConverter
        from src.config import Config
        
        # Setup mock
        mock_instance = AsyncMock()
        mock_communicate.return_value = mock_instance
        
        config = Config()
        config.temp_dir = tmp_path
        
        converter = TTSConverter(config)
        converter._edge_tts = MagicMock()
        converter._edge_tts.Communicate = mock_communicate
        
        output_path = tmp_path / "test_output.mp3"
        
        # Create the file that would be created
        async def fake_save(path):
            Path(path).touch()
        mock_instance.save = fake_save
        
        segment = await converter.convert_single_async(
            text="Hello yaar!",
            speaker="RAVI",
            output_path=output_path
        )
        
        assert segment.speaker == "RAVI"
        assert segment.text == "Hello yaar!"


