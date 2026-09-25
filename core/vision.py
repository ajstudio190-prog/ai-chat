"""
Visual & Desktop Perception Engine for AizenOS.
Inspired by Open-Interpreter (68k ⭐) and Project Astra.
Provides real-time desktop screen awareness, active app detection, and window tracking.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

SCREENSHOT_PATH = Path("/tmp/aizen_screen.png")

def get_frontmost_app() -> str:
    """Returns the name of the active frontmost macOS application."""
    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "Desktop"

def get_running_desktop_apps() -> List[str]:
    """Returns list of all active non-background user applications."""
    script = 'tell application "System Events" to get name of every application process whose background only is false'
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            raw = res.stdout.strip()
            # Split comma separated apps and clean up
            apps = [a.strip() for a in raw.split(",") if a.strip()]
            # Filter out duplicates while preserving order
            seen = set()
            unique_apps = []
            for app in apps:
                if app not in seen:
                    seen.add(app)
                    unique_apps.append(app)
            return unique_apps
    except Exception:
        pass
    return []

def capture_screen_snapshot() -> Tuple[bool, str]:
    """Captures a silent screenshot of the primary display if permissions allow."""
    try:
        res = subprocess.run(
            ["screencapture", "-x", "-C", str(SCREENSHOT_PATH)],
            capture_output=True,
            text=True,
            timeout=3
        )
        if res.returncode == 0 and SCREENSHOT_PATH.exists():
            return True, str(SCREENSHOT_PATH)
        return False, "Screen capture requires Screen Recording permission in macOS System Settings."
    except Exception as e:
        return False, f"Screenshot capture error: {e}"

def get_desktop_visual_summary() -> str:
    """Produces a real-time Project Astra-grade visual summary of the user's desktop."""
    front = get_frontmost_app()
    running = get_running_desktop_apps()
    running_str = ", ".join(running[:8]) if running else "None detected"
    
    return f"Active Front App: '{front}' | Running Apps: [{running_str}]"
