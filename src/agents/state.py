"""Shared, JSON-backed state for the three-agent crew.

All agents read and write to the same store so they can coordinate: Rico drops
research notes, Trevor manages tasks and the schedule, Coco files creative
briefs, and any agent can hand work off to another by adding a task.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DIR = Path(__file__).resolve().parents[2] / "data"
STATE_FILE = STATE_DIR / "state.json"

EMPTY_STATE: dict[str, Any] = {
    "tasks": [],
    "schedule": [],
    "research_notes": [],
    "creative_briefs": [],
    "handoff_log": [],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class Store:
    """Tiny JSON-backed store. Single-process, no locking — fine for one user."""

    def __init__(self, path: Path = STATE_FILE) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(EMPTY_STATE)

    def _read(self) -> dict[str, Any]:
        with self.path.open() as f:
            data = json.load(f)
        for key, default in EMPTY_STATE.items():
            data.setdefault(key, default if not isinstance(default, list) else [])
        return data

    def _write(self, data: dict[str, Any]) -> None:
        with self.path.open("w") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    # ---- Tasks --------------------------------------------------------------

    def add_task(
        self,
        title: str,
        owner: str = "user",
        due: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        data = self._read()
        task = {
            "id": _new_id("task"),
            "title": title,
            "owner": owner,
            "status": "pending",
            "due": due,
            "notes": notes,
            "created_at": _now(),
            "completed_at": None,
        }
        data["tasks"].append(task)
        self._write(data)
        return task

    def list_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        tasks = self._read()["tasks"]
        if status:
            return [t for t in tasks if t["status"] == status]
        return tasks

    def complete_task(self, task_id: str) -> dict[str, Any] | None:
        data = self._read()
        for t in data["tasks"]:
            if t["id"] == task_id:
                t["status"] = "done"
                t["completed_at"] = _now()
                self._write(data)
                return t
        return None

    # ---- Schedule -----------------------------------------------------------

    def add_event(self, title: str, when: str, notes: str | None = None) -> dict[str, Any]:
        data = self._read()
        event = {
            "id": _new_id("evt"),
            "title": title,
            "when": when,
            "notes": notes,
            "created_at": _now(),
        }
        data["schedule"].append(event)
        self._write(data)
        return event

    def list_schedule(self) -> list[dict[str, Any]]:
        return self._read()["schedule"]

    # ---- Research notes (Rico) ---------------------------------------------

    def add_research_note(
        self,
        title: str,
        summary: str,
        product_ideas: list[str] | None = None,
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
        data = self._read()
        note = {
            "id": _new_id("note"),
            "title": title,
            "summary": summary,
            "product_ideas": product_ideas or [],
            "sources": sources or [],
            "created_at": _now(),
        }
        data["research_notes"].append(note)
        self._write(data)
        return note

    def list_research_notes(self) -> list[dict[str, Any]]:
        return self._read()["research_notes"]

    # ---- Creative briefs (Coco) --------------------------------------------

    def add_creative_brief(
        self,
        title: str,
        format: str,
        platform: str,
        brief: str,
    ) -> dict[str, Any]:
        data = self._read()
        item = {
            "id": _new_id("brief"),
            "title": title,
            "format": format,
            "platform": platform,
            "brief": brief,
            "created_at": _now(),
        }
        data["creative_briefs"].append(item)
        self._write(data)
        return item

    def list_creative_briefs(self) -> list[dict[str, Any]]:
        return self._read()["creative_briefs"]

    # ---- Handoffs -----------------------------------------------------------

    def log_handoff(self, from_agent: str, to_agent: str, message: str) -> dict[str, Any]:
        data = self._read()
        entry = {
            "id": _new_id("ho"),
            "from": from_agent,
            "to": to_agent,
            "message": message,
            "created_at": _now(),
        }
        data["handoff_log"].append(entry)
        self._write(data)
        return entry

    def pending_handoffs(self, to_agent: str) -> list[dict[str, Any]]:
        return [h for h in self._read()["handoff_log"] if h["to"] == to_agent]

    # ---- Snapshot -----------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Compact summary an agent can read at the start of a turn."""
        data = self._read()
        return {
            "open_tasks": [
                {"id": t["id"], "title": t["title"], "owner": t["owner"], "due": t["due"]}
                for t in data["tasks"]
                if t["status"] == "pending"
            ],
            "upcoming_events": data["schedule"][-10:],
            "recent_research": [
                {"title": n["title"], "summary": n["summary"][:200]}
                for n in data["research_notes"][-5:]
            ],
            "recent_creative": [
                {"title": b["title"], "format": b["format"], "platform": b["platform"]}
                for b in data["creative_briefs"][-5:]
            ],
        }
