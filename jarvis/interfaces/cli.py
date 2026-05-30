"""Plain text chat loop - type to JARVIS in your terminal."""

from __future__ import annotations

from ..agent import Jarvis


def run() -> None:
    jarvis = Jarvis()
    jarvis.start_background()  # reminders/recurring tasks fire while you chat
    print("JARVIS (text mode). Type 'quit' to exit.\n")
    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not text:
            continue
        if text.lower() in {"quit", "exit", "bye"}:
            print("Goodbye.")
            break
        reply = jarvis.ask(text)
        print(f"JARVIS: {reply}\n")
