"""Accumulates an EvidenceBundle across a workflow run. Evidence is not optional."""
from __future__ import annotations

import uuid

from florence_core.schemas import (
    AgentDefinition,
    EDENADecision,
    EvidenceBundle,
    HumanReview,
    Signal,
    ToolCallRecord,
    WorkflowRun,
    utcnow,
)


class EvidenceBundleBuilder:
    def __init__(self, run: WorkflowRun, signal: Signal) -> None:
        self.run = run
        self.signal = signal
        self.bundle = EvidenceBundle(
            bundle_id=f"ev_{uuid.uuid4().hex[:12]}",
            workflow_run_id=run.workflow_run_id,
            signal_id=signal.signal_id,
            signal_received_at=signal.created_at,
        )

    @classmethod
    def from_bundle(cls, bundle: EvidenceBundle) -> "EvidenceBundleBuilder":
        """Wrap an in-progress bundle (e.g. one carried in durable graph state) so
        the same record_*/finalize operations apply — keeps evidence assembly
        identical across the minimal and graph runtimes."""
        obj = cls.__new__(cls)
        obj.run = None
        obj.signal = None
        obj.bundle = bundle
        return obj

    def set_context(self, context_hash: str) -> None:
        self.bundle.context_hash = context_hash

    def record_model(self, model: str, version: str | None = None) -> None:
        self.bundle.model_used = model
        self.bundle.model_version = version

    def record_agent(self, agent: AgentDefinition) -> None:
        self.bundle.agent_versions[agent.agent_id] = agent.version

    def add_decision(self, decision: EDENADecision) -> None:
        self.bundle.edena_decisions.append(decision)

    def add_review(self, review: HumanReview) -> None:
        self.bundle.human_reviews.append(review)
        self.bundle.reviewed_at = review.reviewed_at

    def record_tool(self, rec: ToolCallRecord) -> None:
        self.bundle.tool_calls.append(rec)

    def add_sources(self, refs: list[str]) -> None:
        for r in refs:
            if r not in self.bundle.source_citations:
                self.bundle.source_citations.append(r)

    def note_deviation(self, note: str) -> None:
        self.bundle.deviations_from_edena.append(note)

    def flag_incident(self, ref: str) -> None:
        self.bundle.incident_flags.append(ref)

    def finalize(self, final_action: str | None) -> EvidenceBundle:
        self.bundle.final_action = final_action
        self.bundle.completed_at = utcnow()
        return self.bundle
