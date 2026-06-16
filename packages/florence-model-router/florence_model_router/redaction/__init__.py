"""PHI redaction pipeline — runs before any non-local model call (Phase 4).

Detected identifiers are replaced with *stable* HMAC-SHA256 tokens, so the same
value always maps to the same token (useful for coreference) while the raw value
never leaves the local boundary (CLAUDE.md rule 3 / RFC 0006). This is a
pattern-based MVP (emails, phones, SSNs, MRNs, dates) plus an explicit
known-identifier list; production swaps in clinical NER.
"""
from __future__ import annotations

import hmac
import re
from hashlib import sha256

# Ordered patterns: (type label, compiled regex).
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("MRN", re.compile(r"\bMRN[:#\s]*\d{4,}\b", re.IGNORECASE)),
    ("PHONE", re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")),
    ("DATE", re.compile(r"\b\d{4}-\d{2}-\d{2}\b")),
    ("DATE", re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")),
    ("ID", re.compile(r"\b\d{6,}\b")),  # long bare digit runs (MRN/account-like)
]

_DEFAULT_KEY = b"florence-x-local-redaction-key"  # deployments must override


class Redactor:
    def __init__(self, key: bytes | str = _DEFAULT_KEY,
                 known_identifiers: list[str] | None = None) -> None:
        self.key = key.encode() if isinstance(key, str) else key
        # Explicit values (e.g. patient name) redacted by exact match, longest first.
        self.known = sorted(known_identifiers or [], key=len, reverse=True)

    def tokenize(self, value: str) -> str:
        return hmac.new(self.key, value.encode(), sha256).hexdigest()[:12]

    def _token(self, label: str, value: str) -> str:
        return f"[REDACTED:{label}:{self.tokenize(value)}]"

    def redact(self, text: str) -> str:
        out = text
        for value in self.known:
            if value:
                out = out.replace(value, self._token("NAME", value))
        for label, pattern in _PATTERNS:
            out = pattern.sub(lambda m, _l=label: self._token(_l, m.group(0)), out)
        return out

    def contains_phi(self, text: str) -> bool:
        if any(value and value in text for value in self.known):
            return True
        return any(pattern.search(text) for _, pattern in _PATTERNS)


def redact(text: str, key: bytes | str = _DEFAULT_KEY) -> str:
    """Convenience: redact with a default Redactor."""
    return Redactor(key).redact(text)
