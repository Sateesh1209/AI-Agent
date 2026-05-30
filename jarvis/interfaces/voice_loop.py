"""Voice mode - speak to JARVIS and hear it reply.

Just speak a command. To stop, say "stop", "quit", "stop listening", or
"goodbye Jarvis" (or press Ctrl+C). While JARVIS is speaking, press Ctrl+C once
to cut it off and go back to listening. If a microphone isn't available, this
falls back to typed input so you can still use the agent.
"""

from __future__ import annotations

from ..agent import Jarvis
from ..config import config
from ..voice import Listener, Speaker

# Spoken phrases that end the session.
_EXIT_PHRASES = {
    "quit", "exit", "stop", "stop now", "bye", "goodbye",
    "stop listening", "stop jarvis", "quit jarvis", "exit jarvis",
    "goodbye jarvis", "bye jarvis", "that's all", "thank you jarvis",
}


def _wants_exit(text: str) -> bool:
    return text.lower().strip(".!?, ") in _EXIT_PHRASES


def run() -> None:
    jarvis = Jarvis(voice_mode=True)  # tells JARVIS to keep replies short
    jarvis.start_background()  # reminders/recurring tasks fire in the background
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
            if _wants_exit(text):
                speaker.speak("Goodbye.")
                break

            reply = jarvis.ask(text)
            print(f"JARVIS: {reply}")
            speaker.speak(reply)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
