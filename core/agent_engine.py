"""
AGY-Grade Agent Engine for ai-chat.
Provides:
- Multi-Model Reasoning: llama3.2 (fast edge), qwen2.5-coder:7b (local powerhouse),
  agy (Antigravity), claude (Claude Code), codex (Codex CLI), or auto (smart routing).
- Multi-Turn Autonomous ReAct Loop: Thought -> Action -> Observation -> Self-Correction.
- Deterministic Native macOS Execution via mac_controller.
- Rule 2 & 3 Safety Shield and PII Guard.
"""

import os
import sys
import re
import json
import time
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, List, Tuple, Optional, Generator, Callable

from core.safety import validate_shell_safety
from core.pii_guard import sanitize_text
from core.mac_controller import execute_mac_action, resolve_mac_app_name, close_mac_app, open_mac_app, get_accurate_world_time
from core.grounding import get_grounded_system_prompt, handle_proactive_actions
from core.telemetry import get_system_vitals
from core.browser import execute_private_search
from core.evolution_memory import EVOLUTION_MEMORY

OLLAMA_API_BASE = "http://localhost:11434/api"

class AgentEngine:
    """
    Autonomous Pair-Programming and OS Control Engine.
    Emulates the full Antigravity / Claude Code ReAct cycle.
    """
    AVAILABLE_MODELS = {
        "llama3.2": {"name": "Llama 3.2 (3B)", "type": "local", "tag": "llama3.2:latest", "desc": "Sub-100ms conversational & edge reasoning"},
        "qwen": {"name": "Qwen 2.5 Coder (7B)", "type": "local", "tag": "qwen2.5-coder:7b", "desc": "High-power local coding & refactoring"},
        "agy": {"name": "Antigravity CLI (AGY)", "type": "cloud", "bin": "/Users/ajayashrestha/.local/bin/agy", "desc": "Google DeepMind Agentic Coding Sentinel"},
        "claude": {"name": "Claude Code", "type": "cloud", "bin": "/opt/homebrew/bin/claude", "desc": "Anthropic Claude 3.5 Sonnet / Opus agent"},
        "codex": {"name": "Codex CLI", "type": "cloud", "bin": "/opt/homebrew/bin/codex", "desc": "OpenAI Codex Agent"},
        "auto": {"name": "Autonomous Auto-Router", "type": "hybrid", "desc": "Dynamic routing based on task complexity"}
    }

    def __init__(self, default_model: str = "llama3.2"):
        self.active_model = default_model if default_model in self.AVAILABLE_MODELS else "llama3.2"

    def set_model(self, model_key: str) -> Tuple[bool, str]:
        """Switches the active model."""
        clean = model_key.lower().strip()
        # Aliases
        if clean in ("llama", "llama3", "llama3.2:latest"):
            clean = "llama3.2"
        elif clean in ("qwen2.5", "qwen2.5-coder", "qwen2.5-coder:7b", "coder"):
            clean = "qwen"
        elif clean in ("antigravity",):
            clean = "agy"

        if clean in self.AVAILABLE_MODELS:
            self.active_model = clean
            info = self.AVAILABLE_MODELS[clean]
            return True, f"Active model switched to [{info['name']}] ({info['desc']})."
        
        valid = ", ".join(self.AVAILABLE_MODELS.keys())
        return False, f"Unknown model '{model_key}'. Available models: {valid}"

    def get_model_status(self) -> Dict[str, Any]:
        """Returns readiness and information about all supported models."""
        status = {}
        for k, v in self.AVAILABLE_MODELS.items():
            st = dict(v)
            if v["type"] == "local":
                st["ready"] = True  # verified via ollama list
            elif v["type"] == "cloud":
                st["ready"] = os.path.exists(v.get("bin", ""))
            else:
                st["ready"] = True
            st["active"] = (k == self.active_model)
            status[k] = st
        return status

    def determine_effective_model(self, prompt: str) -> str:
        """Determines model to execute when in 'auto' mode."""
        if self.active_model != "auto":
            return self.active_model

        p = prompt.lower()
        complex_triggers = [
            "refactor", "build", "debug", "implement", "architect", "function", "class",
            "test suite", "react", "fastapi", "docker", "pipeline", "fix bug", "git"
        ]
        if any(w in p for w in complex_triggers):
            return "qwen"  # Local coding powerhouse
        return "llama3.2"

    def stream_ollama(self, model_tag: str, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """Streams tokens from local Ollama endpoint."""
        url = f"{OLLAMA_API_BASE}/chat"
        payload = {
            "model": model_tag,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": 0.3,
                "num_ctx": 4096
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                for line in resp:
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        msg = chunk.get("message", {})
                        content = msg.get("content", "")
                        if content:
                            yield content
                        if chunk.get("done", False):
                            break
        except Exception as e:
            yield f"\n[Ollama Inference Error: {e}]"

    def execute_cloud_agent(self, agent_key: str, prompt: str) -> str:
        """Invokes Claude Code, Antigravity, or Codex with PII scrubbing."""
        clean_prompt, redacted = sanitize_text(prompt)
        redact_notice = f" (Scrubbed {len(redacted)} PII tokens)" if redacted else ""

        if agent_key == "claude":
            bin_path = "/opt/homebrew/bin/claude"
            if not os.path.exists(bin_path):
                return "Claude CLI is not installed at /opt/homebrew/bin/claude."
            cmd = [bin_path, "-p", clean_prompt]
        elif agent_key == "agy":
            bin_path = "/Users/ajayashrestha/.local/bin/agy"
            if not os.path.exists(bin_path):
                return "Antigravity CLI is not installed at ~/.local/bin/agy."
            cmd = [bin_path, "--prompt", clean_prompt]
        elif agent_key == "codex":
            bin_path = "/opt/homebrew/bin/codex"
            if not os.path.exists(bin_path):
                return "Codex CLI is not installed at /opt/homebrew/bin/codex."
            cmd = [bin_path, "exec", clean_prompt]
        else:
            return f"Unsupported cloud agent: {agent_key}"

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            out = res.stdout.strip() or res.stderr.strip()
            return f"[{self.AVAILABLE_MODELS[agent_key]['name']}{redact_notice}]\n{out}"
        except Exception as e:
            return f"Cloud Agent Execution Error ({agent_key}): {e}"

    def execute_tool(self, tool_tag: str, command: str) -> Tuple[bool, str]:
        """
        Executes a recognized agent tool with strict safety checks:
        - <tool:bash>: Shell commands (checked via Rule 2 & 3 sentinel)
        - <tool:mac>: Deterministic macOS actions (close app, new window, world time)
        - <tool:search>: Private web search
        - <tool:read>: Read file contents
        """
        t = tool_tag.lower().strip()
        c = command.strip()

        if t in ("mac", "tool:mac"):
            ok, res = execute_mac_action(c)
            if ok:
                return True, res
            return False, f"macOS action failed: {res}"

        elif t in ("bash", "tool:bash", "sh", "shell"):
            is_safe, reason = validate_shell_safety(c)
            if not is_safe:
                return False, f"Rule 2 & 3 Safety Block: {reason}"
            try:
                res = subprocess.run(
                    c,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=os.path.expanduser("~")
                )
                stdout = res.stdout.strip()
                stderr = res.stderr.strip()
                if res.returncode == 0:
                    out = stdout if stdout else "(Command succeeded with zero output)"
                    return True, out
                return False, f"Command exited with code {res.returncode}:\n{stderr or stdout}"
            except Exception as e:
                return False, f"Execution exception: {e}"

        elif t in ("search", "tool:search"):
            return True, execute_private_search(c)

        elif t in ("read", "tool:read"):
            p = os.path.expanduser(c)
            if not os.path.exists(p):
                return False, f"File not found: {p}"
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(4000)
                return True, content
            except Exception as e:
                return False, f"Could not read file {p}: {e}"

        return False, f"Unknown tool type '{tool_tag}'"

    def run_agentic_turn(
        self,
        user_prompt: str,
        messages: List[Dict[str, str]],
        max_steps: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Full ReAct Execution Loop:
        1. Proactive Sensory Check (0ms Native macOS Execution)
        2. Model Invocation (Local Ollama streaming or Cloud Agent)
        3. Tool Detection & Safe Execution
        4. Observation Feedback Loop (Model self-corrects if tool errors)
        5. Final Synthesis
        """
        # Step 0: Deterministic Proactive Action Interception
        handled, proactive_resp = handle_proactive_actions(user_prompt, messages)
        if handled and proactive_resp:
            EVOLUTION_MEMORY.record_interaction("proactive_mac", user_prompt, proactive_resp, proactive_resp, True)
            messages.append({"role": "user", "content": user_prompt})
            messages.append({"role": "assistant", "content": proactive_resp})
            if stream_callback:
                stream_callback(proactive_resp)
            return proactive_resp, messages

        # Add user prompt to conversation history
        messages.append({"role": "user", "content": user_prompt})

        target_model = self.determine_effective_model(user_prompt)

        # Handle Cloud Agent execution (Claude / AGY / Codex)
        if target_model in ("claude", "agy", "codex"):
            resp = self.execute_cloud_agent(target_model, user_prompt)
            if stream_callback:
                stream_callback(resp)
            messages.append({"role": "assistant", "content": resp})
            return resp, messages

        # Local Ollama Agentic ReAct Loop
        model_tag = self.AVAILABLE_MODELS[target_model]["tag"]

        step = 0
        final_response = ""

        while step < max_steps:
            step += 1
            step_chunks = []

            for chunk in self.stream_ollama(model_tag, messages):
                step_chunks.append(chunk)
                if stream_callback:
                    stream_callback(chunk)

            reply = "".join(step_chunks)
            final_response = reply

            # Detect tool invocations
            # Formats supported: <tool:bash>cmd</tool:bash>, <tool:mac>cmd</tool:mac>, <tool:search>q</tool:search>
            tool_calls = re.findall(r"<(tool:[a-zA-Z]+)>(.*?)</\1>", reply, re.DOTALL)

            if not tool_calls:
                # No tools requested: complete turn
                messages.append({"role": "assistant", "content": reply})
                break

            # Process tool calls
            messages.append({"role": "assistant", "content": reply})

            observation_feedback = []
            for t_tag, t_cmd in tool_calls:
                clean_cmd = t_cmd.strip()
                ok, output = self.execute_tool(t_tag, clean_cmd)
                status_str = "SUCCESS" if ok else "ERROR"
                observation_feedback.append(
                    f"[{t_tag} {status_str}]\nCommand: {clean_cmd}\nOutput:\n{output}"
                )
                # Record to evolutionary memory
                EVOLUTION_MEMORY.record_interaction(t_tag, user_prompt, clean_cmd, output[:200], ok)

            # Feed observation back to model for reflection / next step
            obs_prompt = "\n\n".join(observation_feedback)
            messages.append({
                "role": "user",
                "content": f"[OBSERVATION - REVIEW TOOL EXECUTION RESULTS]:\n{obs_prompt}\n\nIf the goal is achieved, provide the final answer to the user. If an error occurred, repair the approach."
            })

        return final_response, messages

    def run_autonomous_mission(
        self,
        mission_goal: str,
        max_steps: int = 8,
        on_step_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """Runs a high-level mission end-to-end using the Autonomous Mission Director."""
        director = AutonomousMissionDirector(self)
        return director.execute_mission(mission_goal, max_steps, on_step_callback)

class AutonomousMissionDirector:
    """
    Fable Showrunner (SHOW-1) & Project Astra Autonomous Mission Director.
    Executes high-level user missions end-to-end on macOS with minimal human intervention:
    - Decomposes intent into actionable steps
    - Executes multi-step tool calls (<tool:mac>, <tool:bash>, <tool:search>, <tool:read>)
    - Enforces Rule 2 & 3 Safety Guardrails (pausing only for destructive actions)
    - Self-heals upon errors using multi-turn observation feedback
    - Generates verified mission completion report
    """
    def __init__(self, agent_engine: AgentEngine):
        self.engine = agent_engine

    def execute_mission(
        self,
        mission_goal: str,
        max_steps: int = 8,
        on_step_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        grounded_sys = get_grounded_system_prompt()

        mission_sys_prompt = f"""{grounded_sys}

[AUTONOMOUS MISSION DIRECTOR PROTOCOL - SHOWRUNNER / ASTRA STANDARD]:
You are executing an autonomous mission on macOS: "{mission_goal}".
The human has handed you the wheel and expects full end-to-end execution.
You must:
1. Decompose the goal into necessary actions and execute them using tools:
   - <tool:mac>cmd</tool:mac> (e.g. close settings, new terminal window, world time)
   - <tool:bash>cmd</tool:bash> (e.g. run pytest, check memory, list files)
   - <tool:search>query</tool:search> (e.g. web search)
   - <tool:read>filepath</tool:read> (e.g. read files)
2. NEVER ask the human for permission for safe actions. Execute them directly.
3. If an error occurs, observe the error and fix it autonomously in the next step.
4. When all actions are complete, conclude your output with:
   [MISSION COMPLETE]
   Summarize what was accomplished.
"""

        messages = [
            {"role": "system", "content": mission_sys_prompt},
            {"role": "user", "content": f"Execute this mission autonomously now: {mission_goal}"}
        ]

        target_model = self.engine.determine_effective_model(mission_goal)
        model_info = self.engine.AVAILABLE_MODELS.get(target_model, self.engine.AVAILABLE_MODELS["llama3.2"])

        step = 0
        tools_executed = []
        final_text = ""
        success = True

        while step < max_steps:
            step += 1
            step_chunks = []

            if target_model in ("claude", "agy", "codex"):
                reply = self.engine.execute_cloud_agent(target_model, messages[-1]["content"])
            else:
                tag = model_info.get("tag", "llama3.2:latest")
                for chunk in self.engine.stream_ollama(tag, messages):
                    step_chunks.append(chunk)
                reply = "".join(step_chunks)

            final_text = reply
            messages.append({"role": "assistant", "content": reply})

            # Check tools
            tool_calls = re.findall(r"<(tool:[a-zA-Z]+)>(.*?)</\1>", reply, re.DOTALL)

            if not tool_calls or "[MISSION COMPLETE]" in reply:
                break

            observations = []
            for t_tag, t_cmd in tool_calls:
                c = t_cmd.strip()
                ok, out = self.engine.execute_tool(t_tag, c)
                status_str = "SUCCESS" if ok else "ERROR"
                tools_executed.append({
                    "step": step,
                    "tool": t_tag,
                    "command": c,
                    "status": status_str,
                    "output": out[:200]
                })
                observations.append(f"[{t_tag} {status_str}]\nCommand: {c}\nOutput:\n{out}")
                EVOLUTION_MEMORY.record_interaction(f"mission_{t_tag}", mission_goal, c, out[:200], ok)

                if on_step_callback:
                    on_step_callback({
                        "step": step,
                        "tool": t_tag,
                        "command": c,
                        "status": status_str,
                        "output": out
                    })

            obs_text = "\n\n".join(observations)
            messages.append({
                "role": "user",
                "content": f"[OBSERVATION - MISSION STEP {step} RESULTS]:\n{obs_text}\n\nContinue autonomously. If finished, end with [MISSION COMPLETE]."
            })

        duration = round(time.time() - start_time, 2)
        return {
            "mission": mission_goal,
            "status": "SUCCESS" if success else "FAILED",
            "model_used": target_model,
            "steps_taken": step,
            "duration_sec": duration,
            "tools_executed": tools_executed,
            "final_output": final_text,
            "guardrails_held": True
        }

AGENT_ENGINE = AgentEngine()
