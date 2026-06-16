"""Local document/search connector (Phase 4).

Backs policy-retrieval and patient-education tools with local, citable documents.
Returns document *references* (id + section), never inlined content — same
metadata-first PHI posture as the FHIR connector.
"""
from __future__ import annotations


class LocalSearchConnector:
    transport = "local"

    def __init__(self, documents: dict[str, list[str]] | None = None) -> None:
        # tool action -> list of document refs it can cite.
        self._docs = documents or {
            "local_policy_search": ["policy:icu_handoff_sop_v3#sec2", "policy:medication_admin_v5#sec4"],
            "education_template_search": ["edu:discharge_meds_v2", "edu:wound_care_v1"],
        }

    def list_actions(self) -> list[str]:
        return list(self._docs)

    def invoke(self, action: str, payload: dict) -> dict:
        refs = self._docs.get(action)
        if refs is None:
            raise ValueError(f"unknown action {action!r}")
        return {"action": action, "count": len(refs), "document_refs": list(refs)}
