import re
from typing import NamedTuple

# Compiled regular expressions for high-risk secret and credential patterns
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "AWS Access Key ID",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "GitHub Token",
        re.compile(r"\b(?:ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b"),
    ),
    (
        "Private Key Block",
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
            r"[\s\S]*?"
            r"-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
        ),
    ),
    (
        "Explicit Key Assignment",
        re.compile(
            r"""(?i)\b(?:api[_-]?key|auth[_-]?token|secret[_-]?key|client[_-]?secret)\s*[:=]\s*['"]([a-zA-Z0-9_\-.~+]{16,})['"]"""
        ),
    ),
    (
        "Bearer Token Header",
        re.compile(r"""(?i)\bBearer\s+([a-zA-Z0-9_\-\.]{24,})\b"""),
    ),
]

REDACTION_TOKEN = "[REDACTED_SECRET]"


class SecretMatch(NamedTuple):
    """Represents a credential or secret string detected in source code."""

    rule_name: str
    matched_text: str
    start: int
    end: int


def scan_for_secrets(text: str) -> list[SecretMatch]:
    """Scans text content for high-risk secrets and credentials."""
    matches: list[SecretMatch] = []
    for rule_name, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            # If the pattern captured a specific sub-group (e.g., the key value), use group 1
            if match.groups():
                start, end = match.span(1)
                secret_str = match.group(1)
            else:
                start, end = match.span(0)
                secret_str = match.group(0)

            matches.append(
                SecretMatch(
                    rule_name=rule_name,
                    matched_text=secret_str,
                    start=start,
                    end=end,
                )
            )
    return matches


def redact_secrets(text: str) -> str:
    """Scans and redacts detected secrets, returning a sanitized string."""
    redacted = text
    for rule_name, pattern in SECRET_PATTERNS:
        if rule_name == "Explicit Key Assignment":
            # Redact only the capture group (the key value inside quotes)
            redacted = pattern.sub(
                lambda m: m.group(0).replace(m.group(1), REDACTION_TOKEN),
                redacted,
            )
        elif rule_name == "Bearer Token Header":
            redacted = pattern.sub(
                lambda m: f"Bearer {REDACTION_TOKEN}",
                redacted,
            )
        else:
            redacted = pattern.sub(REDACTION_TOKEN, redacted)

    return redacted
