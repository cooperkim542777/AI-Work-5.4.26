"""Rico — the research and trends agent.

Rico scouts trending products, analyzes competitor moves, and surfaces
opportunities for the Etsy store and AI dropshipping. He uses Claude's
server-side web_search and web_fetch tools, plus local custom tools to file
findings into the shared store and hand off action items to Trevor or Coco.
"""

from __future__ import annotations

from typing import Any

from agents.base import BaseAgent, tool_result_text
from agents.state import Store

SYSTEM_PROMPT = """You are Rico, a sharp, no-fluff product research and market analyst on a small e-commerce team.

# Who you work with
- The user runs an Etsy store and is building out an AI-assisted dropshipping operation. Their goal is passive income from winning products.
- Trevor handles the user's tasks, calendar, and accountability. When you find something the user needs to act on, hand off a task to Trevor — don't just leave it in chat.
- Coco handles creative — short-form AI video scripts (Gemini), Meta and TikTok ad concepts. When a product looks promising and needs creative, hand off a brief to Coco.

# How you work
1. Use `web_search` and `web_fetch` aggressively. Real recent data beats general knowledge every time for trends.
2. For every product or trend you surface, give the user:
   - What it is and who's buying it
   - Why it's trending now (driver: TikTok, season, news, etc.)
   - Estimated demand signal (search interest, social mentions, marketplace listings)
   - Margin / sourcing notes (rough cost, supplier difficulty, Etsy vs dropship fit)
   - A concrete next step for the user
3. File the result with `add_research_note` so it persists. Don't make the user remember anything you found.
4. If the user should DO something — order a sample, list a variant, kill a SKU — call `handoff_to_trevor` to drop a task on their list.
5. If a product is worth promoting — call `handoff_to_coco` with a creative brief (target audience, hook angle, format).

# Style
- Direct. Skip preamble like "Great question!". Lead with the finding.
- Number your picks 1, 2, 3. Easy to scan.
- Honest about uncertainty. If a trend is fading or saturated, say so.
- No hype. The user pays your bills; they need truth, not affiliate-speak."""


class Rico(BaseAgent):
    name = "Rico"
    persona = "Product research & trends analyst"
    system_prompt = SYSTEM_PROMPT

    def __init__(self, store: Store, **kwargs):
        super().__init__(**kwargs)
        self.store = store
        self.tools = [
            {"type": "web_search_20260209", "name": "web_search", "max_uses": 8},
            {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 5},
            {
                "name": "add_research_note",
                "description": (
                    "File a research finding into the shared store so it persists "
                    "across sessions and is visible to the user and other agents. "
                    "Call this for every substantive product/trend you surface."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short title, e.g. 'LED neon-sign demand spike'."},
                        "summary": {"type": "string", "description": "2-5 sentence summary of the finding."},
                        "product_ideas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Concrete product/SKU ideas the user could list.",
                        },
                        "sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URLs you used to back up the finding.",
                        },
                    },
                    "required": ["title", "summary"],
                },
            },
            {
                "name": "handoff_to_trevor",
                "description": (
                    "Hand off an action item to Trevor (tasks/scheduling agent). "
                    "Use this when the user needs to DO something based on your research."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Imperative-form task, e.g. 'Order sample of X from Alibaba'."},
                        "due": {"type": "string", "description": "Optional due date or 'today'/'this week'."},
                        "context": {"type": "string", "description": "Why this matters — Trevor will pass it along."},
                    },
                    "required": ["task"],
                },
            },
            {
                "name": "handoff_to_coco",
                "description": (
                    "Hand off a creative brief to Coco (content/ads agent). Use when "
                    "a product is worth promoting and needs ad creative or short-form video."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product": {"type": "string"},
                        "audience": {"type": "string", "description": "Who buys this — be specific."},
                        "hook_angle": {"type": "string", "description": "The emotional/positioning angle."},
                        "format": {
                            "type": "string",
                            "enum": ["short_form_video", "static_ad", "carousel", "ugc_script"],
                        },
                        "platform": {
                            "type": "string",
                            "enum": ["tiktok", "meta", "instagram", "youtube_shorts"],
                        },
                    },
                    "required": ["product", "audience", "hook_angle", "format", "platform"],
                },
            },
        ]

    def execute_tool(self, name: str, tool_input: dict[str, Any]) -> str:
        if name == "add_research_note":
            note = self.store.add_research_note(
                title=tool_input["title"],
                summary=tool_input["summary"],
                product_ideas=tool_input.get("product_ideas"),
                sources=tool_input.get("sources"),
            )
            return tool_result_text({"filed": note["id"], "title": note["title"]})

        if name == "handoff_to_trevor":
            task = self.store.add_task(
                title=tool_input["task"],
                owner="user",
                due=tool_input.get("due"),
                notes=tool_input.get("context"),
            )
            self.store.log_handoff("Rico", "Trevor", tool_input["task"])
            return tool_result_text(
                {"handed_to": "Trevor", "task_id": task["id"], "title": task["title"]}
            )

        if name == "handoff_to_coco":
            brief_text = (
                f"Product: {tool_input['product']}\n"
                f"Audience: {tool_input['audience']}\n"
                f"Hook angle: {tool_input['hook_angle']}\n"
            )
            brief = self.store.add_creative_brief(
                title=f"Brief: {tool_input['product']}",
                format=tool_input["format"],
                platform=tool_input["platform"],
                brief=brief_text,
            )
            self.store.log_handoff("Rico", "Coco", tool_input["product"])
            return tool_result_text(
                {"handed_to": "Coco", "brief_id": brief["id"]}
            )

        return tool_result_text({"error": f"unknown tool {name}"})
