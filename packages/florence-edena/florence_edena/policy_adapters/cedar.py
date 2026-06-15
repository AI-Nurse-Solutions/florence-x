"""CedarBackend — placeholder for an AWS Cedar authorization adapter.

Cedar is a strong alternative for RBAC/ABAC authorization-style policies.
Implemented in a later phase; see docs/rfcs/0002-edena-decision-api.md.
"""
from __future__ import annotations


class CedarBackend:  # pragma: no cover - Phase 4+
    def evaluate(self, features: dict) -> dict:
        raise NotImplementedError("Cedar adapter is planned for a later phase.")
