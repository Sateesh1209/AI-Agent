"""The JARVIS agent: ties together the brain, the tools and the system prompt."""

from __future__ import annotations

from . import runtime
from .brain import make_brain
from .config import Config, config as default_config
from .notify import ConsoleNotifier, Notifier
from .scheduler import JarvisScheduler
from .store import TaskStore
from .tools import load_builtin_tools

SYSTEM_PROMPT = """You are JARVIS, a capable AI assistant that runs on the \
user's own computer and acts on their behalf. You can take real actions on \
this machine by calling the tools available to you: running shell commands, \
reading/writing files, opening applications and URLs, reporting system info, \
and scheduling reminders or recurring tasks.

Guidelines:
- The user talks to you by voice, text, or Telegram. Keep replies short and \
  clear, especially for voice.
- When a request needs an action, USE A TOOL rather than just describing it.
- NEVER guess or make up facts like the current time, date, file contents, or
  system info. ALWAYS call the matching tool (e.g. get_system_info for the
  time/date) and use its real result. If you don't have a tool for something,
  say so honestly instead of inventing an answer.
- Think step by step: you may call several tools in a row to finish a task.
- For anything time-based ("remind me", "every morning", "at 5pm", "in 10 \
  minutes"), use the scheduling tools. JARVIS keeps running in the background \
  and will message the user when a task fires — even if they're away.
- Be careful with destructive actions (deleting files, etc.). If something is \
  risky or ambiguous, ask the user to confirm first.
- After finishing, briefly tell the user what you did.
"""

VOICE_NOTE = """

VOICE MODE: The user HEARS your replies spoken aloud by text-to-speech. So:
- Keep every reply to 1-2 short, natural spoken sentences.
- Do NOT use markdown, bullet points, headings, asterisks, emojis, or symbols.
- If the answer is long, give the key point only and offer to say more.
"""


class Jarvis:
    """Main entry point used by every interface (CLI, voice, Telegram)."""

    def __init__(
        self,
        config: Config | None = None,
        notifier: Notifier | None = None,
        voice_mode: bool = False,
    ):
        self.config = config or default_config
        self.config.validate()
        self.registry = load_builtin_tools()
        prompt = SYSTEM_PROMPT + (VOICE_NOTE if voice_mode else "")
        self.brain = make_brain(self.config, self.registry, prompt)

        # Notifications + scheduling let JARVIS act "on time" and reach the user.
        self.notifier = notifier or ConsoleNotifier()
        self.store = TaskStore()
        self.scheduler = JarvisScheduler(self.store, self.notifier, self.run_oneshot)

        # Expose live objects so tools (e.g. set_reminder) can use them.
        runtime.RUNTIME.scheduler = self.scheduler
        runtime.RUNTIME.notifier = self.notifier

    def start_background(self) -> None:
        """Start the scheduler so reminders/recurring tasks fire."""
        self.scheduler.start()

    def ask(self, text: str) -> str:
        """Send a user instruction to JARVIS (stateful conversation)."""
        return self.brain.chat(text)

    def run_oneshot(self, instruction: str) -> str:
        """Run a single instruction with a fresh brain (used by the scheduler).

        Kept separate from ``ask`` so a background task doesn't disturb the
        ongoing interactive conversation history.
        """
        brain = make_brain(self.config, self.registry, SYSTEM_PROMPT)
        return brain.chat(instruction)
