"""
Text-to-Speech converter for The Synthetic Radio Host.

Converts dialogue turns to audio using Edge TTS with distinct voices.
"""

import asyncio
import logging
import tempfile
import ssl
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
import uuid

import aiohttp

from .config import get_config, Config
from .dialogue_parser import DialogueTurn

logger = logging.getLogger(__name__)

# =============================================================================
# SSL CONFIGURATION - DISABLE FOR CORPORATE PROXY
# =============================================================================

# Completely disable SSL verification for aiohttp
# This is necessary for corporate proxy environments

# Patch aiohttp.ClientSession._request to disable SSL
_original_client_session_request = aiohttp.ClientSession._request

async def _patched_client_session_request(self, method, url, **kwargs):
    # Force disable SSL verification
    kwargs['ssl'] = False
    return await _original_client_session_request(self, method, url, **kwargs)

aiohttp.ClientSession._request = _patched_client_session_request


@dataclass
class AudioSegment:
    """Represents a generated audio segment."""
    
    file_path: Path
    speaker: str
    text: str
    duration_ms: Optional[float] = None
    
    def exists(self) -> bool:
        """Check if audio file exists."""
        return self.file_path.exists()


class TTSConverter:
    """
    Converts text to speech using Microsoft Edge TTS.
    
    Features:
    - Multiple voice support for different speakers
    - Async batch processing for efficiency
    - Indian English voices with natural prosody
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the TTS converter.
        
        Args:
            config: Configuration object (uses global config if None)
        """
        self.config = config or get_config()
        self._edge_tts = None
        self._temp_dir = None
    
    def _ensure_imports(self):
        """Ensure edge_tts is imported."""
        if self._edge_tts is None:
            try:
                import edge_tts
                self._edge_tts = edge_tts
            except ImportError:
                raise ImportError(
                    "edge-tts is required. Install with: pip install edge-tts"
                )
    
    def _get_temp_dir(self) -> Path:
        """Get or create temporary directory for audio files."""
        if self._temp_dir is None:
            self._temp_dir = self.config.temp_dir / f"tts_{uuid.uuid4().hex[:8]}"
            self._temp_dir.mkdir(parents=True, exist_ok=True)
        return self._temp_dir
    
    def _number_to_words_indian(self, num: int) -> str:
        """
        Convert number to words using Indian numbering system (lakhs, crores).
        
        Examples:
            100000 -> "one lakh"
            10000000 -> "one crore"
            5000 -> "five thousand"
            2024 -> "two thousand twenty four"
        """
        if num == 0:
            return "zero"
        
        ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
                "seventeen", "eighteen", "nineteen"]
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
        
        def two_digits(n):
            if n < 20:
                return ones[n]
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
        
        def three_digits(n):
            if n < 100:
                return two_digits(n)
            return ones[n // 100] + " hundred" + (" " + two_digits(n % 100) if n % 100 else "")
        
        if num < 0:
            return "minus " + self._number_to_words_indian(-num)
        
        if num < 1000:
            return three_digits(num)
        
        # Indian system: crores (10^7), lakhs (10^5), thousands (10^3)
        result = []
        
        # Crores (1,00,00,000+)
        if num >= 10000000:
            crores = num // 10000000
            result.append(three_digits(crores) + " crore")
            num %= 10000000
        
        # Lakhs (1,00,000 - 99,99,999)
        if num >= 100000:
            lakhs = num // 100000
            result.append(two_digits(lakhs) + " lakh")
            num %= 100000
        
        # Thousands (1,000 - 99,999)
        if num >= 1000:
            thousands = num // 1000
            result.append(two_digits(thousands) + " thousand")
            num %= 1000
        
        # Hundreds and below
        if num > 0:
            result.append(three_digits(num))
        
        return " ".join(result)
    
    def _convert_numbers_to_words(self, text: str) -> str:
        """
        Convert all numbers in text to words for natural TTS pronunciation.
        
        Handles:
        - Large numbers with Indian system (lakhs, crores)
        - Years (1947 -> nineteen forty seven)
        - Regular numbers
        """
        import re
        
        def replace_number(match):
            num_str = match.group(0).replace(",", "").replace(" ", "")
            try:
                num = int(num_str)
                # Handle years specially (1900-2099)
                if 1900 <= num <= 2099:
                    # Read as "twenty twenty four" or "nineteen forty seven"
                    century = num // 100
                    year_part = num % 100
                    ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                            "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
                            "seventeen", "eighteen", "nineteen"]
                    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
                    
                    def two_digits(n):
                        if n < 20:
                            return ones[n]
                        return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
                    
                    if year_part == 0:
                        return two_digits(century) + " hundred"
                    elif year_part < 10:
                        return two_digits(century) + " oh " + ones[year_part]
                    else:
                        return two_digits(century) + " " + two_digits(year_part)
                else:
                    return self._number_to_words_indian(num)
            except ValueError:
                return match.group(0)
        
        # Match numbers with optional commas (Indian format: 1,00,000 or Western: 100,000)
        text = re.sub(r'\b\d{1,3}(?:,?\d{2,3})*\b', replace_number, text)
        
        return text
    
    def _break_long_sentences(self, text: str) -> str:
        """
        Break up long sentences by adding commas at natural pause points.
        
        This makes long sentences easier to understand by adding pauses
        after connecting words if the sentence is getting too long.
        """
        import re
        
        # Words after which we can add a comma for natural pause
        # These are common Hindi/English connecting words
        pause_words = [
            # Hindi connectors
            r'\baur\b', r'\btoh\b', r'\bphir\b', r'\blekin\b', r'\bpar\b',
            r'\bisliye\b', r'\bkyunki\b', r'\bjab\b', r'\btab\b',
            r'\bjaise\b', r'\bwaisa\b', r'\bjahan\b', r'\bwahan\b',
            r'\bmatlab\b', r'\bbasically\b', r'\bactually\b',
            # English connectors  
            r'\band\b', r'\bbut\b', r'\bso\b', r'\bthen\b', r'\bbecause\b',
            r'\bwhen\b', r'\bwhere\b', r'\bwhich\b', r'\bthat\b',
            r'\balso\b', r'\bplus\b', r'\blike\b',
        ]
        
        # Process each sentence
        sentences = re.split(r'([.!?])', text)
        result = []
        
        for i, part in enumerate(sentences):
            if part in '.!?':
                result.append(part)
                continue
                
            # Count words in this sentence segment
            words = part.split()
            
            # If sentence is long (more than 12 words), add commas at natural points
            if len(words) > 12:
                # Add comma after connecting words (if not already followed by punctuation)
                for pause_word in pause_words:
                    # Add comma after the word if not already there
                    part = re.sub(
                        pause_word + r'(?!\s*[,.])',  # word not followed by comma/period
                        lambda m: m.group(0) + ',',
                        part,
                        flags=re.IGNORECASE
                    )
            
            result.append(part)
        
        text = ''.join(result)
        
        # Clean up any double commas created
        text = re.sub(r',\s*,', ',', text)
        
        return text
    
    def _fix_pronunciation(self, text: str) -> str:
        """
        Fix common pronunciation issues - ONLY for abbreviations and English words.
        
        NOTE: Hindi words are NOT converted because we use Hindi TTS voices
        (hi-IN-MadhurNeural, hi-IN-SwaraNeural) which already know how to
        pronounce Hindi words correctly!
        
        Only handles:
        - "US" dollars -> "American" dollars (avoid "us" pronunciation)
        - Abbreviations and acronyms that need spelling out
        """
        import re
        
        # =================================================================
        # FIX ABBREVIATIONS & ACRONYMS ONLY
        # =================================================================
        
        # US/U.S. -> American or United States (context-dependent)
        text = re.sub(r'\bUS\s+dollars?\b', 'American dollars', text, flags=re.IGNORECASE)
        text = re.sub(r'\bUS\s+dollar\b', 'American dollar', text, flags=re.IGNORECASE)
        text = re.sub(r'\bUSD\b', 'American dollars', text)
        text = re.sub(r'\bUS\$', 'American dollars ', text)
        text = re.sub(r'\$\s*(\d)', r'dollars \1', text)  # $50 -> dollars 50
        text = re.sub(r'\bUS\b(?!\s+dollars?)', 'United States', text)  # US alone -> United States
        text = re.sub(r'\bU\.S\.', 'United States', text)
        text = re.sub(r'\bUSA\b', 'United States', text)
        
        # UK -> United Kingdom
        text = re.sub(r'\bUK\b', 'United Kingdom', text)
        text = re.sub(r'\bU\.K\.', 'United Kingdom', text)
        
        # Common abbreviations - spell them out for clarity
        text = re.sub(r'\bIPL\b', 'I P L', text)
        text = re.sub(r'\bBCCI\b', 'B C C I', text)
        text = re.sub(r'\bCEO\b', 'C E O', text)
        text = re.sub(r'\bCFO\b', 'C F O', text)
        text = re.sub(r'\bIIT\b', 'I I T', text)
        text = re.sub(r'\bIIM\b', 'I I M', text)
        text = re.sub(r'\bMBA\b', 'M B A', text)
        text = re.sub(r'\bPhD\b', 'P H D', text)
        text = re.sub(r'\bAI\b', 'A I', text)
        text = re.sub(r'\bML\b', 'M L', text)
        text = re.sub(r'\bNGO\b', 'N G O', text)
        text = re.sub(r'\bATM\b', 'A T M', text)
        text = re.sub(r'\bEMI\b', 'E M I', text)
        
        # These are pronounced as words, keep as-is
        # NASA, ISRO, UNESCO, etc.
        
        # =================================================================
        # DO NOT CONVERT HINDI WORDS!
        # Hindi TTS voices (hi-IN-MadhurNeural, hi-IN-SwaraNeural) already
        # know how to pronounce: mein, hai, hain, aur, kya, hua, hui, etc.
        # Converting them to phonetic English makes it sound WORSE!
        # =================================================================
        
        return text
    
    def _preprocess_text_for_natural_speech(self, text: str) -> str:
        """
        Preprocess text to make TTS sound more natural.
        
        - Removes markdown formatting (**, #, etc.)
        - Fixes pronunciation issues (US dollars, Hindi words)
        - Converts numbers to words for proper pronunciation
        - Removes excessive punctuation that causes unnatural pauses
        - Makes speech flow continuously like human conversation
        - Converts action markers appropriately
        """
        import re
        
        # FIRST: Remove markdown/formatting that TTS reads literally
        # Remove bold/italic markers (**text**, *text*, __text__, _text_)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic* -> italic
        text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__ -> bold
        text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_ -> italic
        
        # Remove any remaining asterisks
        text = text.replace('**', '')
        text = text.replace('*', '')
        
        # Remove markdown headers (# Title, ## Subtitle, etc.)
        text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
        
        # Remove markdown links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove markdown images ![alt](url)
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove Wikipedia reference markers like [1], [2], [citation needed]
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\[citation needed\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[edit\]', '', text, flags=re.IGNORECASE)
        
        # FIX PRONUNCIATION ISSUES (US dollars, Hindi words, etc.)
        text = self._fix_pronunciation(text)
        
        # Convert numbers to words for natural pronunciation
        text = self._convert_numbers_to_words(text)
        
        # Remove ALL action markers - they break flow
        text = re.sub(r'\[laughs?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[chuckles?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[interrupts?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[excited\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[pauses?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[sighs?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[[^\]]*\]', '', text)  # Remove any remaining brackets
        
        # BREAK UP LONG SENTENCES for better understanding
        # Add commas after connecting words in long sentences
        text = self._break_long_sentences(text)
        
        # KEEP COMMAS for natural pauses in speech
        # Clean up multiple commas first
        text = re.sub(r',+', ',', text)
        
        # Add slight pause after commas
        text = re.sub(r',\s*', ', ', text)  # Normalize comma spacing
        
        # Remove ellipsis - causes too long pauses, replace with comma for short pause
        text = text.replace('...', ', ')
        text = text.replace('..', ', ')
        
        # Remove dashes - replace with comma for natural pause
        text = text.replace('--', ',')
        text = text.replace(' - ', ', ')
        
        # Keep exclamation for emphasis but remove multiple
        text = re.sub(r'!+', '!', text)
        
        # Keep question marks
        text = re.sub(r'\?+', '?', text)
        
        # Replace semicolons with commas (short pause)
        text = text.replace(';', ',')
        
        # Keep colons but clean up
        text = re.sub(r':\s*(?=[a-z])', ', ', text)
        
        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    async def convert_single_async(
        self,
        text: str,
        speaker: str,
        output_path: Optional[Path] = None
    ) -> AudioSegment:
        """
        Convert a single text to audio asynchronously.
        
        Args:
            text: Text to convert to speech
            speaker: Speaker name (for voice selection)
            output_path: Optional output file path
            
        Returns:
            AudioSegment with the generated audio
        """
        self._ensure_imports()
        
        # Preprocess text for more natural speech
        text = self._preprocess_text_for_natural_speech(text)
        
        # Get voice for speaker - should be Hindi voice for Indian accent
        voice = self.config.get_voice_for_speaker(speaker)
        
        # Log voice selection for debugging
        logger.info(f"Using voice '{voice}' for speaker '{speaker}'")
        
        # Generate output path if not provided
        if output_path is None:
            output_path = self._get_temp_dir() / f"{uuid.uuid4().hex}.mp3"
        
        # Create communicate object with optimized settings
        # Use Hindi voices for authentic Indian accent
        communicate = self._edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=self.config.tts.rate,
            volume=self.config.tts.volume,
            pitch=self.config.tts.pitch
        )
        
        # Generate audio
        logger.debug(f"Generating audio with {voice}: {text[:50]}...")
        await communicate.save(str(output_path))
        
        return AudioSegment(
            file_path=output_path,
            speaker=speaker,
            text=text
        )
    
    def convert_single(
        self,
        text: str,
        speaker: str,
        output_path: Optional[Path] = None
    ) -> AudioSegment:
        """
        Convert a single text to audio (synchronous wrapper).
        
        Args:
            text: Text to convert to speech
            speaker: Speaker name (for voice selection)
            output_path: Optional output file path
            
        Returns:
            AudioSegment with the generated audio
        """
        return asyncio.run(self.convert_single_async(text, speaker, output_path))
    
    async def convert_dialogues_async(
        self,
        dialogues: List[DialogueTurn],
        max_concurrent: int = 10
    ) -> List[AudioSegment]:
        """
        Convert multiple dialogue turns to audio asynchronously IN PARALLEL.
        
        Args:
            dialogues: List of DialogueTurn objects
            max_concurrent: Maximum concurrent TTS requests (default 10)
            
        Returns:
            List of AudioSegment objects in order
        """
        self._ensure_imports()
        
        logger.info(f"Converting {len(dialogues)} dialogue turns to audio (parallel mode)...")
        
        # Semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def convert_with_semaphore(index: int, dialogue: DialogueTurn):
            """Convert a single dialogue with semaphore limit."""
            async with semaphore:
                text = dialogue.get_clean_text()
                if not text.strip():
                    logger.warning(f"Skipping empty dialogue at index {index}")
                    return None
                
                segment = await self.convert_single_async(
                    text=text,
                    speaker=dialogue.speaker
                )
                logger.debug(f"Generated audio {index+1}/{len(dialogues)}")
                return segment
        
        # Create all tasks
        tasks = [
            convert_with_semaphore(i, dialogue)
            for i, dialogue in enumerate(dialogues)
        ]
        
        # Run all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None values and exceptions, preserve order
        segments = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to convert dialogue {i}: {result}")
            elif result is not None:
                segments.append(result)
        
        logger.info(f"Successfully generated {len(segments)} audio segments")
        return segments
    
    def convert_dialogues(
        self,
        dialogues: List[DialogueTurn]
    ) -> List[AudioSegment]:
        """
        Convert multiple dialogue turns to audio (synchronous wrapper).
        
        For environments that don't support asyncio (like some Jupyter notebooks),
        this provides a synchronous interface.
        
        Args:
            dialogues: List of DialogueTurn objects
            
        Returns:
            List of AudioSegment objects in order
        """
        # Handle nested event loops (e.g., in Jupyter)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In Jupyter or similar environment
                import nest_asyncio
                nest_asyncio.apply()
        except RuntimeError:
            pass
        
        return asyncio.run(self.convert_dialogues_async(dialogues))
    
    def cleanup(self):
        """Remove temporary audio files."""
        if self._temp_dir and self._temp_dir.exists():
            import shutil
            shutil.rmtree(self._temp_dir)
            logger.info(f"Cleaned up temp directory: {self._temp_dir}")
            self._temp_dir = None


class MockTTSConverter(TTSConverter):
    """
    Mock TTS converter for testing.
    
    Generates empty audio files without calling external services.
    """
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.calls = []
    
    async def convert_single_async(
        self,
        text: str,
        speaker: str,
        output_path: Optional[Path] = None
    ) -> AudioSegment:
        """Mock conversion that logs calls and creates empty files."""
        # Log the call
        self.calls.append({
            "text": text,
            "speaker": speaker,
            "output_path": output_path
        })
        
        # Generate output path if not provided
        if output_path is None:
            output_path = self._get_temp_dir() / f"{uuid.uuid4().hex}.mp3"
        
        # Create empty file
        output_path.touch()
        
        return AudioSegment(
            file_path=output_path,
            speaker=speaker,
            text=text
        )


async def list_voices() -> List[Dict]:
    """
    List available Edge TTS voices.
    
    Returns:
        List of voice dictionaries with name, gender, locale
    """
    try:
        import edge_tts
        voices = await edge_tts.list_voices()
        return voices
    except ImportError:
        raise ImportError(
            "edge-tts is required. Install with: pip install edge-tts"
        )


def get_indian_voices() -> Dict[str, List[str]]:
    """
    Get available Indian English voices.
    
    Returns:
        Dictionary with 'male' and 'female' voice lists
    """
    return {
        "male": [
            "en-IN-PrabhatNeural",
        ],
        "female": [
            "en-IN-NeerjaNeural",
            "en-IN-NeerjaExpressiveNeural",
        ]
    }


