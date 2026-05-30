"""The scheduler that lets JARVIS do things 'on time'.

Wraps APScheduler. Two kinds of scheduled task are supported:

* ``reminder``    - JARVIS just messages you the text when it fires.
* ``instruction`` - JARVIS actually runs the instruction (through the brain)
                    and messages you the result. e.g. "apply to 5 new jobs".

Schedules can be:
* ``once``     - run one time ({"type": "once", "run_at": "<iso datetime>"})
* ``cron``     - recurring at a time of day
                 ({"type": "cron", "hour": 9, "minute": 0, "day_of_week": "*"})
* ``interval`` - every N minutes ({"type": "interval", "minutes": 30})

Task definitions are persisted via ``TaskStore`` so they survive restarts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .notify import Notifier
from .store import TaskStore


class JarvisScheduler:
    def __init__(
        self,
        store: TaskStore,
        notifier: Notifier,
        run_instruction: Callable[[str], str],
    ):
        self.store = store
        self.notifier = notifier
        self.run_instruction = run_instruction
        self._sched = BackgroundScheduler()
        self._started = False

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        if self._started:
            return
        for task in self.store.all():
            if task.get("enabled", True):
                try:
                    self._add_job(task)
                except Exception as exc:  # noqa: BLE001
                    print(f"[scheduler] could not load task {task.get('id')}: {exc}")
        self._sched.start()
        self._started = True

    def shutdown(self) -> None:
        if self._started:
            self._sched.shutdown(wait=False)
            self._started = False

    # -- public API used by tools -----------------------------------------
    def add_task(self, task: dict[str, Any]) -> None:
        self.store.add(task)
        if not self._started:
            self.start()
        self._add_job(task)

    def remove_task(self, task_id: str) -> None:
        try:
            self._sched.remove_job(task_id)
        except Exception:  # noqa: BLE001
            pass
        self.store.remove(task_id)

    def list_tasks(self) -> list[dict[str, Any]]:
        return self.store.all()

    # -- internals ---------------------------------------------------------
    def _build_trigger(self, schedule: dict[str, Any]):
        kind = schedule.get("type")
        if kind == "once":
            return DateTrigger(run_date=datetime.fromisoformat(schedule["run_at"]))
        if kind == "cron":
            return CronTrigger(
                hour=schedule.get("hour", 0),
                minute=schedule.get("minute", 0),
                day_of_week=schedule.get("day_of_week", "*"),
            )
        if kind == "interval":
            return IntervalTrigger(minutes=schedule.get("minutes", 60))
        raise ValueError(f"unknown schedule type: {kind}")

    def _add_job(self, task: dict[str, Any]) -> None:
        trigger = self._build_trigger(task["schedule"])
        self._sched.add_job(
            self._fire,
            trigger=trigger,
            args=[task["id"]],
            id=task["id"],
            replace_existing=True,
        )

    def _fire(self, task_id: str) -> None:
        task = self.store.get(task_id)
        if not task:
            return
        try:
            if task.get("kind") == "instruction":
                result = self.run_instruction(task["text"])
                self.notifier.send(f"✅ Done — '{task['text']}':\n{result}")
            else:
                self.notifier.send(f"⏰ Reminder: {task['text']}")
        except Exception as exc:  # noqa: BLE001
            self.notifier.send(f"⚠️ Task '{task.get('text')}' failed: {exc}")
        finally:
            # one-off tasks are removed after they fire
            if task.get("schedule", {}).get("type") == "once":
                self.store.remove(task_id)
