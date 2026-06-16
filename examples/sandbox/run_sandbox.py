"""Phase 4 sandbox demo — run each MVP workflow's tool actions through the governed
gateway + connectors with EDENA gating, local route only, no real PHI.

    PYTHONPATH=... python examples/sandbox/run_sandbox.py
"""
from __future__ import annotations

from florence_connectors.sandbox import build_sandbox_gateway
from florence_core.schemas import CandidateAction
from florence_edena import EdenaClient
from florence_model_router import ModelRouter

DEMOS = [
    ("ICU handoff — read context", "fhir_read_patient_summary", "retrieve", "phi_local", False, "a"),
    ("Patient education — templates", "education_template_search", "retrieve", "internal", False, "a"),
    ("Policy retrieval — cite policy", "local_policy_search", "retrieve", "internal", False, "a"),
    ("Prior auth — read meds", "fhir_read_medications", "retrieve", "phi_local", False, "a"),
    ("Prior auth — external submit", "payer_portal_submit", "call_api", "phi_redacted", True, "a"),
    ("Agentic review — prod exec", "code_exec", "execute_code", "internal", False, "run-on-prod"),
]


def main() -> None:
    gw = build_sandbox_gateway(EdenaClient())
    router = ModelRouter()
    print("Florence-X healthcare sandbox — governed tool execution\n")
    for name, tool, atype, dc, ext, aid in DEMOS:
        action = CandidateAction(
            action_id=aid, workflow_run_id="demo", agent_id="ag", requester_role="rn",
            action_type=atype, intended_target=tool, tool_requested=tool,
            data_classification=dc, reversible=not ext, external_boundary_crossed=ext,
            proposed_payload_hash="h")
        route = router.route(workflow_run_id="demo", data_classification=dc, risk_tier="yellow")
        res = gw.invoke(action)
        verdict = "EXECUTED" if res.executed else f"REFUSED ({res.reason})"
        refs = (res.result or {}).get("resource_ids") or (res.result or {}).get("document_refs") or []
        print(f"• {name:32s} → {verdict:28s} model={route.locality:10s} refs={refs}")


if __name__ == "__main__":
    main()
