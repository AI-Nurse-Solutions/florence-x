"""PHI-boundary enforcement for model calls (Phase 4).

The hard rule (CLAUDE.md rule 3): PHI never leaves the local boundary. A local
route may carry PHI as-is (it stays inside the perimeter); any non-local route
must be redacted first, and if PHI survives redaction the call is refused
(fail-closed) rather than risk a leak.
"""
from __future__ import annotations

from florence_core.schemas import ModelRoute

from .redaction import Redactor


class PhiBoundaryViolation(Exception):
    """Raised when PHI would cross the local boundary — the send is refused."""


def prepare_prompt(route: ModelRoute, prompt: str, redactor: Redactor | None = None) -> str:
    """Return the prompt text safe to hand to the route's model.

    Local route → unchanged (stays local). Non-local route → redacted, and
    verified PHI-free before it leaves the perimeter."""
    if route.locality.startswith("local"):
        return prompt
    redactor = redactor or Redactor()
    redacted = redactor.redact(prompt)
    if redactor.contains_phi(redacted):
        raise PhiBoundaryViolation(
            "PHI remains after redaction; refusing to send to a non-local model.")
    return redacted
