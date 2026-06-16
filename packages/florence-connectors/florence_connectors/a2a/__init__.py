"""Agent-to-Agent (A2A) connector (Phase 4).

A handoff to another agent is just another tool invocation — so it is a
CandidateAction subject to EDENA, executed only through the gateway (RFC 0004).
Returns a handoff reference, never raw context payloads.
"""
from __future__ import annotations


class A2AConnector:
    transport = "a2a"

    def __init__(self, reachable_agents: list[str] | None = None) -> None:
        self._agents = set(reachable_agents or [])

    def list_actions(self) -> list[str]:
        return ["handoff_to_agent"]

    def invoke(self, action: str, payload: dict) -> dict:
        if action != "handoff_to_agent":
            raise ValueError(f"unknown action {action!r}")
        target = payload.get("target_agent", "unknown")
        accepted = (not self._agents) or target in self._agents
        return {"action": action, "target_agent": target, "accepted": accepted}
