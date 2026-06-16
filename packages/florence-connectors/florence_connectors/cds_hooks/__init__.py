"""CDS Hooks service — turns an EHR hook into a governed Signal (Phase 4).

A CDS Hooks invocation (patient-view, order-select, …) is a *trigger*: it does
not act, it raises a Signal into the Florence-X loop, which EDENA then gates.
Responses are CDS cards summarizing the governed outcome — never an ungoverned
action.
"""
from __future__ import annotations

from florence_core.schemas import CDSHookContext, RequesterContext, Signal


# CDS service id -> (hook, signal_type, title).
SERVICES: dict[str, tuple[str, str, str]] = {
    "florence-patient-education": ("patient-view", "patient_education_needed",
                                   "Florence-X patient education draft"),
    "florence-prior-auth": ("order-select", "prior_auth_needed",
                            "Florence-X prior authorization draft"),
    "florence-policy": ("patient-view", "policy_question",
                        "Florence-X policy & protocol retrieval"),
}


def discovery() -> dict:
    """CDS Hooks discovery document (GET /cds-services)."""
    return {
        "services": [
            {"id": sid, "hook": hook, "title": title,
             "description": title, "prefetch": {}}
            for sid, (hook, _stype, title) in SERVICES.items()
        ]
    }


def signal_from_request(service_id: str, request: dict, signal_id: str) -> Signal:
    if service_id not in SERVICES:
        raise KeyError(f"unknown CDS service {service_id!r}")
    hook, signal_type, _title = SERVICES[service_id]
    context = request.get("context", {})
    has_patient = bool(context.get("patientId"))
    return Signal(
        signal_id=signal_id,
        source="cds_hooks",
        signal_type=signal_type,
        requester=RequesterContext(role="rn"),
        data_classification="phi_local" if has_patient else "internal",
        patient_context_present=has_patient,
        cds_hook_context=CDSHookContext(
            hook=request.get("hook", hook),
            hook_instance=request.get("hookInstance", "unknown"),
            fhir_server=request.get("fhirServer"),
            context=context,
        ),
    )
