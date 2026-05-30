"""Control the Mac screen: screenshot, move/click the mouse, type, scroll.

Used by the screen-control agent so JARVIS can operate your REAL Chrome (where
you're already logged into JobRight) by looking at the screen — like a person.

Requires macOS permissions (System Settings -> Privacy & Security):
  * Screen Recording  -> enable for Terminal (so screenshots work)
  * Accessibility     -> enable for Terminal (so it can move the mouse/type)

pyautogui is imported lazily so the rest of JARVIS runs without it.
"""

from __future__ import annotations


def scale_coords(x: float, y: float,
                 shot_size: tuple[int, int],
                 logical_size: tuple[int, int]) -> tuple[int, int]:
    """Convert pixel coords on a (Retina) screenshot to logical screen coords.

    Screenshots on Retina Macs are 2x the logical resolution the mouse uses, so
    a click target seen at pixel (x, y) must be scaled down before clicking.
    """
    sw, sh = shot_size
    lw, lh = logical_size
    if not sw or not sh:
        return int(x), int(y)
    return int(x * (lw / sw)), int(y * (lh / sh))


class ScreenController:
    def __init__(self):
        import pyautogui

        self._pg = pyautogui
        pyautogui.FAILSAFE = True  # slam mouse to a corner to abort
        pyautogui.PAUSE = 0.3
        self.logical_size = tuple(pyautogui.size())
        self.shot_size = self.logical_size

    def screenshot(self, path: str) -> str:
        img = self._pg.screenshot()
        self.shot_size = img.size
        img.save(path)
        return path

    def _to_logical(self, x: float, y: float) -> tuple[int, int]:
        return scale_coords(x, y, self.shot_size, self.logical_size)

    def click(self, x: float, y: float, double: bool = False) -> None:
        lx, ly = self._to_logical(x, y)
        if double:
            self._pg.doubleClick(lx, ly)
        else:
            self._pg.click(lx, ly)

    def move(self, x: float, y: float) -> None:
        lx, ly = self._to_logical(x, y)
        self._pg.moveTo(lx, ly, duration=0.2)

    def type_text(self, text: str) -> None:
        self._pg.typewrite(text, interval=0.02)

    def press(self, key: str) -> None:
        self._pg.press(key)

    def hotkey(self, *keys: str) -> None:
        self._pg.hotkey(*keys)

    def scroll(self, amount: int) -> None:
        self._pg.scroll(amount)
