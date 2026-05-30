"""Tests for the autonomous browser agent's pure logic.

Run:  python tests/test_webagent.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis.jobs.webagent import WebAgent, collect_elements, parse_action  # noqa: E402


def test_parse_action_plain_json():
    a = parse_action('{"action": "click", "index": 3, "value": "", "reason": "go"}')
    assert a["action"] == "click" and a["index"] == 3


def test_parse_action_with_prose_and_fences():
    raw = 'Sure!\n```json\n{"action":"fill","index":1,"value":"x","reason":"y"}\n```'
    a = parse_action(raw)
    assert a["action"] == "fill" and a["value"] == "x"


def test_parse_action_garbage_returns_none():
    assert parse_action("no json here") is None
    assert parse_action("") is None


class _FakeHandle:
    def __init__(self, tag, text="", visible=True, attrs=None, value=""):
        self._tag = tag
        self._text = text
        self._visible = visible
        self._attrs = attrs or {}
        self._value = value

    def is_visible(self):
        return self._visible

    def evaluate(self, _js):
        return self._tag.upper()

    def get_attribute(self, name):
        return self._attrs.get(name)

    def inner_text(self):
        return self._text

    def input_value(self):
        return self._value


class _FakePage:
    def __init__(self, handles):
        self._handles = handles

    def query_selector_all(self, _sel):
        return self._handles


def test_collect_elements_describes_buttons_and_fields_skips_hidden():
    handles = [
        _FakeHandle("button", text="Apply with Autofill"),
        _FakeHandle("input", attrs={"type": "email", "aria-label": "Email"}, value="a@b.com"),
        _FakeHandle("input", attrs={"type": "hidden"}),       # skipped
        _FakeHandle("a", text="", visible=True),               # no text -> skipped
        _FakeHandle("button", text="Submit", visible=False),   # invisible -> skipped
    ]
    items = collect_elements(_FakePage(handles))
    descs = [d for _, d in items]
    assert any("Apply with Autofill" in d for d in descs)
    assert any("Email" in d and "a@b.com" in d for d in descs)
    assert len(items) == 2  # only the button + email field


def test_agent_done_stops_immediately():
    page = _FakePage([_FakeHandle("button", text="X")])

    class _S:
        def __init__(self, p):
            self.page = p

        def use_latest_page(self):
            return self.page

    decide = lambda _p: '{"action":"done","index":null,"value":"","reason":"finished"}'
    agent = WebAgent(_S(page), decide=decide)
    out = agent.run("goal", max_steps=5)
    assert "Done" in out


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in funcs:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nAll {len(funcs)} tests passed.")
