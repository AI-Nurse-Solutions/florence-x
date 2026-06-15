"""ModelRouter — implements the routing decision matrix from docs/architecture.md.

Returns a recorded ModelRoute. PHI-bearing work stays local; cloud is allowed only
for non-PHI / redacted inputs (and requires a BAA + redaction in deployment).
"""
from __future__ import annotations

import uuid

from florence_core.schemas import ModelRoute
from florence_core.schemas.enums import DataClass, RiskTier

# Minimal default catalogue; replace with configured endpoints in deployment.
LOCAL_SLM = "local_clinical_slm"
LOCAL_LLM = "local_clinical_llm"
CLOUD = "approved_cloud_model"


class ModelRouter:
    def __init__(self, *, allow_cloud: bool = False) -> None:
        self.allow_cloud = allow_cloud

    def route(self, *, workflow_run_id: str, data_classification: str,
              risk_tier: str, latency_budget_ms: int | None = None) -> ModelRoute:
        dc = data_classification
        phi = dc in (DataClass.PHI_LOCAL.value, DataClass.PHI_REDACTED.value)
        high_risk = risk_tier in (RiskTier.ORANGE.value, RiskTier.RED.value, RiskTier.RED_BLOCKED.value)

        if dc == DataClass.PHI_LOCAL.value or high_risk:
            model, locality, redaction = LOCAL_SLM, "local_slm", False
            rationale = "PHI-local or high-risk → local model only; PHI stays inside the perimeter."
        elif dc == DataClass.PHI_REDACTED.value:
            model, locality, redaction = (CLOUD if self.allow_cloud else LOCAL_LLM), \
                ("cloud" if self.allow_cloud else "local_llm"), True
            rationale = "De-identified input; cloud allowed with redaction + BAA, else local LLM."
        else:  # public / internal
            model, locality, redaction = (CLOUD if self.allow_cloud else LOCAL_SLM), \
                ("cloud" if self.allow_cloud else "local_slm"), False
            rationale = "Non-PHI task; cloud permitted when configured."

        return ModelRoute(
            route_id=f"mr_{uuid.uuid4().hex[:10]}",
            workflow_run_id=workflow_run_id,
            selected_model=model,
            locality=locality,
            phi_allowed=phi and locality.startswith("local"),
            data_classification=dc,
            risk_tier=risk_tier,
            redaction_required=redaction,
            latency_budget_ms=latency_budget_ms,
            rationale=rationale,
            fallback_model=LOCAL_SLM,
        )
