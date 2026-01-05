# 🎙️ The Synthetic Radio Host

> Generate natural-sounding Hinglish radio conversations from Wikipedia articles using AI.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Project Overview

The Synthetic Radio Host is an AI-powered pipeline that transforms Wikipedia articles into engaging, natural-sounding radio conversations in **Hinglish** (Hindi + English in Roman script). The system generates a 2-minute conversational script between two Indian radio hosts, complete with:

- Natural fillers (umm, achcha, yaar, matlab)
- Realistic interruptions
- Light laughter and reactions
- Informal, friendly tone

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Wikipedia     │────▶│   LLM Script     │────▶│   Dialogue      │
│   Article       │     │   Generator      │     │   Parser        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Final MP3     │◀────│   Audio          │◀────│   TTS           │
│   Output        │     │   Stitcher       │     │   Converter     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## 🚀 Quick Start (Windows)

### Prerequisites

1. **Python 3.9+** - Download from [python.org](https://www.python.org/downloads/)
2. **FFmpeg** - Required for audio processing
   - Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (ffmpeg-release-essentials.zip)
   - Extract to `C:\ffmpeg`
   - Add `C:\ffmpeg\bin` to PATH

### Installation

```powershell
# Navigate to the project directory
cd synthetic_radio_host

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set up API key
copy env.example.txt .env
notepad .env
# Add: GEMINI_API_KEY=your_key_here
```

### Get Gemini API Key (Free)

1. Go to: https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key to your `.env` file

---

## 🌐 Option 1: Web UI (Recommended - Easiest!)

**The easiest way to use this project is through the Streamlit web interface:**

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Run the Streamlit app
streamlit run app.py
```

This will open a browser at `http://localhost:8501` with a beautiful UI:

![Streamlit UI](docs/streamlit_ui.png)

### Web UI Features:
- ✅ Enter any Wikipedia **topic OR URL**
- ✅ Quick example buttons
- ✅ Real-time progress tracking
- ✅ Audio player in browser
- ✅ Download MP3 and script
- ✅ No command line needed!

---

## 💻 Option 2: Command Line

### Generate Full Radio Show (Topic Name)
```powershell
python -m src.main --topic "Mumbai Indians" --output "output\show.mp3"
```

### Generate Full Radio Show (Wikipedia URL)
```powershell
python -m src.main --topic "https://en.wikipedia.org/wiki/Virat_Kohli" --output "output\show.mp3"
```

### Generate Script Only (No Audio)
```powershell
python -m src.main --topic "Mumbai Indians" --script-only
```

### Generate Audio from Existing Script
```powershell
python -m src.main --from-script "output\show.txt" --output "output\show.mp3"
```

### With Verbose Output
```powershell
python -m src.main --topic "Shah Rukh Khan" --output "output\srk_show.mp3" --verbose
```

---

## 🐍 Option 3: Python API

```python
from src.pipeline import SyntheticRadioHost

# Initialize the pipeline
radio_host = SyntheticRadioHost()

# Generate radio show from Wikipedia article
output_path = radio_host.generate(
    topic="Mumbai Indians",
    duration_minutes=2,
    output_path="output\\mumbai_indians_show.mp3"
)

print(f"Audio saved to: {output_path}")
```

---

## 📓 Option 4: Google Colab

Open `notebooks/synthetic_radio_host.ipynb` in Google Colab for a guided notebook experience.

---

## 📁 Project Structure

```
synthetic_radio_host\
├── app.py                  # 🌐 Streamlit Web UI
├── src\
│   ├── main.py             # CLI entry point
│   ├── pipeline.py         # Main orchestrator
│   ├── wikipedia_fetcher.py
│   ├── script_generator.py
│   ├── dialogue_parser.py
│   ├── tts_converter.py
│   ├── audio_processor.py
│   └── config.py
├── notebooks\
│   └── synthetic_radio_host.ipynb
├── output\                 # Generated files go here
│   ├── show.mp3
│   └── show.txt
├── DESIGN.md              # Technical documentation
├── DEMO_SCRIPT.md         # Hackathon presentation script
├── LLM_PROMPT.md          # LLM prompt documentation
├── HINGLISH_PROMPT_EXPLANATION.md
├── DELIVERABLES.md        # Submission checklist
├── requirements.txt
└── README.md
```

---

## 📊 Example Output

### Input
Wikipedia article: "Mumbai Indians"

### Generated Script (excerpt)
```
RAVI: Hello everyone and welcome back to our show! Main hoon RAVI, aur aaj 
hamare saath hai meri amazing co-host...

PRIYA: Hi listeners! Main PRIYA, and today we're talking about something 
super exciting - Mumbai Indians! [laughs]

RAVI: Bilkul! You know, they've won FIVE IPL championships - 2013, 2015, 
2017, 2019, and 2020. Kya record hai yaar!

PRIYA: [interrupts] Arrey haan! And Rohit Sharma's captaincy, matlab, 
incredible hai!
```

### Output
🎵 `output\show.mp3` (2-3 minute audio with two distinct voices)

---

## 🔑 API Keys Required

| API | Required | Cost | Get Key |
|-----|----------|------|---------|
| Google Gemini | Yes | Free | [makersuite.google.com](https://makersuite.google.com/app/apikey) |
| Edge TTS | No | Free | Built-in, no key needed |

---

## 🛠️ Troubleshooting

### FFmpeg Not Found
```powershell
# Check if installed
ffmpeg -version

# If not, download from https://www.gyan.dev/ffmpeg/builds/
# Extract to C:\ffmpeg
# Add to PATH:
$env:PATH += ";C:\ffmpeg\bin"
```

### SSL Certificate Error
This is common on corporate networks. The code includes automatic SSL bypass.

### Rate Limit Error (429)
Wait 30-60 seconds between requests. Free tier has limits.

### PowerShell Execution Policy
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [DESIGN.md](DESIGN.md) | Technical architecture & code explanation |
| [LLM_PROMPT.md](LLM_PROMPT.md) | Complete LLM prompt documentation |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | 3-minute hackathon presentation |
| [DELIVERABLES.md](DELIVERABLES.md) | Submission checklist |
| [HINGLISH_PROMPT_EXPLANATION.md](HINGLISH_PROMPT_EXPLANATION.md) | 100-word Hinglish explanation |

---

## 🧪 Running Tests

```powershell
# Run all tests
pytest tests\ -v

# Run with coverage
pytest tests\ -v --cov=src --cov-report=html
```

---

## 📝 License

MIT License - feel free to use for hackathons and competitions!

---

Built with ❤️ for AI Hackathons
