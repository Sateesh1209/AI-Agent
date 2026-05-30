"""Two-way 'JARVIS asks YOU' interaction with Telegram escalation.

When JARVIS needs information mid-task (e.g. a job form asks something it
doesn't know), it calls ``ask_user(question)``. That:

  1. Asks at the keyboard and waits a short while (default 30s).
  2. If you don't answer (you're away from the laptop) and Telegram is set up,
     it messages you on Telegram and waits for your reply there.
  3. Returns your answer (from either channel), or None if nobody responded.

The Telegram bot routes your reply back into the waiting question via
``RUNTIME.pending_question``.
"""

from __future__ import annotations

import sys
import threading

from .runtime import RUNTIME


class PendingQuestion:
    def __init__(self, question: str):
        self.question = question
        self.answer: str | None = None
        self._event = threading.Event()

    def respond(self, text: str) -> None:
        self.answer = text
        self._event.set()

    def wait(self, timeout: float) -> bool:
        return self._event.wait(timeout=timeout)


def _read_console(timeout: float) -> str | None:
    """Wait up to ``timeout`` seconds for a typed line. POSIX only; safe."""
    # Only attempt if we actually have an interactive terminal.
    try:
        if not sys.stdin or not sys.stdin.isatty():
            return None
        import select

        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            line = sys.stdin.readline().strip()
            return line or None
    except Exception:
        return None
    return None


def ask_user(
    question: str,
    console_timeout: float = 30.0,
    telegram_timeout: float = 600.0,
) -> str | None:
    """Ask the user a question, escalating to Telegram if they're away."""
    print(f"\n❓ [JARVIS needs info] {question}")

    # 1) Give the person at the keyboard a chance to answer.
    answer = _read_console(console_timeout)
    if answer:
        return answer

    # 2) Escalate to Telegram if we can reach them there.
    notifier = RUNTIME.notifier
    can_telegram = (
        notifier is not None
        and getattr(notifier, "chat_id", None)
        and hasattr(notifier, "send")
    )
    if can_telegram:
        pending = PendingQuestion(question)
        RUNTIME.pending_question = pending
        try:
            notifier.send(f"❓ I need your input to continue:\n{question}\n\n"
                          "Just reply to this message.")
            if pending.wait(timeout=telegram_timeout):
                return pending.answer
        finally:
            RUNTIME.pending_question = None
        return None

    # No Telegram set up: the user is at the keyboard, so wait (blocking) for
    # them to answer — e.g. after they finish logging into a portal.
    try:
        if sys.stdin and sys.stdin.isatty():
            print("(JARVIS is waiting — type your answer and press Enter)")
            line = input("> ").strip()
            return line or None
    except (EOFError, KeyboardInterrupt):
        return None
    return None
