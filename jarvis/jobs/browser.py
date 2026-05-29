"""A thin Playwright wrapper so JARVIS can drive a real Chrome browser.

Preferred mode (CDP attach): you launch a normal Chrome yourself (where Google
login works fine) with remote debugging enabled, log in by hand, and JARVIS
*attaches* to that already-logged-in Chrome to drive it. Google never sees
automation during login, so "Sign in with Google" works.

Fallback mode (launch): Playwright launches its own Chrome with a dedicated
profile. Simpler, but Google may block sign-in in this automated browser.

First-time setup on your Mac:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

# Where Chrome lives on each OS (for launching the debugging instance).
_CHROME_PATHS = {
    "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "Linux": "google-chrome",
    "Windows": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
}


def launch_debug_chrome(debug_dir: str, port: int = 9222,
                        url: str | None = None) -> subprocess.Popen:
    """Launch a normal (non-automation) Chrome with remote debugging on.

    This is the Chrome JARVIS will attach to. Because the user launches and
    logs into it normally, Google sign-in is not blocked.
    """
    chrome = _CHROME_PATHS.get(platform.system(), "google-chrome")
    Path(debug_dir).expanduser().mkdir(parents=True, exist_ok=True)
    args = [
        chrome,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={Path(debug_dir).expanduser()}",
    ]
    if url:
        args.append(url)
    return subprocess.Popen(args)


class BrowserSession:
    def __init__(self, user_data_dir: str, headless: bool = False,
                 channel: str = "chrome", cdp_url: str | None = None):
        self.user_data_dir = str(Path(user_data_dir).expanduser())
        self.headless = headless
        self.channel = channel
        self.cdp_url = cdp_url or None
        self._pw = None
        self._browser = None       # set when attached over CDP
        self._context = None
        self._via_cdp = False
        self.page = None

    @classmethod
    def from_config(cls, config) -> "BrowserSession":
        return cls(
            config.chrome_user_data_dir,
            headless=False,
            cdp_url=getattr(config, "chrome_cdp_url", "") or None,
        )

    def start(self) -> None:
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()

        # Preferred: attach to a user-launched Chrome that's already logged in.
        if self.cdp_url:
            try:
                self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
                self._via_cdp = True
                self._context = (
                    self._browser.contexts[0]
                    if self._browser.contexts
                    else self._browser.new_context()
                )
                self.page = (
                    self._context.pages[0]
                    if self._context.pages
                    else self._context.new_page()
                )
                return
            except Exception as exc:  # noqa: BLE001
                self._pw.stop()
                raise RuntimeError(
                    "Couldn't connect to JARVIS's Chrome. Run "
                    "'python main.py login <url>' first and keep that Chrome "
                    f"window open. (details: {exc})"
                )

        # Fallback: launch our own Chrome (Google login may be blocked here).
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
        launch_kwargs = {"user_data_dir": self.user_data_dir, "headless": self.headless}
        try:
            self._context = self._pw.chromium.launch_persistent_context(
                channel=self.channel, **launch_kwargs
            )
        except Exception:
            self._context = self._pw.chromium.launch_persistent_context(**launch_kwargs)
        self.page = (
            self._context.pages[0] if self._context.pages else self._context.new_page()
        )

    # -- navigation / reading ---------------------------------------------
    def goto(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")

    def visible_text(self, max_chars: int = 6000) -> str:
        text = self.page.inner_text("body")
        return text[:max_chars]

    def screenshot(self, path: str) -> str:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=path, full_page=True)
        return path

    def use_latest_page(self):
        """Switch to the most recently opened tab (e.g. after 'Apply')."""
        if self._context and self._context.pages:
            self.page = self._context.pages[-1]
        return self.page

    def page_count(self) -> int:
        return len(self._context.pages) if self._context else 0

    # -- interaction -------------------------------------------------------
    def click(self, selector: str, timeout: int = 8000) -> bool:
        try:
            self.page.click(selector, timeout=timeout)
            return True
        except Exception:
            return False

    def fill(self, selector: str, value: str, timeout: int = 8000) -> bool:
        try:
            self.page.fill(selector, value, timeout=timeout)
            return True
        except Exception:
            return False

    def upload(self, selector: str, file_path: str, timeout: int = 8000) -> bool:
        try:
            self.page.set_input_files(selector, file_path, timeout=timeout)
            return True
        except Exception:
            return False

    def close(self) -> None:
        # When attached over CDP, leave the user's Chrome running.
        try:
            if self._context and not self._via_cdp:
                self._context.close()
        finally:
            if self._pw:
                self._pw.stop()
