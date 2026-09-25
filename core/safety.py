"""
ai-os Safety Sentinel & Destructive Guardrails Engine.
Enforces Rule 2 & 3 Guardrails across macOS and Linux environments.
"""

import re
import os

DESTRUCTIVE_SHELL_PATTERNS = [
    r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f?|--recursive)\b",
    r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r?\b",
    r"\brm\s+-[a-zA-Z]*r\b",
    r"\brm\s+\*",
    r"\brm\s+.*-(?:rf|fr)\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[a-zA-Z]*f\b",
    r"\bgit\s+push\s+.*(?:--force|-f)\b",
    r"\bgit\s+branch\s+-D\b",
    r"\bdrop\s+(database|table)\b",
    r"\btruncate\s+table\b",
    r"\bflushall\b",
    r"\b(format|mkfs)\b",
    r"\bdd\s+if=",
    r":\(\)\s*\{\s*:\|:&\s*\};:",
]

SENSITIVE_TARGET_PATTERNS = [
    r"\.env(\.[a-zA-Z0-9_-]+)?",
    r"~?/\.ssh(/.*)?",
    r"~?/\.gnupg(/.*)?",
    r"~?/\.aws(/.*)?",
    r"credentials",
    r"id_rsa",
    r"id_ed25519"
]

def validate_shell_safety(cmd: str) -> tuple[bool, str]:
    """
    Enforces Rule 2 & 3 Guardrails: Strictly blocks destructive operations,
    data wiping, force resets, and unauthorized credential manipulation.
    """
    low = cmd.lower().strip()

    # 1. Hard blocked destructive patterns
    for pat in DESTRUCTIVE_SHELL_PATTERNS:
        if re.search(pat, low):
            return False, f"Prohibited destructive command '{cmd}'. Strictly blocked by Safety Guardrail (Rule 2). Use .trash/ or request manual execution."

    # 2. Sensitive files protection (destructive overwrite / deletion)
    if re.search(r"\b(rm|shred|unlink|truncate|>\s*|mv)\b", low):
        for s_pat in SENSITIVE_TARGET_PATTERNS:
            if re.search(s_pat, low):
                return False, f"Prohibited operation on sensitive security target matching '{s_pat}'. Blocked by Safety Guardrail."

    return True, ""
