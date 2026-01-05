"""
🎙️ The Synthetic Radio Host - Streamlit Web Interface

A beautiful web UI for generating Hinglish radio conversations from Wikipedia articles.

Run with: streamlit run app.py
"""

import streamlit as st
import os
import sys
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="📺 Synthetic Talk Show Host",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #FF6B6B;
        --secondary-color: #4ECDC4;
        --bg-dark: #1a1a2e;
        --bg-card: #16213e;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .main-header h1 {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.9;
    }
    
    /* Card styling */
    .info-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #667eea;
        color: #000000;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: bold;
    }
    
    .status-success {
        background-color: #d4edda;
        color: #155724;
    }
    
    .status-warning {
        background-color: #fff3cd;
        color: #856404;
    }
    
    .status-error {
        background-color: #f8d7da;
        color: #721c24;
    }
    
    /* Script display - explicit colors for visibility */
    .script-box {
        background-color: #1e1e1e !important;
        color: #e0e0e0 !important;
        border: 2px solid #444 !important;
        border-radius: 10px;
        padding: 1.5rem;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.6;
        white-space: pre-wrap;
        max-height: 500px;
        overflow-y: auto;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #6c757d;
        border-top: 1px solid #dee2e6;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)


def check_api_key():
    """Check if Gemini API key is configured."""
    api_key = os.environ.get("GEMINI_API_KEY") or st.session_state.get("api_key")
    return bool(api_key and len(api_key) > 10)


def check_ffmpeg():
    """Check if FFmpeg is installed."""
    import shutil
    return shutil.which("ffmpeg") is not None


def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📺 The Synthetic Talk Show Host</h1>
        <p>Transform Wikipedia Articles into TV-Style Hinglish Talk Shows (Max 5 Minutes)</p>
        <p style="font-size: 0.9rem; opacity: 0.8;">✨ TV Intro • Speaker Intros • Key Points Only • 10-sec Exit</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key - check if already loaded from .env
        st.subheader("🔑 API Key")
        
        env_api_key = os.environ.get("GEMINI_API_KEY")
        
        if env_api_key and len(env_api_key) > 10:
            # API key found in .env
            st.success("✅ API Key loaded from .env")
            st.caption(f"Key: {env_api_key[:8]}...{env_api_key[-4:]}")
        else:
            # No API key in .env, ask user to enter
            st.warning("⚠️ No API key in .env file")
            api_key = st.text_input(
                "Enter Gemini API Key",
                type="password",
                help="Get your free API key from https://makersuite.google.com/app/apikey"
            )
            if api_key:
                os.environ["GEMINI_API_KEY"] = api_key
                st.session_state["api_key"] = api_key
                st.success("✅ API Key set!")
        
        # Status checks
        st.subheader("📊 System Status")
        
        col1, col2 = st.columns(2)
        with col1:
            if check_api_key():
                st.success("✅ API Key")
            else:
                st.error("❌ API Key")
        
        with col2:
            if check_ffmpeg():
                st.success("✅ FFmpeg")
            else:
                st.error("❌ FFmpeg")
        
        # Settings
        st.subheader("🎛️ Settings")
        
        duration = st.slider(
            "Duration (minutes)",
            min_value=2.0,
            max_value=5.0,
            value=4.0,
            step=0.5,
            help="Target duration of the TV-style talk show (MAX 5 min). Includes: TV intro, speaker intros, key points discussion, 10-sec exit."
        )
        
        st.info("📺 **TV Show Format:**\n- Dramatic opening\n- Speaker introductions\n- Key points only\n- 10-sec exit dialogue")
        
        style = st.selectbox(
            "Conversation Style",
            ["Casual & Fun", "Informative", "Sports Commentary"],
            help="Style of the conversation"
        )
        
        st.divider()
        
        # Quick links
        st.subheader("📚 Resources")
        st.markdown("""
        - [📖 Documentation](DESIGN.md)
        - [🎯 Demo Script](DEMO_SCRIPT.md)
        - [🤖 LLM Prompt](LLM_PROMPT.md)
        """)
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📝 Enter Topic or URL")
        
        # Use a form so Enter key triggers generation
        with st.form(key="generate_form"):
            # Topic input
            topic = st.text_input(
                "Wikipedia Topic or URL",
                placeholder="e.g., Mumbai Indians or https://en.wikipedia.org/wiki/Mumbai_Indians",
                help="Enter a Wikipedia topic name OR paste a Wikipedia URL directly (NOT BBC/CNN)"
            )
            
            # Big submit button inside form
            generate_button = st.form_submit_button(
                "📺 Generate TV Talk Show",
                type="primary",
                use_container_width=True
            )
        
        # Example topics (outside form)
        st.markdown("**Quick Examples** (click to auto-fill):")
        example_cols = st.columns(4)
        examples = ["Mumbai Indians", "Shah Rukh Khan", "Indian Cuisine", "Taj Mahal"]
        
        for i, example in enumerate(examples):
            with example_cols[i]:
                if st.button(example, key=f"example_{i}", use_container_width=True):
                    st.session_state["selected_topic"] = example
                    st.rerun()
        
        # Use session state topic if button was clicked
        if "selected_topic" in st.session_state:
            topic = st.session_state["selected_topic"]
            # Clear after use
            del st.session_state["selected_topic"]
            st.info(f"Selected: **{topic}** - Press the Generate button or Enter to start!")
    
    with col2:
        st.header("ℹ️ How It Works")
        st.markdown("""
        <div class="info-card">
        <strong>Step 1:</strong> Enter a Wikipedia topic<br>
        <strong>Step 2:</strong> Press Enter or click Generate<br>
        <strong>Step 3:</strong> AI extracts KEY points only<br>
        <strong>Step 4:</strong> Creates TV-style script with:<br>
        &nbsp;&nbsp;• 📺 Dramatic TV intro<br>
        &nbsp;&nbsp;• 👋 Welcome to listeners<br>
        &nbsp;&nbsp;• 🎤 Speaker introductions<br>
        &nbsp;&nbsp;• 📰 Important points discussion<br>
        &nbsp;&nbsp;• 👋 10-second exit dialogue<br>
        <strong>Step 5:</strong> Download your talk show!
        </div>
        """, unsafe_allow_html=True)
        
        # Warning about non-Wikipedia URLs
        st.warning("⚠️ **Only Wikipedia** topics/URLs are supported. BBC, CNN, etc. won't work.")
    
    st.divider()
    
    # Validation
    if generate_button and not topic:
        st.error("❌ Please enter a Wikipedia topic or URL!")
    
    if generate_button and not check_api_key():
        st.error("❌ Please enter your Gemini API key in the sidebar!")
    
    # Generation process
    if generate_button and topic and check_api_key():
        try:
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Fetch Wikipedia
            status_text.text("📚 Step 1/5: Fetching Wikipedia article...")
            progress_bar.progress(10)
            
            from src.wikipedia_fetcher import WikipediaFetcher
            fetcher = WikipediaFetcher()
            article = fetcher.fetch(topic)
            
            progress_bar.progress(20)
            status_text.text(f"✅ Fetched: {article.title}")
            time.sleep(0.5)
            
            # Step 2: Generate script
            status_text.text("🤖 Step 2/5: Generating TV-style Hinglish script (key points only)...")
            progress_bar.progress(30)
            
            from src.script_generator import ScriptGenerator
            from src.config import get_config
            
            config = get_config()
            generator = ScriptGenerator(config)
            # Duration is capped at 5 minutes in the generator
            script = generator.generate(article, duration_minutes=min(duration, 5.0))
            
            progress_bar.progress(50)
            status_text.text(f"✅ Generated {script.word_count} words")
            time.sleep(0.5)
            
            # Save script - use article title for filename (handles URLs properly)
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            # Create safe filename from article title (not the URL)
            safe_title = "".join(c if c.isalnum() or c in ' _-' else '_' for c in article.title)
            safe_title = safe_title.replace(' ', '_')
            script_path = output_dir / f"{safe_title}_script.txt"
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(f"# Hinglish Radio Script: {article.title}\n")
                f.write(f"# Hosts: {script.host_1} & {script.host_2}\n")
                f.write(f"# Words: {script.word_count}\n")
                f.write("=" * 50 + "\n\n")
                f.write(script.raw_text)
            
            # Step 3: Parse dialogue
            status_text.text("📋 Step 3/5: Parsing dialogue...")
            progress_bar.progress(60)
            
            from src.dialogue_parser import DialogueParser
            parser = DialogueParser(expected_speakers=[config.host_1_name, config.host_2_name])
            
            try:
                dialogues = parser.parse(script.raw_text)
            except ValueError as parse_error:
                st.error(f"❌ Parsing Error: {parse_error}")
                st.warning("Generated script format may not match expected format. Here's the raw script:")
                with st.expander("View Raw Generated Script", expanded=True):
                    st.code(script.raw_text, language=None)
                st.info("💡 The script should have format: `SpeakerName: dialogue text`")
                raise parse_error
            
            status_text.text(f"✅ Parsed {len(dialogues)} dialogue turns")
            time.sleep(0.5)
            
            # Step 4: Convert to audio
            status_text.text("🔊 Step 4/5: Converting to audio...")
            progress_bar.progress(70)
            
            from src.tts_converter import TTSConverter
            tts = TTSConverter(config)
            audio_segments = tts.convert_dialogues(dialogues)
            
            progress_bar.progress(85)
            status_text.text(f"✅ Generated {len(audio_segments)} audio segments")
            time.sleep(0.5)
            
            # Step 5: Stitch audio
            status_text.text("🎵 Step 5/5: Stitching audio...")
            progress_bar.progress(90)
            
            from src.audio_processor import AudioProcessor
            processor = AudioProcessor(config)
            
            output_path = output_dir / f"{safe_title}_show.mp3"
            final_path = processor.stitch_segments(audio_segments, output_path)
            
            # Get duration
            final_duration = processor.get_duration(final_path)
            
            progress_bar.progress(100)
            status_text.text("✅ Generation complete!")
            
            # Read audio bytes before cleanup
            with open(final_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
            
            # Read script text
            with open(script_path, 'r', encoding='utf-8') as f:
                script_text = f.read()
            
            # Store in session state so it persists across reruns
            st.session_state['generated_audio'] = audio_bytes
            st.session_state['generated_script'] = script_text
            st.session_state['generated_raw_script'] = script.raw_text
            st.session_state['audio_duration'] = final_duration
            st.session_state['dialogue_count'] = len(dialogues)
            st.session_state['word_count'] = script.word_count
            st.session_state['safe_title'] = safe_title
            st.session_state['generation_complete'] = True
            
            # Cleanup temp files
            tts.cleanup()
            
            # Success message
            st.success(f"🎉 TV-style talk show generated successfully! (Max 5 min with TV intro, speaker intros & 10-sec exit)")
        
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)
    
    # Display results from session state (persists across reruns)
    if st.session_state.get('generation_complete'):
        # Results section
        st.header("📊 Results")
        
        result_col1, result_col2, result_col3 = st.columns(3)
        
        with result_col1:
            st.metric("Duration", f"{st.session_state['audio_duration']:.1f} sec")
        
        with result_col2:
            st.metric("Dialogue Turns", st.session_state['dialogue_count'])
        
        with result_col3:
            st.metric("Word Count", st.session_state['word_count'])
        
        # Audio player - use session state bytes
        st.subheader("🎧 Listen to Your TV-Style Talk Show")
        st.audio(st.session_state['generated_audio'], format='audio/mp3')
        
        # Download buttons
        download_col1, download_col2 = st.columns(2)
        
        safe_title = st.session_state['safe_title']
        
        with download_col1:
            st.download_button(
                label="📥 Download MP3",
                data=st.session_state['generated_audio'],
                file_name=f"{safe_title}_show.mp3",
                mime="audio/mpeg",
                key="download_mp3"
            )
        
        with download_col2:
            st.download_button(
                label="📄 Download Script",
                data=st.session_state['generated_script'],
                file_name=f"{safe_title}_script.txt",
                mime="text/plain",
                key="download_script"
            )
        
        # Script preview
        st.subheader("📜 Script Preview")
        
        with st.expander("View Generated Script", expanded=True):
            # Use st.code for better visibility across themes
            st.code(st.session_state['generated_raw_script'], language=None)
        
        # Button to generate new show
        if st.button("🔄 Generate New Show", type="secondary"):
            # Clear session state
            for key in ['generated_audio', 'generated_script', 'generated_raw_script', 
                       'audio_duration', 'dialogue_count', 'word_count', 'safe_title', 'generation_complete']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>Built with ❤️ for AI Hackathons</p>
        <p>📺 The Synthetic Talk Show Host | Transform Wikipedia into TV-Style Talk Shows</p>
        <p style="font-size: 0.8rem; opacity: 0.7;">Features: TV Intro • Speaker Intros • Key Points Only • 10-sec Exit • Max 5 Minutes</p>
    </div>
    """, unsafe_allow_html=True)


# Script-only mode
def generate_script_only():
    """Alternative page for script-only generation."""
    st.header("📝 Script Only Mode")
    st.info("Generate just the script without audio (faster, no FFmpeg needed)")
    
    topic = st.text_input("Wikipedia Topic", placeholder="e.g., Mumbai Indians")
    
    if st.button("Generate Script Only") and topic and check_api_key():
        with st.spinner("Generating script..."):
            try:
                from src.pipeline import SyntheticRadioHost
                
                pipeline = SyntheticRadioHost()
                script = pipeline.generate_script_only(topic)
                
                st.success("✅ Script generated!")
                st.text_area("Generated Script", script.raw_text, height=400)
                
                st.download_button(
                    "📥 Download Script",
                    script.raw_text,
                    file_name=f"{topic}_script.txt"
                )
            
            except Exception as e:
                st.error(f"Error: {e}")


if __name__ == "__main__":
    # Check for script-only mode
    if len(sys.argv) > 1 and sys.argv[1] == "--script-only":
        generate_script_only()
    else:
        main()

