"""Trevor — the tasks, schedule, and accountability agent.

Trevor owns the user's to-do list and calendar. He triages new tasks, reminds
the user what's due, and is the only agent who completes tasks on the user's
behalf. He can also run a daily "check-in" — see Trevor.daily_checkin().
"""

from __future__ import annotations

from typing import Any

from agents.base import BaseAgent, tool_result_text
from agents.state import Store

SYSTEM_PROMPT = """You are Trevor, the operations and accountability partner on a small e-commerce team.

# Who you work with
- The user runs an Etsy store + AI dropshipping side. You keep their day organized so they can focus on the work that grows the business.
- Rico (research) hands you tasks based on product opportunities he finds. Don't second-guess his picks — just queue them.
- Coco (creative) hands you tasks like "review this video draft by Friday."

# Your job
1. Manage the user's task list and schedule. Use your tools — don't just talk about doing it.
2. When the user says "I did X" or "X is done", call `complete_task` with the matching id.
3. When you check in (daily or on demand), surface:
   - What's overdue
   - What's due today
   - The 1–3 most leverage-y next moves (high-value tasks first; busywork last)
   - Anything Rico or Coco handed off that the user hasn't acted on
4. Keep the user accountable. If they keep snoozing the same task, call it out kindly but directly.
5. If a task isn't really a Trevor thing — it's a research question or a creative ask — say so and suggest the right agent.

# Style
- Crisp. No life-coach voice. The user wants a competent COO, not a wellness app.
- Use short bullet lists. The user is busy.
- When you complete tasks, acknowledge briefly and move on. No celebratory paragraphs.
- Numbers and dates explicit. "Due Friday" beats "soon"."""


class Trevor(BaseAgent):
    name = "Trevor"
    persona = "Operations, scheduling, and accountability partner"
    system_prompt = SYSTEM_PROMPT

    def __init__(self, store: Store, **kwargs):
        super().__init__(**kwargs)
        self.store = store
        self.tools = [
            {
                "name": "list_tasks",
                "description": "List tasks. Filter by status if you only want pending/done.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "done", "all"],
                            "default": "pending",
                        }
                    },
                },
            },
            {
                "name": "add_task",
                "description": "Add a task to the user's list.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "due": {"type": "string", "description": "Free-form date, e.g. 'Friday' or '2026-05-10'."},
                        "notes": {"type": "string"},
                    },
                    "required": ["title"],
                },
            },
            {
                "name": "complete_task",
                "description": "Mark a task done. Use when the user says they finished one.",
                "input_schema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                },
            },
            {
                "name": "add_event",
                "description": "Add a calendar event / appointment.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "when": {"type": "string", "description": "Free-form datetime, e.g. 'Tomorrow 3pm'."},
                        "notes": {"type": "string"},
                    },
                    "required": ["title", "when"],
                },
            },
            {
                "name": "list_schedule",
                "description": "List upcoming events the user has on the calendar.",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]

    def execute_tool(self, name: str, tool_input: dict[str, Any]) -> str:
        if name == "list_tasks":
            status = tool_input.get("status", "pending")
            tasks = self.store.list_tasks(status=None if status == "all" else status)
            return tool_result_text(tasks)

        if name == "add_task":
            t = self.store.add_task(
                title=tool_input["title"],
                owner="user",
                due=tool_input.get("due"),
                notes=tool_input.get("notes"),
            )
            return tool_result_text(t)

        if name == "complete_task":
            t = self.store.complete_task(tool_input["task_id"])
            return tool_result_text(t or {"error": "task not found"})

        if name == "add_event":
            e = self.store.add_event(
                title=tool_input["title"],
                when=tool_input["when"],
                notes=tool_input.get("notes"),
            )
            return tool_result_text(e)

        if name == "list_schedule":
            return tool_result_text(self.store.list_schedule())

        return tool_result_text({"error": f"unknown tool {name}"})

    def daily_checkin(self, history: list[dict[str, Any]] | None = None) -> tuple[str, list[dict[str, Any]]]:
        """Trigger a self-directed check-in. Call 3-5 times a day from the CLI."""
        prompt = (
            "Run a check-in. Look at my task list and schedule, surface anything "
            "overdue or due today, flag any pending handoffs from Rico or Coco I "
            "haven't acted on, and recommend the 1–3 highest-leverage next moves. "
            "Keep it under 200 words."
        )
        return self.chat(prompt, history=history)
