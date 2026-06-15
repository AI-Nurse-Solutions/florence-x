"""Connector protocol — the contract every transport adapter implements."""
from __future__ import annotations
from typing import Protocol


class Connector(Protocol):
    transport: str            # mcp | fhir | smart | cds_hooks | openapi | a2a | rpa | local
    def list_actions(self) -> list[str]: ...
    def invoke(self, action: str, payload: dict) -> dict: ...
