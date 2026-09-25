"""
AizenOS Multi-OS Agent Cluster & Hyper-Orchestration Subsystem.
Enables OS-level agent daemons (macOS host, Linux micro-VM, Windows)
coordinated by a unified Sovereign Meta-Orchestrator.
"""

import platform
import subprocess
import shutil
import threading
import time
from typing import Dict, List, Tuple
from core.container_bridge import detect_linux_runtime, run_in_linux
from core.shell_translator import translate_command
from core.telemetry import get_system_vitals
from core.safety import validate_shell_safety

class OSNode:
    def __init__(self, node_id: str, os_type: str, name: str, capabilities: List[str]):
        self.node_id = node_id
        self.os_type = os_type.lower()
        self.name = name
        self.capabilities = capabilities
        self.is_active = True
        self.last_seen = time.time()

    def execute(self, cmd: str, timeout: int = 30) -> Tuple[bool, str]:
        """Executes a command targeted directly at this OS node."""
        self.last_seen = time.time()
        
        # 1. Native macOS Execution
        if self.os_type == "darwin" or self.os_type == "macos":
            is_safe, reason = validate_shell_safety(cmd)
            if not is_safe:
                return False, f"⚠️ Guardrail blocked command on macOS node: {reason}"
            try:
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
                out = f"{proc.stdout.strip()}\n{proc.stderr.strip()}".strip()
                return proc.returncode == 0, out or "(Completed with 0 output)"
            except Exception as e:
                return False, f"macOS node error: {e}"

        # 2. Linux Micro-VM / Container Node Execution
        elif self.os_type == "linux":
            ok, res = run_in_linux(cmd, timeout=timeout)
            return ok, res

        # 3. Windows Subsystem / PowerShell Execution
        elif self.os_type == "windows":
            translated = translate_command(cmd, target_os="Windows")
            if shutil.which("powershell"):
                try:
                    proc = subprocess.run(["powershell", "-NoProfile", "-Command", translated], capture_output=True, text=True, timeout=timeout)
                    out = f"{proc.stdout.strip()}\n{proc.stderr.strip()}".strip()
                    return proc.returncode == 0, out
                except Exception as e:
                    return False, f"Windows node error: {e}"
            return False, "Windows PowerShell runtime unavailable on host."

        return False, f"Unsupported OS node type '{self.os_type}'"

class MultiOSOrchestrator:
    """
    Hyper-Orchestrator coordinating heterogeneous OS agents (macOS + Linux + Windows).
    Shards tasks, executes across OS nodes concurrently, and aggregates results.
    """
    def __init__(self):
        self.nodes: Dict[str, OSNode] = {}
        self.auto_discover_nodes()

    def auto_discover_nodes(self):
        """Scans host environment and registers active OS-level agent nodes."""
        current_sys = platform.system()
        
        # Node 1: Host macOS Agent
        if current_sys == "Darwin":
            self.nodes["macos-host"] = OSNode(
                node_id="macos-host",
                os_type="macos",
                name="macOS Host Node (Apple Silicon M4)",
                capabilities=["metal_gpu", "coreaudio_voice", "applescript", "screen_capture", "gui_automation"]
            )
        elif current_sys == "Linux":
            self.nodes["linux-host"] = OSNode(
                node_id="linux-host",
                os_type="linux",
                name="Linux Host Node (Native Kernel)",
                capabilities=["ebpf", "systemd", "raw_cgroups", "cuda", "apt_packages"]
            )

        # Node 2: Linux Micro-VM / Container Agent
        linux_rt = detect_linux_runtime()
        if linux_rt["available"]:
            self.nodes["linux-vm"] = OSNode(
                node_id="linux-vm",
                os_type="linux",
                name=f"Linux Subsystem ({linux_rt['name']})",
                capabilities=["container_isolation", "posix_elf", "cgroups", "alpine_packages"]
            )

        # Node 3: Windows Node (PowerShell bridge or WSL)
        if shutil.which("powershell") or current_sys == "Windows":
            self.nodes["windows-sub"] = OSNode(
                node_id="windows-sub",
                os_type="windows",
                name="Windows Subsystem (PowerShell / CIM Engine)",
                capabilities=["directml", "powershell_cmdlets", "win32_wmi", "sapi_voice"]
            )

    def list_nodes(self) -> str:
        """Returns visual status of all active OS-level agent nodes."""
        self.auto_discover_nodes()
        lines = [f"🌐 AizenOS Multi-OS Cluster ({len(self.nodes)} Nodes Active):"]
        for nid, node in sorted(self.nodes.items()):
            caps = ", ".join(node.capabilities[:3])
            lines.append(f"  • [{nid}] {node.name} (Caps: {caps})")
        return "\n".join(lines)

    def broadcast_command(self, cmd: str) -> Dict[str, str]:
        """Executes a command across all active OS nodes simultaneously."""
        results = {}
        threads = []

        def worker(nid: str, node: OSNode):
            ok, out = node.execute(cmd)
            status = "✅" if ok else "❌"
            results[nid] = f"{status} {out}"

        for nid, node in self.nodes.items():
            t = threading.Thread(target=worker, args=(nid, node))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=35)

        return results

    def shard_task(self, tasks_map: Dict[str, str]) -> Dict[str, str]:
        """
        Shards specific commands to specific OS nodes concurrently.
        Example: {'macos-host': 'pmset -g batt', 'linux-vm': 'uname -a'}
        """
        results = {}
        threads = []

        def worker(target_id: str, sub_cmd: str):
            node = self.nodes.get(target_id)
            if not node:
                results[target_id] = f"❌ Error: Node '{target_id}' not found."
                return
            ok, out = node.execute(sub_cmd)
            results[target_id] = out

        for target_id, sub_cmd in tasks_map.items():
            t = threading.Thread(target=worker, args=(target_id, sub_cmd))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=35)

        return results

HYPER_ORCHESTRATOR = MultiOSOrchestrator()
