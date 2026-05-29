"""Run the autonomous job-application agent on your logged-in JobRight.

Run:  python main.py apply [how_many]

JARVIS attaches to your open Chrome, and for each job uses its Claude brain to
click 'Apply with Autofill', generate/download the tailored resume, complete the
application, asking you (console/Telegram) when it needs info — and pausing for
your OK before any final submit.
"""

from __future__ import annotations

import sys


def run(how_many: int = 1) -> None:
    from ..brain import claude_oneshot
    from ..config import config
    from ..jobs.browser import BrowserSession
    from ..jobs.webagent import JOBRIGHT_GOAL, WebAgent
    from ..runtime import RUNTIME

    if config.backend != "claude_code":
        print("⚠️  The job agent works best with JARVIS_BACKEND=claude_code "
              "(your Claude Max plan). Continuing anyway.")

    session = BrowserSession.from_config(config)
    try:
        session.start()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ {exc}")
        print("Run 'python main.py login https://jobright.ai' first and keep "
              "that Chrome open.")
        return

    session.focus("jobright")
    agent = WebAgent(session, decide=claude_oneshot, notifier=RUNTIME.notifier,
                     use_vision=True)

    for n in range(how_many):
        print(f"\n===== Applying to job {n+1} of {how_many} =====")
        result = agent.run(JOBRIGHT_GOAL, max_steps=30)
        print(result)
        # Return to the job list for the next one.
        try:
            session.focus("jobright")
            session.goto("https://jobright.ai/jobs/recommend")
            session.page.wait_for_timeout(2000)
        except Exception:
            pass

    session.close()
    print("\nFinished. Review the browser to confirm.")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
