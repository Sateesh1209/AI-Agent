"""An autonomous browser agent driven by Claude.

Instead of hand-coding every click for a specific site, JARVIS looks at the
page's interactive elements, asks Claude for the single next action, performs
it, and repeats. It escalates to the user (console/Telegram) when it needs
info, and — for safety — never submits an application without the user's OK.

Decisions use Claude via the subscription (free), so this works on a Max plan.
"""

from __future__ import annotations

import json
import re
from typing import Callable

from ..interaction import ask_user

_ACTION_PROMPT = """You are JARVIS, controlling a web browser to accomplish a goal.

GOAL: {goal}

CURRENT PAGE: {url}
TITLE: {title}
RECENT ACTIONS:
{history}

INTERACTIVE ELEMENTS (each is outlined with a numbered RED box in the
screenshot — pick one by its [index]):
{elements}

Decide the SINGLE next action. Respond with ONLY a JSON object (no prose):
{{"action": "click|fill|upload|wait|ask_user|done", "index": <int or null>,
  "value": "<text to type / question to ask / empty>", "reason": "<short>"}}

Rules:
- "click": click the element at "index".
- "fill": type "value" into the input at "index".
- "upload": attach the freshly-downloaded resume to the file input at "index".
- "wait": page is still loading or generating; pause and look again.
- "ask_user": you need info you don't have — put the question in "value".
- NEVER click a final Submit / Apply-confirm button. Instead use "ask_user"
  with value starting "CONFIRM_SUBMIT: " and a summary, so the human approves.
- "done": the goal is finished (submitted, or handed to the user).
"""


JOBRIGHT_GOAL = (
    "You are on JobRight (jobright.ai), logged in as Sateesh Kumar Nunna, a "
    "Senior Data Engineer (7 years; Python, SQL, Spark, Snowflake, AWS/Azure/GCP). "
    "Apply to the NEXT not-yet-applied job in the recommendations list:\n"
    "1. Click that job's 'Apply with Autofill' button (it may open a NEW tab on "
    "the company's portal — work in that newest tab).\n"
    "2. On the company portal, click 'Apply' / 'Apply now' to open the form.\n"
    "3. If the portal needs SIGN IN / login, use ask_user with value "
    "'LOGIN NEEDED: <portal> — please sign in to that portal in the Chrome "
    "window, then reply done'. Then continue.\n"
    "4. If JobRight offers 'Customize/Generate resume' (full edit + add missing "
    "skills), use it, wait ~15s, then 'upload' the downloaded resume to any "
    "resume file input.\n"
    "5. Fill empty REQUIRED fields sensibly; use ask_user for personal info you "
    "don't have.\n"
    "6. Do NOT click the final Submit — use ask_user 'CONFIRM_SUBMIT: <summary>'.\n"
    "When the application is submitted or handed to the user, use 'done'."
)


def parse_action(text: str) -> dict | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def collect_elements(page) -> list[tuple[object, str]]:
    """Return [(handle, description)] for visible, actionable elements."""
    items: list[tuple[object, str]] = []
    try:
        handles = page.query_selector_all(
            "button, a, input, textarea, select, [role=button]"
        )
    except Exception:
        return items
    for h in handles:
        try:
            if not h.is_visible():
                continue
            tag = h.evaluate("e => e.tagName").lower()
            if tag in ("input", "textarea", "select"):
                kind = (h.get_attribute("type") or tag).lower()
                if kind == "hidden":
                    continue
                label = (h.get_attribute("aria-label") or h.get_attribute("placeholder")
                         or h.get_attribute("name") or "")
                try:
                    val = h.input_value()
                except Exception:
                    val = ""
                desc = f"{kind} field '{label[:40]}' (current='{val[:20]}')"
            else:
                text = " ".join((h.inner_text() or "").split())
                if not text:
                    continue
                desc = f"button/link '{text[:50]}'"
            items.append((h, desc))
        except Exception:
            continue
    return items


def collect_marks(page) -> list[tuple[object, str, dict | None]]:
    """Like collect_elements, but also returns each element's bounding box."""
    items: list[tuple[object, str, dict | None]] = []
    try:
        handles = page.query_selector_all(
            "button, a, input, textarea, select, [role=button]"
        )
    except Exception:
        return items
    for h in handles:
        try:
            if not h.is_visible():
                continue
            box = h.bounding_box()
            tag = h.evaluate("e => e.tagName").lower()
            if tag in ("input", "textarea", "select"):
                kind = (h.get_attribute("type") or tag).lower()
                if kind == "hidden":
                    continue
                label = (h.get_attribute("aria-label") or h.get_attribute("placeholder")
                         or h.get_attribute("name") or "")
                try:
                    val = h.input_value()
                except Exception:
                    val = ""
                desc = f"{kind} field '{label[:40]}' (current='{val[:20]}')"
            else:
                text = " ".join((h.inner_text() or "").split())
                if not text:
                    continue
                desc = f"'{text[:50]}'"
            items.append((h, desc, box))
        except Exception:
            continue
    return items


def annotate_marks(page, items, shot_path: str) -> str | None:
    """Screenshot the viewport and draw a numbered red box on each element.

    Numbers match the element indices so Claude can pick what it SEES and the
    code clicks the EXACT element handle (no pixel guessing).
    """
    try:
        page.screenshot(path=shot_path, full_page=False)
    except Exception:
        return None
    try:
        from PIL import Image, ImageDraw

        dsf = page.evaluate("window.devicePixelRatio") or 1
        vh = page.evaluate("window.innerHeight") or 100000
        img = Image.open(shot_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        for i, (_, _, box) in enumerate(items):
            if not box or box["y"] < 0 or box["y"] > vh:
                continue
            x0, y0 = box["x"] * dsf, box["y"] * dsf
            x1 = (box["x"] + box["width"]) * dsf
            y1 = (box["y"] + box["height"]) * dsf
            draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=2)
            ty = max(0, y0 - 15)
            draw.rectangle([x0, ty, x0 + 9 * len(str(i)) + 6, ty + 14],
                           fill=(255, 0, 0))
            draw.text((x0 + 3, ty + 1), str(i), fill=(255, 255, 255))
        img.save(shot_path)
        return shot_path
    except Exception:
        return shot_path  # plain screenshot if drawing fails


class WebAgent:
    def __init__(self, session, decide: Callable[..., str], notifier=None,
                 use_vision: bool = False, shot_path: str | None = None):
        self.session = session
        self.decide = decide  # (prompt[, image_path]) -> raw text (Claude)
        self.notifier = notifier
        self.use_vision = use_vision
        self.shot_path = shot_path or "/tmp/jarvis_step.png"

    def run(self, goal: str, max_steps: int = 25) -> str:
        from .downloads import latest_download

        history: list[str] = []
        for step in range(max_steps):
            self.session.use_latest_page()
            page = self.session.page

            # Collect elements with exact positions; mark them on a screenshot.
            shot = None
            if self.use_vision:
                items = collect_marks(page)
                shot = annotate_marks(page, items, self.shot_path)
            else:
                items = [(h, d, None) for h, d in collect_elements(page)]

            elements = "\n".join(f"[{i}] {d}" for i, (_, d, _) in enumerate(items))
            try:
                title = page.title()
            except Exception:
                title = ""
            prompt = _ACTION_PROMPT.format(
                goal=goal, url=getattr(page, "url", ""), title=title,
                history="\n".join(history[-6:]) or "(none yet)",
                elements=elements[:6000] or "(none found)",
            )
            raw = self.decide(prompt, shot) if shot else self.decide(prompt)
            action = parse_action(raw)
            if not action:
                history.append("could not decide; waiting")
                page.wait_for_timeout(1500)
                continue

            a = action.get("action")
            idx = action.get("index")
            val = action.get("value", "") or ""
            print(f"[agent] step {step+1}: {a} idx={idx} {val[:40]} "
                  f"— {action.get('reason','')[:60]}")

            if a == "done":
                return f"✅ Done: {action.get('reason', '')}"
            if a == "wait":
                page.wait_for_timeout(2500)
                history.append("waited")
                continue
            if a == "ask_user":
                answer = ask_user(val) or "(no answer)"
                history.append(f"asked: {val[:60]} -> {answer[:60]}")
                continue
            if idx is None or not (0 <= idx < len(items)):
                history.append(f"invalid index {idx}")
                continue

            handle, desc, _box = items[idx]
            try:
                if a == "click":
                    handle.click(timeout=8000)
                    page.wait_for_timeout(1500)
                    history.append(f"clicked {desc}")
                elif a == "fill":
                    handle.fill(val, timeout=8000)
                    history.append(f"filled {desc} = {val[:30]}")
                elif a == "upload":
                    resume = latest_download()
                    if resume:
                        handle.set_input_files(resume, timeout=8000)
                        history.append(f"uploaded resume to {desc}")
                    else:
                        history.append("no downloaded resume found to upload")
                else:
                    history.append(f"unknown action {a}")
            except Exception as exc:  # noqa: BLE001
                history.append(f"error doing {a} on {desc}: {exc}")

        summary = "Stopped after max steps.\n" + "\n".join(history[-10:])
        if self.notifier:
            self.notifier.send("ℹ️ Job agent paused (reached step limit). "
                               "Check the browser.")
        return summary
