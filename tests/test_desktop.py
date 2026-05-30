"""Tests for the screen-control coordinate scaling (Retina-safe).

Run:  python tests/test_desktop.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis.desktop import scale_coords  # noqa: E402


def test_retina_2x_halves_coords():
    # Screenshot is 2880x1800 px, logical screen is 1440x900.
    assert scale_coords(1000, 600, (2880, 1800), (1440, 900)) == (500, 300)


def test_non_retina_identity():
    assert scale_coords(300, 200, (1440, 900), (1440, 900)) == (300, 200)


def test_zero_size_is_safe():
    assert scale_coords(10, 20, (0, 0), (1440, 900)) == (10, 20)


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in funcs:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nAll {len(funcs)} tests passed.")
