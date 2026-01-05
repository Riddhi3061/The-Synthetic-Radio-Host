"""
Unit tests for DialogueParser module.

Tests cover:
- Dialogue parsing from script text
- Action extraction ([laughs], [interrupts])
- Validation of script format
- Edge cases and error handling
"""

import pytest
from src.dialogue_parser import (
    DialogueParser,
    DialogueTurn,
    DialogueAction,
    ActionType,
    parse_script
)


class TestActionType:
    """Tests for ActionType enum."""
    
    def test_from_string_laughs(self):
        """Test parsing laughter action."""
        assert ActionType.from_string("laughs") == ActionType.LAUGHS
        assert ActionType.from_string("LAUGHS") == ActionType.LAUGHS
        assert ActionType.from_string("she laughs") == ActionType.LAUGHS
    
    def test_from_string_interrupts(self):
        """Test parsing interruption action."""
        assert ActionType.from_string("interrupts") == ActionType.INTERRUPTS
        assert ActionType.from_string("INTERRUPTS") == ActionType.INTERRUPTS
    
    def test_from_string_unknown(self):
        """Test parsing unknown action."""
        assert ActionType.from_string("random action") == ActionType.UNKNOWN
        assert ActionType.from_string("") == ActionType.UNKNOWN


class TestDialogueAction:
    """Tests for DialogueAction dataclass."""
    
    def test_is_laughter(self):
        """Test laughter detection."""
        action_laughs = DialogueAction(
            action_type=ActionType.LAUGHS,
            raw_text="[laughs]",
            position=0
        )
        action_chuckles = DialogueAction(
            action_type=ActionType.CHUCKLES,
            raw_text="[chuckles]",
            position=0
        )
        action_other = DialogueAction(
            action_type=ActionType.SIGHS,
            raw_text="[sighs]",
            position=0
        )
        
        assert action_laughs.is_laughter() is True
        assert action_chuckles.is_laughter() is True
        assert action_other.is_laughter() is False
    
    def test_is_interruption(self):
        """Test interruption detection."""
        action_interrupt = DialogueAction(
            action_type=ActionType.INTERRUPTS,
            raw_text="[interrupts]",
            position=0
        )
        action_other = DialogueAction(
            action_type=ActionType.LAUGHS,
            raw_text="[laughs]",
            position=0
        )
        
        assert action_interrupt.is_interruption() is True
        assert action_other.is_interruption() is False


class TestDialogueTurn:
    """Tests for DialogueTurn dataclass."""
    
    def test_get_clean_text_basic(self):
        """Test basic text cleaning."""
        turn = DialogueTurn(
            speaker="RAVI",
            text="Hello yaar! [laughs] How are you?",
            actions=[]
        )
        
        clean = turn.get_clean_text()
        
        assert clean == "Hello yaar! How are you?"
        assert "[laughs]" not in clean
    
    def test_get_clean_text_multiple_actions(self):
        """Test cleaning with multiple actions."""
        turn = DialogueTurn(
            speaker="PRIYA",
            text="[interrupts] Wait! [laughs] That's so funny [chuckles]",
            actions=[]
        )
        
        clean = turn.get_clean_text()
        
        assert "[interrupts]" not in clean
        assert "[laughs]" not in clean
        assert "[chuckles]" not in clean
        assert "Wait! That's so funny" in clean
    
    def test_word_count(self):
        """Test word counting."""
        turn = DialogueTurn(
            speaker="RAVI",
            text="One two three [laughs] four five",
            actions=[]
        )
        
        # Should count words without action markers
        assert turn.word_count() == 5
    
    def test_has_laughter(self):
        """Test laughter detection in turn."""
        turn_with = DialogueTurn(
            speaker="RAVI",
            text="Ha ha!",
            actions=[DialogueAction(ActionType.LAUGHS, "[laughs]", 0)]
        )
        turn_without = DialogueTurn(
            speaker="RAVI",
            text="Serious talk",
            actions=[]
        )
        
        assert turn_with.has_laughter() is True
        assert turn_without.has_laughter() is False


class TestDialogueParser:
    """Tests for DialogueParser class."""
    
    def test_parse_simple_script(self):
        """Test parsing a simple two-speaker script."""
        parser = DialogueParser()
        
        script = """RAVI: Hello everyone, welcome to our show!

PRIYA: Thanks Ravi, excited to be here!

RAVI: Let's get started."""
        
        dialogues = parser.parse(script)
        
        assert len(dialogues) == 3
        assert dialogues[0].speaker == "RAVI"
        assert dialogues[1].speaker == "PRIYA"
        assert dialogues[2].speaker == "RAVI"
    
    def test_parse_with_actions(self):
        """Test parsing script with action markers."""
        parser = DialogueParser()
        
        script = """RAVI: [laughs] That's so funny!

PRIYA: [interrupts] Wait, let me tell you something!"""
        
        dialogues = parser.parse(script)
        
        assert len(dialogues) == 2
        assert len(dialogues[0].actions) == 1
        assert dialogues[0].actions[0].action_type == ActionType.LAUGHS
        assert len(dialogues[1].actions) == 1
        assert dialogues[1].actions[0].action_type == ActionType.INTERRUPTS
    
    def test_parse_empty_script_raises(self):
        """Test that empty script raises ValueError."""
        parser = DialogueParser()
        
        with pytest.raises(ValueError) as excinfo:
            parser.parse("")
        
        assert "empty" in str(excinfo.value).lower()
    
    def test_parse_no_valid_dialogues_raises(self):
        """Test that script without valid dialogues raises."""
        parser = DialogueParser()
        
        script = "This is just random text without speaker labels."
        
        with pytest.raises(ValueError) as excinfo:
            parser.parse(script)
        
        assert "No valid dialogue" in str(excinfo.value)
    
    def test_parse_multiline_dialogue(self):
        """Test parsing dialogue that spans multiple lines."""
        parser = DialogueParser()
        
        script = """RAVI: This is a long dialogue that
continues on the next line without a new speaker.

PRIYA: Short response."""
        
        dialogues = parser.parse(script)
        
        assert len(dialogues) == 2
        assert "continues" in dialogues[0].text
    
    def test_validate_script_valid(self):
        """Test validation of a valid script."""
        parser = DialogueParser(expected_speakers=["RAVI", "PRIYA"])
        
        script = """RAVI: Arey yaar, umm, let me tell you something!

PRIYA: [laughs] Achcha achcha, go ahead!

RAVI: [interrupts] Wait, matlab, I forgot!

PRIYA: [chuckles] That's so typical of you!"""
        
        is_valid, errors = parser.validate_script(script)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_script_missing_fillers(self):
        """Test validation catches missing fillers."""
        parser = DialogueParser(expected_speakers=["RAVI", "PRIYA"])
        
        # Script without fillers
        script = """RAVI: Hello there.

PRIYA: Hi.

RAVI: Goodbye.

PRIYA: Bye."""
        
        is_valid, errors = parser.validate_script(script)
        
        # Should flag missing fillers
        assert any("filler" in err.lower() for err in errors)
    
    def test_get_stats(self):
        """Test statistics generation."""
        parser = DialogueParser()
        
        script = """RAVI: Hello! [laughs]

PRIYA: [interrupts] Hi there!

RAVI: One two three four five words here."""
        
        dialogues = parser.parse(script)
        stats = parser.get_stats(dialogues)
        
        assert stats["total_turns"] == 3
        assert stats["speakers"]["RAVI"] == 2
        assert stats["speakers"]["PRIYA"] == 1
        assert stats["laughter_count"] == 1
        assert stats["interruption_count"] == 1


class TestParseScriptFunction:
    """Tests for convenience parse_script function."""
    
    def test_parse_script_basic(self):
        """Test basic usage of convenience function."""
        # Dialogues must be at least 5 characters to be parsed
        script = """RAVI: Hello everyone, welcome to the show!

PRIYA: Thanks for having me here today!"""
        
        dialogues = parse_script(script)
        
        assert len(dialogues) == 2
    
    def test_parse_script_with_expected_speakers(self):
        """Test with custom expected speakers."""
        # Dialogues must be at least 5 characters to be parsed
        script = """HOST1: Hello everyone, welcome!

HOST2: Great to be here today!"""
        
        dialogues = parse_script(script, expected_speakers=["HOST1", "HOST2"])
        
        assert len(dialogues) == 2
        assert dialogues[0].speaker == "HOST1"


