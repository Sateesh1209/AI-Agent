"""Greenhouse-specific helper: list the jobs on a Greenhouse board.

The actual form-filling now uses the generic engine in ``autofill.py`` (which
works on any portal), so this module just knows how to read a Greenhouse board.
``classify_field``/``read_form_fields`` are re-exported from ``fields`` for
backward compatibility.
"""

from __future__ import annotations

from .browser import BrowserSession
from .fields import classify_field, read_form_fields  # noqa: F401  (re-export)


def list_jobs(session: BrowserSession, board_url: str) -> list[dict[str, str]]:
    """Return [{title, url}] for the openings on a Greenhouse board."""
    session.goto(board_url)
    jobs: list[dict[str, str]] = []
    anchors = session.page.query_selector_all("a[href*='/jobs/']")
    seen = set()
    for a in anchors:
        href = a.get_attribute("href") or ""
        title = (a.inner_text() or "").strip()
        if not href or href in seen or not title:
            continue
        seen.add(href)
        if href.startswith("/"):
            origin = "//".join(board_url.split("/")[:1] + [board_url.split("/")[2]])
            href = origin + href
        jobs.append({"title": title, "url": href})
    return jobs
