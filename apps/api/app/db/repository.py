"""PostgresRepository — durable implementation of the florence_core Repository
Protocol backed by SQLAlchemy 2.0 (P1-6).

Design (mirrors BUILD_PLAN Phase 1 guidance):
  * Pydantic objects are serialized whole into the ``payload`` JSON column; the
    typed columns exist only for querying / indexing (status, signal_type,
    decision, risk_tier, …). Reconstruction always comes from ``payload`` so the
    round-trip is lossless.
  * ``save_signal`` / ``save_run`` / ``save_action`` / ``save_decision`` /
    ``save_review`` UPSERT (a run is saved repeatedly as its status advances).
  * ``save_evidence`` is APPEND-ONLY: one immutable row per ``finalize()``; an
    existing bundle_id is never updated in place (CLAUDE.md rule 5 / append-only).

This class is engine-agnostic — Postgres is the production target, but the same
code runs against any SQLAlchemy URL (SQLite is used in the integration test so
it runs without Docker).
"""
from __future__ import annotations

from enum import Enum

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
from sqlalchemy import select

from .models import (
    CandidateActionRow,
    EdenaDecisionRow,
    EvidenceBundleRow,
    HumanReviewRow,
    IncidentRow,
    PolicyPackRow,
    SignalRow,
    WorkflowRunRow,
)


def _s(value):
    """Plain string for a (possibly str-)Enum, else the value unchanged."""
    return value.value if isinstance(value, Enum) else value


class PostgresRepository:
    """Implements florence_core.state.Repository against SQLAlchemy models."""

    def __init__(self, session_factory) -> None:
        # session_factory is a sessionmaker (e.g. apps.api.app.db.session.SessionLocal).
        self._session_factory = session_factory

    # -- write path ---------------------------------------------------------
    def _commit(self, fn) -> None:
        session = self._session_factory()
        try:
            fn(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_signal(self, signal: Signal) -> None:
        self._commit(lambda s: s.merge(SignalRow(
            signal_id=signal.signal_id,
            source=signal.source,
            signal_type=signal.signal_type,
            data_classification=_s(signal.data_classification),
            payload=signal.model_dump(mode="json"),
            created_at=signal.created_at,
        )))

    def save_run(self, run: WorkflowRun) -> None:
        self._commit(lambda s: s.merge(WorkflowRunRow(
            workflow_run_id=run.workflow_run_id,
            workflow_id=run.workflow_id,
            signal_id=run.signal_id,
            status=_s(run.status),
            context_id=run.context_id,
            evidence_bundle_id=run.evidence_bundle_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
            payload=run.model_dump(mode="json"),
        )))

    def get_run(self, workflow_run_id: str) -> WorkflowRun | None:
        session = self._session_factory()
        try:
            row = session.get(WorkflowRunRow, workflow_run_id)
            return WorkflowRun.model_validate(row.payload) if row else None
        finally:
            session.close()

    def list_runs(self, status: str | None = None) -> list[WorkflowRun]:
        session = self._session_factory()
        try:
            stmt = select(WorkflowRunRow)
            if status is not None:
                stmt = stmt.where(WorkflowRunRow.status == status)
            return [WorkflowRun.model_validate(r.payload) for r in session.scalars(stmt)]
        finally:
            session.close()

    def save_action(self, action: CandidateAction) -> None:
        self._commit(lambda s: s.merge(CandidateActionRow(
            action_id=action.action_id,
            workflow_run_id=action.workflow_run_id,
            agent_id=action.agent_id,
            action_type=_s(action.action_type),
            data_classification=_s(action.data_classification),
            reversible=action.reversible,
            external_boundary_crossed=action.external_boundary_crossed,
            proposed_payload_hash=action.proposed_payload_hash,
            payload=action.model_dump(mode="json"),
        )))

    def get_action(self, action_id: str) -> CandidateAction | None:
        session = self._session_factory()
        try:
            row = session.get(CandidateActionRow, action_id)
            return CandidateAction.model_validate(row.payload) if row else None
        finally:
            session.close()

    def save_decision(self, decision: EDENADecision) -> None:
        self._commit(lambda s: s.merge(EdenaDecisionRow(
            decision_id=decision.decision_id,
            action_id=decision.action_id,
            decision=_s(decision.decision),
            risk_tier=_s(decision.risk_tier),
            rationale=decision.rationale,
            payload=decision.model_dump(mode="json"),
        )))

    def save_review(self, review: HumanReview) -> None:
        self._commit(lambda s: s.merge(HumanReviewRow(
            review_id=review.review_id,
            action_id=review.action_id,
            decision_id=review.decision_id,
            reviewer_role=review.reviewer_role,
            outcome=_s(review.outcome),
            payload=review.model_dump(mode="json"),
            reviewed_at=review.reviewed_at,
        )))

    def save_evidence(self, bundle: EvidenceBundle) -> None:
        # Append-only: never UPDATE an existing bundle in place. A re-save of the
        # same bundle_id is a no-op rather than a mutation.
        def _insert(session) -> None:
            if session.get(EvidenceBundleRow, bundle.bundle_id) is not None:
                return
            session.add(EvidenceBundleRow(
                bundle_id=bundle.bundle_id,
                workflow_run_id=bundle.workflow_run_id,
                signal_id=bundle.signal_id,
                final_action=bundle.final_action,
                payload=bundle.model_dump(mode="json"),
                created_at=bundle.created_at,
            ))

        self._commit(_insert)

    def get_evidence(self, bundle_id: str) -> EvidenceBundle | None:
        session = self._session_factory()
        try:
            row = session.get(EvidenceBundleRow, bundle_id)
            return EvidenceBundle.model_validate(row.payload) if row else None
        finally:
            session.close()

    def save_incident(self, incident: Incident) -> None:
        # Append-only: an incident id is recorded once; never mutated in place here.
        def _insert(session) -> None:
            if session.get(IncidentRow, incident.incident_id) is not None:
                return
            session.add(IncidentRow(
                incident_id=incident.incident_id,
                workflow_run_id=incident.workflow_run_id,
                action_id=incident.action_id,
                category=_s(incident.category),
                severity=_s(incident.severity),
                triggered_by=incident.triggered_by,
                payload=incident.model_dump(mode="json"),
                created_at=incident.created_at,
            ))

        self._commit(_insert)

    def list_incidents(self) -> list[Incident]:
        session = self._session_factory()
        try:
            return [Incident.model_validate(r.payload)
                    for r in session.scalars(select(IncidentRow))]
        finally:
            session.close()

    def save_policy_pack(self, pack: PolicyPack) -> None:
        self._commit(lambda s: s.merge(PolicyPackRow(
            pack_id=pack.pack_id, name=pack.name, version=pack.version,
            superseded_by=pack.superseded_by, payload=pack.model_dump(mode="json"),
        )))

    def list_policy_packs(self) -> list[PolicyPack]:
        session = self._session_factory()
        try:
            return [PolicyPack.model_validate(r.payload)
                    for r in session.scalars(select(PolicyPackRow))]
        finally:
            session.close()
