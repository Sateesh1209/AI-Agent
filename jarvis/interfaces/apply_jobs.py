"""Run the autonomous job-application agent on your logged-in JobRight.

Run:  python main.py apply [how_many]

JARVIS attaches to your open Chrome, and for each job uses its Claude brain to
click 'Apply with Autofill', generate/download the tailored resume, complete the
application, asking you (console/Telegram) when it needs info — and pausing for
your OK before any final submit.
"""

from __future__ import annotations

import sys

_GOAL = (
    "You are on JobRight (jobright.ai), logged in as Sateesh Kumar Nunna, a "
    "Senior Data Engineer (7 years; Python, SQL, Spark, Snowflake, AWS/Azure/GCP). "
    "Apply to the NEXT not-yet-applied job in the recommendations list:\n"
    "1. Click that job's 'Apply with Autofill' button.\n"
    "2. If a 'generate/customize resume' option appears, choose the full/complete "
    "option and WAIT (~10-20s) for it to finish, then download the resume if asked.\n"
    "3. Proceed through the application; let the site's autofill do most of it.\n"
    "4. Fill any empty REQUIRED fields sensibly for this candidate. If a file/resume "
    "upload is needed, use the 'upload' action.\n"
    "5. If you need personal info you don't have, use 'ask_user'.\n"
    "6. Do NOT click the final Submit — use ask_user 'CONFIRM_SUBMIT: <summary>'.\n"
    "When the application is submitted or fully handed to the user, use 'done'."
)


def run(how_many: int = 1) -> None:
    from ..brain import claude_oneshot
    from ..config import config
    from ..jobs.browser import BrowserSession
    from ..jobs.webagent import WebAgent
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
    agent = WebAgent(session, decide=claude_oneshot, notifier=RUNTIME.notifier)

    for n in range(how_many):
        print(f"\n===== Applying to job {n+1} of {how_many} =====")
        result = agent.run(_GOAL, max_steps=30)
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
