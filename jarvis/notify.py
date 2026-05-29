"""Outbound notifications: how JARVIS reaches YOU.

This powers proactive messages — JARVIS telling you a reminder fired or a
scheduled task finished — independent of whoever is currently chatting with it.
"""

from __future__ import annotations

from .config import Config


class Notifier:
    def send(self, text: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    """Prints to the terminal (used in CLI / voice mode)."""

    def send(self, text: str) -> None:
        print(f"\n🔔 [JARVIS] {text}\n")


class TelegramNotifier(Notifier):
    """Sends a message to the user on Telegram via a plain HTTP call.

    ``chat_id`` may be unknown until the user first messages the bot; it can be
    filled in later by the Telegram interface.
    """

    def __init__(self, token: str, chat_id: str | None = None):
        self.token = token
        self.chat_id = chat_id

    def send(self, text: str) -> None:
        if not self.chat_id:
            print(f"🔔 [JARVIS - message you on Telegram first] {text}")
            return
        import requests

        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text},
                timeout=30,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[notify] Telegram send failed: {exc}")


def make_notifier(config: Config) -> Notifier:
    """Pick the best notifier available from config."""
    if config.telegram_token:
        return TelegramNotifier(config.telegram_token, config.telegram_allowed_user_id)
    return ConsoleNotifier()
