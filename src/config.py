"""
Configuration management for The Synthetic Radio Host.

Handles environment variables, default settings, and voice configurations.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path


@dataclass
class TTSConfig:
    """Text-to-Speech configuration."""
    
    # Indian Hindi voices from Edge TTS for better Hindi pronunciation
    voices: Dict[str, str] = field(default_factory=lambda: {
        "RAVI": "hi-IN-MadhurNeural",            # Hindi Male - better Hindi pronunciation
        "PRIYA": "hi-IN-SwaraNeural",            # Hindi Female - better Hindi pronunciation
    })
    
    # Speech rate - slightly slower for natural pauses at commas
    rate: str = "-3%"
    
    # Volume adjustment
    volume: str = "+0%"
    
    # Pitch adjustment - slight variation for more natural sound
    pitch: str = "+0Hz"


@dataclass
class LLMConfig:
    """Language Model configuration."""
    
    # Model to use
    model_name: str = "models/gemini-2.5-flash"
    
    # Temperature for generation (0.0 = deterministic, 1.0 = creative)
    temperature: float = 0.8
    
    # Maximum tokens to generate (8000 for complete 3-min scripts)
    max_tokens: int = 8000
    
    # Top-p sampling
    top_p: float = 0.95


@dataclass
class AudioConfig:
    """Audio processing configuration."""
    
    # Output format
    format: str = "mp3"
    
    # Bitrate for MP3
    bitrate: str = "192k"
    
    # Sample rate
    sample_rate: int = 44100
    
    # Pause between dialogues (milliseconds) - very short for natural conversation
    dialogue_pause_ms: int = 80
    
    # Pause after laughter (milliseconds)
    laughter_pause_ms: int = 50


@dataclass
class Config:
    """Main configuration class."""
    
    # API Keys (loaded from environment)
    gemini_api_key: Optional[str] = None
    
    # Sub-configurations
    tts: TTSConfig = field(default_factory=TTSConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    
    # Paths
    output_dir: Path = field(default_factory=lambda: Path("output"))
    temp_dir: Path = field(default_factory=lambda: Path("temp"))
    
    # Host names (default)
    host_1_name: str = "RAVI"
    host_2_name: str = "PRIYA"
    
    # Script generation - 3 minutes default for comprehensive coverage
    default_duration_minutes: float = 3.0
    words_per_minute: int = 140  # Slightly slower for natural Hindi speech
    
    def __post_init__(self):
        """Load environment variables after initialization."""
        self._load_env()
        self._ensure_directories()
    
    def _load_env(self):
        """Load configuration from environment variables."""
        # Try to load .env file if it exists
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        # API Keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", self.gemini_api_key)
        
        # TTS voices from environment
        male_voice = os.getenv("TTS_VOICE_MALE")
        female_voice = os.getenv("TTS_VOICE_FEMALE")
        if male_voice:
            self.tts.voices[self.host_1_name] = male_voice
        if female_voice:
            self.tts.voices[self.host_2_name] = female_voice
        
        # Paths from environment
        output_dir = os.getenv("OUTPUT_DIR")
        temp_dir = os.getenv("TEMP_DIR")
        if output_dir:
            self.output_dir = Path(output_dir)
        if temp_dir:
            self.temp_dir = Path(temp_dir)
    
    def _ensure_directories(self):
        """Create output and temp directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def get_voice_for_speaker(self, speaker: str) -> str:
        """Get the TTS voice for a given speaker."""
        # Normalize speaker name - remove extra spaces and convert to upper
        speaker_upper = speaker.upper().strip()
        
        # Check for exact match first
        if speaker_upper in self.tts.voices:
            return self.tts.voices[speaker_upper]
        
        # Check if speaker name contains known host names
        if self.host_1_name.upper() in speaker_upper:
            return self.tts.voices.get(self.host_1_name, "hi-IN-MadhurNeural")
        if self.host_2_name.upper() in speaker_upper:
            return self.tts.voices.get(self.host_2_name, "hi-IN-SwaraNeural")
        
        # Alternate between male/female Hindi voices for unknown speakers
        # Use Hindi voices as default, NOT English
        return "hi-IN-MadhurNeural"  # Default to Hindi male voice
    
    def get_target_word_count(self, duration_minutes: float) -> int:
        """Calculate target word count for desired duration."""
        return int(duration_minutes * self.words_per_minute)
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> "Config":
        """Create Config from dictionary."""
        config = cls()
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config):
    """Set the global configuration instance."""
    global _config
    _config = config


# Available Indian voices in Edge TTS
AVAILABLE_VOICES = {
    "hindi_male": [
        "hi-IN-MadhurNeural",   # Hindi male - BEST for Hinglish
    ],
    "hindi_female": [
        "hi-IN-SwaraNeural",    # Hindi female - BEST for Hinglish
    ],
    "english_male": [
        "en-IN-PrabhatNeural",  # Indian English male
    ],
    "english_female": [
        "en-IN-NeerjaNeural",   # Indian English female
        "en-IN-NeerjaExpressiveNeural",  # Expressive variant
    ],
}


