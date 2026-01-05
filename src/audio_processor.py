"""
Audio processor for The Synthetic Radio Host.

Stitches audio segments and exports final MP3.
"""

import logging
from pathlib import Path
from typing import List, Optional
import subprocess

from .config import get_config, Config
from .tts_converter import AudioSegment

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Processes and combines audio segments into final output.
    
    Features:
    - Concatenation with natural pauses
    - Volume normalization
    - MP3 export with configurable bitrate
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the audio processor.
        
        Args:
            config: Configuration object (uses global config if None)
        """
        self.config = config or get_config()
        self._pydub_available = None
    
    def _check_pydub(self) -> bool:
        """Check if pydub is available."""
        if self._pydub_available is None:
            try:
                from pydub import AudioSegment as PydubSegment
                self._pydub_available = True
            except ImportError:
                self._pydub_available = False
        return self._pydub_available
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def stitch_segments(
        self,
        segments: List[AudioSegment],
        output_path: Path,
        pause_duration_ms: Optional[int] = None
    ) -> Path:
        """
        Stitch audio segments together with pauses.
        
        Args:
            segments: List of AudioSegment objects
            output_path: Path for output file
            pause_duration_ms: Pause duration between segments (default from config)
            
        Returns:
            Path to output file
        """
        if not segments:
            raise ValueError("No audio segments to stitch")
        
        # Use config pause if not specified
        if pause_duration_ms is None:
            pause_duration_ms = self.config.audio.dialogue_pause_ms
        
        # Try pydub first
        if self._check_pydub():
            return self._stitch_with_pydub(segments, output_path, pause_duration_ms)
        
        # Fallback to ffmpeg
        if self._check_ffmpeg():
            return self._stitch_with_ffmpeg(segments, output_path)
        
        raise RuntimeError(
            "Neither pydub nor ffmpeg available. "
            "Install with: pip install pydub OR install ffmpeg"
        )
    
    def _stitch_with_pydub(
        self,
        segments: List[AudioSegment],
        output_path: Path,
        pause_duration_ms: int
    ) -> Path:
        """
        Stitch audio using pydub.
        
        Args:
            segments: List of AudioSegment objects
            output_path: Path for output file
            pause_duration_ms: Pause duration between segments
            
        Returns:
            Path to output file
        """
        from pydub import AudioSegment as PydubSegment
        
        logger.info(f"Stitching {len(segments)} segments with pydub...")
        
        # Create silence for pauses
        pause = PydubSegment.silent(duration=pause_duration_ms)
        
        # Start with empty audio
        combined = PydubSegment.empty()
        
        for i, segment in enumerate(segments):
            # Load segment
            if not segment.file_path.exists():
                logger.warning(f"Segment file not found: {segment.file_path}")
                continue
            
            try:
                audio = PydubSegment.from_file(str(segment.file_path))
                
                # Add to combined
                if len(combined) > 0:
                    combined += pause
                combined += audio
                
                logger.debug(f"Added segment {i+1}/{len(segments)}: {len(audio)}ms")
            except Exception as e:
                logger.error(f"Failed to load segment {segment.file_path}: {e}")
        
        # Normalize volume
        combined = self._normalize_audio(combined)
        
        # Export
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        combined.export(
            str(output_path),
            format=self.config.audio.format,
            bitrate=self.config.audio.bitrate
        )
        
        logger.info(f"Exported audio to: {output_path} ({len(combined)}ms)")
        return output_path
    
    def _stitch_with_ffmpeg(
        self,
        segments: List[AudioSegment],
        output_path: Path
    ) -> Path:
        """
        Stitch audio using FFmpeg directly.
        
        Args:
            segments: List of AudioSegment objects
            output_path: Path for output file
            
        Returns:
            Path to output file
        """
        import tempfile
        
        logger.info(f"Stitching {len(segments)} segments with ffmpeg...")
        
        # Create concat file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for segment in segments:
                if segment.file_path.exists():
                    f.write(f"file '{segment.file_path.absolute()}'\n")
            concat_file = f.name
        
        try:
            # Run ffmpeg concat
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            result = subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-acodec", "libmp3lame",
                "-b:a", self.config.audio.bitrate,
                str(output_path)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")
            
            logger.info(f"Exported audio to: {output_path}")
            return output_path
            
        finally:
            # Cleanup concat file
            Path(concat_file).unlink(missing_ok=True)
    
    def _normalize_audio(self, audio) -> "PydubSegment":
        """
        Normalize audio volume.
        
        Args:
            audio: Pydub AudioSegment
            
        Returns:
            Normalized AudioSegment
        """
        from pydub import AudioSegment as PydubSegment
        
        # Target dBFS (decibels relative to full scale)
        target_dBFS = -20.0
        
        change_in_dBFS = target_dBFS - audio.dBFS
        return audio.apply_gain(change_in_dBFS)
    
    def add_intro_outro(
        self,
        main_audio_path: Path,
        output_path: Path,
        intro_path: Optional[Path] = None,
        outro_path: Optional[Path] = None
    ) -> Path:
        """
        Add intro and outro to the main audio.
        
        Args:
            main_audio_path: Path to main audio file
            output_path: Path for output file
            intro_path: Optional path to intro audio
            outro_path: Optional path to outro audio
            
        Returns:
            Path to output file
        """
        if not self._check_pydub():
            logger.warning("pydub not available, skipping intro/outro")
            return main_audio_path
        
        from pydub import AudioSegment as PydubSegment
        
        # Load main audio
        main = PydubSegment.from_file(str(main_audio_path))
        
        # Add intro if provided
        if intro_path and intro_path.exists():
            intro = PydubSegment.from_file(str(intro_path))
            main = intro + main
        
        # Add outro if provided
        if outro_path and outro_path.exists():
            outro = PydubSegment.from_file(str(outro_path))
            main = main + outro
        
        # Export
        output_path = Path(output_path)
        main.export(str(output_path), format=self.config.audio.format)
        
        return output_path
    
    def get_duration(self, audio_path: Path) -> float:
        """
        Get duration of audio file in seconds.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Duration in seconds
        """
        if self._check_pydub():
            from pydub import AudioSegment as PydubSegment
            audio = PydubSegment.from_file(str(audio_path))
            return len(audio) / 1000.0
        
        # Fallback to ffprobe
        try:
            result = subprocess.run([
                "ffprobe",
                "-i", str(audio_path),
                "-show_entries", "format=duration",
                "-v", "quiet",
                "-of", "csv=p=0"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            pass
        
        return 0.0


class MockAudioProcessor(AudioProcessor):
    """Mock audio processor for testing."""
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.calls = []
    
    def stitch_segments(
        self,
        segments: List[AudioSegment],
        output_path: Path,
        pause_duration_ms: Optional[int] = None
    ) -> Path:
        """Mock stitching that creates empty file."""
        self.calls.append({
            "segments": segments,
            "output_path": output_path,
            "pause_duration_ms": pause_duration_ms
        })
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        
        return output_path


