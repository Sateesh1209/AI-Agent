"""Higher-level OS actions: open apps / URLs and report basic system info."""

from __future__ import annotations

import platform
import subprocess
import webbrowser
from datetime import datetime

from . import tool


@tool(
    name="open_url",
    description="Open a URL in the user's default web browser.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to open."},
        },
        "required": ["url"],
    },
)
def open_url(url: str) -> str:
    webbrowser.open(url)
    return f"Opened {url} in the browser."


@tool(
    name="open_application",
    description=(
        "Open a desktop application by name (e.g. 'Safari', 'Notes', "
        "'Calculator'). Works on macOS, Windows and Linux."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Application name."},
        },
        "required": ["name"],
    },
)
def open_application(name: str) -> str:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", "-a", name], check=True)
        elif system == "Windows":
            subprocess.run(["cmd", "/c", "start", "", name], check=True)
        else:  # Linux
            subprocess.Popen([name])
        return f"Launched '{name}'."
    except Exception as exc:
        return f"Could not open '{name}': {exc}"


@tool(
    name="get_system_info",
    description="Return the current date/time and basic OS information.",
    input_schema={"type": "object", "properties": {}},
)
def get_system_info() -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"Date/time: {now}\n"
        f"OS: {platform.system()} {platform.release()}\n"
        f"Machine: {platform.machine()}\n"
        f"Python: {platform.python_version()}"
    )
