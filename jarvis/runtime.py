"""Shared runtime objects.

Some tools (like scheduling a reminder) need to reach the live scheduler and
notifier that the running interface set up. Rather than passing them through
every layer, the active interface registers them here at startup and tools read
them back.
"""

from __future__ import annotations

from typing import Any


class Runtime:
    scheduler: Any = None
    notifier: Any = None


# Single shared instance populated by the Jarvis agent at startup.
RUNTIME = Runtime()
