"""Tool registry for JARVIS.

A "tool" is a Python function JARVIS can decide to call. Each tool declares a
name, a description (so the model knows when to use it) and a JSON-schema for
its inputs. Tools register themselves with the global ``REGISTRY`` via the
``@tool`` decorator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    func: Callable[..., str]

    def run(self, **kwargs: Any) -> str:
        try:
            result = self.func(**kwargs)
            return str(result)
        except Exception as exc:  # surface errors back to the model
            return f"ERROR while running tool '{self.name}': {exc}"


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self.get(name)
        if tool is None:
            return f"ERROR: unknown tool '{name}'."
        return tool.run(**(arguments or {}))

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def anthropic_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def ollama_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in self._tools.values()
        ]


# Global registry every tool module registers into.
REGISTRY = ToolRegistry()


def tool(name: str, description: str, input_schema: dict[str, Any]):
    """Decorator that turns a plain function into a registered JARVIS tool."""

    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        REGISTRY.register(
            Tool(
                name=name,
                description=description,
                input_schema=input_schema,
                func=func,
            )
        )
        return func

    return decorator


def load_builtin_tools() -> ToolRegistry:
    """Import the built-in tool modules so they register themselves."""
    from . import filesystem, jobs, schedule, shell, system  # noqa: F401

    return REGISTRY
