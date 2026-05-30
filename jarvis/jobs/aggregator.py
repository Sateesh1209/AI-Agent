"""Generic 'apply from a job aggregator' flow (works across several sites).

Aggregators (Jobright, LinkedIn-style boards, company lists, ...) show many
jobs, each with an "Apply" / "Apply with autofill" button that redirects to
whatever portal the job actually lives on. This module:

  1. Opens the aggregator page.
  2. Finds the apply buttons.
  3. For each job: clicks Apply (handling a new tab / redirect), lets the site's
     own autofill run, then JARVIS finishes the remaining fields via the
     generic ``autofill_application`` engine, and submits or escalates.

Aggregators differ a lot, so the button/title selectors here are best-effort
and are the main thing you'll tune when you first run this live on your Mac.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .autofill import autofill_application
from .browser import BrowserSession
from .profile import Profile
from .resume import build_resume

# Button text used to start an application, most specific first.
_APPLY_TEXTS = (
    "apply with autofill",
    "autofill",
    "easy apply",
    "quick apply",
    "apply now",
    "apply",
)


def _apply_buttons(session: BrowserSession):
    """Return the visible 'apply' buttons/links on the current listing page."""
    for text in _APPLY_TEXTS:
        sel = f"button:has-text('{text}'), a:has-text('{text}')"
        els = [e for e in session.page.query_selector_all(sel) if e.is_visible()]
        if els:
            return els
    return []


def apply_from_job_board(
    session: BrowserSession,
    board_url: str,
    profile: Profile,
    config,
    max_jobs: int = 5,
    mode: str = "auto_simple",
    brain=None,
    notifier=None,
) -> str:
    """Apply to up to ``max_jobs`` jobs on a generic aggregator board."""
    out_dir = str(Path(config.profile_path).expanduser().parent / "applications")
    summaries: list[str] = []

    session.goto(board_url)
    total = len(_apply_buttons(session))
    if not total:
        return (
            f"No 'Apply' buttons found on {board_url}. Make sure you're logged "
            "in (run 'python main.py login <url>' once) and that the page has "
            "loaded job results."
        )

    count = min(total, max_jobs)
    for index in range(count):
        # Re-find buttons each round; navigating away invalidates old handles.
        session.goto(board_url)
        buttons = _apply_buttons(session)
        if index >= len(buttons):
            break
        btn = buttons[index]
        title = "job"
        try:
            # Grab a nearby title for the resume + notifications.
            title = (btn.evaluate(
                "e => (e.closest('[class*=card],li,article,div]')||e).innerText"
            ) or "job").strip().split("\n")[0][:80] or "job"
        except Exception:
            pass

        pages_before = session.page_count()
        try:
            btn.click()
        except Exception as exc:  # noqa: BLE001
            summaries.append(f"- {title}: could not click apply ({exc})")
            continue

        # The portal often opens in a new tab; switch to it.
        session.page.wait_for_timeout(2500)
        if session.page_count() > pages_before:
            session.use_latest_page()
        try:
            session.page.wait_for_load_state("domcontentloaded")
        except Exception:
            pass

        # Tailor a resume to the destination job, then finish the form.
        description = session.visible_text()
        resume = build_resume(profile, title, description, out_dir, brain=brain)
        resume_file = resume.get("pdf") or resume.get("html")

        result = autofill_application(
            session, profile, resume_file, out_dir, mode, notifier, title
        )
        status = (
            "submitted"
            if result["submitted"]
            else ("needs review: " + (", ".join(result["tricky"]) or "—"))
        )
        summaries.append(f"- {title}: {status}")

        # Close the portal tab and return to the board.
        if session.page_count() > pages_before:
            try:
                session.page.close()
            except Exception:
                pass
            session.use_latest_page()

    return f"Processed {len(summaries)} job(s):\n" + "\n".join(summaries)
