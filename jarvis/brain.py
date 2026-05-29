"""The 'brain' of JARVIS: an LLM that can call tools in a loop.

Two interchangeable backends are supported:

* ``AnthropicBrain`` - uses the Claude API (best quality, paid).
* ``OllamaBrain``    - uses a local Ollama model (free, private, offline).

Both expose the same interface::

    brain = make_brain(config, registry, system_prompt)
    reply = brain.chat("open my downloads folder")

Each instance keeps its own conversation history so JARVIS remembers context
within a session.
"""

from __future__ import annotations

import json
from typing import Any

from .config import Config
from .tools import ToolRegistry

# How many tool round-trips to allow before forcing a final answer.
_MAX_TOOL_TURNS = 10


class AnthropicBrain:
    def __init__(self, config: Config, registry: ToolRegistry, system_prompt: str):
        import anthropic  # imported lazily so Ollama-only users don't need it

        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.model = config.model
        self.registry = registry
        self.system_prompt = system_prompt
        self.messages: list[dict[str, Any]] = []

    def chat(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(_MAX_TOOL_TURNS):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.system_prompt,
                tools=self.registry.anthropic_schema(),
                messages=self.messages,
            )
            self.messages.append(
                {"role": "assistant", "content": response.content}
            )

            if response.stop_reason != "tool_use":
                return self._text_of(response.content)

            # Execute every requested tool and feed the results back.
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    output = self.registry.execute(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": output,
                        }
                    )
            self.messages.append({"role": "user", "content": tool_results})

        return "I tried several steps but couldn't finish that. Please rephrase."

    @staticmethod
    def _text_of(content: list[Any]) -> str:
        return "".join(b.text for b in content if getattr(b, "type", "") == "text")


class OllamaBrain:
    def __init__(self, config: Config, registry: ToolRegistry, system_prompt: str):
        self.host = config.ollama_host.rstrip("/")
        self.model = config.ollama_model
        self.registry = registry
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

    def chat(self, user_text: str) -> str:
        import requests

        self.messages.append({"role": "user", "content": user_text})

        for _ in range(_MAX_TOOL_TURNS):
            resp = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": self.messages,
                    "tools": self.registry.ollama_schema(),
                    "stream": False,
                },
                timeout=300,
            )
            resp.raise_for_status()
            message = resp.json()["message"]
            self.messages.append(message)

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return message.get("content", "")

            for call in tool_calls:
                fn = call["function"]
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                output = self.registry.execute(fn["name"], args)
                self.messages.append(
                    {"role": "tool", "name": fn["name"], "content": output}
                )

        return "I tried several steps but couldn't finish that. Please rephrase."


class ClaudeCodeBrain:
    """Use the Claude Code CLI (``claude``) as the brain.

    This lets JARVIS run on a Claude Max/Pro *subscription* (no per-token API
    fees): the ``claude`` command is logged in with the user's account. Claude
    Code brings its own powerful built-in tools (Bash, file read/write, web),
    so JARVIS can reliably act on the local machine.

    Auth: relies on ``claude`` being logged in (``claude /login``) or a
    ``CLAUDE_CODE_OAUTH_TOKEN`` env var. We deliberately drop ANTHROPIC_API_KEY
    from the subprocess so the subscription is used, not paid API tokens.
    """

    # Built-in Claude Code tools JARVIS is allowed to use without prompts.
    ALLOWED_TOOLS = "Bash Read Write Edit Glob Grep WebFetch WebSearch"

    def __init__(self, config: Config, registry: ToolRegistry, system_prompt: str):
        import shutil

        if shutil.which("claude") is None:
            raise RuntimeError(
                "The 'claude' command (Claude Code) isn't installed. Install it "
                "and log in with your Max account — see SETUP.md."
            )
        self.system_prompt = system_prompt
        self.session_id: str | None = None

    def chat(self, user_text: str) -> str:
        import json
        import os
        import subprocess

        cmd = [
            "claude", "-p", user_text,
            "--output-format", "json",
            "--allowedTools", self.ALLOWED_TOOLS,
        ]
        if self.session_id:
            cmd += ["--resume", self.session_id]
        else:
            cmd += ["--append-system-prompt", self.system_prompt]

        env = os.environ.copy()
        # Ensure the subscription (OAuth) is used rather than billed API tokens.
        env.pop("ANTHROPIC_API_KEY", None)

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, env=env, timeout=600
            )
        except FileNotFoundError:
            return "Claude Code isn't installed. See SETUP.md."
        except subprocess.TimeoutExpired:
            return "That took too long, let's try a smaller step."

        if proc.returncode != 0:
            return f"(Claude Code error: {proc.stderr.strip()[:300]})"
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return proc.stdout.strip() or "(no response)"
        self.session_id = data.get("session_id", self.session_id)
        return data.get("result", "") or "(done)"


def make_brain(
    config: Config, registry: ToolRegistry, system_prompt: str
):
    """Factory that returns the brain matching the configured backend."""
    if config.backend == "ollama":
        return OllamaBrain(config, registry, system_prompt)
    if config.backend == "claude_code":
        return ClaudeCodeBrain(config, registry, system_prompt)
    return AnthropicBrain(config, registry, system_prompt)
