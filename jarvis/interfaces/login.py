"""One-time login: open JARVIS's Chrome so you can sign into your job sites.

Run:  python main.py login [url]

You log in once here; the session is saved in JARVIS's dedicated Chrome profile
and reused for future applications. No passwords are stored by JARVIS.
"""

from __future__ import annotations

from ..config import config
from ..jobs.browser import BrowserSession


def run(url: str | None = None) -> None:
    session = BrowserSession(config.chrome_user_data_dir, headless=False)
    session.start()
    if url:
        session.goto(url)
    print(
        "\nA Chrome window controlled by JARVIS is open.\n"
        "Log into your job boards/portals there (Jobright, Workday, etc.).\n"
        "When you're done, come back here and press Enter to save the session."
    )
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass
    session.close()
    print("Session saved. JARVIS will reuse these logins.")
