"""Health check: verify JARVIS is set up correctly.

Run:  python main.py check

Prints what's installed, what's configured, and (if a backend is ready) does a
tiny live test to prove the brain works — without needing a mic, Telegram, or a
browser.
"""

from __future__ import annotations

import importlib.util

OK = "✅"
NO = "❌"
WARN = "⚠️ "


def _have(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def run() -> None:
    import platform
    import sys

    print("\n=== JARVIS self-check ===\n")
    print(f"{OK} Python {platform.python_version()}  ({sys.executable})")
    if sys.version_info < (3, 10):
        print(f"{WARN}Python 3.10+ is recommended.")

    # 1) Core dependencies
    print("\n-- Dependencies --")
    core = {
        "dotenv": "python-dotenv (config)",
        "anthropic": "anthropic (Claude brain)",
        "requests": "requests (Ollama brain)",
        "apscheduler": "APScheduler (reminders/scheduling)",
    }
    optional = {
        "speech_recognition": "SpeechRecognition (voice in)",
        "pyttsx3": "pyttsx3 (voice out)",
        "telegram": "python-telegram-bot (Telegram)",
        "playwright": "playwright (job applications)",
    }
    for mod, label in core.items():
        print(f"  {OK if _have(mod) else NO} {label}")
    print("  (optional)")
    for mod, label in optional.items():
        print(f"  {OK if _have(mod) else WARN} {label}")

    # 2) Configuration
    print("\n-- Configuration --")
    try:
        from ..config import config

        print(f"  Backend: {config.backend}")
        if config.backend == "anthropic":
            key = config.anthropic_api_key
            print(f"  {OK if key else NO} ANTHROPIC_API_KEY "
                  f"{'set (' + key[:7] + '…)' if key else 'MISSING'}")
            print(f"  Model: {config.model}")
        else:
            print(f"  Ollama host: {config.ollama_host}  model: {config.ollama_model}")
        print(f"  {OK if config.telegram_token else WARN} Telegram token "
              f"{'set' if config.telegram_token else 'not set (optional)'}")
        from pathlib import Path

        prof = Path(config.profile_path).expanduser()
        print(f"  {OK if prof.is_file() else WARN} Job profile "
              f"{'found' if prof.is_file() else 'not set up (optional for jobs)'}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {NO} Could not load config: {exc}")
        return

    # 3) Tools register
    print("\n-- Tools --")
    try:
        from ..tools import load_builtin_tools

        names = [t.name for t in load_builtin_tools().all()]
        print(f"  {OK} {len(names)} tools loaded: {', '.join(names)}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {NO} Tool loading failed: {exc}")

    # 4) Live brain test (only if backend looks ready)
    print("\n-- Live test --")
    try:
        from ..config import config

        config.validate()
    except Exception as exc:  # noqa: BLE001
        print(f"  {WARN}Skipped (backend not ready): {exc}")
        print("\nFix the items above, then run 'python main.py check' again.\n")
        return

    try:
        from ..agent import Jarvis

        jarvis = Jarvis()
        reply = jarvis.ask("Reply with exactly: JARVIS online and ready.")
        print(f"  {OK} Brain replied: {reply.strip()[:120]}")
        print(f"\n{OK} JARVIS is working! Try:  python main.py text\n")
    except Exception as exc:  # noqa: BLE001
        print(f"  {NO} Brain test failed: {exc}")
        print("  (Check your API key / that Ollama is running.)\n")
