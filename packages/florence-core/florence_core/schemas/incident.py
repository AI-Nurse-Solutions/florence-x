"""Incident — refusal and containment are normal, successful governance events."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow
from .enums import IncidentCategory, IncidentSeverity


class Incident(FlorenceModel):
    incident_id: str
    workflow_run_id: str | None = None
    action_id: str | None = None
    category: IncidentCategory
    severity: IncidentSeverity
    summary: str
    triggered_by: str = Field(..., description="edena_stop | circuit_breaker | phi_leak_detector | human")
    containment_applied: list[str] = Field(default_factory=list)
    owner_role: str | None = None
    resolved: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None
