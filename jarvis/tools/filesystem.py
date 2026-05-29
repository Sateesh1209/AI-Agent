"""Read, write and list files on the local machine."""

from __future__ import annotations

import os
from pathlib import Path

from . import tool

_MAX_READ_CHARS = 20_000


@tool(
    name="read_file",
    description="Read the contents of a text file on the local machine.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file."},
        },
        "required": ["path"],
    },
)
def read_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.is_file():
        return f"No such file: {p}"
    text = p.read_text(errors="replace")
    if len(text) > _MAX_READ_CHARS:
        return text[:_MAX_READ_CHARS] + "\n...(truncated)"
    return text


@tool(
    name="write_file",
    description=(
        "Create or overwrite a text file with the given content. "
        "Parent directories are created automatically."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to write to."},
            "content": {"type": "string", "description": "Text to write."},
        },
        "required": ["path", "content"],
    },
)
def write_file(path: str, content: str) -> str:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"Wrote {len(content)} characters to {p}"


@tool(
    name="list_directory",
    description="List the files and folders inside a directory.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path (default: current directory).",
            },
        },
    },
)
def list_directory(path: str = ".") -> str:
    p = Path(path).expanduser()
    if not p.is_dir():
        return f"Not a directory: {p}"
    entries = sorted(os.listdir(p))
    if not entries:
        return f"{p} is empty."
    lines = []
    for name in entries:
        full = p / name
        kind = "dir " if full.is_dir() else "file"
        lines.append(f"[{kind}] {name}")
    return "\n".join(lines)
