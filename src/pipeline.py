"""
Main pipeline orchestrator for The Synthetic Radio Host.

Coordinates all components to transform Wikipedia articles into radio audio.
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .config import get_config, Config
from .wikipedia_fetcher import WikipediaFetcher, ArticleData
from .script_generator import ScriptGenerator, GeneratedScript
from .dialogue_parser import DialogueParser, DialogueTurn
from .tts_converter import TTSConverter, AudioSegment
from .audio_processor import AudioProcessor

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """
    Result of the complete pipeline execution.
    
    Contains all intermediate and final outputs for inspection.
    """
    
    topic: str
    article: ArticleData
    script: GeneratedScript
    dialogues: list  # List[DialogueTurn]
    audio_segments: list  # List[AudioSegment]
    output_path: Path
    duration_seconds: float
    
    def summary(self) -> str:
        """Get a summary of the pipeline result."""
        return f"""
Pipeline Result Summary
=======================
Topic: {self.topic}
Article: {self.article.title}
Script words: {self.script.word_count}
Dialogue turns: {len(self.dialogues)}
Audio duration: {self.duration_seconds:.1f} seconds
Output: {self.output_path}
"""


class SyntheticRadioHost:
    """
    Main orchestrator for the Synthetic Radio Host pipeline.
    
    This class coordinates:
    1. Wikipedia content fetching
    2. Hinglish script generation
    3. Dialogue parsing
    4. Text-to-speech conversion
    5. Audio stitching and export
    
    Example:
        >>> radio_host = SyntheticRadioHost()
        >>> result = radio_host.generate(
        ...     topic="Mumbai Indians",
        ...     duration_minutes=2,
        ...     output_path="output/show.mp3"
        ... )
        >>> print(f"Generated: {result.output_path}")
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the pipeline.
        
        Args:
            config: Configuration object (uses global config if None)
        """
        self.config = config or get_config()
        
        # Initialize components
        self.fetcher = WikipediaFetcher()
        self.generator = ScriptGenerator(self.config)
        self.parser = DialogueParser(
            expected_speakers=[self.config.host_1_name, self.config.host_2_name]
        )
        self.tts = TTSConverter(self.config)
        self.audio_processor = AudioProcessor(self.config)
        
        logger.info("SyntheticRadioHost initialized")
    
    def generate(
        self,
        topic: str,
        duration_minutes: float = 2.0,
        output_path: Optional[str] = None,
        cleanup_temp: bool = True
    ) -> PipelineResult:
        """
        Generate a complete radio show from a Wikipedia topic.
        
        This is the main entry point for the pipeline.
        
        Args:
            topic: Wikipedia article topic (e.g., "Mumbai Indians")
            duration_minutes: Target duration in minutes
            output_path: Path for output MP3 file (auto-generated if None)
            cleanup_temp: Whether to cleanup temporary files
            
        Returns:
            PipelineResult with all outputs
        """
        logger.info(f"Starting generation for topic: {topic}")
        
        # Generate output path if not provided
        if output_path is None:
            safe_topic = "".join(c if c.isalnum() else "_" for c in topic)
            output_path = self.config.output_dir / f"{safe_topic}_show.mp3"
        else:
            output_path = Path(output_path)
        
        try:
            # Step 1: Fetch Wikipedia content
            logger.info("Step 1/5: Fetching Wikipedia content...")
            article = self.fetcher.fetch(topic)
            logger.info(f"  Fetched: {article.title}")
            
            # Step 2: Generate script
            logger.info("Step 2/5: Generating Hinglish script...")
            script = self.generator.generate(
                article=article,
                duration_minutes=duration_minutes
            )
            logger.info(f"  Generated {script.word_count} words")
            
            # Save script to file for viewing (even if audio fails)
            script_file = output_path.with_suffix('.txt')
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(f"# Hinglish Radio Script: {topic}\n")
                f.write(f"# Hosts: {script.host_1} & {script.host_2}\n")
                f.write(f"# Words: {script.word_count}\n")
                f.write("=" * 50 + "\n\n")
                f.write(script.raw_text)
            logger.info(f"  Script saved to: {script_file}")
            
            # Step 3: Parse dialogue
            logger.info("Step 3/5: Parsing dialogue...")
            dialogues = self.parser.parse(script.raw_text)
            logger.info(f"  Parsed {len(dialogues)} dialogue turns")
            
            # Step 4: Convert to audio
            logger.info("Step 4/5: Converting to audio...")
            audio_segments = self.tts.convert_dialogues(dialogues)
            logger.info(f"  Generated {len(audio_segments)} audio segments")
            
            # Step 5: Stitch audio
            logger.info("Step 5/5: Stitching audio...")
            final_path = self.audio_processor.stitch_segments(
                segments=audio_segments,
                output_path=output_path
            )
            
            # Get final duration
            duration = self.audio_processor.get_duration(final_path)
            
            logger.info(f"Generation complete! Output: {final_path}")
            
            return PipelineResult(
                topic=topic,
                article=article,
                script=script,
                dialogues=dialogues,
                audio_segments=audio_segments,
                output_path=final_path,
                duration_seconds=duration
            )
            
        finally:
            if cleanup_temp:
                self.tts.cleanup()
    
    def generate_script_only(
        self,
        topic: str,
        duration_minutes: float = 2.0
    ) -> GeneratedScript:
        """
        Generate only the script (no audio).
        
        Useful for testing and debugging script generation.
        
        Args:
            topic: Wikipedia article topic
            duration_minutes: Target duration in minutes
            
        Returns:
            GeneratedScript object
        """
        article = self.fetcher.fetch(topic)
        return self.generator.generate(article, duration_minutes)
    
    def generate_from_script(
        self,
        script_text: str,
        output_path: Optional[str] = None,
        cleanup_temp: bool = True
    ) -> Path:
        """
        Generate audio from a pre-written script.
        
        Args:
            script_text: Raw script text with speaker labels
            output_path: Path for output MP3 file
            cleanup_temp: Whether to cleanup temporary files
            
        Returns:
            Path to output audio file
        """
        if output_path is None:
            output_path = self.config.output_dir / "custom_show.mp3"
        else:
            output_path = Path(output_path)
        
        try:
            # Parse dialogue
            dialogues = self.parser.parse(script_text)
            
            # Convert to audio
            audio_segments = self.tts.convert_dialogues(dialogues)
            
            # Stitch audio
            final_path = self.audio_processor.stitch_segments(
                segments=audio_segments,
                output_path=output_path
            )
            
            return final_path
            
        finally:
            if cleanup_temp:
                self.tts.cleanup()
    
    def validate_script(self, script_text: str) -> tuple:
        """
        Validate a script before processing.
        
        Args:
            script_text: Script text to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        return self.parser.validate_script(script_text)


def generate_radio_show(
    topic: str,
    duration_minutes: float = 2.0,
    output_path: Optional[str] = None
) -> Path:
    """
    Convenience function to generate a radio show.
    
    Args:
        topic: Wikipedia article topic
        duration_minutes: Target duration
        output_path: Output file path
        
    Returns:
        Path to generated audio file
    """
    pipeline = SyntheticRadioHost()
    result = pipeline.generate(
        topic=topic,
        duration_minutes=duration_minutes,
        output_path=output_path
    )
    return result.output_path


