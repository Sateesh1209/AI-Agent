"""Apply to jobs on Greenhouse boards.

Flow per board:
  1. Open the board, collect the list of job postings.
  2. For each job (up to a limit): open it, read the application form.
  3. Tailor a resume to that job and attach it.
  4. Fill the 'simple' fields automatically from your profile.
  5. Mode 'auto_simple': if every remaining field is simple/known, submit;
     if there are 'tricky' fields (essays, custom questions), DON'T submit —
     screenshot it and message you on Telegram to finish/approve.

The field-classification logic is pure and unit-tested. The browser steps use
best-effort Greenhouse selectors and may need light tuning the first time you
run them live (Greenhouse periodically changes its markup).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .browser import BrowserSession
from .profile import Profile
from .resume import build_resume

# Map a profile attribute to the keywords that identify its form field.
_FIELD_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("first_name", ("first name", "firstname", "given name")),
    ("last_name", ("last name", "lastname", "surname", "family name")),
    ("email", ("email", "e-mail")),
    ("phone", ("phone", "mobile", "telephone")),
    ("linkedin", ("linkedin",)),
    ("github", ("github",)),
    ("website", ("website", "portfolio", "personal site")),
    ("location", ("location", "city", "where are you based")),
    ("full_name", ("full name", "your name", "name")),  # generic, checked last
]

_RESUME_KEYWORDS = ("resume", "cv", "résumé")


def classify_field(label: str) -> tuple[str, str]:
    """Classify a form field by its label.

    Returns one of:
      ("profile", "<profile_attr>")  -> fill automatically from the profile
      ("resume", "")                 -> attach the tailored resume file
      ("tricky", "")                 -> needs the user (essays, custom questions)
    """
    text = (label or "").strip().lower()
    if not text:
        return ("tricky", "")
    if any(k in text for k in _RESUME_KEYWORDS):
        return ("resume", "")
    for attr, keywords in _FIELD_KEYWORDS:
        if any(k in text for k in keywords):
            return ("profile", attr)
    return ("tricky", "")


# ----------------------------------------------------------------------------
# Browser-driven steps (run these on your Mac with Chrome installed).
# ----------------------------------------------------------------------------

def list_jobs(session: BrowserSession, board_url: str) -> list[dict[str, str]]:
    """Return [{title, url}] for the openings on a Greenhouse board."""
    session.goto(board_url)
    jobs: list[dict[str, str]] = []
    # Greenhouse boards render openings as anchors linking to /jobs/<id>.
    anchors = session.page.query_selector_all("a[href*='/jobs/']")
    seen = set()
    for a in anchors:
        href = a.get_attribute("href") or ""
        title = (a.inner_text() or "").strip()
        if not href or href in seen or not title:
            continue
        seen.add(href)
        if href.startswith("/"):
            href = board_url.split("/", 3)[0] + "//" + board_url.split("/")[2] + href
        jobs.append({"title": title, "url": href})
    return jobs


def read_form_fields(session: BrowserSession) -> list[dict[str, Any]]:
    """Best-effort read of the application form's fields and their labels."""
    fields: list[dict[str, Any]] = []
    inputs = session.page.query_selector_all(
        "form input:not([type=hidden]):not([type=submit]), "
        "form textarea, form select"
    )
    for el in inputs:
        input_type = (el.get_attribute("type") or el.evaluate("e => e.tagName")).lower()
        name = el.get_attribute("name") or ""
        el_id = el.get_attribute("id") or ""
        aria = el.get_attribute("aria-label") or ""
        label = aria or name
        # Try to find a <label for=id>.
        if el_id:
            lab = session.page.query_selector(f"label[for='{el_id}']")
            if lab:
                label = (lab.inner_text() or label).strip()
        required = bool(el.get_attribute("required")) or "*" in label
        selector = f"#{el_id}" if el_id else (f"[name='{name}']" if name else None)
        if not selector:
            continue
        fields.append(
            {
                "label": label,
                "selector": selector,
                "type": input_type,
                "required": required,
            }
        )
    return fields


def apply_to_job(
    session: BrowserSession,
    job: dict[str, str],
    profile: Profile,
    out_dir: str,
    mode: str = "auto_simple",
    brain=None,
    notifier=None,
) -> dict[str, Any]:
    """Open one job, tailor a resume, fill what we can, submit or escalate."""
    session.goto(job["url"])
    description = session.visible_text()

    # 1) Tailored resume for this specific job.
    resume = build_resume(profile, job["title"], description, out_dir, brain=brain)
    resume_file = resume.get("pdf") or resume.get("html")

    # 2) Make the application form visible (Greenhouse "Apply" button if any).
    session.click("a#apply_button, button:has-text('Apply')")

    fields = read_form_fields(session)
    filled, tricky = [], []
    for f in fields:
        category, attr = classify_field(f["label"])
        if category == "resume" and "file" in f["type"]:
            if resume_file and session.upload(f["selector"], resume_file):
                filled.append(f"resume -> {Path(resume_file).name}")
        elif category == "profile":
            value = profile.field_value(attr)
            if value and session.fill(f["selector"], value):
                filled.append(f"{f['label']} -> {value}")
            elif f["required"]:
                tricky.append(f["label"])
        else:  # tricky
            answer = profile.answer_for(f["label"])
            if answer and session.fill(f["selector"], answer):
                filled.append(f"{f['label']} -> {answer}")
            elif f["required"]:
                tricky.append(f["label"])

    # 3) Decide: submit, or escalate to the user.
    needs_user = bool(tricky) and mode != "full_auto"
    result = {
        "job": job["title"],
        "url": job["url"],
        "filled": filled,
        "tricky": tricky,
        "resume": resume_file,
        "submitted": False,
    }

    if needs_user:
        shot = str(Path(out_dir).expanduser() / "needs_review.png")
        try:
            session.screenshot(shot)
            result["screenshot"] = shot
        except Exception:
            pass
        if notifier:
            notifier.send(
                f"📝 Job '{job['title']}' is filled but needs you for: "
                f"{', '.join(tricky)}.\n{job['url']}"
            )
        return result

    # Submit (simple form, everything known).
    submitted = session.click("button:has-text('Submit'), input[type=submit]")
    result["submitted"] = submitted
    if notifier and submitted:
        notifier.send(f"✅ Applied to '{job['title']}'.\n{job['url']}")
    return result


def run_job_applications(
    board_url: str,
    profile: Profile,
    config,
    max_jobs: int = 5,
    mode: str = "auto_simple",
    brain=None,
    notifier=None,
) -> str:
    """Apply to up to ``max_jobs`` openings on a Greenhouse board."""
    out_dir = str(Path(config.profile_path).expanduser().parent / "applications")
    session = BrowserSession(config.chrome_user_data_dir, headless=False)
    summaries: list[str] = []
    try:
        session.start()
        jobs = list_jobs(session, board_url)
        if not jobs:
            return f"No job postings found on {board_url}."
        for job in jobs[:max_jobs]:
            try:
                r = apply_to_job(session, job, profile, out_dir, mode, brain, notifier)
                status = (
                    "submitted" if r["submitted"]
                    else ("needs review: " + ", ".join(r["tricky"]))
                )
                summaries.append(f"- {r['job']}: {status}")
            except Exception as exc:  # noqa: BLE001
                summaries.append(f"- {job['title']}: error ({exc})")
    finally:
        session.close()
    return f"Processed {len(summaries)} job(s) on Greenhouse:\n" + "\n".join(summaries)
