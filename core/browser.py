"""
ai-os Private Web Search & Browser Engine.
Conducts zero-tracking web searches with mandatory PII Guard redaction.
"""

import subprocess
import shutil
import re
from core.pii_guard import sanitize_text

def execute_private_search(query: str) -> str:
    """Performs privacy-preserving web search via Playwright or Bing with pre-scrubbed PII."""
    clean_query, masked = sanitize_text(query, "Search Engine")

    browser_bin = shutil.which("ai-browser") or "/Users/ajayashrestha/.local/bin/ai-browser"
    if browser_bin and shutil.which(browser_bin):
        try:
            out = subprocess.check_output([browser_bin, "search", clean_query], text=True, timeout=25).strip()
            scrubbed, _ = sanitize_text(out, "Local Display")
            return scrubbed
        except Exception as e:
            return f"Search error: {e}"

    return f"Private search ready for: {clean_query}"
