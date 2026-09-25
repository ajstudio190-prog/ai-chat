"""
AizenOS Linux Micro-Virtualization & Container Subsystem.
Enables instant, isolated Linux execution on macOS (via Colima/Docker/Lima)
and Windows (via WSL2/Docker) with shared directory mounting.
"""

import subprocess
import shutil
import platform
import os

IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"

def detect_linux_runtime() -> dict:
    """Detects available Linux virtualization engines on host machine."""
    if IS_LINUX:
        return {
            "available": True,
            "engine": "native_linux",
            "name": f"Native Linux ({platform.release()})",
            "active": True
        }

    # Check for WSL on Windows
    if IS_WINDOWS:
        wsl_bin = shutil.which("wsl")
        if wsl_bin:
            try:
                res = subprocess.run(["wsl", "--status"], capture_output=True, text=True, timeout=5)
                return {
                    "available": True,
                    "engine": "wsl",
                    "name": "Windows Subsystem for Linux (WSL2)",
                    "active": res.returncode == 0
                }
            except Exception:
                pass

    # Check for Docker CLI
    docker_bin = shutil.which("docker")
    if docker_bin:
        try:
            res = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=4)
            if res.returncode == 0:
                return {
                    "available": True,
                    "engine": "docker",
                    "name": "Docker Engine (Linux Container)",
                    "active": True
                }
        except Exception:
            pass

    # Check for Podman
    podman_bin = shutil.which("podman")
    if podman_bin:
        try:
            res = subprocess.run(["podman", "info"], capture_output=True, text=True, timeout=4)
            if res.returncode == 0:
                return {
                    "available": True,
                    "engine": "podman",
                    "name": "Podman Micro-VM",
                    "active": True
                }
        except Exception:
            pass

    # Check for Colima
    colima_bin = shutil.which("colima")
    if colima_bin:
        return {
            "available": True,
            "engine": "colima",
            "name": "Colima Linux Micro-VM",
            "active": False
        }

    return {
        "available": False,
        "engine": "none",
        "name": "No Linux container runtime found",
        "active": False
    }

def run_in_linux(cmd: str, image: str = "alpine:latest", mount_cwd: bool = True, timeout: int = 30) -> tuple[bool, str]:
    """
    Executes a command inside an isolated Linux container with the current directory mounted.
    Returns (success, output).
    """
    runtime = detect_linux_runtime()

    if runtime["engine"] == "native_linux":
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            out = f"{res.stdout.strip()}\n{res.stderr.strip()}".strip()
            return res.returncode == 0, out
        except Exception as e:
            return False, f"Linux execution failed: {e}"

    if runtime["engine"] == "wsl":
        try:
            wsl_cmd = ["wsl", "bash", "-c", cmd]
            res = subprocess.run(wsl_cmd, capture_output=True, text=True, timeout=timeout)
            out = f"{res.stdout.strip()}\n{res.stderr.strip()}".strip()
            return res.returncode == 0, out
        except Exception as e:
            return False, f"WSL execution failed: {e}"

    if runtime["engine"] in ("docker", "podman"):
        cwd = os.getcwd()
        bin_name = runtime["engine"]
        mount_args = ["-v", f"{cwd}:/workspace", "-w", "/workspace"] if mount_cwd else []
        docker_cmd = [bin_name, "run", "--rm"] + mount_args + [image, "sh", "-c", cmd]
        try:
            res = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout)
            out = f"{res.stdout.strip()}\n{res.stderr.strip()}".strip()
            return res.returncode == 0, out
        except Exception as e:
            return False, f"{bin_name} container execution failed: {e}"

    return False, "⚠️ No active Linux container runtime (Docker, Podman, or WSL) is running. Install Docker or run 'brew install colima docker'."
