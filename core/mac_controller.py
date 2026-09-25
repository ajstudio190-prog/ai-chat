"""
Native macOS Automation & Controller Engine for AizenOS.
Provides deterministic, zero-hallucination OS control:
- Accurate Window & Application Management (Open, Close, New Window)
- Precise Mathematical World Clock & Timezone Resolution (zoneinfo)
- Direct AppleScript Execution with Error Handling
"""

import os
import sys
import re
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Tuple, Optional

# Canonical macOS Application Mapping
APP_MAP = {
    "settings": "System Settings",
    "setting": "System Settings",
    "system settings": "System Settings",
    "system preferences": "System Settings",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "weather": "Weather",
    "safari": "Safari",
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "notes": "Notes",
    "music": "Music",
    "calculator": "Calculator",
    "calendar": "Calendar",
    "messages": "Messages",
    "finder": "Finder",
    "slack": "Slack",
    "vscode": "Visual Studio Code",
    "code": "Visual Studio Code",
    "mail": "Mail",
    "photos": "Photos",
    "reminders": "Reminders"
}

# Major Global Timezone Mapping
CITY_TZ_MAP = {
    "kathmandu": ("Asia/Kathmandu", "Kathmandu, Nepal"),
    "nepal": ("Asia/Kathmandu", "Nepal"),
    "tokyo": ("Asia/Tokyo", "Tokyo, Japan"),
    "japan": ("Asia/Tokyo", "Japan"),
    "london": ("Europe/London", "London, UK"),
    "uk": ("Europe/London", "United Kingdom"),
    "paris": ("Europe/Paris", "Paris, France"),
    "france": ("Europe/Paris", "France"),
    "berlin": ("Europe/Berlin", "Berlin, Germany"),
    "new york": ("America/New_York", "New York, USA"),
    "nyc": ("America/New_York", "New York, USA"),
    "los angeles": ("America/Los_Angeles", "Los Angeles, California"),
    "california": ("America/Los_Angeles", "California, USA"),
    "san francisco": ("America/Los_Angeles", "San Francisco, USA"),
    "chicago": ("America/Chicago", "Chicago, USA"),
    "texas": ("America/Chicago", "Texas, USA"),
    "dallas": ("America/Chicago", "Dallas, Texas"),
    "sydney": ("Australia/Sydney", "Sydney, Australia"),
    "australia": ("Australia/Sydney", "Australia"),
    "dubai": ("Asia/Dubai", "Dubai, UAE"),
    "uae": ("Asia/Dubai", "United Arab Emirates"),
    "singapore": ("Asia/Singapore", "Singapore"),
    "toronto": ("America/Toronto", "Toronto, Canada"),
    "india": ("Asia/Kolkata", "India"),
    "delhi": ("Asia/Kolkata", "New Delhi, India"),
    "mumbai": ("Asia/Kolkata", "Mumbai, India"),
    "seoul": ("Asia/Seoul", "Seoul, South Korea"),
    "korea": ("Asia/Seoul", "South Korea")
}

def resolve_mac_app_name(raw_name: str) -> str:
    """Normalizes informal user app names to official macOS process names."""
    clean = raw_name.lower().replace("app", "").replace("the", "").strip()
    return APP_MAP.get(clean, raw_name.strip().title())

def close_mac_app(app_query: str) -> Tuple[bool, str]:
    """Gracefully quits a macOS application using AppleScript, with killall fallback."""
    app_name = resolve_mac_app_name(app_query)
    script = f'tell application "{app_name}" to quit'
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            return True, f"Closed {app_name} for you."
    except Exception:
        pass

    # Fallback to killall
    try:
        res2 = subprocess.run(["killall", app_name], capture_output=True, text=True, timeout=2)
        if res2.returncode == 0:
            return True, f"Closed {app_name}."
    except Exception:
        pass

    return False, f"Could not close '{app_name}'. It may not be currently running."

def open_mac_app(app_query: str, new_window: bool = False) -> Tuple[bool, str]:
    """Opens a macOS app or specifically opens a new window."""
    app_name = resolve_mac_app_name(app_query)
    
    if new_window:
        if app_name == "Terminal":
            script = 'tell application "Terminal" to do script ""'
            try:
                res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    subprocess.run(["osascript", "-e", 'tell application "Terminal" to activate'], timeout=2)
                    return True, "Opened a new Terminal window on your screen."
            except Exception as e:
                return False, f"Error opening new Terminal window: {e}"
        elif app_name in ("Google Chrome", "Safari"):
            script = f'tell application "{app_name}" to make new window'
            try:
                res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    subprocess.run(["osascript", "-e", f'tell application "{app_name}" to activate'], timeout=2)
                    return True, f"Opened a new {app_name} window on your screen."
            except Exception:
                pass

    # Standard app open / new instance
    cmd = ["open", "-n", "-a", app_name] if new_window else ["open", "-a", app_name]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            return True, f"Opened {app_name} for you."
        return False, f"Could not open {app_name}: {res.stderr.strip()}"
    except Exception as e:
        return False, f"Error launching {app_name}: {e}"

def get_accurate_world_time(query: str) -> Tuple[bool, str]:
    """
    Computes exact astronomical local time for any global city or country
    using Python's zoneinfo database with zero hallucinations.
    """
    q = query.lower()
    matched_tz = None
    location_label = None

    for key, (tz_name, label) in CITY_TZ_MAP.items():
        if key in q:
            matched_tz = tz_name
            location_label = label
            break

    if not matched_tz:
        return False, "Timezone not recognized."

    try:
        now = datetime.now(ZoneInfo(matched_tz))
        fmt_time = now.strftime("%A, %B %d, %Y, %I:%M %p %Z")
        return True, f"In {location_label}, the current time is {fmt_time}."
    except Exception as e:
        return False, f"Error calculating timezone: {e}"

def execute_mac_action(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Evaluates natural language action intents and routes them to native macOS automation.
    Handles:
    - Close/Quit application
    - Open new window / Open app
    - Accurate World Time query
    """
    p = prompt.lower().strip()

    # 1. Close / Quit Application
    close_match = re.search(r"\b(close|quit|kill|exit|shut)\s+(?:the\s+)?([a-zA-Z\s]+?)(?:\s+app)?$", p)
    if close_match and not any(k in p for k in ("window", "tab", "file")):
        target = close_match.group(2).strip()
        if target:
            return close_mac_app(target)

    # 2. Open new terminal or app window
    if any(k in p for k in ("new terminal", "new terminal window", "another terminal", "open new terminal")):
        return open_mac_app("Terminal", new_window=True)

    new_window_match = re.search(r"\b(open\s+new\s+window\s+(?:for|in|of)?\s*([a-zA-Z\s]+)|open\s+a\s+new\s+([a-zA-Z\s]+)\s+window)\b", p)
    if new_window_match:
        app_target = (new_window_match.group(2) or new_window_match.group(3) or "").strip()
        if app_target:
            return open_mac_app(app_target, new_window=True)

    # 3. World Time Check
    if any(k in p for k in ("what time", "current time", "what's the time", "time in", "time is it in", "kathmandu", "nepal", "tokyo", "london")):
        ok, time_str = get_accurate_world_time(p)
        if ok:
            return True, time_str

    return False, None
