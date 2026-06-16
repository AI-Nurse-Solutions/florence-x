"""Healthcare sandbox wiring (Phase 4): all connectors behind one governed gateway.

Local-only routes, synthetic FHIR, no real PHI. Used by the sandbox demos/tests
to run each MVP workflow's tool actions through EDENA + connectors.
"""
from __future__ import annotations

from .a2a import A2AConnector
from .fhir import FhirReadConnector
from .gateway import ToolGateway
from .local_files import LocalSearchConnector

DEFAULT_BUNDLE = "examples/_fixtures/fhir/synthetic_icu_patient_bundle.json"


def build_sandbox_gateway(edena, fhir_bundle_path: str = DEFAULT_BUNDLE) -> ToolGateway:
    gw = ToolGateway(edena)
    fhir = FhirReadConnector(fhir_bundle_path)
    gw.register("fhir_read_patient_summary", fhir, "read_patient_summary")
    gw.register("fhir_read_observations", fhir, "read_observations")
    gw.register("fhir_read_medications", fhir, "read_medications")

    local = LocalSearchConnector()
    gw.register("local_policy_search", local, "local_policy_search")
    gw.register("education_template_search", local, "education_template_search")

    gw.register("handoff_to_agent", A2AConnector(), "handoff_to_agent")
    return gw
