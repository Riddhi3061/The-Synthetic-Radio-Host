"""
Script generator for The Synthetic Radio Host.

Uses LLM to generate natural Hinglish conversations from Wikipedia content.
This module contains the critical prompt engineering for achieving authentic
radio host dialogue.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from .config import get_config, Config
from .wikipedia_fetcher import ArticleData

logger = logging.getLogger(__name__)


# =============================================================================
# PROMPT ENGINEERING - THE HEART OF HINGLISH GENERATION
# =============================================================================

SYSTEM_PROMPT = """You are an expert scriptwriter for Indian TV/Radio talk shows. Your specialty is writing natural, engaging conversations in HINGLISH - a mix of Hindi and English written in Roman script (Latin alphabet).

## HINGLISH RULES:
1. Mix Hindi and English words naturally in each sentence
2. Write ALL text in Roman script (no Devanagari)
3. Use common Hindi words: achcha, yaar, matlab, bilkul, dekho, sunno, hai na, kya baat hai
4. English for technical terms, Hindi for emotions and reactions
5. Code-switch naturally mid-sentence, like real Indians speak

## EXAMPLES OF GOOD HINGLISH:
- "Arey yaar, ye Mumbai Indians ka history toh amazing hai!"
- "Matlab dekho, 2008 mein start hui thi team, right? And now five-time champions!"
- "Achcha achcha, tell me more about Rohit Sharma's captaincy"
- "Basically, unka bowling attack bahut strong hai"

## CONVERSATION STYLE:
You must write like real TV show hosts talk:
1. Use FILLERS naturally: umm, err, achcha, basically, you know, matlab, like, toh
2. Include INTERRUPTIONS marked as [interrupts]
3. Add REACTIONS: [laughs], [chuckles], haan haan, achcha achcha, wow, arrey wah
4. Make it INFORMAL and friendly, like friends chatting
5. Hosts should AGREE, DISAGREE, and BUILD on each other's points
6. Keep content FOCUSED - only important facts, no fluff"""


def get_script_generation_prompt(
    article: ArticleData,
    host_1: str,
    host_2: str,
    duration_minutes: float,
    word_count: int
) -> str:
    """
    Generate the main prompt for script creation.
    
    This prompt is carefully engineered to produce:
    1. TV show style dramatic opening
    2. Authentic Hinglish dialogue
    3. Natural conversation flow with only KEY points
    4. Proper speaker labels for parsing
    5. 10-second exit dialogue
    
    Args:
        article: Wikipedia article data
        host_1: Name of first host
        host_2: Name of second host
        duration_minutes: Target duration in minutes (MAX 5 minutes)
        word_count: Target word count
        
    Returns:
        Complete prompt string
    """
    # Cap duration at 5 minutes max
    duration_minutes = min(duration_minutes, 5.0)
    
    # Calculate dialogue turns (aim for ~8 turns per minute for concise content)
    min_dialogues = max(25, int(duration_minutes * 8))
    max_dialogues = min_dialogues + 5
    
    return f"""## YOUR TASK
Write a COMPLETE TV-STYLE TALK SHOW conversation (MAXIMUM {duration_minutes} minutes) between two Indian hosts discussing: **{article.title}**

## ⚠️ CRITICAL REQUIREMENTS:
1. **MAXIMUM {max_dialogues} DIALOGUE TURNS** - Keep it concise!
2. **MAXIMUM {word_count} WORDS** - Quality over quantity!
3. **ONLY IMPORTANT POINTS** - Extract and discuss ONLY the KEY facts from the article
4. **TV SHOW FORMAT** - Dramatic opening, host introductions, focused content, quick exit
5. **TOTAL DURATION: MAX 5 MINUTES** - Be concise and impactful!

## HOST PROFILES
- **{host_1}**: Lead anchor, warm authoritative voice, introduces the show dramatically. Senior host who guides the conversation.
- **{host_2}**: Co-host, energetic personality, asks insightful questions. Adds enthusiasm and reactions.

## KEY CONTENT TO EXTRACT & DISCUSS (ONLY IMPORTANT POINTS):
{article.get_content_for_script(max_words=800)}

⚠️ From the above content, ONLY extract and discuss:
- 3-4 most important facts/achievements
- 1-2 key dates or milestones
- 1-2 notable personalities
- Current relevance (if any)

## TV SHOW STRUCTURE (FOLLOW EXACTLY):

### 🎬 SEGMENT 1: TV SHOW INTRO (3 turns ONLY - NO REPETITION!)
**SINGLE FLOW INTRODUCTION - Each host speaks ONCE!**

Turn 1 - {host_1} ONLY (Main host does ALL introductions):
- Welcome audience: "Namaste doston! Gyan Ki Baatein mein aapka swagat hai!"
- Introduce self: "Main hoon aapka host {host_1}!"
- Announce topic: "Aaj hum baat karenge {article.title} ke baare mein!"
- Introduce co-host: "Aur aaj mere saath hain {host_2}!"
- This should be ONE dialogue covering welcome + self intro + topic + co-host intro

Turn 2 - {host_2} ONLY (Co-host responds):
- Thank host: "Thank you {host_1}! Namaste everyone!"
- Show excitement: "Yaar mujhe toh ye topic bahut interesting lagta hai!"
- Ask first question to start discussion: "Toh {host_1}, batao iska story kya hai?"

Turn 3 - {host_1}: Answer and begin main discussion
- Start explaining the first key fact about the topic

⚠️ NO MORE INTRO AFTER THIS - GO DIRECTLY TO MAIN CONTENT!

### 📰 SEGMENT 2: MAIN DISCUSSION (15-18 turns) - ~3-3.5 minutes
**FOCUSED discussion on ONLY KEY POINTS**

- Cover ONLY 3-4 most important facts from the article
- Each fact gets 3-4 turns of discussion
- Include specific dates, numbers, names
- Natural back-and-forth conversation
- {host_1} explains facts, {host_2} reacts and asks follow-up questions
- Keep each dialogue 20-35 words (concise but meaningful)

### 🎯 SEGMENT 3: QUICK SUMMARY (2 turns) - ~15 seconds
- Brief recap: "Toh aaj humne jaana..."
- Co-host agrees and appreciates

### 🎬 SEGMENT 4: NATURAL EXIT DIALOGUE (3 turns) - ~10 SECONDS
**WARM, NATURAL INDIAN TV SHOW SIGN-OFF**

Turn 1 - {host_1}: Express hope + Thank audience
- "Toh I hope aap logon ko aaj ka show pasand aaya!"
- Warm, sincere tone
- ~10-12 words

Turn 2 - {host_2}: Tease next episode + Build anticipation
- "Haan bilkul! Milte hain agle episode mein kuch aur interesting topic ke saath!"
- Sound excited about future
- ~10-12 words

Turn 3 - {host_1} ONLY: Final goodbye (MAIN HOST CLOSES THE SHOW)
- "Tab tak ke liye goodbye!"
- Only main host says the final goodbye
- ~5-6 words ONLY

## ⚠️ CRITICAL OUTPUT FORMAT (MUST FOLLOW EXACTLY):
- **PLAIN TEXT ONLY** - NO markdown, NO headers, NO bullet points in the script
- Every dialogue line MUST be: `{host_1}: dialogue text` or `{host_2}: dialogue text`
- Speaker name followed by COLON and SPACE, then the dialogue
- One dialogue per paragraph (separated by blank line)
- Actions in square brackets: [laughs], [chuckles], [excited]
- Each turn: 20-35 words (CONCISE!)
- Exit turns: 6-10 words ONLY
- ALTERNATE speakers always
- DO NOT include segment headers or turn numbers in the output

## HINGLISH STYLE (Natural Mix):
- Hindi connectors: toh, matlab, basically, achcha, yaar
- Hindi reactions: waah, kya baat hai, sahi mein, bilkul, arrey
- English for facts/technical terms, Hindi for emotions
- Natural code-switching mid-sentence

## EXAMPLE TV SHOW OPENING (FOLLOW THIS EXACTLY - NO REPETITION!):
{host_1}: Namaste doston! Gyan Ki Baatein mein aapka swagat hai! Main hoon aapka host {host_1}! Aaj hum baat karenge {article.title} ke baare mein aur mere saath hain {host_2}!

{host_2}: Thank you {host_1}! Namaste everyone! Yaar ye topic toh bahut interesting hai! Toh batao {host_1}, iska story kya hai?

{host_1}: Haan toh dekho, ye story shuru hui...

## EXAMPLE NATURAL EXIT (FOLLOW THIS STYLE):
{host_1}: Toh I hope aap logon ko aaj ka show pasand aaya!

{host_2}: Haan bilkul! Milte hain agle episode mein kuch aur interesting topic ke saath!

{host_1}: Tab tak ke liye goodbye!

## ⚠️ CRITICAL RULES:
1. MAXIMUM {max_dialogues} dialogues - DO NOT exceed!
2. EXIT must be NATURAL INDIAN STYLE: "I hope aap logon ko pasand aaya... milte hain agle episode mein... tab tak ke liye goodbye!"
3. Focus ONLY on important points - skip minor details
4. Total audio should be UNDER 5 minutes
5. INTRO: {host_1} welcomes everyone, introduces self, topic AND {host_2} in ONE dialogue!
6. INTRO: {host_2} says "Thank you" and asks first question - NO self-introduction needed!
7. NO REPETITION in intro - each info mentioned ONCE only!
8. OUTPUT FORMAT: Only `{host_1}: text` and `{host_2}: text` lines!
9. ENDING: Main host ({host_1}) says "Tab tak ke liye goodbye!" at the very end!

## ❌ DO NOT:
- Include markdown formatting (##, **, etc.)
- Include segment headers or turn numbers
- Include every detail from the article
- Make exit longer than 10 seconds
- Exceed {word_count} words total
- Have {host_2} introduce themselves separately (host 1 already introduced them!)
- Repeat the welcome or topic announcement multiple times
- Have both hosts say "Namaste" separately in intro
- Have lengthy introductions - ONLY 3 turns for intro!

## ✅ CORRECT OUTPUT FORMAT EXAMPLE (NO INTRO REPETITION!):
{host_1}: Namaste doston! Gyan Ki Baatein mein aapka swagat hai! Main hoon aapka host {host_1}! Aaj hum baat karenge {article.title} ke baare mein aur mere saath hain {host_2}!

{host_2}: Thank you {host_1}! Namaste everyone! Yaar ye topic toh bahut interesting hai! Toh batao {host_1}, iska story kya hai?

{host_1}: Haan toh dekho, ye story shuru hui jab...

[... main discussion about key facts ...]

{host_1}: Toh I hope aap logon ko aaj ka show pasand aaya!

{host_2}: Haan bilkul! Milte hain agle episode mein kuch aur interesting topic ke saath!

{host_1}: Tab tak ke liye goodbye!

## NOW WRITE THE COMPLETE SCRIPT (PLAIN DIALOGUE ONLY, NO HEADERS):"""


@dataclass
class GeneratedScript:
    """Container for generated script data."""
    
    raw_text: str
    topic: str
    host_1: str
    host_2: str
    word_count: int
    
    def __str__(self) -> str:
        return self.raw_text


class ScriptGenerator:
    """
    Generates Hinglish radio scripts using LLM.
    
    This class handles:
    - Prompt construction with proper engineering
    - LLM API calls (Gemini or OpenAI)
    - Response validation and cleaning
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the script generator.
        
        Args:
            config: Configuration object (uses global config if None)
        """
        self.config = config or get_config()
        self._client = None
        self._model = None
    
    def _init_gemini(self):
        """Initialize Google Gemini client."""
        try:
            import google.generativeai as genai
            
            if not self.config.gemini_api_key:
                raise ValueError(
                    "Gemini API key not found. Set GEMINI_API_KEY environment variable."
                )
            
            genai.configure(api_key=self.config.gemini_api_key)
            
            self._model = genai.GenerativeModel(
                self.config.llm.model_name,
                generation_config={
                    "temperature": self.config.llm.temperature,
                    "top_p": self.config.llm.top_p,
                    "max_output_tokens": self.config.llm.max_tokens,
                }
            )
            logger.info(f"Initialized Gemini model: {self.config.llm.model_name}")
            
        except ImportError:
            raise ImportError(
                "google-generativeai is required. Install with: pip install google-generativeai"
            )
    
    def generate(
        self,
        article: ArticleData,
        duration_minutes: float = 2.0,
        host_1: Optional[str] = None,
        host_2: Optional[str] = None
    ) -> GeneratedScript:
        """
        Generate a Hinglish TV-style talk show script from article data.
        
        Args:
            article: Wikipedia article data
            duration_minutes: Target duration in minutes (MAX 5 minutes)
            host_1: Name of first host (default from config)
            host_2: Name of second host (default from config)
            
        Returns:
            GeneratedScript object with the conversation
        """
        # Use default host names if not provided
        host_1 = host_1 or self.config.host_1_name
        host_2 = host_2 or self.config.host_2_name
        
        # Cap duration at 5 minutes maximum
        duration_minutes = min(duration_minutes, 5.0)
        
        # Calculate target word count (aim for ~120 words per minute for concise content)
        # 5 min max = ~600 words max
        word_count = min(int(duration_minutes * 120), 600)
        
        logger.info(f"Generating TV-style script: {duration_minutes} min, ~{word_count} words target")
        
        # Build the prompt
        user_prompt = get_script_generation_prompt(
            article=article,
            host_1=host_1,
            host_2=host_2,
            duration_minutes=duration_minutes,
            word_count=word_count
        )
        
        # Generate using LLM
        raw_text = self._call_llm(user_prompt)
        
        # Clean and validate
        raw_text = self._clean_script(raw_text)
        
        return GeneratedScript(
            raw_text=raw_text,
            topic=article.title,
            host_1=host_1,
            host_2=host_2,
            word_count=len(raw_text.split())
        )
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM with the given prompt.
        
        Args:
            prompt: User prompt for generation
            
        Returns:
            Generated text response
        """
        # Initialize client if needed
        if self._model is None:
            self._init_gemini()
        
        logger.info("Generating script with LLM...")
        
        # Combine system and user prompts
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        
        try:
            response = self._model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise RuntimeError(f"Script generation failed: {e}")
    
    def _clean_script(self, text: str) -> str:
        """
        Clean and validate generated script.
        
        Args:
            text: Raw generated text
            
        Returns:
            Cleaned script text
        """
        # Remove any markdown formatting
        text = text.replace("```", "")
        
        # Remove extra whitespace
        lines = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if line:
                lines.append(line)
        
        return "\n\n".join(lines)
    
    def generate_from_topic(
        self,
        topic: str,
        duration_minutes: float = 2.0
    ) -> GeneratedScript:
        """
        Generate script directly from a topic (fetches Wikipedia automatically).
        
        Args:
            topic: Wikipedia article topic
            duration_minutes: Target duration in minutes
            
        Returns:
            GeneratedScript object
        """
        from .wikipedia_fetcher import WikipediaFetcher
        
        fetcher = WikipediaFetcher()
        article = fetcher.fetch(topic)
        
        return self.generate(article, duration_minutes)


# =============================================================================
# PROMPT EXPLANATION (FOR DOCUMENTATION)
# =============================================================================

PROMPT_EXPLANATION = """
## How the Hinglish Prompt Engineering Works

### 1. Explicit Language Definition
The prompt explicitly defines Hinglish as "Hindi and English in Roman script" with
concrete examples. This prevents the model from:
- Using Devanagari script
- Writing pure English or pure Hindi
- Code-switching unnaturally

### 2. Filler Enforcement
The prompt requires "at least 8 fillers" with specific examples (umm, achcha, matlab).
This forces the model to include these markers that make speech sound natural.
The fillers are both Hindi (achcha, matlab) and English (umm, basically) for authentic
code-switching.

### 3. Interruption Markers
By requiring "[interrupts]" tags, we:
- Create natural conversation dynamics
- Give the TTS system cues for timing
- Prevent robotic turn-taking

### 4. Character Differentiation
Each host has a defined personality:
- RAVI: Senior, uses more Hindi, explanatory
- PRIYA: Younger, uses more English, asks questions

This ensures the dialogue has natural dynamics rather than two identical voices.

### 5. Structural Format
The "SPEAKER: dialogue" format enables:
- Easy parsing into DialogueTurn objects
- Clear voice assignment for TTS
- Validation of script structure

### 6. Quantity Requirements
Specific numbers (8 fillers, 3 interruptions, 4 reactions) force the model to
hit quality targets rather than taking shortcuts.
"""


def get_prompt_explanation() -> str:
    """Return the prompt engineering explanation."""
    return PROMPT_EXPLANATION


