"""Tests for the 'JARVIS asks you, escalates to Telegram' logic.

Run:  python tests/test_interaction.py
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis import interaction  # noqa: E402
from jarvis.interaction import PendingQuestion, ask_user  # noqa: E402
from jarvis.runtime import RUNTIME  # noqa: E402


class FakeTelegramNotifier:
    chat_id = 123  # pretend the user has messaged the bot

    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)


def test_no_console_no_telegram_returns_none():
    RUNTIME.notifier = None
    RUNTIME.pending_question = None
    # console_timeout 0 -> don't wait; no telegram -> give up
    assert ask_user("Your phone number?", console_timeout=0) is None


def test_escalates_to_telegram_and_gets_reply():
    notifier = FakeTelegramNotifier()
    RUNTIME.notifier = notifier
    RUNTIME.pending_question = None

    # Simulate the user replying on Telegram shortly after the question is sent.
    def reply_later():
        for _ in range(50):
            if RUNTIME.pending_question is not None:
                RUNTIME.pending_question.respond("555-1234")
                return
            time.sleep(0.02)

    threading.Thread(target=reply_later, daemon=True).start()

    answer = ask_user("Your phone number?", console_timeout=0, telegram_timeout=5)
    assert answer == "555-1234"
    assert notifier.sent and "need your input" in notifier.sent[0].lower()
    assert RUNTIME.pending_question is None  # cleaned up


def test_telegram_timeout_returns_none():
    RUNTIME.notifier = FakeTelegramNotifier()
    RUNTIME.pending_question = None
    answer = ask_user("Anyone there?", console_timeout=0, telegram_timeout=0.2)
    assert answer is None
    assert RUNTIME.pending_question is None


def test_pending_question_respond():
    pq = PendingQuestion("Q?")
    assert pq.wait(timeout=0.01) is False
    pq.respond("A")
    assert pq.wait(timeout=0.01) is True
    assert pq.answer == "A"


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in funcs:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nAll {len(funcs)} tests passed.")
