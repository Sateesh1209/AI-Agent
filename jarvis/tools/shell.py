"""Run shell commands on the local machine."""

from __future__ import annotations

import subprocess

from . import tool
from ..config import config

# Commands containing these tokens are treated as dangerous and (optionally)
# require confirmation before running.
_DANGEROUS_TOKENS = ("rm ", "rmdir", "mkfs", "dd ", "shutdown", "reboot",
                     "format", ":(){", "> /dev", "sudo rm")


def _looks_dangerous(command: str) -> bool:
    lowered = command.lower()
    return any(tok in lowered for tok in _DANGEROUS_TOKENS)


@tool(
    name="run_shell_command",
    description=(
        "Run a shell command on the user's local machine and return its "
        "stdout/stderr. Use this for tasks like listing files, checking "
        "system info, opening apps, or running scripts. Avoid destructive "
        "commands unless the user clearly asked for them."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Max seconds to wait (default 60).",
            },
        },
        "required": ["command"],
    },
)
def run_shell_command(command: str, timeout: int = 60) -> str:
    if config.confirm_dangerous and _looks_dangerous(command):
        answer = input(
            f"\n[JARVIS] This command looks dangerous:\n  {command}\n"
            f"Run it? [y/N] "
        )
        if answer.strip().lower() not in {"y", "yes"}:
            return "Command cancelled by the user."

    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds."

    parts = []
    if proc.stdout:
        parts.append(proc.stdout.strip())
    if proc.stderr:
        parts.append(f"[stderr] {proc.stderr.strip()}")
    parts.append(f"[exit code: {proc.returncode}]")
    return "\n".join(parts) or "(no output)"
