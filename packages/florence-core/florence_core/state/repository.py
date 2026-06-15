"""Repository abstraction for durable run state.

The MVP ships an InMemoryRepository. apps/api/app/db swaps in a SQLAlchemy /
PostgreSQL implementation behind the same Protocol (see docs/rfcs and the
BUILD_PLAN Phase 1 tasks).
"""
from __future__ import annotations

from typing import Protocol

from florence_core.schemas import (
    CandidateAction,
    EDENADecision,
    EvidenceBundle,
    HumanReview,
    Incident,
    PolicyPack,
    Signal,
    WorkflowRun,
)


class Repository(Protocol):
    def save_signal(self, signal: Signal) -> None: ...
    def save_run(self, run: WorkflowRun) -> None: ...
    def get_run(self, workflow_run_id: str) -> WorkflowRun | None: ...
    def list_runs(self, status: str | None = None) -> list[WorkflowRun]: ...
    def save_action(self, action: CandidateAction) -> None: ...
    def get_action(self, action_id: str) -> CandidateAction | None: ...
    def save_decision(self, decision: EDENADecision) -> None: ...
    def save_review(self, review: HumanReview) -> None: ...
    def save_evidence(self, bundle: EvidenceBundle) -> None: ...
    def get_evidence(self, bundle_id: str) -> EvidenceBundle | None: ...
    def save_incident(self, incident: Incident) -> None: ...
    def list_incidents(self) -> list[Incident]: ...
    def save_policy_pack(self, pack: PolicyPack) -> None: ...
    def list_policy_packs(self) -> list[PolicyPack]: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self.signals: dict[str, Signal] = {}
        self.runs: dict[str, WorkflowRun] = {}
        self.actions: dict[str, CandidateAction] = {}
        self.decisions: dict[str, EDENADecision] = {}
        self.reviews: dict[str, HumanReview] = {}
        self.evidence: dict[str, EvidenceBundle] = {}
        self.incidents: dict[str, Incident] = {}
        self.policy_packs: dict[str, PolicyPack] = {}

    def save_signal(self, signal: Signal) -> None:
        self.signals[signal.signal_id] = signal

    def save_run(self, run: WorkflowRun) -> None:
        self.runs[run.workflow_run_id] = run

    def get_run(self, workflow_run_id: str) -> WorkflowRun | None:
        return self.runs.get(workflow_run_id)

    def list_runs(self, status: str | None = None) -> list[WorkflowRun]:
        runs = list(self.runs.values())
        if status is not None:
            runs = [r for r in runs if r.status == status]
        return runs

    def save_action(self, action: CandidateAction) -> None:
        self.actions[action.action_id] = action

    def get_action(self, action_id: str) -> CandidateAction | None:
        return self.actions.get(action_id)

    def save_decision(self, decision: EDENADecision) -> None:
        self.decisions[decision.decision_id] = decision

    def save_review(self, review: HumanReview) -> None:
        self.reviews[review.review_id] = review

    def save_evidence(self, bundle: EvidenceBundle) -> None:
        self.evidence[bundle.bundle_id] = bundle

    def get_evidence(self, bundle_id: str) -> EvidenceBundle | None:
        return self.evidence.get(bundle_id)

    def save_incident(self, incident: Incident) -> None:
        self.incidents[incident.incident_id] = incident

    def list_incidents(self) -> list[Incident]:
        return list(self.incidents.values())

    def save_policy_pack(self, pack: PolicyPack) -> None:
        self.policy_packs[pack.pack_id] = pack

    def list_policy_packs(self) -> list[PolicyPack]:
        return list(self.policy_packs.values())
