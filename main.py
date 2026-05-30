#!/usr/bin/env python3
"""JARVIS launcher.

Usage:
    python main.py            # voice mode (falls back to text if no mic)
    python main.py text       # text chat in the terminal
    python main.py voice      # voice mode
    python main.py telegram   # run the Telegram bot
    python main.py login [url]# open JARVIS's Chrome to log into job sites once
    python main.py check          # verify your setup (run this first!)
    python main.py setup-profile  # create your job-application profile
"""

from __future__ import annotations

import sys


def main() -> None:
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "voice"

    if mode == "text":
        from jarvis.interfaces import cli

        cli.run()
    elif mode in {"voice", "speak"}:
        from jarvis.interfaces import voice_loop

        voice_loop.run()
    elif mode == "telegram":
        from jarvis.interfaces import telegram_bot

        telegram_bot.run()
    elif mode == "login":
        from jarvis.interfaces import login

        login.run(sys.argv[2] if len(sys.argv) > 2 else None)
    elif mode == "check":
        from jarvis.interfaces import selfcheck

        selfcheck.run()
    elif mode == "setup-profile":
        from jarvis.interfaces import setup_profile

        setup_profile.run()
    elif mode == "browser-check":
        from jarvis.interfaces import browser_check

        browser_check.run()
    elif mode == "snapshot":
        from jarvis.interfaces import snapshot

        snapshot.run(sys.argv[2] if len(sys.argv) > 2 else None)
    elif mode == "apply":
        from jarvis.interfaces import apply_jobs

        apply_jobs.run(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    elif mode == "screen-apply":
        from jarvis.interfaces import screen_apply

        screen_apply.run()
    elif mode == "prep":
        from jarvis.interfaces import prep

        prep.run()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
