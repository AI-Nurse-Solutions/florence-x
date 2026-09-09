"""Read-only registry viewers for the steward console (Phase 3).

Agents are registered labor (CLAUDE.md rule 4); this exposes them and the tool
authorization graph with NAIO approval status. Editing / persistence is a later
RFC — these endpoints are read-only.
"""
from __future__ import annotations

from fastapi import APIRouter
from florence_core.schemas import AgentDefinition

from ..services import get_orchestrator

router = APIRouter(tags=["registry"])


@router.get("/agents", response_model=list[AgentDefinition])
def list_agents() -> list[AgentDefinition]:
    return get_orchestrator().list_agents()


@router.get("/tools")
def list_tools() -> list[dict]:
    return get_orchestrator().list_tools()
