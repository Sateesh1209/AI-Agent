"""Central configuration for JARVIS, loaded from environment / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a local .env file if present.
load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    """All runtime settings in one place."""

    backend: str = os.getenv("JARVIS_BACKEND", "anthropic").lower()

    # Anthropic / Claude
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    model: str = os.getenv("JARVIS_MODEL", "claude-opus-4-8")

    # Ollama
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")

    # Voice
    voice_enabled: bool = _as_bool(os.getenv("JARVIS_VOICE"), default=True)

    # Telegram
    telegram_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN") or None
    telegram_allowed_user_id: str | None = (
        os.getenv("TELEGRAM_ALLOWED_USER_ID") or None
    )

    # Safety
    confirm_dangerous: bool = _as_bool(
        os.getenv("JARVIS_CONFIRM_DANGEROUS"), default=True
    )

    # Job applications
    profile_path: str = os.getenv(
        "JARVIS_PROFILE_PATH", str(Path.home() / ".jarvis" / "profile.json")
    )
    # JARVIS drives a dedicated Chrome profile so you stay logged in.
    chrome_user_data_dir: str = os.getenv(
        "JARVIS_CHROME_DIR", str(Path.home() / ".jarvis" / "chrome")
    )

    def validate(self) -> None:
        """Raise a friendly error if the chosen backend is misconfigured."""
        if self.backend == "anthropic" and not self.anthropic_api_key:
            raise RuntimeError(
                "JARVIS_BACKEND is 'anthropic' but ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file, or switch JARVIS_BACKEND=ollama."
            )
        if self.backend not in {"anthropic", "ollama"}:
            raise RuntimeError(
                f"Unknown JARVIS_BACKEND '{self.backend}'. "
                "Use 'anthropic' or 'ollama'."
            )


# A ready-to-use singleton.
config = Config()
