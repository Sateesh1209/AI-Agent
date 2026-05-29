"""Tools that let JARVIS apply to jobs on Greenhouse boards."""

from __future__ import annotations

from . import tool
from ..config import config
from ..runtime import RUNTIME


def _load_profile():
    from ..jobs.profile import load_profile

    return load_profile(config.profile_path)


@tool(
    name="list_greenhouse_jobs",
    description=(
        "Open a Greenhouse job board in Chrome and list the open positions "
        "(title + link). Use this to see what's available before applying."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "board_url": {
                "type": "string",
                "description": "Greenhouse board URL, e.g. "
                "https://boards.greenhouse.io/<company>",
            },
        },
        "required": ["board_url"],
    },
)
def list_greenhouse_jobs(board_url: str) -> str:
    from ..jobs.browser import BrowserSession
    from ..jobs.greenhouse import list_jobs

    session = BrowserSession(config.chrome_user_data_dir, headless=False)
    try:
        session.start()
        jobs = list_jobs(session, board_url)
    finally:
        session.close()
    if not jobs:
        return f"No jobs found on {board_url}."
    return "\n".join(f"- {j['title']}: {j['url']}" for j in jobs)


@tool(
    name="apply_to_greenhouse_jobs",
    description=(
        "Apply to jobs on a Greenhouse board. JARVIS opens each posting in "
        "Chrome, tailors a resume from your profile, fills the simple fields "
        "automatically, and submits straightforward applications. For "
        "applications with tricky questions (essays, custom fields) it stops, "
        "screenshots the form, and messages you to finish/approve. Requires a "
        "profile at the configured path and Chrome logged in to the site."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "board_url": {
                "type": "string",
                "description": "Greenhouse board URL.",
            },
            "max_jobs": {
                "type": "integer",
                "description": "Maximum number of jobs to apply to (default 5).",
            },
        },
        "required": ["board_url"],
    },
)
def apply_to_greenhouse_jobs(board_url: str, max_jobs: int = 5) -> str:
    from ..jobs.greenhouse import run_job_applications

    profile = _load_profile()
    # A fresh brain tailors each resume without disturbing the chat history.
    brain = None
    try:
        from ..brain import make_brain
        from ..tools import REGISTRY

        brain = make_brain(config, REGISTRY, "You write tailored resumes.")
    except Exception:
        brain = None  # fall back to template resume

    return run_job_applications(
        board_url=board_url,
        profile=profile,
        config=config,
        max_jobs=int(max_jobs),
        mode="auto_simple",
        brain=brain,
        notifier=RUNTIME.notifier,
    )
