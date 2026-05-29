"""Voice input/output for JARVIS.

* ``listen()``  -> capture speech from the microphone and return text.
* ``speak()``   -> say text out loud (offline, via pyttsx3).

Both degrade gracefully: if the audio libraries or hardware are missing,
JARVIS keeps working in text-only mode instead of crashing.
"""

from __future__ import annotations


class Speaker:
    """Offline text-to-speech."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._engine = None
        if enabled:
            try:
                import pyttsx3

                self._engine = pyttsx3.init()
            except Exception as exc:  # noqa: BLE001
                print(f"[voice] Text-to-speech unavailable ({exc}). "
                      "Continuing in text mode.")
                self.enabled = False

    def speak(self, text: str) -> None:
        if not text:
            return
        if self.enabled and self._engine is not None:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                return
            except Exception as exc:  # noqa: BLE001
                print(f"[voice] Could not speak ({exc}).")
        # Fallback: at least show the reply.
        print(f"JARVIS: {text}")


class Listener:
    """Speech-to-text from the microphone."""

    def __init__(self):
        self._recognizer = None
        self._sr = None
        try:
            import speech_recognition as sr

            self._sr = sr
            self._recognizer = sr.Recognizer()
        except Exception as exc:  # noqa: BLE001
            print(f"[voice] Microphone input unavailable ({exc}). "
                  "Use text input instead.")

    @property
    def available(self) -> bool:
        return self._recognizer is not None

    def listen(self, timeout: int = 8, phrase_time_limit: int = 15) -> str | None:
        """Record one phrase and transcribe it. Returns None on failure."""
        if not self.available:
            return None
        sr = self._sr
        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
                print("[voice] Listening...")
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            print("[voice] Transcribing...")
            return self._recognizer.recognize_google(audio)
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("[voice] Sorry, I didn't catch that.")
            return None
        except Exception as exc:  # noqa: BLE001
            print(f"[voice] Recognition error ({exc}).")
            return None
