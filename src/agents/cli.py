"""Interactive CLI for the three-agent crew.

Usage:
    crew                  # menu mode
    crew rico "your msg"  # one-shot to a specific agent
    crew checkin          # run Trevor's daily check-in
    crew status           # print the shared state snapshot
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running as `python src/agents/cli.py` without install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.orchestrator import Orchestrator  # noqa: E402

BANNER = """
================================================================
  AI Work Crew — Rico · Trevor · Coco
================================================================
  rico    — product research & trending finds
  trevor  — tasks, schedule, accountability
  coco    — creative, scripts, ads

  Commands inside chat:
    /switch <agent>   change who you're talking to
    /checkin          run Trevor's check-in
    /status           print the shared state snapshot
    /reset            clear current agent's chat history
    /quit             exit
================================================================
"""


def _print_status(orch: Orchestrator) -> None:
    print(json.dumps(orch.store.snapshot(), indent=2, default=str))


def _interactive(orch: Orchestrator) -> None:
    print(BANNER)
    current = "trevor"
    while True:
        try:
            user = input(f"\n[{current}] you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not user:
            continue

        if user.startswith("/switch "):
            target = user.split(maxsplit=1)[1].strip().lower()
            if target in orch.agents:
                current = target
                print(f"-- switched to {current} --")
            else:
                print("agents: rico, trevor, coco")
            continue

        if user == "/checkin":
            print("\n[trevor] " + orch.trevor_checkin())
            continue

        if user == "/status":
            _print_status(orch)
            continue

        if user == "/reset":
            orch.reset(current)
            print(f"-- {current}'s history cleared --")
            continue

        if user in ("/quit", "/exit", "exit", "quit"):
            return

        if user.lower() in orch.agents:
            current = user.lower()
            print(f"-- switched to {current} --")
            continue

        reply = orch.talk(current, user)
        print(f"\n[{current}] {reply}")


def main() -> None:
    load_dotenv()
    orch = Orchestrator()

    if len(sys.argv) == 1:
        _interactive(orch)
        return

    cmd = sys.argv[1].lower()

    if cmd in orch.agents:
        message = " ".join(sys.argv[2:]).strip()
        if not message:
            print(f"Usage: crew {cmd} \"your message\"")
            sys.exit(1)
        print(orch.talk(cmd, message))
        return

    if cmd == "checkin":
        print(orch.trevor_checkin())
        return

    if cmd == "status":
        _print_status(orch)
        return

    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    main()
