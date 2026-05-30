"""Tools that let JARVIS schedule reminders and recurring tasks for itself."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from . import tool
from ..runtime import RUNTIME


def _scheduler():
    if RUNTIME.scheduler is None:
        raise RuntimeError("The scheduler isn't running right now.")
    return RUNTIME.scheduler


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _next_occurrence(hhmm: str) -> datetime:
    """Turn 'HH:MM' into the next datetime that matches (today or tomorrow)."""
    hour, minute = (int(x) for x in hhmm.split(":"))
    now = datetime.now()
    run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run <= now:
        run += timedelta(days=1)
    return run


@tool(
    name="set_reminder",
    description=(
        "Set a one-time reminder. JARVIS will message the user when it fires. "
        "Provide EITHER in_minutes (relative) OR at_time as 'HH:MM' 24h "
        "(next occurrence today/tomorrow)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "What to remind about."},
            "in_minutes": {
                "type": "integer",
                "description": "Fire this many minutes from now.",
            },
            "at_time": {
                "type": "string",
                "description": "Clock time 'HH:MM' (24-hour) for the reminder.",
            },
        },
        "required": ["message"],
    },
)
def set_reminder(message: str, in_minutes: int | None = None,
                 at_time: str | None = None) -> str:
    sched = _scheduler()
    if in_minutes is not None:
        run_at = datetime.now() + timedelta(minutes=int(in_minutes))
    elif at_time:
        run_at = _next_occurrence(at_time)
    else:
        return "Tell me when: give in_minutes or at_time (HH:MM)."

    task = {
        "id": _new_id(),
        "kind": "reminder",
        "text": message,
        "schedule": {"type": "once", "run_at": run_at.isoformat()},
        "enabled": True,
    }
    sched.add_task(task)
    return f"Reminder set for {run_at.strftime('%a %Y-%m-%d %H:%M')} (id {task['id']})."


@tool(
    name="schedule_recurring_task",
    description=(
        "Schedule a recurring task at a time of day. Use kind='reminder' to "
        "just notify the user, or kind='instruction' to have JARVIS actually "
        "perform the text (e.g. 'apply to 5 new software jobs') and report "
        "back. day_of_week examples: '*' (daily), 'mon-fri', 'sat,sun'."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The reminder text or the instruction to run.",
            },
            "hour": {"type": "integer", "description": "Hour 0-23."},
            "minute": {"type": "integer", "description": "Minute 0-59 (default 0)."},
            "day_of_week": {
                "type": "string",
                "description": "Which days (default '*' = every day).",
            },
            "kind": {
                "type": "string",
                "enum": ["reminder", "instruction"],
                "description": "'reminder' notifies; 'instruction' runs the task.",
            },
        },
        "required": ["text", "hour"],
    },
)
def schedule_recurring_task(text: str, hour: int, minute: int = 0,
                            day_of_week: str = "*", kind: str = "reminder") -> str:
    sched = _scheduler()
    task = {
        "id": _new_id(),
        "kind": kind,
        "text": text,
        "schedule": {
            "type": "cron",
            "hour": int(hour),
            "minute": int(minute),
            "day_of_week": day_of_week,
        },
        "enabled": True,
    }
    sched.add_task(task)
    return (
        f"Scheduled {kind} '{text}' at {hour:02d}:{minute:02d} "
        f"on {day_of_week} (id {task['id']})."
    )


@tool(
    name="list_scheduled_tasks",
    description="List all reminders and recurring tasks JARVIS has scheduled.",
    input_schema={"type": "object", "properties": {}},
)
def list_scheduled_tasks() -> str:
    tasks = _scheduler().list_tasks()
    if not tasks:
        return "No scheduled tasks."
    lines = []
    for t in tasks:
        sch = t.get("schedule", {})
        when = sch.get("run_at") or (
            f"{sch.get('hour', 0):02d}:{sch.get('minute', 0):02d} "
            f"on {sch.get('day_of_week', '*')}"
            if sch.get("type") == "cron"
            else f"every {sch.get('minutes')} min"
        )
        lines.append(f"[{t['id']}] ({t.get('kind')}) {t.get('text')} — {when}")
    return "\n".join(lines)


@tool(
    name="cancel_scheduled_task",
    description="Cancel a scheduled reminder or task by its id.",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "The task id to cancel."},
        },
        "required": ["task_id"],
    },
)
def cancel_scheduled_task(task_id: str) -> str:
    _scheduler().remove_task(task_id)
    return f"Cancelled task {task_id}."
