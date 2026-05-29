"""Voice mode - speak to JARVIS and hear it reply.

Say the wake word ('jarvis') or just speak a command. Say 'stop listening'
or press Ctrl+C to exit. If a microphone isn't available, this falls back to
typed input so you can still test the agent.
"""

from __future__ import annotations

from ..agent import Jarvis
from ..config import config
from ..voice import Listener, Speaker

_EXIT_PHRASES = {"stop listening", "goodbye jarvis", "quit", "exit"}


def run() -> None:
    jarvis = Jarvis()
    speaker = Speaker(enabled=config.voice_enabled)
    listener = Listener()

    greeting = "JARVIS online. How can I help?"
    print(greeting)
    speaker.speak(greeting)

    while True:
        try:
            if listener.available:
                text = listener.listen()
                if not text:
                    continue
                print(f"You: {text}")
            else:
                text = input("You (type): ").strip()

            if not text:
                continue
            if text.lower().strip(".!? ") in _EXIT_PHRASES:
                speaker.speak("Goodbye.")
                break

            reply = jarvis.ask(text)
            print(f"JARVIS: {reply}")
            speaker.speak(reply)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
