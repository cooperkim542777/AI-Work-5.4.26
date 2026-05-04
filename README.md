# AI Work Crew — Rico · Trevor · Coco

Three Claude-powered agents that help run a small e-commerce business
(Etsy + AI dropshipping). They share state, hand work off to each other,
and keep your day organized.

| Agent      | Role                                                  | Tools                                                   |
| ---------- | ----------------------------------------------------- | ------------------------------------------------------- |
| **Rico**   | Product research & trending product analysis          | Web search, web fetch, files notes, hands off tasks     |
| **Trevor** | Tasks, schedule, accountability & daily check-ins     | Task list, calendar, completion tracking                |
| **Coco**   | Creative — short-form video scripts, ads, copy        | Files briefs, hands creative production tasks to Trevor |

Everything they do is persisted to `data/state.json` so nothing is lost
between sessions. Each agent gets a snapshot of the shared state at the
start of every turn, so they all know what the others are working on.

## Setup

You'll need Python 3.10+ and an Anthropic API key.

```bash
# 1. Get your API key from https://console.anthropic.com/settings/keys
cp .env.example .env
# Open .env and paste your key.

# 2. Install
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e .
```

## Usage

### Interactive mode

```bash
crew
```

Brings up a menu where you chat with whichever agent you pick. Inside
the chat:

- `/switch rico`  — switch to Rico
- `/switch trevor` — switch to Trevor
- `/switch coco` — switch to Coco
- `/checkin` — run Trevor's check-in (he'll review your tasks, schedule, and pending handoffs)
- `/status` — print the full shared state snapshot
- `/reset` — clear the current agent's chat history (state is kept)
- `/quit` — exit

### One-shot

```bash
crew rico "what's trending on Etsy right now in home decor under $30?"
crew trevor "I just finished ordering the LED neon samples"
crew coco "give me 3 TikTok hooks for the LED neon sign launch"
crew checkin   # Trevor's check-in (run this 3-5 times a day)
crew status    # see what's in the shared store
```

## How the handoffs work

Each agent has explicit handoff tools. Real example flow:

1. You ask **Rico** what's hot on Etsy right now. He web-searches, files
   research notes, and decides one trend is worth acting on.
2. Rico calls `handoff_to_trevor` with a task ("Order samples from supplier X")
   and `handoff_to_coco` with a creative brief.
3. Next time you talk to **Trevor**, he sees the new task. When you say
   "I ordered the samples," he marks it done.
4. Next time you talk to **Coco**, she sees Rico's brief and produces three
   TikTok script directions. If filming is needed, she hands a task back to Trevor.

### Daily rhythm

Run `crew checkin` 3–5 times a day (morning, midday, end-of-day at minimum).
Trevor will surface what's overdue, what's due today, and any pending
handoffs from Rico or Coco that you haven't acted on.

## Project layout

```
.
├── src/agents/
│   ├── base.py           # shared Claude API loop with prompt caching
│   ├── state.py          # JSON-backed shared store
│   ├── rico.py           # research agent (web search + handoffs)
│   ├── trevor.py         # tasks/schedule agent
│   ├── coco.py           # creative agent
│   ├── orchestrator.py   # wires it together
│   └── cli.py            # interactive CLI
├── data/state.json       # auto-created on first run
├── pyproject.toml
└── .env                  # your API key (gitignored)
```

## Tech notes

- All three agents run on Claude Opus 4.7 (`claude-opus-4-7`).
- Adaptive thinking is on by default — Claude decides when to think harder.
- System prompts are prompt-cached, so repeat turns are ~90% cheaper for the
  cached prefix.
- Rico uses the server-side `web_search_20260209` and `web_fetch_20260209`
  tools — no scraping setup needed.
- Trevor and Coco use custom Python tools that read/write `data/state.json`.

## Cost expectations

Conversational use is cheap. Rough order-of-magnitude:

- Trevor check-in: a few cents
- Rico research session with web search: $0.10–$0.50 depending on depth
- Coco generating 3 ad scripts: a few cents

You can always check usage at <https://console.anthropic.com/settings/usage>.

## Extending

The simplest way to add a fourth agent (say, a customer-service agent) is to:

1. Copy `src/agents/coco.py` to `src/agents/<new>.py`
2. Replace `SYSTEM_PROMPT`, `name`, and the `tools` list
3. Implement `execute_tool` for the new tools
4. Register the agent in `orchestrator.py`
5. The CLI picks it up automatically

To plug in real integrations (Google Calendar, Gmail, Etsy API, etc.),
add tool definitions and back them with the relevant SDK calls inside
each agent's `execute_tool` method.
