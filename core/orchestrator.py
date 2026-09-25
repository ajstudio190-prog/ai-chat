"""
ai-os Multi-Agent Router & ReAct Execution Engine.
Orchestrates local Ollama models, cloud frontier agents, and autonomous OS tools.
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
import re
import signal
import threading
from core.safety import validate_shell_safety
from core.telemetry import get_battery_info, get_wifi_info, get_system_vitals
from core.voice import speak_text, listen_for_voice
from core.browser import execute_private_search
from core.pii_guard import sanitize_text
from core.shell_translator import translate_command
from core.container_bridge import detect_linux_runtime, run_in_linux

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_FAST_MODEL = "llama3.2:latest"
DEFAULT_CODE_MODEL = "qwen2.5-coder:7b"

MAX_BACKGROUND_JOBS = 3  # Recommended limit for 16GB Apple Silicon Mac to prevent memory pressure & system hang

class BackgroundJobManager:
    def __init__(self):
        self.jobs = {}
        self.counter = 0
        self.lock = threading.Lock()

    def get_active_count(self) -> int:
        with self.lock:
            for jid, info in self.jobs.items():
                if info["status"] == "RUNNING" and info["proc"].poll() is not None:
                    code = info["proc"].poll()
                    info["status"] = "FINISHED" if code == 0 else f"FAILED (code {code})"
            return sum(1 for j in self.jobs.values() if j["status"] == "RUNNING")

    def start_job(self, cmd: str, cwd: str = None) -> tuple[bool, str]:
        active = self.get_active_count()
        if active >= MAX_BACKGROUND_JOBS:
            return False, f"⚠️ Mac Resource Safeguard: {MAX_BACKGROUND_JOBS} background jobs are already running. To protect your Mac's RAM and CPU from hanging, wait for one to finish or type '/jobs kill <id>'."

        with self.lock:
            self.counter += 1
            jid = self.counter
            log_path = f"/tmp/ai_job_{jid}.log"
            log_f = open(log_path, "w")
            proc = subprocess.Popen(
                cmd,
                shell=True,
                cwd=cwd or os.getcwd(),
                stdout=log_f,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            self.jobs[jid] = {
                "id": jid,
                "cmd": cmd,
                "proc": proc,
                "log_file": log_path,
                "log_handle": log_f,
                "start_time": time.time(),
                "status": "RUNNING"
            }
            return True, f"⚡ Launched background job #{jid}: '{cmd}'\n   Logs: {log_path} (Run '/jobs' to monitor or keep chatting freely!)"

    def list_jobs(self) -> str:
        self.get_active_count()
        if not self.jobs:
            return "No background jobs running."
        lines = [f"🔄 Background Jobs ({self.get_active_count()}/{MAX_BACKGROUND_JOBS} active):"]
        for jid, info in sorted(self.jobs.items()):
            dur = time.time() - info["start_time"]
            lines.append(f"  #{jid} [{info['status']}] ({dur:.1f}s) : {info['cmd']} (Logs: {info['log_file']})")
        return "\n".join(lines)

    def kill_job(self, jid: int) -> str:
        with self.lock:
            if jid not in self.jobs:
                return f"Job #{jid} not found."
            info = self.jobs[jid]
            if info["status"] == "RUNNING":
                try:
                    os.killpg(os.getpgid(info["proc"].pid), signal.SIGTERM)
                    info["status"] = "KILLED"
                    return f"Job #{jid} killed."
                except Exception as e:
                    return f"Error killing job #{jid}: {e}"
            return f"Job #{jid} is already {info['status']}."

BG_JOBS = BackgroundJobManager()

def execute_safe_command(cmd: str, cwd: str = None, is_voice: bool = False) -> str:
    """Executes commands with polyglot translation, micro-VM routing, and double confirmation for destructive actions."""
    clean_cmd = cmd.strip()

    # Check for direct Linux container execution request: 'linux <cmd>' or 'linux:<cmd>'
    if clean_cmd.startswith("linux:") or clean_cmd.startswith("linux "):
        linux_sub_cmd = clean_cmd[6:].strip()
        ok, res = run_in_linux(linux_sub_cmd)
        clean_res, _ = sanitize_text(res)
        return clean_res[:3500]

    # Translate command across Windows/POSIX polyglot dialects
    effective_cmd = translate_command(clean_cmd)

    is_safe, reason = validate_shell_safety(effective_cmd)
    if not is_safe:
        print(f"\n⚠️  DESTRUCTIVE ACTION DETECTED: {effective_cmd}")
        print(f"Implications: {reason}")
        print("Data loss cannot be undone.")
        if is_voice:
            speak_text("Caution: This will permanently delete or overwrite data. Do you want to proceed?", wait=True)
            spoken = listen_for_voice(6).strip().lower()
            if spoken not in ("yes", "y", "proceed", "do it"):
                return "❌ Action cancelled by user."
            speak_text("Please confirm a second time: are you completely sure?", wait=True)
            spoken2 = listen_for_voice(6).strip().lower()
            if spoken2 not in ("yes", "y", "proceed", "do it"):
                return "❌ Action cancelled on final confirmation."
        else:
            try:
                c1 = input("\nDo you want to proceed? [y/N]: ").strip().lower()
                if c1 not in ("y", "yes"):
                    return "❌ Action cancelled by user."
                c2 = input("FINAL CONFIRMATION: Type 'yes' to permanently execute: ").strip().lower()
                if c2 != "yes":
                    return "❌ Action cancelled on final confirmation."
            except Exception:
                return "❌ Action cancelled."

    try:
        proc = subprocess.run(
            effective_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=35,
            cwd=cwd or os.getcwd()
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        combined = f"{out}\n{err}".strip() if err else out
        if not combined:
            combined = f"(Completed with exit code {proc.returncode})"
        clean, _ = sanitize_text(combined)
        return clean[:3500]
    except subprocess.TimeoutExpired:
        return "❌ Error: Command timed out after 35s."
    except Exception as e:
        return f"❌ Execution error: {e}"

def stream_chat(model: str, messages: list):
    """Streams tokens from local Ollama with warm Metal/CUDA GPU keep-alive."""
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": True,
        "keep_alive": "60m",
        "options": {
            "temperature": 0.3,
            "num_thread": 8,
            "num_gpu": 99,
            "num_ctx": 4096
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done", False):
                        break
                except Exception:
                    continue
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot connect to Ollama at {OLLAMA_HOST}") from e

def route_task(prompt: str) -> tuple[str, str]:
    """
    Local-first Multi-Agent Task Router:
    Prioritizes local Apple Silicon / Linux models for 95% of tasks, only escalating to
    Claude Code, Antigravity, or Codex for massive multi-file projects or explicit commands.
    """
    p = prompt.lower().strip()

    # 1. Explicit requests for specific cloud agents
    if re.search(r"\b(ask claude|dispatch to claude|claude code|have claude|with claude)\b", p):
        return "claude", "Explicitly requested Claude Code"
    if re.search(r"\b(ask antigravity|dispatch to agy|have antigravity|antigravity cli|with agy)\b", p):
        return "agy", "Explicitly requested Antigravity"
    if re.search(r"\b(ask codex|dispatch to codex|have codex|codex cli|with codex)\b", p):
        return "codex", "Explicitly requested Codex CLI"

    # 2. Only escalate to cloud when a task is truly massive, heavy multi-file architecture, or whole-repo scale
    massive_architecture_patterns = [
        r"\b(build a fullstack|scaffold a complete|architect an entire system|create a full saas)\b",
        r"\b(entire repo|all files in the repo|whole codebase|repo-wide migration|rewrite the whole project)\b"
    ]
    for pattern in massive_architecture_patterns:
        if re.search(pattern, p):
            if "frontend" in p or "ui" in p or "react" in p or "tailwind" in p:
                return "claude", "Heavy multi-file frontend architecture"
            elif "backend" in p or "database" in p or "pipeline" in p:
                return "codex", "Heavy backend pipeline architecture"
            else:
                return "agy", "Large-scale repository-wide task (Gemini 1M+ context)"

    # 3. Local coding specialist
    if re.search(r"\b(write a python|write a script|function|component|bug|fix|unit test|regex|sql query)\b", p):
        return "local_code", "Handled locally via coding specialist (qwen2.5-coder:7b)"

    # 4. Default to local fast model (llama3.2)
    return "local", "Handled directly on local machine (llama3.2 sub-second)"
