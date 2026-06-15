"""Shared value objects used across the Florence-X schemas."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FlorenceModel(BaseModel):
    """Base for all Florence-X objects.

    `frozen` is deliberately False (runtime objects accrete state), but
    `extra="forbid"` guarantees no silently-dropped fields cross the wire,
    which matters for an auditable governance system.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class RequesterContext(FlorenceModel):
    role: str = Field(..., description="e.g. rn, charge_rn, pharmacist, md, compliance")
    user_ref: str | None = Field(
        default=None, description="Opaque, non-PHI identity reference (never a raw name)."
    )
    unit: str | None = None
    institution_ref: str | None = None
