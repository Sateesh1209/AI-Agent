"""The JARVIS agent: ties together the brain, the tools and the system prompt."""

from __future__ import annotations

from .brain import make_brain
from .config import Config, config as default_config
from .tools import load_builtin_tools

SYSTEM_PROMPT = """You are JARVIS, a helpful AI assistant that runs on the \
user's own computer. You can take real actions on this machine by calling the \
tools available to you: running shell commands, reading and writing files, \
opening applications and URLs, and reporting system info.

Guidelines:
- The user talks to you by voice or text. Keep spoken replies short and clear.
- When a request requires an action on the computer, USE A TOOL rather than \
  just describing what to do.
- Think step by step: you may call several tools in a row to finish a task.
- Be careful with destructive actions (deleting files, etc.). If something is \
  risky or ambiguous, ask the user to confirm before doing it.
- After finishing, briefly tell the user what you did.
"""


class Jarvis:
    """Main entry point used by every interface (CLI, voice, Telegram)."""

    def __init__(self, config: Config | None = None):
        self.config = config or default_config
        self.config.validate()
        self.registry = load_builtin_tools()
        self.brain = make_brain(self.config, self.registry, SYSTEM_PROMPT)

    def ask(self, text: str) -> str:
        """Send a user instruction to JARVIS and get its reply."""
        return self.brain.chat(text)
