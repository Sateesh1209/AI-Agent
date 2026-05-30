"""Build a 'job prep kit' for a specific posting.

Given the candidate's profile/resume and a job posting, JARVIS (Claude) writes:
  * a tailored cover letter,
  * strong answers to common application questions,
  * a few talking points on why the candidate fits.

Reliable, high-value, and no fragile browser automation — just Claude writing.
"""

from __future__ import annotations

from pathlib import Path

from .profile import Profile
from .resume import _profile_summary_text


def build_prep_prompt(profile: Profile, job_text: str) -> str:
    name = profile.full_name or "the candidate"
    salary = profile.answer_for("expected salary") or "Negotiable"
    auth = profile.answer_for("are you authorized to work") or "Yes"
    sponsorship = profile.answer_for("do you require sponsorship") or "Unknown"
    return f"""You are helping {name} prepare a strong job application.

CANDIDATE PROFILE:
{_profile_summary_text(profile)}

CANDIDATE RESUME (ground every claim in these real facts only):
{(profile.base_resume_text or '')[:5000]}

JOB POSTING:
{job_text[:5000]}

Write the following in clean Markdown, truthful and specific (never invent
facts the resume doesn't support):

## Cover Letter
A concise (~250-300 word) cover letter in {name}'s voice, tailored to THIS
role and company.

## Application Q&A
Strong 2-4 sentence answers to:
- Why this company?
- Why are you a strong fit for this role?
- Describe a relevant project from your experience.
- Salary expectations? (use: {salary})
- Work authorization / sponsorship? (authorized: {auth}; sponsorship: {sponsorship})

## Talking Points
3 bullets on the candidate's strongest matches to this job.
"""


def save_prep(content: str, out_dir: str, label: str = "job") -> str:
    safe = "".join(c for c in label if c.isalnum() or c in " -_").strip()
    safe = (safe or "job").replace(" ", "_")[:50]
    base = Path(out_dir).expanduser() / "prep"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{safe}.md"
    path.write_text(content)
    return str(path)
