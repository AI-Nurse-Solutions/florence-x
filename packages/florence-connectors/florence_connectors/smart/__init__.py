"""SMART on FHIR launch context (Phase 4, MVP stub).

Captures the EHR launch handshake (iss + launch token → patient/encounter
context) without a real OAuth flow. Production swaps in the full SMART
authorization-code grant; here it validates the launch parameters and returns a
bounded context object the loop can attach to a Signal.
"""
from __future__ import annotations

from pydantic import BaseModel


class SmartLaunchContext(BaseModel):
    model_config = {"extra": "forbid"}

    iss: str               # FHIR server base URL the EHR launched against
    launch: str            # opaque launch token
    patient: str | None = None
    encounter: str | None = None
    intent: str | None = None


def launch(iss: str, launch_token: str, *, patient: str | None = None,
           encounter: str | None = None) -> SmartLaunchContext:
    if not iss or not launch_token:
        raise ValueError("SMART launch requires both `iss` and `launch`.")
    return SmartLaunchContext(iss=iss, launch=launch_token, patient=patient, encounter=encounter)
