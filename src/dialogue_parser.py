"""
Dialogue parser for The Synthetic Radio Host.

Parses raw script text into structured dialogue turns for TTS processing.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions that can appear in dialogue."""
    
    LAUGHS = "laughs"
    CHUCKLES = "chuckles"
    INTERRUPTS = "interrupts"
    SIGHS = "sighs"
    PAUSES = "pauses"
    CLEARS_THROAT = "clears throat"
    UNKNOWN = "unknown"
    
    @classmethod
    def from_string(cls, text: str) -> "ActionType":
        """Convert string to ActionType."""
        text_lower = text.lower().strip()
        for action in cls:
            if action.value in text_lower:
                return action
        return cls.UNKNOWN


@dataclass
class DialogueAction:
    """Represents an action within dialogue (e.g., [laughs])."""
    
    action_type: ActionType
    raw_text: str
    position: int  # Character position in the dialogue text
    
    def is_laughter(self) -> bool:
        """Check if action is a form of laughter."""
        return self.action_type in [ActionType.LAUGHS, ActionType.CHUCKLES]
    
    def is_interruption(self) -> bool:
        """Check if action is an interruption."""
        return self.action_type == ActionType.INTERRUPTS


@dataclass
class DialogueTurn:
    """
    Represents a single turn in the dialogue.
    
    Attributes:
        speaker: Name of the speaker (e.g., "RAVI", "PRIYA")
        text: The spoken text content
        actions: List of actions embedded in the dialogue
        raw_line: Original unparsed line
    """
    
    speaker: str
    text: str
    actions: List[DialogueAction] = field(default_factory=list)
    raw_line: str = ""
    
    def get_clean_text(self) -> str:
        """Get text with action markers removed (for TTS)."""
        # Remove all bracketed actions
        clean = re.sub(r'\[.*?\]', '', self.text)
        # Clean up extra spaces
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean
    
    def has_laughter(self) -> bool:
        """Check if this turn contains laughter."""
        return any(a.is_laughter() for a in self.actions)
    
    def has_interruption(self) -> bool:
        """Check if this turn contains an interruption."""
        return any(a.is_interruption() for a in self.actions)
    
    def word_count(self) -> int:
        """Count words in the spoken text."""
        return len(self.get_clean_text().split())


class DialogueParser:
    """
    Parses script text into structured dialogue turns.
    
    This parser handles:
    - Speaker label extraction
    - Action marker identification
    - Multi-line dialogue joining
    - Joint speaker lines (e.g., "Host1 and Host2: goodbye!")
    - Validation of script format
    """
    
    # Regex pattern for dialogue lines: "Speaker: text" (case-insensitive speaker name)
    # Supports: "RAVI:", "Ravi:", "ravi:", "Host 1:", "Ravi and Priya:", etc.
    DIALOGUE_PATTERN = re.compile(r'^([A-Za-z][A-Za-z0-9_\s]*?)\s*:\s*(.+)$', re.MULTILINE)
    
    # Regex pattern for joint speakers: "Speaker1 and Speaker2: text"
    JOINT_SPEAKER_PATTERN = re.compile(r'^([A-Za-z]+)\s+and\s+([A-Za-z]+)\s*:\s*(.+)$', re.IGNORECASE)
    
    # Regex pattern for action markers: [action]
    ACTION_PATTERN = re.compile(r'\[([^\]]+)\]')
    
    def __init__(self, expected_speakers: Optional[List[str]] = None):
        """
        Initialize the parser.
        
        Args:
            expected_speakers: List of expected speaker names for validation
        """
        self.expected_speakers = [s.upper() for s in (expected_speakers or ["RAVI", "PRIYA"])]
    
    def parse(self, script_text: str) -> List[DialogueTurn]:
        """
        Parse script text into dialogue turns.
        
        Args:
            script_text: Raw script text with speaker labels
            
        Returns:
            List of DialogueTurn objects
            
        Raises:
            ValueError: If script format is invalid
        """
        if not script_text or not script_text.strip():
            raise ValueError("Script text cannot be empty")
        
        dialogues = []
        
        # Split into lines and process
        lines = script_text.strip().split('\n')
        current_speaker = None
        current_text = []
        current_raw = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip markdown headers, segment markers, comments
            if line.startswith('#') or line.startswith('**') or line.startswith('---'):
                continue
            
            # Skip lines that are just section headers like "SEGMENT 1:" etc.
            if re.match(r'^(SEGMENT|Turn|Opening|Closing|Section)\s*\d*\s*[-:]', line, re.IGNORECASE):
                continue
            
            # First check for joint speaker pattern (e.g., "Ravi and Priya: goodbye!")
            joint_match = self.JOINT_SPEAKER_PATTERN.match(line)
            
            if joint_match:
                # Joint speaker line - create TWO dialogue turns with same text
                speaker1 = joint_match.group(1).strip().upper()
                speaker2 = joint_match.group(2).strip().upper()
                dialogue_text = joint_match.group(3).strip()
                
                if len(dialogue_text) >= 3:
                    # Save previous dialogue if exists
                    if current_speaker and current_text:
                        dialogues.append(self._create_turn(
                            speaker=current_speaker,
                            text=' '.join(current_text),
                            raw_line='\n'.join(current_raw)
                        ))
                        current_speaker = None
                        current_text = []
                        current_raw = []
                    
                    # Add dialogue for first speaker
                    dialogues.append(self._create_turn(
                        speaker=speaker1,
                        text=dialogue_text,
                        raw_line=line
                    ))
                    # Add same dialogue for second speaker (for joint effect)
                    dialogues.append(self._create_turn(
                        speaker=speaker2,
                        text=dialogue_text,
                        raw_line=line
                    ))
                continue
            
            # Check if this is a new speaker line
            match = self.DIALOGUE_PATTERN.match(line)
            
            if match:
                speaker_name = match.group(1).strip()
                dialogue_text = match.group(2).strip()
                
                # Skip if speaker name looks like a section header
                if speaker_name.upper() in ['SEGMENT', 'TURN', 'OPENING', 'CLOSING', 'SECTION', 'EXAMPLE']:
                    continue
                
                # Skip if dialogue is empty or too short
                if len(dialogue_text) < 5:
                    continue
                
                # Save previous dialogue if exists
                if current_speaker and current_text:
                    dialogues.append(self._create_turn(
                        speaker=current_speaker,
                        text=' '.join(current_text),
                        raw_line='\n'.join(current_raw)
                    ))
                
                # Start new dialogue - normalize speaker name to uppercase
                current_speaker = speaker_name.upper().strip()
                current_text = [dialogue_text]
                current_raw = [line]
            else:
                # Continuation of previous dialogue
                if current_speaker:
                    current_text.append(line)
                    current_raw.append(line)
        
        # Don't forget the last dialogue
        if current_speaker and current_text:
            dialogues.append(self._create_turn(
                speaker=current_speaker,
                text=' '.join(current_text),
                raw_line='\n'.join(current_raw)
            ))
        
        # Validate we got some dialogues
        if not dialogues:
            logger.error(f"No dialogues found. Script preview: {script_text[:500]}...")
            raise ValueError("No valid dialogue lines found in script. Check that format is 'Speaker: dialogue text'")
        
        logger.info(f"Parsed {len(dialogues)} dialogue turns")
        return dialogues
    
    def _create_turn(self, speaker: str, text: str, raw_line: str) -> DialogueTurn:
        """
        Create a DialogueTurn with extracted actions.
        
        Args:
            speaker: Speaker name
            text: Dialogue text
            raw_line: Original line
            
        Returns:
            DialogueTurn object
        """
        # Extract actions from text
        actions = self._extract_actions(text)
        
        return DialogueTurn(
            speaker=speaker,
            text=text,
            actions=actions,
            raw_line=raw_line
        )
    
    def _extract_actions(self, text: str) -> List[DialogueAction]:
        """
        Extract action markers from dialogue text.
        
        Args:
            text: Dialogue text
            
        Returns:
            List of DialogueAction objects
        """
        actions = []
        
        for match in self.ACTION_PATTERN.finditer(text):
            action_text = match.group(1)
            action_type = ActionType.from_string(action_text)
            
            actions.append(DialogueAction(
                action_type=action_type,
                raw_text=match.group(0),
                position=match.start()
            ))
        
        return actions
    
    def validate_script(self, script_text: str) -> Tuple[bool, List[str]]:
        """
        Validate script format and content.
        
        Args:
            script_text: Raw script text
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        try:
            dialogues = self.parse(script_text)
        except ValueError as e:
            return False, [str(e)]
        
        # Check minimum dialogue count
        if len(dialogues) < 4:
            errors.append(f"Too few dialogue turns: {len(dialogues)} (minimum 4)")
        
        # Check speaker variety
        speakers = set(d.speaker for d in dialogues)
        if len(speakers) < 2:
            errors.append("Script should have at least 2 speakers")
        
        # Check for expected speakers
        for speaker in self.expected_speakers:
            if speaker not in speakers:
                errors.append(f"Expected speaker '{speaker}' not found")
        
        # Check for fillers (at least some natural speech markers)
        full_text = ' '.join(d.text for d in dialogues).lower()
        fillers = ['umm', 'achcha', 'matlab', 'basically', 'you know', 'yaar', 'toh']
        filler_count = sum(full_text.count(f) for f in fillers)
        if filler_count < 3:
            errors.append(f"Too few fillers ({filler_count}), script may sound unnatural")
        
        # Check for actions
        total_actions = sum(len(d.actions) for d in dialogues)
        if total_actions < 2:
            errors.append(f"Too few action markers ({total_actions}), add [laughs], [interrupts], etc.")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def get_stats(self, dialogues: List[DialogueTurn]) -> dict:
        """
        Get statistics about parsed dialogues.
        
        Args:
            dialogues: List of DialogueTurn objects
            
        Returns:
            Dictionary of statistics
        """
        if not dialogues:
            return {}
        
        speakers = {}
        total_words = 0
        total_actions = 0
        laughter_count = 0
        interruption_count = 0
        
        for turn in dialogues:
            # Speaker counts
            speakers[turn.speaker] = speakers.get(turn.speaker, 0) + 1
            
            # Word count
            total_words += turn.word_count()
            
            # Action counts
            total_actions += len(turn.actions)
            if turn.has_laughter():
                laughter_count += 1
            if turn.has_interruption():
                interruption_count += 1
        
        return {
            "total_turns": len(dialogues),
            "speakers": speakers,
            "total_words": total_words,
            "total_actions": total_actions,
            "laughter_count": laughter_count,
            "interruption_count": interruption_count,
            "avg_words_per_turn": total_words / len(dialogues) if dialogues else 0
        }


def parse_script(script_text: str, expected_speakers: List[str] = None) -> List[DialogueTurn]:
    """
    Convenience function to parse a script.
    
    Args:
        script_text: Raw script text
        expected_speakers: Optional list of expected speakers
        
    Returns:
        List of DialogueTurn objects
    """
    parser = DialogueParser(expected_speakers)
    return parser.parse(script_text)


