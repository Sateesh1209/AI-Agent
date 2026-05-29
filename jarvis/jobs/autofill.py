"""Generic, portal-agnostic autofill engine.

Given whatever application page the browser has landed on (after a job-board's
"Apply with autofill" redirect), this:

  1. Reads the form fields on the current page.
  2. Fills only the EMPTY ones from your profile (so it "finishes the rest"
     after the site's own autofill).
  3. Attaches your tailored resume to file inputs.
  4. Walks multi-page forms (Workday-style) via Next/Continue buttons.
  5. Submits when the form is simple and complete; otherwise screenshots the
     page and messages you on Telegram to handle the tricky bits.

It is deliberately generic — it does not assume Greenhouse/Workday/Lever.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .fields import classify_field, is_empty, read_form_fields
from .profile import Profile

# Button text we treat as "go to next page" vs "final submit".
_NEXT_TEXTS = ("next", "continue", "save and continue", "review")
_SUBMIT_TEXTS = ("submit application", "submit", "send application", "apply")


def _find_button(session, texts: tuple[str, ...]):
    for t in texts:
        sel = (
            f"button:has-text('{t}'), input[type=submit][value*='{t}' i], "
            f"a[role=button]:has-text('{t}')"
        )
        el = session.page.query_selector(sel)
        if el and el.is_visible():
            return el
    return None


def autofill_current_page(
    session, profile: Profile, resume_file: str | None
) -> dict[str, list[str]]:
    """Fill the empty fields on the current page. Returns filled/tricky labels."""
    filled: list[str] = []
    tricky: list[str] = []
    for f in read_form_fields(session):
        if not is_empty(f):
            continue  # site already filled it — leave it alone
        category, attr = classify_field(f["label"])
        if category == "resume" and f["type"] == "file":
            if resume_file and session.upload(f["selector"], resume_file):
                filled.append(f"resume -> {Path(resume_file).name}")
            elif f["required"]:
                tricky.append(f["label"])
        elif category == "profile":
            value = profile.field_value(attr)
            if value and session.fill(f["selector"], value):
                filled.append(f"{f['label']} -> {value}")
            elif f["required"]:
                tricky.append(f["label"])
        else:  # tricky / custom question
            answer = profile.answer_for(f["label"])
            if answer and session.fill(f["selector"], answer):
                filled.append(f"{f['label']} -> {answer}")
            elif f["required"]:
                tricky.append(f["label"])
    return {"filled": filled, "tricky": tricky}


def autofill_application(
    session,
    profile: Profile,
    resume_file: str | None,
    out_dir: str,
    mode: str = "auto_simple",
    notifier=None,
    job_label: str = "this job",
    max_steps: int = 8,
) -> dict[str, Any]:
    """Drive a (possibly multi-page) application to completion or escalation."""
    all_filled: list[str] = []
    all_tricky: list[str] = []

    for _ in range(max_steps):
        page_result = autofill_current_page(session, profile, resume_file)
        all_filled += page_result["filled"]
        all_tricky += page_result["tricky"]

        submit_btn = _find_button(session, _SUBMIT_TEXTS)
        next_btn = _find_button(session, _NEXT_TEXTS)

        # If there are tricky required fields and we're not fully automatic,
        # stop and ask the user before going further / submitting.
        if all_tricky and mode != "full_auto":
            break

        if submit_btn:
            submit_btn.click()
            return {
                "submitted": True,
                "filled": all_filled,
                "tricky": all_tricky,
            }
        if next_btn:
            next_btn.click()
            session.page.wait_for_load_state("domcontentloaded")
            continue
        break  # no submit, no next — nothing more we can do automatically

    # Needs the user.
    result: dict[str, Any] = {
        "submitted": False,
        "filled": all_filled,
        "tricky": all_tricky,
    }
    shot = str(Path(out_dir).expanduser() / "needs_review.png")
    try:
        session.screenshot(shot)
        result["screenshot"] = shot
    except Exception:
        pass
    if notifier:
        detail = ", ".join(all_tricky) if all_tricky else "review before submit"
        notifier.send(
            f"📝 {job_label}: filled {len(all_filled)} field(s). "
            f"Needs you for: {detail}.\n{session.page.url}"
        )
    return result
