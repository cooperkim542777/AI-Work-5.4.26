"""Base agent — handles the Claude API loop, tool dispatch, and prompt caching.

Each concrete agent (Rico, Trevor, Coco) subclasses this and provides:
  - a name + system prompt
  - a list of tools (both custom client-side and Anthropic server-side)
  - an `execute_tool(name, input)` implementation for the custom tools

The system prompt + tool list form the stable cache prefix; the conversation
history is appended after the breakpoint, so repeat turns reuse the cache.
"""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic

MODEL = "claude-opus-4-7"
MAX_TOKENS = 8000
MAX_LOOP_ITERATIONS = 8


class BaseAgent:
    name: str = "base"
    persona: str = ""
    system_prompt: str = ""
    tools: list[dict[str, Any]] = []

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self.client = client or anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )

    def execute_tool(self, name: str, tool_input: dict[str, Any]) -> str:
        """Run a custom (client-side) tool. Subclasses implement.

        Server-side tools (web_search, etc.) are handled by Anthropic and never
        reach this method.
        """
        return f"Tool '{name}' is not implemented for {self.name}."

    def _system_blocks(self, extra_context: str | None = None) -> list[dict[str, Any]]:
        """System prompt as a cacheable block list. Stable content first, volatile last."""
        blocks: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": self.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        if extra_context:
            blocks.append({"type": "text", "text": extra_context})
        return blocks

    def chat(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
        extra_context: str | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Send one user message and run the tool-use loop until Claude finishes.

        Returns (final_text, updated_history).
        """
        messages: list[dict[str, Any]] = list(history or [])
        messages.append({"role": "user", "content": user_message})

        for _ in range(MAX_LOOP_ITERATIONS):
            kwargs: dict[str, Any] = {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "thinking": {"type": "adaptive"},
                "system": self._system_blocks(extra_context),
                "messages": messages,
            }
            if self.tools:
                kwargs["tools"] = self.tools
            response = self.client.messages.create(**kwargs)

            if response.stop_reason == "end_turn":
                messages.append({"role": "assistant", "content": response.content})
                final_text = "\n".join(
                    block.text for block in response.content if block.type == "text"
                )
                return final_text, messages

            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": response.content})
                continue

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        try:
                            result = self.execute_tool(block.name, block.input)
                        except Exception as e:
                            result = f"Tool error: {e}"
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result,
                                    "is_error": True,
                                }
                            )
                            continue
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )
                messages.append({"role": "user", "content": tool_results})
                continue

            messages.append({"role": "assistant", "content": response.content})
            final_text = "\n".join(
                block.text for block in response.content if block.type == "text"
            )
            return final_text or f"[stopped: {response.stop_reason}]", messages

        return "[hit tool-use loop limit]", messages


def tool_result_text(value: Any) -> str:
    """Serialize a Python value as a tool_result content string."""
    if isinstance(value, str):
        return value
    return json.dumps(value, indent=2, default=str)
