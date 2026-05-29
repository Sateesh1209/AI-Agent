"""Unit tests for the job-application logic that doesn't need a browser.

Run with:  python -m pytest tests/  (or just: python tests/test_jobs.py)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis.jobs.greenhouse import classify_field  # noqa: E402
from jarvis.jobs.profile import Profile  # noqa: E402
from jarvis.jobs.resume import tailor_resume_html  # noqa: E402


def test_classify_simple_fields():
    assert classify_field("First Name *") == ("profile", "first_name")
    assert classify_field("Last Name") == ("profile", "last_name")
    assert classify_field("Email") == ("profile", "email")
    assert classify_field("Phone") == ("profile", "phone")
    assert classify_field("LinkedIn Profile") == ("profile", "linkedin")
    assert classify_field("Full Name") == ("profile", "full_name")


def test_classify_resume_and_tricky():
    assert classify_field("Resume/CV") == ("resume", "")
    assert classify_field("Upload your résumé") == ("resume", "")
    assert classify_field("Why do you want to work here?") == ("tricky", "")
    assert classify_field("") == ("tricky", "")


def test_profile_name_derivation():
    p = Profile(full_name="Jane Q Public")
    assert p.first_name == "Jane"
    assert p.last_name == "Q Public"


def test_profile_canned_answers():
    p = Profile(answers={"authorized to work": "Yes", "sponsorship": "No"})
    assert p.answer_for("Are you authorized to work here?") == "Yes"
    assert p.answer_for("Do you need sponsorship?") == "No"
    assert p.answer_for("totally unrelated") is None


def test_resume_fallback_html_contains_profile():
    p = Profile(full_name="Jane Public", email="j@x.com",
                skills=["Python", "AWS"])
    html = tailor_resume_html(p, "Engineer", "Python role", brain=None)
    assert "<html" in html
    assert "Jane Public" in html
    assert "Python" in html


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in funcs:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nAll {len(funcs)} tests passed.")
