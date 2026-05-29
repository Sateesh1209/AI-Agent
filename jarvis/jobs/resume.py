"""Generate a resume tailored to a specific job.

Given your profile (and existing resume text) plus a job's title/description,
JARVIS produces an HTML resume that emphasises the most relevant experience and
skills, then renders it to PDF for upload.

If an LLM brain is provided, it does the tailoring; otherwise a clean template
is assembled directly from the profile (so this always works offline too).
"""

from __future__ import annotations

import html
from pathlib import Path

from .profile import Profile

_TAILOR_INSTRUCTIONS = """You are an expert resume writer. Produce a concise, \
ATS-friendly, ONE-PAGE resume in clean semantic HTML (no <html>/<head> tags, \
just the body content) tailored to the job below. Emphasise the candidate's \
experience and skills that match the job. Do not invent facts — only use what \
the profile provides. Return ONLY the HTML.

=== CANDIDATE PROFILE (JSON-ish) ===
{profile}

=== EXISTING RESUME TEXT (may be empty) ===
{resume_text}

=== JOB ===
Title: {job_title}
Description:
{job_description}
"""

_HTML_WRAPPER = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body {{ font-family: -apple-system, Arial, sans-serif; font-size: 11pt;
        color: #111; margin: 40px; line-height: 1.4; }}
h1 {{ font-size: 20pt; margin: 0; }}
h2 {{ font-size: 13pt; border-bottom: 1px solid #ccc; margin-top: 18px; }}
.contact {{ color: #555; font-size: 10pt; margin-bottom: 8px; }}
ul {{ margin: 4px 0 4px 18px; }}
</style></head><body>
{body}
</body></html>"""


def _profile_summary_text(profile: Profile) -> str:
    """A compact text form of the profile for the LLM prompt."""
    lines = [
        f"Name: {profile.full_name}",
        f"Contact: {profile.email} | {profile.phone} | {profile.location}",
        f"Links: {profile.linkedin} {profile.github} {profile.website}".strip(),
        f"Summary: {profile.summary}",
        f"Skills: {', '.join(profile.skills)}",
        "Experience:",
    ]
    for e in profile.experience:
        lines.append(
            f"  - {e.get('title','')} at {e.get('company','')} "
            f"({e.get('start','')}-{e.get('end','')})"
        )
        for b in e.get("bullets", []):
            lines.append(f"      * {b}")
    lines.append("Education:")
    for ed in profile.education:
        lines.append(
            f"  - {ed.get('degree','')} , {ed.get('school','')} "
            f"({ed.get('year','')})"
        )
    return "\n".join(lines)


def _fallback_html(profile: Profile) -> str:
    """A solid template resume built straight from the profile (no LLM)."""
    esc = html.escape
    contact = " | ".join(
        x for x in [profile.email, profile.phone, profile.location] if x
    )
    links = " | ".join(
        x for x in [profile.linkedin, profile.github, profile.website] if x
    )
    parts = [f"<h1>{esc(profile.full_name)}</h1>"]
    if contact:
        parts.append(f'<div class="contact">{esc(contact)}</div>')
    if links:
        parts.append(f'<div class="contact">{esc(links)}</div>')
    if profile.summary:
        parts.append(f"<h2>Summary</h2><p>{esc(profile.summary)}</p>")
    if profile.skills:
        parts.append(f"<h2>Skills</h2><p>{esc(', '.join(profile.skills))}</p>")
    if profile.experience:
        parts.append("<h2>Experience</h2>")
        for e in profile.experience:
            parts.append(
                f"<p><strong>{esc(e.get('title',''))}</strong> — "
                f"{esc(e.get('company',''))} "
                f"<em>({esc(str(e.get('start','')))}–{esc(str(e.get('end','')))})</em></p>"
            )
            bullets = e.get("bullets", [])
            if bullets:
                parts.append(
                    "<ul>" + "".join(f"<li>{esc(b)}</li>" for b in bullets) + "</ul>"
                )
    if profile.education:
        parts.append("<h2>Education</h2>")
        for ed in profile.education:
            parts.append(
                f"<p>{esc(ed.get('degree',''))}, {esc(ed.get('school',''))} "
                f"<em>({esc(str(ed.get('year','')))})</em></p>"
            )
    return "\n".join(parts)


def tailor_resume_html(
    profile: Profile,
    job_title: str,
    job_description: str,
    brain=None,
) -> str:
    """Return a full HTML document for a resume tailored to the job."""
    body = ""
    if brain is not None:
        try:
            prompt = _TAILOR_INSTRUCTIONS.format(
                profile=_profile_summary_text(profile),
                resume_text=(profile.base_resume_text or "")[:4000],
                job_title=job_title,
                job_description=(job_description or "")[:4000],
            )
            body = brain.chat(prompt).strip()
            # Strip markdown code fences if the model added them.
            if body.startswith("```"):
                body = body.split("```", 2)[1]
                if body.lstrip().lower().startswith("html"):
                    body = body.lstrip()[4:]
        except Exception:
            body = ""
    if not body:
        body = _fallback_html(profile)
    return _HTML_WRAPPER.format(body=body)


def render_pdf(html_doc: str, pdf_path: str) -> bool:
    """Render an HTML resume to a PDF using headless Chromium. Best-effort."""
    out = Path(pdf_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_doc, wait_until="load")
            page.pdf(path=str(out), format="A4",
                     margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
            browser.close()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[resume] PDF render failed ({exc}); saved HTML instead.")
        return False


def build_resume(
    profile: Profile,
    job_title: str,
    job_description: str,
    out_dir: str,
    brain=None,
) -> dict[str, str]:
    """Create tailored resume files for a job. Returns the paths written."""
    safe = "".join(c for c in job_title if c.isalnum() or c in " -_").strip()
    safe = (safe or "job").replace(" ", "_")[:50]
    base = Path(out_dir).expanduser() / f"resume_{safe}"
    base.parent.mkdir(parents=True, exist_ok=True)

    html_doc = tailor_resume_html(profile, job_title, job_description, brain=brain)
    html_path = base.with_suffix(".html")
    html_path.write_text(html_doc)

    result = {"html": str(html_path)}
    pdf_path = base.with_suffix(".pdf")
    if render_pdf(html_doc, str(pdf_path)):
        result["pdf"] = str(pdf_path)
    return result
