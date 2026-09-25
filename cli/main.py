#!/usr/bin/env python3
"""
ai-chat: Sovereign Autonomous Terminal Agent.
Natural Language Only • Zero Slash Commands • Self-Driving ReAct Execution.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.agent_engine import AGENT_ENGINE
from core.grounding import get_grounded_system_prompt
from core.telemetry import get_system_vitals

def print_banner():
    v = get_system_vitals()
    print("\n⚡ AI-CHAT (Sovereign Autonomous Agent)")
    print("─────────────────────────────────────────────────────────────")
    print(f"🍎 SYSTEM : {v['free_disk_gb']} GB free | {v['free_ram_gb']} GB RAM avail | macOS M4 Metal")
    print("🤖 ENGINE : Autonomous Driving Active (Auto-Routing & ReAct Loop)")
    print("─────────────────────────────────────────────────────────────")
    print("💬 Talk or type naturally. Tell me what to do, ask questions, or hand me full missions.")
    print("─────────────────────────────────────────────────────────────\n")

def run_chat_session():
    print_banner()
    grounded_sys = get_grounded_system_prompt()
    messages = [{"role": "system", "content": grounded_sys}]

    while True:
        try:
            prompt = input("ai-chat ❯ ").strip()

            if not prompt:
                continue

            # Natural exit
            if prompt.lower() in ("exit", "quit", "goodbye", "bye", ":q"):
                print("\nGoodbye!\n")
                break

            # Natural reset
            if prompt.lower() in ("clear", "clear history", "reset", "clean"):
                messages = [{"role": "system", "content": grounded_sys}]
                print("\n🧹 Memory reset. Fresh session ready.\n")
                continue

            # Fully Autonomous Agentic Execution
            print("\nai ❯ ", end="", flush=True)

            def print_chunk(c: str):
                sys.stdout.write(c)
                sys.stdout.flush()

            reply, messages = AGENT_ENGINE.run_agentic_turn(
                user_prompt=prompt,
                messages=messages,
                max_steps=8,
                stream_callback=print_chunk
            )
            print("\n")

        except (KeyboardInterrupt, EOFError):
            print("\n\nSession ended.")
            break

def main():
    run_chat_session()

if __name__ == "__main__":
    main()
