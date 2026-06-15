"""The Florence-X canonical runtime loop.

    Signal -> WorkflowRun -> AgentInvocation -> CandidateAction
           -> EDENADecision -> HumanReview | SystemBlock | ToolExecution
           -> EvidenceBundle -> (EvaluationFeedback)

Design invariants (enforced here, mirrored in CLAUDE.md):
  * No consequential action executes without an EDENADecision.
  * A blocked/denied action is a successful governance event, not a crash.
  * Every run produces an EvidenceBundle, even when blocked or paused.
  * PHI never leaves the boundary: the loop passes hashes/refs, not raw content.

External collaborators are injected (EdenaClient, AgentRunner, HumanReviewer,
Repository, EventLog) so the loop is deterministic and unit-testable.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Protocol

from florence_core.dispatcher import Dispatcher  # noqa: F401 (re-exported convenience)
from florence_core.events import EventLog
from florence_core.evidence import EvidenceBundleBuilder
from florence_core.observability import set_attributes, span
from florence_core.schemas import (
    AgentDefinition,
    CandidateAction,
    ContextBundle,
    EDENADecision,
    EvidenceBundle,
    HumanReview,
    Incident,
    Signal,
    ToolCallRecord,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStep,
)
from florence_core.schemas.enums import (
    ActionType,
    DataClass,
    EdenaDecisionType,
    HumanReviewOutcome,
    IncidentCategory,
    IncidentSeverity,
    WorkflowRunStatus,
)
from florence_core.state import InMemoryRepository, Repository


# --- collaborator protocols ------------------------------------------------
class EdenaGateway(Protocol):
    def evaluate_action(self, action: CandidateAction) -> EDENADecision: ...


class AgentRunner(Protocol):
    def run(self, agent: AgentDefinition | None, step: WorkflowStep,
            context: ContextBundle, signal: Signal) -> dict: ...


class HumanReviewer(Protocol):
    def review(self, action: CandidateAction, decision: EDENADecision,
               agent_output: dict) -> HumanReview | None: ...


# --- default collaborators (no LLM, no UI) ---------------------------------
def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()[:24]


# --- shared, pure loop helpers ---------------------------------------------
# Module-level so both the minimal Runtime and the durable GraphRuntime use the
# IDENTICAL context/action/ordering logic — evidence parity is by construction.
def build_context(run: WorkflowRun, signal: Signal) -> ContextBundle:
    # Layer 2: classify + select minimum-necessary context (synthetic here).
    source_refs = ["fhir:Bundle/synthetic-icu-001", "policy:icu_handoff_sop_v3"]
    return ContextBundle(
        context_id=f"ctx_{uuid.uuid4().hex[:10]}",
        workflow_run_id=run.workflow_run_id,
        data_classification=signal.data_classification,
        phi_present=signal.data_classification in (DataClass.PHI_LOCAL.value, DataClass.PHI_REDACTED.value),
        minimum_necessary_justification="Task-scoped clinical summary for handoff drafting.",
        source_refs=source_refs,
        content_hash=_hash("|".join(source_refs)),
    )


def candidate_action(run: WorkflowRun, step: WorkflowStep, signal: Signal, output: dict) -> CandidateAction:
    spec = step.action
    action_type = spec.action_type if spec else ActionType.DRAFT.value
    data_class = (spec.data_classification if (spec and spec.data_classification) else signal.data_classification)
    return CandidateAction(
        action_id=f"act_{uuid.uuid4().hex[:10]}",
        workflow_run_id=run.workflow_run_id,
        agent_id=step.agent_id or "unassigned",
        requester_role=signal.requester.role,
        action_type=action_type,
        intended_target=spec.intended_target if spec else step.step_id,
        tool_requested=spec.tool_requested if spec else None,
        data_classification=data_class,
        reversible=spec.reversible if spec else True,
        external_boundary_crossed=spec.external_boundary_crossed if spec else False,
        clinical_impact=spec.clinical_impact if spec else None,
        proposed_payload_hash=output["payload_hash"],
        evidence_refs=output.get("source_refs", []),
    )


def ordered_steps(wf: WorkflowDefinition) -> list[WorkflowStep]:
    by_id = {s.step_id: s for s in wf.steps}
    order, seen, cur = [], set(), wf.steps[0] if wf.steps else None
    while cur and cur.step_id not in seen:
        order.append(cur)
        seen.add(cur.step_id)
        cur = by_id.get(cur.next_steps[0]) if cur.next_steps else None
    return order


def record_incident(repo, run: WorkflowRun, action_id: str, triggered_by: str,
                    summary: str, containment_applied: list[str] | None = None) -> Incident:
    """Persist an Incident for a blocked/stopped/contained action. Refusal and
    containment are successful governance outcomes (CLAUDE.md rule 9), so they are
    recorded as first-class evidence, not swallowed."""
    incident = Incident(
        incident_id=f"inc_{uuid.uuid4().hex[:10]}",
        workflow_run_id=run.workflow_run_id,
        action_id=action_id,
        category=IncidentCategory.SAFETY,
        severity=IncidentSeverity.SEV2,
        summary=summary,
        triggered_by=triggered_by,
        containment_applied=containment_applied or [],
    )
    repo.save_incident(incident)
    return incident


def _containment_for(decision) -> list[str]:
    """Containment actions to record when EDENA returns `contain`."""
    return ["execution_halted", "agent_contained"] if decision.is_containment else []


class StubAgentRunner:
    """Deterministic agent stand-in. Produces a draft + source refs + flags.

    Real model calls are added in florence-model-router; this keeps the
    governance loop runnable and reproducible without an LLM.
    """

    def run(self, agent, step, context, signal) -> dict:
        target = step.action.intended_target if step.action else step.step_id
        summary = f"[DRAFT:{target}] synthesized from approved local context for {signal.signal_type}."
        return {
            "summary": summary,
            "payload_hash": _hash(summary + context.content_hash),
            "missing_data_flags": ["weight_not_documented", "code_status_unconfirmed"],
            "source_refs": list(context.source_refs),
            "model": (agent.model_route.default if agent else "stub_model"),
        }


class AutoApproveReviewer:
    """Simulated human approval for demos/tests. LOGS that approval was simulated."""

    def __init__(self, outcome: HumanReviewOutcome = HumanReviewOutcome.APPROVE) -> None:
        self.outcome = outcome

    def review(self, action, decision, agent_output) -> HumanReview:
        return HumanReview(
            review_id=f"hr_{uuid.uuid4().hex[:10]}",
            action_id=action.action_id,
            decision_id=decision.decision_id,
            reviewer_role=decision.required_human_role or action.requester_role,
            reviewer_ref="SIMULATED-REVIEWER",
            outcome=self.outcome,
            note="Simulated review (demo). Replace with the steward console in Phase 3.",
        )


class QueueReviewer:
    """Production-shaped reviewer: pauses the run by returning None (awaiting human)."""

    def review(self, action, decision, agent_output) -> None:
        return None


# --- the runtime -----------------------------------------------------------
class Runtime:
    def __init__(
        self,
        edena: EdenaGateway,
        *,
        repo: Repository | None = None,
        events: EventLog | None = None,
        agent_runner: AgentRunner | None = None,
        reviewer: HumanReviewer | None = None,
        agents: dict[str, AgentDefinition] | None = None,
    ) -> None:
        self.edena = edena
        self.repo = repo or InMemoryRepository()
        self.events = events or EventLog()
        self.agent_runner = agent_runner or StubAgentRunner()
        self.reviewer = reviewer or AutoApproveReviewer()
        self.agents = agents or {}

    # -- helpers (delegate to shared module-level functions) ----------------
    def _build_context(self, run: WorkflowRun, signal: Signal) -> ContextBundle:
        return build_context(run, signal)

    def _candidate_action(self, run, step: WorkflowStep, signal, output) -> CandidateAction:
        return candidate_action(run, step, signal, output)

    def _ordered_steps(self, wf: WorkflowDefinition) -> list[WorkflowStep]:
        return ordered_steps(wf)

    # -- main entrypoint ----------------------------------------------------
    def run(self, workflow: WorkflowDefinition, signal: Signal,
            run_id: str | None = None) -> EvidenceBundle:
        with span("florence.workflow_run",
                  workflow_id=workflow.workflow_id, signal_type=signal.signal_type) as run_span:
            self.repo.save_signal(signal)
            run = WorkflowRun(
                # A pre-allocated run_id (from async enqueue) makes the run pollable
                # before the worker picks it up; otherwise generate one.
                workflow_run_id=run_id or f"wfr_{uuid.uuid4().hex[:10]}",
                workflow_id=workflow.workflow_id,
                signal_id=signal.signal_id,
                status=WorkflowRunStatus.RUNNING,
            )
            set_attributes(run_span, workflow_run_id=run.workflow_run_id)
            self.repo.save_run(run)
            self.events.emit("workflow_run.started", run.workflow_run_id,
                             workflow_id=workflow.workflow_id, signal_type=signal.signal_type)

            builder = EvidenceBundleBuilder(run, signal)
            context = self._build_context(run, signal)
            builder.set_context(context.content_hash)
            run.context_id = context.context_id
            self.events.emit("context.classified", run.workflow_run_id,
                             data_classification=context.data_classification, phi_present=context.phi_present)

            final_action: str | None = None

            for step in self._ordered_steps(workflow):
                with span("florence.workflow_step",
                          step_id=step.step_id, produces_action=step.produces_action):
                    run.current_step = step.step_id
                    self.events.emit("workflow_step.entered", run.workflow_run_id, step=step.step_id)
                    if not step.produces_action:
                        continue

                    agent = self.agents.get(step.agent_id) if step.agent_id else None
                    output = self.agent_runner.run(agent, step, context, signal)
                    if agent:
                        builder.record_agent(agent)
                    builder.record_model(output.get("model", "stub_model"))
                    builder.add_sources(output.get("source_refs", []))

                    action = self._candidate_action(run, step, signal, output)
                    self.repo.save_action(action)
                    self.events.emit("candidate_action.created", run.workflow_run_id,
                                     action_id=action.action_id, action_type=action.action_type)

                    decision = self.edena.evaluate_action(action)
                    self.repo.save_decision(decision)
                    builder.add_decision(decision)
                    self.events.emit("edena.decision", run.workflow_run_id,
                                     action_id=action.action_id, decision=decision.decision, tier=decision.risk_tier)

                    if decision.is_terminal_block:
                        run.status = (WorkflowRunStatus.STOPPED
                                      if decision.decision == EdenaDecisionType.STOP.value
                                      else WorkflowRunStatus.BLOCKED)
                        builder.flag_incident(f"edena_{decision.decision}:{action.action_id}")
                        record_incident(self.repo, run, action.action_id,
                                        f"edena_{decision.decision}", decision.rationale,
                                        containment_applied=_containment_for(decision))
                        final_action = f"blocked:{decision.decision}"
                        self.events.emit("action.blocked", run.workflow_run_id,
                                         action_id=action.action_id, decision=decision.decision)
                        break

                    if decision.requires_human:
                        run.status = WorkflowRunStatus.AWAITING_HUMAN
                        self.repo.save_run(run)
                        self.events.emit("human_review.requested", run.workflow_run_id,
                                         action_id=action.action_id, required_role=decision.required_human_role)
                        review = self.reviewer.review(action, decision, output)
                        if review is None:
                            # Truly async: persist partial evidence and pause.
                            bundle = builder.finalize(final_action="awaiting_human_review")
                            self.repo.save_evidence(bundle)
                            run.evidence_bundle_id = bundle.bundle_id
                            self.repo.save_run(run)
                            self.events.emit("workflow_run.paused", run.workflow_run_id,
                                             evidence_bundle_id=bundle.bundle_id)
                            set_attributes(run_span, status=run.status, final_action="awaiting_human_review")
                            return bundle
                        self.repo.save_review(review)
                        builder.add_review(review)
                        self.events.emit("human_review.completed", run.workflow_run_id,
                                         outcome=review.outcome, reviewer_role=review.reviewer_role)
                        if review.outcome in (HumanReviewOutcome.DENY.value, HumanReviewOutcome.STOP.value):
                            run.status = WorkflowRunStatus.BLOCKED
                            record_incident(self.repo, run, action.action_id,
                                            f"human_{review.outcome}",
                                            review.note or f"Human {review.outcome} of action.")
                            final_action = f"human_{review.outcome}"
                            self.events.emit("action.blocked", run.workflow_run_id, action_id=action.action_id,
                                             decision=f"human_{review.outcome}")
                            break
                        # Approved/edited: resume execution.
                        run.status = WorkflowRunStatus.RUNNING

                    # Allowed (auto or post-approval): simulate the bounded tool execution.
                    with span("florence.tool.execute",
                              action_id=action.action_id,
                              tool_id=action.tool_requested or "noop_executor"):
                        tool_id = action.tool_requested or "noop_executor"
                        builder.record_tool(ToolCallRecord(
                            tool_id=tool_id, action_id=action.action_id, proposed=True,
                            executed=True, output_hash=output["payload_hash"]))
                        final_action = action.action_type
                        self.events.emit("tool.executed", run.workflow_run_id,
                                         tool_id=tool_id, action_id=action.action_id)

            if run.status not in (WorkflowRunStatus.BLOCKED, WorkflowRunStatus.STOPPED,
                                  WorkflowRunStatus.AWAITING_HUMAN):
                run.status = WorkflowRunStatus.COMPLETED

            bundle = builder.finalize(final_action=final_action)
            self.repo.save_evidence(bundle)
            run.evidence_bundle_id = bundle.bundle_id
            run.completed_at = bundle.completed_at
            self.repo.save_run(run)
            self.events.emit("evidence_bundle.persisted", run.workflow_run_id,
                             evidence_bundle_id=bundle.bundle_id, final_action=final_action, status=run.status)
            set_attributes(run_span, status=run.status, final_action=final_action)
            return bundle
