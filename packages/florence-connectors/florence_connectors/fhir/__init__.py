"""FHIR R4 connector (read-only initially). Reads synthetic bundles for the MVP."""
from __future__ import annotations

import json
from pathlib import Path


class FhirReadConnector:
    """Minimal read-only FHIR connector over a local synthetic bundle (Phase 4 expands)."""

    transport = "fhir"

    def __init__(self, bundle_path: str) -> None:
        self._bundle = json.loads(Path(bundle_path).read_text())

    def list_actions(self) -> list[str]:
        return ["read_patient_summary", "read_observations", "read_medications"]

    def invoke(self, action: str, payload: dict) -> dict:
        rt = {"read_observations": "Observation",
              "read_medications": "MedicationRequest"}.get(action)
        entries = [e["resource"] for e in self._bundle.get("entry", [])]
        if action == "read_patient_summary":
            data = [r for r in entries if r["resourceType"] in {"Patient", "Encounter", "Condition"}]
        elif rt:
            data = [r for r in entries if r["resourceType"] == rt]
        else:
            raise ValueError(f"unknown action {action!r}")
        # Return resource refs/codes, not raw narrative (PHI boundary: metadata-first).
        return {"action": action, "count": len(data),
                "resource_ids": [f"{r['resourceType']}/{r['id']}" for r in data]}
