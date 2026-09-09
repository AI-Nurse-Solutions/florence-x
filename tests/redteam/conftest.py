"""Shared helpers for the adversarial (red-team) suite.

Each test tries to *violate* a Florence-X invariant and asserts it cannot. Tests
are tagged in their docstrings with the OWASP Top-10-for-Agentic-Apps-2026 code
(ASI01–ASI10) from docs/threat-model.md; docs/assurance.md is the full
invariant ↔ attack ↔ test matrix.
"""
from __future__ import annotations

import pytest
from florence_core.schemas import CandidateAction


@pytest.fixture
def mk_action():
    """Build a CandidateAction with adversary-controllable fields overridable."""
    def _make(**kw) -> CandidateAction:
        base = {
            'action_id': 'atk',
            'workflow_run_id': 'w',
            'agent_id': 'ag',
            'requester_role': 'rn',
            'action_type': 'draft',
            'intended_target': 't',
            'data_classification': 'phi_local',
            'reversible': True,
            'external_boundary_crossed': False,
            'proposed_payload_hash': 'h',
        }
        base.update(kw)
        return CandidateAction(**base)
    return _make
