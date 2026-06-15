"""ModelRoute: the recorded model-selection decision + rationale."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow
from .enums import DataClass, RiskTier


class ModelRoute(FlorenceModel):
    route_id: str
    workflow_run_id: str
    selected_model: str
    locality: str = Field(..., description="local_slm | local_llm | cloud | enterprise_endpoint")
    phi_allowed: bool
    data_classification: DataClass
    risk_tier: RiskTier
    redaction_required: bool = False
    cost_ceiling_usd: float | None = None
    latency_budget_ms: int | None = None
    rationale: str
    fallback_model: str | None = None
    decided_at: datetime = Field(default_factory=utcnow)
