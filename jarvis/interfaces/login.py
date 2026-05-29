"""One-time login: open a normal Chrome so you can sign into your job sites.

Run:  python main.py login [url]

This launches a NORMAL Chrome (not an automated one) with remote debugging
enabled, so "Sign in with Google" works without being blocked. You log in by
hand; JARVIS later attaches to this same Chrome to do tasks. Keep the window
open while you use JARVIS for job applications.
"""

from __future__ import annotations

from ..config import config
from ..jobs.browser import launch_debug_chrome


def run(url: str | None = None) -> None:
    target = url or "https://jobright.ai"
    print("Launching JARVIS's Chrome (a normal browser, debugging enabled)...")
    try:
        launch_debug_chrome(config.chrome_debug_dir, config.chrome_debug_port, target)
    except FileNotFoundError:
        print("Couldn't find Google Chrome. Please install it from "
              "https://www.google.com/chrome/ and try again.")
        return

    print(
        "\nA Chrome window opened.\n"
        f"  1. Log into {target} (and any portals you use) normally — "
        "Google sign-in works here.\n"
        "  2. Leave this Chrome window OPEN.\n"
        "  3. Then run your job-application command; JARVIS attaches to this "
        "same window.\n\n"
        f"(JARVIS connects on {config.chrome_cdp_url}. Don't close that Chrome "
        "while JARVIS is working.)"
    )
