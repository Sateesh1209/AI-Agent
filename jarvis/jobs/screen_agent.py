"""Screen-control agent: JARVIS operates your Mac by looking at screenshots.

Each step: screenshot the whole screen -> Claude (vision) decides the next
action (click here / type this / press a key) -> JARVIS performs it on the real
screen. It pauses for you on logins and before any final submit.

This drives your REAL Chrome, so you stay logged into JobRight and your portals.
"""

from __future__ import annotations

from typing import Callable

from ..interaction import ask_user
from .webagent import parse_action  # reuse the robust JSON extractor

_PROMPT = """You are JARVIS, operating a Mac by looking at screenshots and \
controlling the mouse and keyboard.

GOAL: {goal}

The screenshot I gave you is {w}x{h} pixels. Coordinates you give MUST be pixel
positions on THAT screenshot.

RECENT ACTIONS:
{history}

Decide the SINGLE next action. Respond with ONLY a JSON object, no prose:
{{"action":"click|double_click|type|key|scroll|wait|ask_user|done",
  "x":<int or null>, "y":<int or null>,
  "text":"<text to type / key name / 'down'|'up' / question>",
  "reason":"<short>"}}

Rules:
- "click"/"double_click": click at pixel (x,y).
- "type": first ensure the field is focused (click it in a previous step), then
  type "text".
- "key": press one key, e.g. text="enter" or "tab".
- "scroll": text="down" or "up".
- "wait": page is loading/generating; pause and look again.
- "ask_user": you need the human (e.g. a login, a CAPTCHA, or info you lack) —
  put a clear request in "text" (for a login: "LOGIN NEEDED: <portal> — sign in,
  then reply done").
- NEVER click a final Submit/Apply-confirm. Use ask_user "CONFIRM_SUBMIT: ...".
- "done": the goal is complete.
"""


class ScreenAgent:
    def __init__(self, controller, decide: Callable[..., str], notifier=None,
                 shot_path: str = "/tmp/jarvis_screen.png"):
        self.c = controller
        self.decide = decide
        self.notifier = notifier
        self.shot_path = shot_path

    def run(self, goal: str, max_steps: int = 40) -> str:
        history: list[str] = []
        for step in range(max_steps):
            try:
                self.c.screenshot(self.shot_path)
            except Exception as exc:  # noqa: BLE001
                return (f"Couldn't capture the screen ({exc}). Grant Terminal "
                        "Screen Recording permission in System Settings.")
            w, h = self.c.shot_size
            prompt = _PROMPT.format(
                goal=goal, w=w, h=h,
                history="\n".join(history[-6:]) or "(none yet)",
            )
            action = parse_action(self.decide(prompt, self.shot_path))
            if not action:
                history.append("could not decide; waiting")
                self._sleep(1.5)
                continue

            a = action.get("action")
            x = action.get("x")
            y = action.get("y")
            text = action.get("text", "") or ""
            print(f"[screen] step {step+1}: {a} ({x},{y}) {text[:30]} "
                  f"— {action.get('reason','')[:60]}")

            try:
                if a == "done":
                    return f"✅ Done: {action.get('reason','')}"
                if a == "wait":
                    self._sleep(2.5); history.append("waited"); continue
                if a == "ask_user":
                    ans = ask_user(text) or "(no answer)"
                    history.append(f"asked: {text[:50]} -> {ans[:50]}")
                    continue
                if a in ("click", "double_click"):
                    if x is None or y is None:
                        history.append("click missing coords"); continue
                    self.c.click(x, y, double=(a == "double_click"))
                    self._sleep(1.2); history.append(f"{a} at ({x},{y})")
                elif a == "type":
                    self.c.type_text(text); history.append(f"typed '{text[:30]}'")
                elif a == "key":
                    self.c.press(text or "enter"); history.append(f"key {text}")
                elif a == "scroll":
                    self.c.scroll(-400 if text == "down" else 400)
                    history.append(f"scroll {text}")
                else:
                    history.append(f"unknown action {a}")
            except Exception as exc:  # noqa: BLE001
                history.append(f"error doing {a}: {exc}")

        return "Stopped after max steps.\n" + "\n".join(history[-10:])

    def _sleep(self, seconds: float) -> None:
        import time
        time.sleep(seconds)
