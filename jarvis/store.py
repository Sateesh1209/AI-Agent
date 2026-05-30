"""Persistent storage for JARVIS (scheduled tasks, reminders).

Tasks are kept as a JSON list on disk (default: ``~/.jarvis/tasks.json``) so
that reminders and recurring jobs survive restarts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path.home() / ".jarvis" / "tasks.json"


class TaskStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else DEFAULT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def _read(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.path.read_text() or "[]")
        except json.JSONDecodeError:
            return []

    def _write(self, data: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def all(self) -> list[dict[str, Any]]:
        return self._read()

    def add(self, task: dict[str, Any]) -> dict[str, Any]:
        data = self._read()
        data.append(task)
        self._write(data)
        return task

    def remove(self, task_id: str) -> None:
        data = [t for t in self._read() if t.get("id") != task_id]
        self._write(data)

    def get(self, task_id: str) -> dict[str, Any] | None:
        return next((t for t in self._read() if t.get("id") == task_id), None)
