"""Your job-search profile: who you are, used to fill forms and tailor resumes.

The profile lives in a JSON file (default ``~/.jarvis/profile.json``). It holds
your contact details, experience and skills, the path to your existing resume
(uploaded directly and used as tailoring source), and canned answers to the
common questions job forms ask (work authorization, sponsorship, etc.).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Profile:
    full_name: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    experience: list[dict[str, Any]] = field(default_factory=list)
    education: list[dict[str, Any]] = field(default_factory=list)
    # Path to your existing resume file (PDF/DOCX) to upload / tailor from.
    base_resume_path: str = ""
    base_resume_text: str = ""
    # Canned answers keyed by lowercase question keyword, e.g.
    # {"authorized to work": "Yes", "require sponsorship": "No"}.
    answers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Derive first/last name if only full_name was given.
        if self.full_name and not (self.first_name or self.last_name):
            parts = self.full_name.split()
            self.first_name = parts[0]
            self.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        if not self.full_name and (self.first_name or self.last_name):
            self.full_name = f"{self.first_name} {self.last_name}".strip()

    def field_value(self, key: str) -> str:
        """Return a profile value as a string for filling a form field."""
        return str(getattr(self, key, "") or "")

    def answer_for(self, question: str) -> str | None:
        """Find a canned answer whose keyword appears in the question text."""
        q = question.lower()
        for keyword, answer in self.answers.items():
            if keyword.lower() in q:
                return answer
        return None


def _read_resume_text(path: str) -> str:
    """Best-effort extraction of text from the existing resume for tailoring."""
    p = Path(path).expanduser()
    if not p.is_file():
        return ""
    suffix = p.suffix.lower()
    if suffix in {".txt", ".md"}:
        return p.read_text(errors="replace")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # optional dependency

            reader = PdfReader(str(p))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""  # we can still upload the file even if we can't read it
    return ""


def load_profile(path: str) -> Profile:
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(
            f"No profile found at {p}. Copy profile.example.json there and "
            "fill it in (see the README)."
        )
    data = json.loads(p.read_text())
    profile = Profile(**{k: v for k, v in data.items() if k in Profile.__annotations__})
    if profile.base_resume_path and not profile.base_resume_text:
        profile.base_resume_text = _read_resume_text(profile.base_resume_path)
    return profile
