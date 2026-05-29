"""Quick diagnostic: prove JARVIS can see your logged-in Chrome.

Run:  python main.py browser-check

Attaches to the Chrome you launched with 'python main.py login', finds the
JobRight tab, reports what it sees, counts the apply buttons, and saves a
screenshot — so you can confirm JARVIS is connected before we automate.
"""

from __future__ import annotations

from pathlib import Path


def run() -> None:
    from ..config import config
    from ..jobs.browser import BrowserSession

    session = BrowserSession.from_config(config)
    try:
        session.start()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ {exc}")
        print("\nMake sure you ran 'python main.py login https://jobright.ai' "
              "and that the Chrome window is still open.")
        return

    print("✅ Connected to your Chrome!\n")

    tabs = session.open_tabs()
    print(f"Open tabs ({len(tabs)}):")
    for t in tabs:
        print(f"  - {t}")

    # Focus the JobRight tab if present.
    session.focus("jobright")
    page = session.page
    try:
        print(f"\nLooking at: {page.url}")
        print(f"Page title: {page.title()}")
    except Exception:
        pass

    # Count the apply / autofill buttons JARVIS can see.
    try:
        buttons = page.query_selector_all("button, a, div[role=button]")
        apply_like = []
        for b in buttons:
            txt = (b.inner_text() or "").strip().lower()
            if "autofill" in txt or txt == "apply" or "apply with" in txt:
                apply_like.append(txt[:40])
        print(f"\nFound {len(apply_like)} apply/autofill buttons on this page.")
        for t in apply_like[:8]:
            print(f"  • {t}")
    except Exception as exc:  # noqa: BLE001
        print(f"(couldn't scan buttons: {exc})")

    # Screenshot proof.
    shot = str(Path(config.profile_path).expanduser().parent / "browser_check.png")
    try:
        session.screenshot(shot)
        print(f"\n📸 Saved a screenshot of what JARVIS sees to:\n   {shot}")
    except Exception as exc:  # noqa: BLE001
        print(f"(screenshot failed: {exc})")

    print("\nIf you see your JobRight job list above, JARVIS is connected. 🎉")
    session.close()
