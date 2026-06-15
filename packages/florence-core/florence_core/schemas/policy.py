"""PolicyPack — versioned EDENA / institutional governance rules (FDA PCCP-aligned)."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow


class PolicyPack(FlorenceModel):
    pack_id: str
    name: str
    version: str
    tiers_covered: list[str] = Field(default_factory=list)
    rego_module_refs: list[str] = Field(default_factory=list)
    institutional_approval_ref: str | None = None
    change_control_ref: str | None = Field(
        default=None, description="FDA PCCP / NAIO change-control record."
    )
    effective_at: datetime = Field(default_factory=utcnow)
    superseded_by: str | None = None
