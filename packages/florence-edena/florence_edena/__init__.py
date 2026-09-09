"""florence-edena: the governance-plane client + policy adapters.

EDENA is NOT a Florence-X module. It is a separate governance service that
Florence-X *calls*. This package contains the client, the risk-feature
extractor, and the policy adapters (OPA / Cedar). The decision *types*
(CandidateAction, EDENADecision) live in florence-core and are re-exported
here for convenience.
"""
from __future__ import annotations

from florence_core.schemas import CandidateAction, EDENADecision  # re-export

from .client import EdenaClient, EdenaConfig, make_backend
from .risk_features import extract_risk_features

__all__ = [
    "CandidateAction",
    "EDENADecision",
    "EdenaClient",
    "EdenaConfig",
    "extract_risk_features",
    "make_backend",
]
