"""
AizenOS Polyglot Shell & Cross-Platform Command Translator.
Enables seamless execution of Windows (PowerShell/CMD), Linux (Bash/Zsh),
and macOS terminal commands across all host operating systems.
"""

import platform
import re
import shlex

def translate_command(cmd: str, target_os: str = None) -> str:
    """
    Translates commands between Windows PowerShell/CMD and POSIX (macOS / Linux).
    If target_os is not specified, it defaults to the current host OS.
    """
    if target_os is None:
        target_os = platform.system()  # 'Darwin', 'Linux', or 'Windows'

    raw = cmd.strip()
    if not raw:
        return raw

    # Handle POSIX target (macOS / Linux)
    if target_os in ("Darwin", "Linux"):
        # Windows -> POSIX mappings
        # Exact alias / command replacements
        if re.match(r"^cls\b", raw, re.I):
            return "clear"
        if re.match(r"^dir(\s+.*)?$", raw, re.I):
            rest = raw[3:].strip()
            return f"ls -la {rest}".strip()
        if re.match(r"^type\s+(.+)$", raw, re.I):
            return re.sub(r"^type\s+", "cat ", raw, flags=re.I)
        if re.match(r"^tasklist\b", raw, re.I):
            return "ps aux"
        if re.match(r"^get-process\b", raw, re.I):
            return "ps aux"
        if re.match(r"^ipconfig(\s+/all)?\b", raw, re.I):
            return "ifconfig" if target_os == "Darwin" else "ip addr"
        if re.match(r"^findstr\s+(.+)$", raw, re.I):
            return re.sub(r"^findstr\s+", "grep ", raw, flags=re.I)
        if re.match(r"^select-string\s+(.+)$", raw, re.I):
            # Select-String -Pattern "x" -> grep "x"
            sub = re.sub(r"-Pattern\s+", "", raw, flags=re.I)
            return re.sub(r"^select-string\s+", "grep ", sub, flags=re.I)
        if re.match(r"^taskkill\s+/pid\s+(\d+)", raw, re.I):
            return re.sub(r"^taskkill\s+/pid\s+(\d+)", r"kill \1", raw, flags=re.I)
        if re.match(r"^copy\s+(.+)$", raw, re.I):
            return re.sub(r"^copy\s+", "cp ", raw, flags=re.I)
        if re.match(r"^move\s+(.+)$", raw, re.I):
            return re.sub(r"^move\s+", "mv ", raw, flags=re.I)
        if re.match(r"^del\s+(?:/[sqf]\s+)*\*", raw, re.I):
            return "rm -rf *"
        if re.match(r"^del\s+(?:/[sqf]\s+)+(.+)$", raw, re.I):
            return re.sub(r"^del\s+(?:/[sqf]\s+)+", "rm -rf ", raw, flags=re.I)
        if re.match(r"^del\s+(.+)$", raw, re.I):
            return re.sub(r"^del\s+", "rm ", raw, flags=re.I)
        if re.match(r"^md\s+(.+)$", raw, re.I):
            return re.sub(r"^md\s+", "mkdir -p ", raw, flags=re.I)
        if re.match(r"^rd\s+(.+)$", raw, re.I):
            return re.sub(r"^rd\s+", "rmdir ", raw, flags=re.I)

    # Handle Windows target
    elif target_os == "Windows":
        # POSIX -> Windows mappings
        if re.match(r"^clear\b", raw):
            return "cls"
        if re.match(r"^ls(\s+-[a-zA-Z]+)?(\s+.*)?$", raw):
            # Replace ls / ls -la with dir
            return re.sub(r"^ls(\s+-[a-zA-Z]+)?", "dir", raw).strip()
        if re.match(r"^cat\s+(.+)$", raw):
            return re.sub(r"^cat\s+", "type ", raw)
        if re.match(r"^ps\s+(aux|ef)?\b", raw):
            return "tasklist"
        if re.match(r"^ifconfig\b", raw) or re.match(r"^ip\s+addr\b", raw):
            return "ipconfig /all"
        if re.match(r"^grep\s+(.+)$", raw):
            return re.sub(r"^grep\s+", "findstr ", raw)
        if re.match(r"^kill\s+-9\s+(\d+)", raw):
            return re.sub(r"^kill\s+-9\s+(\d+)", r"taskkill /F /PID \1", raw)
        if re.match(r"^kill\s+(\d+)", raw):
            return re.sub(r"^kill\s+(\d+)", r"taskkill /PID \1", raw)
        if re.match(r"^cp\s+(.+)$", raw):
            return re.sub(r"^cp\s+", "copy ", raw)
        if re.match(r"^mv\s+(.+)$", raw):
            return re.sub(r"^mv\s+", "move ", raw)

    return raw
