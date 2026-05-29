"""Snapshot whatever screen JARVIS is currently looking at.

Run:  python main.py snapshot [url-substring]

Attaches to your Chrome, focuses the matching tab (or the latest one), and
reports the buttons and form fields it sees, plus a screenshot. This is how we
'teach' JARVIS each step of a new site: navigate there, snapshot it, and the
automation gets built to match.
"""

from __future__ import annotations

import sys
from pathlib import Path


def run(focus_substring: str | None = None) -> None:
    from ..config import config
    from ..jobs.browser import BrowserSession

    session = BrowserSession.from_config(config)
    try:
        session.start()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ {exc}")
        return

    tabs = session.open_tabs()
    print(f"Open tabs ({len(tabs)}):")
    for t in tabs:
        print(f"  - {t}")

    if focus_substring:
        session.focus(focus_substring)
    else:
        session.use_latest_page()
    page = session.page

    try:
        print(f"\n📍 Looking at: {page.url}")
        print(f"   Title: {page.title()}\n")
    except Exception:
        pass

    # Buttons / clickable things.
    try:
        clickables = page.query_selector_all("button, a, div[role=button], [role=button]")
        seen = []
        for el in clickables:
            txt = " ".join((el.inner_text() or "").split())
            if txt and txt not in seen:
                seen.append(txt)
        print(f"🔘 Buttons/links ({len(seen)} unique):")
        for t in seen[:30]:
            print(f"   • {t[:60]}")
    except Exception as exc:  # noqa: BLE001
        print(f"(couldn't scan buttons: {exc})")

    # Form fields.
    try:
        inputs = page.query_selector_all("input, textarea, select")
        fields = []
        for el in inputs:
            itype = (el.get_attribute("type") or el.evaluate("e=>e.tagName")).lower()
            if itype in {"hidden"}:
                continue
            label = (el.get_attribute("aria-label") or el.get_attribute("placeholder")
                     or el.get_attribute("name") or "")
            fields.append(f"{itype}: {label[:40]}")
        if fields:
            print(f"\n📝 Form fields ({len(fields)}):")
            for f in fields[:30]:
                print(f"   • {f}")
    except Exception as exc:  # noqa: BLE001
        print(f"(couldn't scan fields: {exc})")

    shot = str(Path(config.profile_path).expanduser().parent / "snapshot.png")
    try:
        session.screenshot(shot)
        print(f"\n📸 Screenshot saved to: {shot}")
    except Exception as exc:  # noqa: BLE001
        print(f"(screenshot failed: {exc})")

    session.close()


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
