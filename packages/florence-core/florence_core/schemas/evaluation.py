"""EvaluationRun — post-run quality, safety, and drift metrics (the learning loop)."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow


class EvaluationRun(FlorenceModel):
    eval_id: str
    workflow_run_id: str
    rubric: str
    scores: dict = Field(default_factory=dict)
    drift_flags: list[str] = Field(default_factory=list)
    override_rate: float | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
