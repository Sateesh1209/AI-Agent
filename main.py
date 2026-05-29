#!/usr/bin/env python3
"""JARVIS launcher.

Usage:
    python main.py            # voice mode (falls back to text if no mic)
    python main.py text       # text chat in the terminal
    python main.py voice      # voice mode
    python main.py telegram   # run the Telegram bot
    python main.py login [url]# open JARVIS's Chrome to log into job sites once
    python main.py check      # verify your setup (run this first!)
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
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
