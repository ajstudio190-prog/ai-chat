"""
ai-os PII Guard Firewall & Anonymizer.
Scans and redacts credentials, private keys, and personal identifiers
before any text touches external search engines or cloud agents.
"""

import re

PII_REGEX_PATTERNS = {
    "API_KEY": [
        r"(?i)(?:api_key|apikey|secret|token|auth_token|access_token|bearer)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{16,})['\"]?",
        r"sk-(?:ant|proj|live|test)-[A-Za-z0-9_\-]{20,}",
        r"gh[pousr]_[A-Za-z0-9]{36,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ],
    "JWT_TOKEN": [
        r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
    ],
    "EMAIL": [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",
    ],
    "PHONE_NUMBER": [
        r"(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
    ],
    "CREDIT_CARD": [
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13})\b",
    ],
}

def sanitize_text(text: str, target: str = "External") -> tuple[str, dict]:
    """
    Deterministic PII & Secret Filter: Intercepts and scrubs API keys,
    tokens, emails, phone numbers, and credentials.
    Returns (clean_text, mapping_dict).
    """
    if not text:
        return text, {}

    clean_text = text
    mask_to_val = {}
    counters = {}

    for category, patterns in PII_REGEX_PATTERNS.items():
        for pat in patterns:
            for match in sorted(re.finditer(pat, clean_text), key=lambda m: m.start(), reverse=True):
                val = match.group(1) if match.lastindex else match.group(0)
                if val not in mask_to_val.values():
                    count = counters.get(category, 0) + 1
                    counters[category] = count
                    mask = f"[{category}_{count}]"
                    mask_to_val[mask] = val
                    clean_text = clean_text[:match.start()] + clean_text[match.start():match.end()].replace(val, mask) + clean_text[match.end():]

    return clean_text, mask_to_val
