"""SQLAlchemy 2.0 models — the durable schema of record for Postgres.

These mirror the Pydantic object model in florence-core/schemas. Append-only
tables (events, evidence) must never be UPDATEd in place; corrections are new
rows. Alembic owns migrations (see docker/ + BUILD_PLAN Phase 1).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SignalRow(Base):
    __tablename__ = "signals"
    signal_id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String)
    signal_type: Mapped[str] = mapped_column(String, index=True)
    data_classification: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkflowRunRow(Base):
    __tablename__ = "workflow_runs"
    workflow_run_id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String, index=True)
    signal_id: Mapped[str] = mapped_column(ForeignKey("signals.signal_id"))
    status: Mapped[str] = mapped_column(String, index=True)
    context_id: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_bundle_id: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)


class CandidateActionRow(Base):
    __tablename__ = "candidate_actions"
    action_id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.workflow_run_id"), index=True)
    agent_id: Mapped[str] = mapped_column(String)
    action_type: Mapped[str] = mapped_column(String)
    data_classification: Mapped[str] = mapped_column(String)
    reversible: Mapped[bool] = mapped_column(Boolean)
    external_boundary_crossed: Mapped[bool] = mapped_column(Boolean)
    proposed_payload_hash: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)


class EdenaDecisionRow(Base):
    __tablename__ = "edena_decisions"
    decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    action_id: Mapped[str] = mapped_column(ForeignKey("candidate_actions.action_id"), index=True)
    decision: Mapped[str] = mapped_column(String, index=True)
    risk_tier: Mapped[str] = mapped_column(String, index=True)
    rationale: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)


class HumanReviewRow(Base):
    """A named human's accountable decision on an action. The loop closes here."""

    __tablename__ = "human_reviews"
    review_id: Mapped[str] = mapped_column(String, primary_key=True)
    action_id: Mapped[str] = mapped_column(ForeignKey("candidate_actions.action_id"), index=True)
    decision_id: Mapped[str] = mapped_column(String, index=True)
    reviewer_role: Mapped[str] = mapped_column(String)
    outcome: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvidenceBundleRow(Base):
    """Append-only. One immutable bundle per finalize(); never updated in place."""

    __tablename__ = "evidence_bundles"
    bundle_id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(String, index=True)
    signal_id: Mapped[str] = mapped_column(String, index=True)
    final_action: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PolicyPackRow(Base):
    """Versioned EDENA policy pack record (provenance for which rules were live)."""

    __tablename__ = "policy_packs"
    pack_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String, index=True)
    superseded_by: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)


class IncidentRow(Base):
    """Refusal / containment events. Append-only; resolution is a new row or an
    explicit update by an authorized steward (Phase 3)."""

    __tablename__ = "incidents"
    incident_id: Mapped[str] = mapped_column(String, primary_key=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    action_id: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String, index=True)
    triggered_by: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventRow(Base):
    """Append-only CloudEvents store."""

    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, index=True)
    subject: Mapped[str] = mapped_column(String, index=True)
    time: Mapped[str] = mapped_column(String)
    envelope: Mapped[dict] = mapped_column(JSON)
