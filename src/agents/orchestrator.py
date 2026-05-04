"""Orchestrator — wires Rico, Trevor, and Coco to the shared store.

Holds per-agent conversation history so each agent remembers context within a
session, and exposes a single `talk(agent_name, message)` entry point for the
CLI. Each agent gets a snapshot of the shared store appended after the cached
system prompt, so they always know about each other's recent work.
"""

from __future__ import annotations

import json
from typing import Any

from agents.coco import Coco
from agents.rico import Rico
from agents.state import Store
from agents.trevor import Trevor


class Orchestrator:
    def __init__(self, store: Store | None = None) -> None:
        self.store = store or Store()
        self.rico = Rico(store=self.store)
        self.trevor = Trevor(store=self.store)
        self.coco = Coco(store=self.store)
        self.agents = {"rico": self.rico, "trevor": self.trevor, "coco": self.coco}
        self.histories: dict[str, list[dict[str, Any]]] = {
            "rico": [],
            "trevor": [],
            "coco": [],
        }

    def _context_for(self, agent_name: str) -> str:
        snap = self.store.snapshot()
        pending = self.store.pending_handoffs(agent_name.capitalize())
        if pending:
            snap["handoffs_to_you"] = pending[-5:]
        return (
            "Current shared state (read-only snapshot — call your tools to make changes):\n"
            + json.dumps(snap, indent=2, default=str)
        )

    def talk(self, agent_name: str, message: str) -> str:
        agent_name = agent_name.lower()
        if agent_name not in self.agents:
            return f"Unknown agent: {agent_name}. Pick one of: rico, trevor, coco."
        agent = self.agents[agent_name]
        reply, history = agent.chat(
            message,
            history=self.histories[agent_name],
            extra_context=self._context_for(agent_name),
        )
        self.histories[agent_name] = history
        return reply

    def trevor_checkin(self) -> str:
        reply, history = self.trevor.daily_checkin(history=self.histories["trevor"])
        self.histories["trevor"] = history
        return reply

    def reset(self, agent_name: str | None = None) -> None:
        """Clear conversation history for one agent or all of them."""
        if agent_name is None:
            for k in self.histories:
                self.histories[k] = []
        elif agent_name.lower() in self.histories:
            self.histories[agent_name.lower()] = []
