"""Coco — the creative and content agent.

Coco generates ad concepts, short-form video scripts (designed for Gemini /
Veo / Sora-style generators), Meta and TikTok ad copy, and visual hooks. She
files briefs to the shared store and can hand follow-up tasks to Trevor.
"""

from __future__ import annotations

from typing import Any

from agents.base import BaseAgent, tool_result_text
from agents.state import Store

SYSTEM_PROMPT = """You are Coco, the creative director on a small e-commerce team.

# Who you work with
- The user runs an Etsy store + an AI-dropshipping side project. They need creative that converts on TikTok, Meta (Facebook/Instagram), and YouTube Shorts.
- Rico (research) sends you product briefs when something looks promising. Treat his briefs as your creative inputs.
- Trevor (tasks) tracks what the user needs to do. If you generate a script that needs the user to film/edit/launch, hand a task to Trevor.

# Your job
1. Generate creative people stop the scroll for. Specialties:
   - Short-form AI video scripts (formatted so the user can paste straight into Gemini/Veo/Sora). Include: shot list, on-screen text, voiceover, suggested music vibe, CTA.
   - Static + carousel ad concepts (visuals + headline + body + CTA).
   - UGC-style scripts (talking-head format, 15-30s, problem→agitation→solution→CTA).
2. ALWAYS produce 3 distinct directions when generating ads/scripts. Don't anchor on the first idea.
3. For each direction, name the angle (e.g. "transformation reveal", "deadpan demo", "POV problem"). Then give the structure.
4. File anything substantial via `add_creative_brief` so it persists.
5. If the work needs the user to act — film a piece, run an ad, A/B test creatives — hand it to Trevor.
6. Be opinionated about what'll work. You're not a yes-machine.

# Style rules for the creative itself
- Hooks land in the first 1.5 seconds. No "Hey guys" intros.
- Every script names a specific viewer ("if you're a small Etsy seller…") not "everyone".
- CTAs are specific: "tap the link, grab one before they restock" — not "click here for more info".
- No generic copy. If a line could be in any ad for any product, rewrite it.

# Style for talking to the user
- Concise. Show, don't explain. Lead with the creative; meta-commentary at the end if needed."""


class Coco(BaseAgent):
    name = "Coco"
    persona = "Creative director — content, scripts, and ads"
    system_prompt = SYSTEM_PROMPT

    def __init__(self, store: Store, **kwargs):
        super().__init__(**kwargs)
        self.store = store
        self.tools = [
            {
                "name": "add_creative_brief",
                "description": (
                    "File a creative brief or generated piece into the shared store. "
                    "Use for finished scripts, ad concepts, and longer creative outputs."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "format": {
                            "type": "string",
                            "enum": [
                                "short_form_video",
                                "static_ad",
                                "carousel",
                                "ugc_script",
                                "email",
                                "landing_copy",
                            ],
                        },
                        "platform": {
                            "type": "string",
                            "enum": [
                                "tiktok",
                                "meta",
                                "instagram",
                                "youtube_shorts",
                                "etsy",
                                "email",
                            ],
                        },
                        "brief": {"type": "string", "description": "The full creative content."},
                    },
                    "required": ["title", "format", "platform", "brief"],
                },
            },
            {
                "name": "list_pending_briefs",
                "description": "List creative briefs Rico (or you) have filed.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "handoff_to_trevor",
                "description": (
                    "Hand off an action item to Trevor. Use for things the user needs to "
                    "do with your output: film it, launch the ad, edit a draft, etc."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "due": {"type": "string"},
                        "context": {"type": "string"},
                    },
                    "required": ["task"],
                },
            },
        ]

    def execute_tool(self, name: str, tool_input: dict[str, Any]) -> str:
        if name == "add_creative_brief":
            b = self.store.add_creative_brief(
                title=tool_input["title"],
                format=tool_input["format"],
                platform=tool_input["platform"],
                brief=tool_input["brief"],
            )
            return tool_result_text({"filed": b["id"], "title": b["title"]})

        if name == "list_pending_briefs":
            return tool_result_text(self.store.list_creative_briefs())

        if name == "handoff_to_trevor":
            t = self.store.add_task(
                title=tool_input["task"],
                owner="user",
                due=tool_input.get("due"),
                notes=tool_input.get("context"),
            )
            self.store.log_handoff("Coco", "Trevor", tool_input["task"])
            return tool_result_text(
                {"handed_to": "Trevor", "task_id": t["id"], "title": t["title"]}
            )

        return tool_result_text({"error": f"unknown tool {name}"})
