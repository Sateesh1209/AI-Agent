# JARVIS 🤖

A voice-controlled AI agent that runs **on your own machine** and does what you
tell it to — open apps, manage files, run commands, browse the web, and more.
Talk to it by voice, text, or from your phone via Telegram.

> This is the foundation. It already works end-to-end; every piece is built to
> be extended with your own tools and tasks (like auto-applying to jobs).

## What it can do today

- 🧠 **Two brains** — use Claude (Anthropic API) for best quality, or run a
  free, private, offline model with [Ollama](https://ollama.com).
- 🗣️ **Voice** — speak to JARVIS and hear it reply (offline TTS).
- 💬 **Telegram** — command JARVIS from your phone.
- 🛠️ **Real actions on your computer** via tools:
  - run shell commands
  - read / write / list files
  - open apps and URLs
  - report system info
- 🔌 **Easily extensible** — add a new capability by writing one decorated
  Python function (see *Adding your own tools* below).

## Architecture

```
main.py                 # launcher: text | voice | telegram
jarvis/
  config.py             # settings from .env
  agent.py              # the JARVIS agent (system prompt + wiring)
  brain.py              # LLM backends (Anthropic + Ollama) with a tool loop
  voice.py              # speech-to-text + text-to-speech
  tools/                # the things JARVIS can actually DO
    shell.py            #   run shell commands
    filesystem.py       #   read/write/list files
    system.py           #   open apps/URLs, system info
  interfaces/           # ways to talk to JARVIS
    cli.py              #   typed chat
    voice_loop.py       #   voice
    telegram_bot.py     #   Telegram
```

The flow: **you speak/type → an interface → the agent → the brain (LLM) decides
which tools to call → tools run on your machine → JARVIS replies.**

## Setup

> Requires **Python 3.10+**. Designed to run on your **local machine** (macOS,
> Windows, or Linux) — not in the cloud — so it can actually control your
> computer.

```bash
# 1. Clone and enter the repo
git clone https://github.com/sateesh1209/ai-agent.git
cd ai-agent

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# then edit .env (add your ANTHROPIC_API_KEY, or set JARVIS_BACKEND=ollama)
```

### Microphone support (for voice)

`SpeechRecognition` needs PyAudio:

- **macOS:** `brew install portaudio && pip install pyaudio`
- **Linux:** `sudo apt-get install portaudio19-dev && pip install pyaudio`
- **Windows:** `pip install pyaudio`

If no microphone is available, voice mode automatically falls back to typing.

### Free brain with Ollama (optional)

```bash
# install from https://ollama.com, then:
ollama pull llama3.1
# in .env: JARVIS_BACKEND=ollama
```

## Usage

```bash
python main.py            # voice mode (mic, or text fallback)
python main.py text       # type to JARVIS in the terminal
python main.py voice      # voice mode
python main.py telegram   # run the Telegram bot
```

Examples of things to say/type:

- "What's the date and time?"
- "List the files in my Downloads folder."
- "Open Spotify."
- "Create a file called notes.txt with my todo list."
- "Open github.com in my browser."

## Adding your own tools

Drop a function in `jarvis/tools/` and decorate it. That's it — JARVIS can now
use it.

```python
from . import tool

@tool(
    name="get_weather",
    description="Get the current weather for a city.",
    input_schema={
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
)
def get_weather(city: str) -> str:
    ...  # call an API
    return f"It's sunny in {city}."
```

Then import your module in `jarvis/tools/__init__.py`'s `load_builtin_tools()`.

## Roadmap ideas

- 🌐 Browser automation tool (Playwright) → auto-apply to jobs on Workday,
  Greenhouse, company sites.
- 📅 Calendar / email tools.
- 🧠 Persistent memory across sessions.
- 🔊 Wake-word detection ("Hey JARVIS").

## Safety

JARVIS can run real commands on your computer. By default
(`JARVIS_CONFIRM_DANGEROUS=true`) it asks before running anything that looks
destructive (e.g. `rm`, `shutdown`). Keep your `.env` private — it holds your
API keys and bot token.
