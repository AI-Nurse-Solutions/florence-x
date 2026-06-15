"""HumanReview — a named human's accountable decision. The loop closes here."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow
from .enums import HumanReviewOutcome


class HumanReview(FlorenceModel):
    review_id: str
    action_id: str
    decision_id: str
    reviewer_role: str
    reviewer_ref: str = Field(..., description="Opaque accountable-human reference.")
    outcome: HumanReviewOutcome
    edited_payload_hash: str | None = None
    note: str | None = None
    reviewed_at: datetime = Field(default_factory=utcnow)
