"""Tools that let JARVIS apply to jobs across job boards / aggregators."""

from __future__ import annotations

from . import tool
from ..config import config
from ..runtime import RUNTIME


def _load_profile():
    from ..jobs.profile import load_profile

    return load_profile(config.profile_path)


def _resume_brain():
    """A throwaway brain for tailoring resumes (no tools, isolated history)."""
    try:
        from ..brain import make_brain
        from ..tools import REGISTRY

        return make_brain(config, REGISTRY, "You write tailored resumes.")
    except Exception:
        return None  # fall back to the offline template resume


@tool(
    name="apply_to_jobs",
    description=(
        "Apply to jobs on a job board / aggregator (Jobright or similar). "
        "JARVIS opens the board in its Chrome (where you're already logged in), "
        "clicks each job's Apply/Autofill button, follows the redirect to "
        "whatever portal the job uses, lets the site's autofill run, then fills "
        "any remaining fields from your profile and attaches a tailored resume. "
        "Simple applications are submitted; ones with tricky questions are "
        "screenshotted and sent to you on Telegram to finish. Requires your "
        "profile file and that you've logged in once (see setup_job_login)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "board_url": {
                "type": "string",
                "description": "URL of the job board/aggregator listing page.",
            },
            "max_jobs": {
                "type": "integer",
                "description": "Max number of jobs to apply to (default 5).",
            },
        },
        "required": ["board_url"],
    },
)
def apply_to_jobs(board_url: str, max_jobs: int = 5) -> str:
    from ..jobs.aggregator import apply_from_job_board
    from ..jobs.browser import BrowserSession

    profile = _load_profile()
    session = BrowserSession(config.chrome_user_data_dir, headless=False)
    try:
        session.start()
        return apply_from_job_board(
            session,
            board_url=board_url,
            profile=profile,
            config=config,
            max_jobs=int(max_jobs),
            mode="auto_simple",
            brain=_resume_brain(),
            notifier=RUNTIME.notifier,
        )
    finally:
        session.close()


@tool(
    name="setup_job_login",
    description=(
        "Open JARVIS's Chrome to a site so the user can log in once. The "
        "session is saved in JARVIS's dedicated Chrome profile and reused for "
        "future applications (no passwords are stored). Use this when the user "
        "needs to sign in to a job board or portal."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Site URL to open for login."},
        },
        "required": ["url"],
    },
)
def setup_job_login(url: str) -> str:
    from ..jobs.browser import BrowserSession

    session = BrowserSession(config.chrome_user_data_dir, headless=False)
    session.start()
    session.goto(url)
    return (
        f"Opened {url} in JARVIS's Chrome. Log in there; the session is saved. "
        "Close the window when done."
    )


@tool(
    name="list_greenhouse_jobs",
    description=(
        "List the open positions on a Greenhouse board (boards.greenhouse.io)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "board_url": {"type": "string", "description": "Greenhouse board URL."},
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
