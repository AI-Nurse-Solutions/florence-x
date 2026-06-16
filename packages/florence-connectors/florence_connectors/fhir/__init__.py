"""FHIR R4 connector (read-only). Reads synthetic bundles for the MVP.

PHI boundary: returns resource *references* (ResourceType/id) and codes, never
raw narrative — the governance/model planes reason over metadata, not content.
"""
from __future__ import annotations

import json
from pathlib import Path

# action -> the FHIR resourceType(s) it surfaces.
_ACTION_RESOURCES: dict[str, tuple[str, ...]] = {
    "read_patient_summary": ("Patient", "Encounter", "Condition"),
    "read_observations": ("Observation",),
    "read_medications": ("MedicationRequest",),
    "read_conditions": ("Condition",),
    "read_allergies": ("AllergyIntolerance",),
    "read_procedures": ("Procedure",),
}


class FhirReadConnector:
    """Minimal read-only FHIR connector over a local synthetic bundle."""

    transport = "fhir"

    def __init__(self, bundle_path: str) -> None:
        self._bundle = json.loads(Path(bundle_path).read_text())

    def list_actions(self) -> list[str]:
        return list(_ACTION_RESOURCES)

    def invoke(self, action: str, payload: dict) -> dict:
        resources = _ACTION_RESOURCES.get(action)
        if resources is None:
            raise ValueError(f"unknown action {action!r}")
        entries = [e["resource"] for e in self._bundle.get("entry", [])]
        data = [r for r in entries if r["resourceType"] in resources]
        # Refs + codes only — never raw narrative (PHI boundary: metadata-first).
        return {
            "action": action,
            "count": len(data),
            "resource_ids": [f"{r['resourceType']}/{r['id']}" for r in data],
        }
