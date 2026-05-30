"""Run the screen-control job agent on your REAL screen.

Run:  python main.py screen-apply

JARVIS looks at your screen and operates your real Chrome to apply on JobRight.
Before running: open Chrome, go to jobright.ai, and make sure you're logged in.

Requires macOS permissions (System Settings -> Privacy & Security):
  * Screen Recording  -> Terminal
  * Accessibility     -> Terminal
"""

from __future__ import annotations

_GOAL = (
    "Apply to the next job on JobRight for Sateesh Kumar Nunna, a Senior Data "
    "Engineer. In the Chrome window showing jobright.ai:\n"
    "1. Pick the top recommended job and open it.\n"
    "2. Use 'Customize/Generate resume' (full edit + add missing skills); wait "
    "~15s for it to finish, then download the resume.\n"
    "3. Click 'Apply with Autofill' / 'Apply now' to start the application.\n"
    "4. If a company portal needs SIGN IN, use ask_user 'LOGIN NEEDED: <portal> "
    "— sign in, then reply done'.\n"
    "5. Fill any empty required fields sensibly; ask_user for info you lack.\n"
    "6. Do NOT submit — use ask_user 'CONFIRM_SUBMIT: <summary>'.\n"
    "Use 'done' when the application is submitted or handed to the user."
)


def run() -> None:
    from ..brain import claude_oneshot
    from ..config import config
    from ..jobs.screen_agent import ScreenAgent
    from ..runtime import RUNTIME

    if config.backend != "claude_code":
        print("⚠️  Screen-control uses Claude's vision — set "
              "JARVIS_BACKEND=claude_code (your Max plan) for best results.")

    try:
        from ..desktop import ScreenController
        controller = ScreenController()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Couldn't start screen control: {exc}")
        print("Install support with:  pip install pyautogui pillow")
        print("And grant Terminal Screen Recording + Accessibility permissions.")
        return

    print("\n🖥️  Screen-control starting in 5 seconds.")
    print("   • Click your Chrome window (on jobright.ai) so it's in front.")
    print("   • Then DON'T touch the mouse/keyboard while JARVIS works.")
    print("   • To STOP instantly: slam the mouse to a screen corner, or "
          "press Ctrl+C here.\n")
    import time
    time.sleep(5)

    agent = ScreenAgent(controller, decide=claude_oneshot,
                        notifier=RUNTIME.notifier)
    result = agent.run(_GOAL, max_steps=40)
    print("\n" + result)
