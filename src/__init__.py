"""
The Synthetic Radio Host
========================

An AI-powered pipeline that transforms Wikipedia articles into 
natural-sounding Hinglish radio conversations.

Main Components:
- WikipediaFetcher: Extracts content from Wikipedia
- ScriptGenerator: Creates Hinglish dialogue using LLM
- DialogueParser: Parses script into structured dialogue
- TTSConverter: Converts text to speech
- AudioProcessor: Stitches audio and exports MP3
- SyntheticRadioHost: Main pipeline orchestrator
"""

from .pipeline import SyntheticRadioHost
from .wikipedia_fetcher import WikipediaFetcher
from .script_generator import ScriptGenerator
from .dialogue_parser import DialogueParser, DialogueTurn
from .tts_converter import TTSConverter
from .audio_processor import AudioProcessor

__version__ = "1.0.0"
__author__ = "Synthetic Radio Host Team"

__all__ = [
    "SyntheticRadioHost",
    "WikipediaFetcher",
    "ScriptGenerator",
    "DialogueParser",
    "DialogueTurn",
    "TTSConverter",
    "AudioProcessor",
]


