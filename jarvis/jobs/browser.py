"""A thin Playwright wrapper so JARVIS can drive a real Chrome browser.

It uses a *dedicated, persistent* Chrome profile (default ~/.jarvis/chrome) so
you log into job sites once and JARVIS reuses that session — acting as you, not
as a fresh suspicious bot. Playwright is imported lazily so the rest of JARVIS
runs even when browser support isn't installed.

First-time setup on your Mac:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

from pathlib import Path


class BrowserSession:
    def __init__(self, user_data_dir: str, headless: bool = False,
                 channel: str = "chrome"):
        self.user_data_dir = str(Path(user_data_dir).expanduser())
        self.headless = headless
        self.channel = channel
        self._pw = None
        self._context = None
        self.page = None

    def start(self) -> None:
        from playwright.sync_api import sync_playwright

        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()
        launch_kwargs = {
            "user_data_dir": self.user_data_dir,
            "headless": self.headless,
        }
        # Prefer the user's installed Chrome; fall back to bundled Chromium.
        try:
            self._context = self._pw.chromium.launch_persistent_context(
                channel=self.channel, **launch_kwargs
            )
        except Exception:
            self._context = self._pw.chromium.launch_persistent_context(
                **launch_kwargs
            )
        self.page = (
            self._context.pages[0]
            if self._context.pages
            else self._context.new_page()
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
        try:
            if self._context:
                self._context.close()
        finally:
            if self._pw:
                self._pw.stop()
