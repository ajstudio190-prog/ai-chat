#!/usr/bin/env python3
"""
ai-chat: AGY-Grade Sovereign Terminal AI Agent.
Autonomous Multi-Model Chat Shell with ReAct Observation Loop.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.agent_engine import AGENT_ENGINE
from core.grounding import get_grounded_system_prompt
from core.telemetry import get_system_vitals, get_battery_info, get_wifi_info
from core.evolution_memory import EVOLUTION_MEMORY

def print_banner():
    v = get_system_vitals()
    st = AGENT_ENGINE.get_model_status()
    act = AGENT_ENGINE.active_model
    act_name = st[act]["name"]

    print("\n⚡ AI-CHAT (AGY-Grade Autonomous Agent Shell)")
    print("─────────────────────────────────────────────────────────────")
    print(f"🍎 SYSTEM   : {v['free_disk_gb']} GB free | {v['free_ram_gb']} GB RAM avail | macOS M4 Metal")
    print(f"🧠 MODEL    : [{act.upper()}] {act_name}")
    print(f"🛠️  MODELS   : /model (llama3.2 • qwen • agy • claude • codex • auto)")
    print("─────────────────────────────────────────────────────────────")
    print("💬 Ask anything, write code, run terminal commands, or control your Mac.")
    print("─────────────────────────────────────────────────────────────\n")

def print_help():
    print("""
⚡ AI-CHAT Commands:
  /model                  ➔ View model status and readiness
  /model <name>           ➔ Switch model (llama3.2, qwen, agy, claude, codex, auto)
  /vitals                 ➔ Live system battery, RAM, and hardware vitals
  /memory                 ➔ View evolutionary lessons and self-learned patterns
  /clear                  ➔ Reset active conversation context
  /help                   ➔ Show this command guide
  /exit or /quit          ➔ Exit session
    """)

def run_chat_session():
    print_banner()
    grounded_sys = get_grounded_system_prompt()
    messages = [{"role": "system", "content": grounded_sys}]

    user_name = os.environ.get("USER", "user")

    while True:
        try:
            act_model = AGENT_ENGINE.active_model
            prompt = input(f"ai-chat({act_model} • {user_name}) ❯ ").strip()

            if not prompt:
                continue

            # Command shortcuts
            if prompt.lower() in ("/exit", "/quit", "exit", "quit", ":q"):
                print("\nGoodbye!\n")
                break

            if prompt.lower() in ("/help", "help"):
                print_help()
                continue

            if prompt.lower() in ("/clear", "clear"):
                messages = [{"role": "system", "content": grounded_sys}]
                print("\n🧹 Conversation memory cleared.\n")
                continue

            if prompt.lower() in ("/vitals", "vitals"):
                v = get_system_vitals()
                print(f"\n🍎 System Vitals: {v['battery']} | {v['wifi']} | Storage: {v['free_disk_gb']}GB free | RAM: {v['free_ram_gb']}GB avail\n")
                continue

            if prompt.lower() in ("/memory", "memory"):
                print(f"\n{EVOLUTION_MEMORY.get_evolution_context()}\n")
                continue

            if prompt.lower().startswith("/model"):
                parts = prompt.split()
                if len(parts) == 1:
                    print("\n🧠 Available Multi-Model Roster:")
                    st = AGENT_ENGINE.get_model_status()
                    for k, v in st.items():
                        active_mark = "👉 ACTIVE" if v["active"] else "         "
                        ready_icon = "🟢 Ready" if v["ready"] else "🔴 Offline"
                        print(f"  {active_mark} [{k}] {v['name']} ({ready_icon})")
                        print(f"              {v['desc']}")
                    print("\n💡 Switch anytime using: /model <name> (e.g. /model qwen or /model agy)\n")
                else:
                    target = parts[1]
                    ok, msg = AGENT_ENGINE.set_model(target)
                    icon = "✅" if ok else "❌"
                    print(f"\n{icon} {msg}\n")
                continue

            # Execute AGY-grade Agentic ReAct Turn
            print("\nai ❯ ", end="", flush=True)

            def print_chunk(c: str):
                sys.stdout.write(c)
                sys.stdout.flush()

            reply, messages = AGENT_ENGINE.run_agentic_turn(
                user_prompt=prompt,
                messages=messages,
                max_steps=5,
                stream_callback=print_chunk
            )
            print("\n")

        except (KeyboardInterrupt, EOFError):
            print("\n\nSession ended.")
            break

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in ("--help", "-h", "help"):
            print_help()
            return
        elif cmd in ("--model", "-m"):
            if len(sys.argv) > 2:
                AGENT_ENGINE.set_model(sys.argv[2])
                run_chat_session()
                return

    run_chat_session()

if __name__ == "__main__":
    main()
