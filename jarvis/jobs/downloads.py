"""Find files JobRight (or a portal) just downloaded to the Mac.

After JobRight generates a tailored resume, it downloads a PDF to the user's
Downloads folder. JARVIS grabs that freshly-downloaded file to upload on the
application form.
"""

from __future__ import annotations

import time
from pathlib import Path


def latest_download(
    folder: str = "~/Downloads",
    suffixes: tuple[str, ...] = (".pdf", ".docx", ".doc"),
    within_seconds: float | None = 600,
) -> str | None:
    """Return the path to the most recently modified resume-like download.

    If ``within_seconds`` is set, ignore files older than that (so we pick the
    one JobRight just generated, not an old file).
    """
    p = Path(folder).expanduser()
    if not p.is_dir():
        return None
    candidates = [
        f for f in p.iterdir()
        if f.is_file() and f.suffix.lower() in suffixes
    ]
    if not candidates:
        return None
    newest = max(candidates, key=lambda f: f.stat().st_mtime)
    if within_seconds is not None:
        age = time.time() - newest.stat().st_mtime
        if age > within_seconds:
            return None
    return str(newest)


def wait_for_download(
    folder: str = "~/Downloads",
    suffixes: tuple[str, ...] = (".pdf",),
    timeout: float = 40,
    poll: float = 1.0,
) -> str | None:
    """Wait up to ``timeout`` seconds for a new download to appear/finish."""
    p = Path(folder).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        # Skip partially-downloaded Chrome files (*.crdownload).
        partial = any(f.suffix == ".crdownload" for f in p.iterdir() if f.is_file())
        if not partial:
            found = latest_download(folder, suffixes, within_seconds=timeout + 10)
            if found:
                return found
        time.sleep(poll)
    return None
