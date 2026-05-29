"""Voice input/output for JARVIS.

* ``listen()``  -> capture speech from the microphone and return text.
* ``speak()``   -> say text out loud.

Text-to-speech prefers macOS's built-in ``say`` command (reliable, natural
voices) and falls back to the cross-platform ``pyttsx3`` library elsewhere.
Speech-to-text needs a microphone (PyAudio). Both degrade gracefully: if audio
isn't available, JARVIS keeps working in text mode instead of crashing.
"""

from __future__ import annotations

import platform
import shutil
import subprocess


class Speaker:
    """Text-to-speech. Uses macOS 'say' when available, else pyttsx3."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._mode: str | None = None
        self._engine = None
        if not enabled:
            return

        # macOS: the built-in 'say' command is the most reliable + best voices.
        if platform.system() == "Darwin" and shutil.which("say"):
            self._mode = "say"
            return

        # Other platforms: offline pyttsx3.
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._mode = "pyttsx3"
        except Exception as exc:  # noqa: BLE001
            print(f"[voice] Text-to-speech unavailable ({exc}). "
                  "Continuing in text mode.")
            self.enabled = False

    def speak(self, text: str) -> None:
        if not text:
            return
        if self.enabled and self._mode == "say":
            try:
                subprocess.run(["say", text], check=False)
                return
            except Exception as exc:  # noqa: BLE001
                print(f"[voice] Could not speak ({exc}).")
        elif self.enabled and self._mode == "pyttsx3" and self._engine is not None:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                return
            except Exception as exc:  # noqa: BLE001
                print(f"[voice] Could not speak ({exc}).")
        # Fallback: at least show the reply.
        print(f"JARVIS: {text}")


class Listener:
    """Speech-to-text from the microphone (requires PyAudio)."""

    def __init__(self):
        self._recognizer = None
        self._sr = None
        try:
            import speech_recognition as sr

            # A microphone needs PyAudio; check it's importable up front so we
            # can fall back to typing cleanly instead of erroring every turn.
            import pyaudio  # noqa: F401

            self._sr = sr
            self._recognizer = sr.Recognizer()
            # Be more patient so full sentences aren't cut off when you pause.
            self._recognizer.pause_threshold = 1.8       # wait ~1.8s of silence
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.non_speaking_duration = 0.6
        except Exception as exc:  # noqa: BLE001
            print(f"[voice] Microphone input not set up ({exc}).")
            print("[voice] You can type instead. To speak to JARVIS, install "
                  "the microphone support (see SETUP.md).")

    @property
    def available(self) -> bool:
        return self._recognizer is not None

    def listen(self, timeout: int = 10, phrase_time_limit: int = 30) -> str | None:
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
