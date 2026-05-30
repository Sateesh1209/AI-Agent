"""Interactive wizard to create your job-application profile.

Run:  python main.py setup-profile

Asks simple questions and writes a valid profile file (default
~/.jarvis/profile.json) — no hand-editing of JSON needed. Run it again any time
to update; your previous answers become the defaults.
"""

from __future__ import annotations

import json
from pathlib import Path


def _build_profile(ask) -> dict:
    """Collect profile fields using the provided ask(prompt, default) callable."""
    print("\nLet's set up your profile. Press Enter to keep the [default].\n")

    full_name = ask("Full name", "")
    email = ask("Email", "")
    phone = ask("Phone number", "")
    location = ask("Location (City, Country)", "")
    linkedin = ask("LinkedIn URL", "")
    github = ask("GitHub URL (optional)", "")
    website = ask("Portfolio/website (optional)", "")
    summary = ask("One-line professional summary", "")
    skills_raw = ask("Top skills (comma-separated)", "")
    resume_path = ask("Full path to your resume file (PDF/DOCX)", "")

    print("\nCommon application questions (these get auto-filled):")
    answers = {
        "authorized to work": ask("Authorized to work? (Yes/No)", "Yes"),
        "require sponsorship": ask("Require visa sponsorship? (Yes/No)", "No"),
        "willing to relocate": ask("Willing to relocate? (Yes/No)", "Yes"),
        "notice period": ask("Notice period", "2 weeks"),
        "salary": ask("Expected salary", "Negotiable"),
        "how did you hear": ask("How did you hear about us?", "Company website"),
    }

    skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
    return {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "location": location,
        "linkedin": linkedin,
        "github": github,
        "website": website,
        "summary": summary,
        "skills": skills,
        "experience": [],
        "education": [],
        "base_resume_path": resume_path,
        "answers": answers,
    }


def run() -> None:
    from ..config import config

    path = Path(config.profile_path).expanduser()
    existing: dict = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text())
            print(f"Found an existing profile at {path} — Enter keeps each value.")
        except Exception:
            existing = {}

    def ask(prompt: str, default: str) -> str:
        # Prefer the existing saved value as the default if present.
        key_map = {
            "Full name": "full_name", "Email": "email", "Phone number": "phone",
            "Location (City, Country)": "location", "LinkedIn URL": "linkedin",
            "GitHub URL (optional)": "github",
            "Portfolio/website (optional)": "website",
            "One-line professional summary": "summary",
            "Full path to your resume file (PDF/DOCX)": "base_resume_path",
        }
        if prompt in key_map and existing.get(key_map[prompt]):
            default = str(existing[key_map[prompt]])
        elif prompt == "Top skills (comma-separated)" and existing.get("skills"):
            default = ", ".join(existing["skills"])
        else:
            ans = existing.get("answers", {})
            for k, v in ans.items():
                if k in prompt.lower():
                    default = v
                    break
        shown = f" [{default}]" if default else ""
        val = input(f"{prompt}{shown}: ").strip()
        return val or default

    data = _build_profile(ask)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))

    print(f"\n✅ Profile saved to {path}")
    if not data["base_resume_path"]:
        print("⚠️  No resume file set — add one later so JARVIS can upload it.")
    print("You can re-run 'python main.py setup-profile' any time to update it.")
