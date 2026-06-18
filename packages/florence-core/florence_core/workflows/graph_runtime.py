"""Durable execution of the canonical loop via LangGraph (P1-9, RFC 0007).

The same Signal -> CandidateAction -> EDENADecision -> (review) -> tool ->
EvidenceBundle loop as the minimal Runtime, but expressed as a LangGraph
StateGraph with a checkpointer, so a run can pause at a human-review interrupt,
survive a process restart, and resume exactly where it left off.

Invariants preserved (RFC 0007):
  * EDENA is a topological gate: `execute_tool` is only reachable via an edge out
    of the `edena` node whose route is "allowed" or "human-approved". No node
    reaches tool execution without a decision.
  * Fail-closed: EDENA evaluation goes through the same EdenaClient.
  * Evidence-always: every terminal path runs `finalize` (or persists a partial
    bundle on pause).
  * PHI boundary: graph state carries only hashes/refs (CandidateAction,
    EvidenceBundle, decisions) — never raw agent payloads.

Evidence parity with the minimal runner is by construction: both use the shared
`build_context`/`candidate_action`/`ordered_steps` helpers and the same
`EvidenceBundleBuilder` operations.
"""
from __future__ import annotations

import uuid
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from florence_core.events import EventLog
from florence_core.evidence import EvidenceBundleBuilder
from florence_core.observability import set_attributes, span
from florence_core.schemas import (
    CandidateAction,
    EDENADecision,
    EvidenceBundle,
    HumanReview,
    Signal,
    ToolCallRecord,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStep,
)
from florence_core.schemas.enums import EdenaDecisionType, HumanReviewOutcome, WorkflowRunStatus
from florence_core.state import InMemoryRepository, Repository

from .runtime import (
    AutoApproveReviewer,
    EdenaGateway,
    StubAgentRunner,
    _containment_for,
    build_context,
    candidate_action,
    ordered_steps,
    record_incident,
)


class GraphState(TypedDict, total=False):
    signal: Any
    steps: list
    run: Any
    bundle: Any
    step_index: int
    final_action: str | None
    route: str
    pending_action: Any
    pending_decision: Any
    pending_payload_hash: str | None


class GraphRuntime:
    """LangGraph-backed durable runtime. Same collaborators as Runtime, plus a
    checkpointer (defaults to in-memory)."""

    def __init__(self, edena: EdenaGateway, *, repo: Repository | None = None,
                 events: EventLog | None = None, agent_runner=None, reviewer=None,
                 agents: dict | None = None, checkpointer=None) -> None:
        self.edena = edena
        self.repo = repo or InMemoryRepository()
        self.events = events or EventLog()
        self.agent_runner = agent_runner or StubAgentRunner()
        self.reviewer = reviewer or AutoApproveReviewer()
        self.agents = agents or {}
        self.checkpointer = checkpointer or MemorySaver()
        self._app = self._build_graph().compile(checkpointer=self.checkpointer)

    # State is kept JSON-native (model_dump'd dicts) so the checkpoint serializes
    # cleanly across MemorySaver/SQLite/Postgres with no custom-type registration.
    @staticmethod
    def _dump(obj) -> dict:
        return obj.model_dump(mode="json")

    # -- state coercion (state holds dicts; coerce to models on read) --------
    @staticmethod
    def _signal(s) -> Signal: return Signal.model_validate(s["signal"])
    @staticmethod
    def _run(s) -> WorkflowRun: return WorkflowRun.model_validate(s["run"])
    @staticmethod
    def _bundle(s) -> EvidenceBundle: return EvidenceBundle.model_validate(s["bundle"])
    @staticmethod
    def _steps(s) -> list[WorkflowStep]: return [WorkflowStep.model_validate(x) for x in s["steps"]]

    # -- nodes --------------------------------------------------------------
    def _n_start(self, state: GraphState) -> dict:
        signal = self._signal(state)
        run = self._run(state)
        self.repo.save_signal(signal)
        run.status = WorkflowRunStatus.RUNNING
        self.repo.save_run(run)
        self.events.emit("workflow_run.started", run.workflow_run_id,
                         workflow_id=run.workflow_id, signal_type=signal.signal_type)
        context = build_context(run, signal)
        run.context_id = context.context_id
        builder = EvidenceBundleBuilder(run, signal)
        builder.set_context(context.content_hash)
        self.events.emit("context.classified", run.workflow_run_id,
                         data_classification=context.data_classification,
                         phi_present=context.phi_present)
        return {"run": self._dump(run), "bundle": self._dump(builder.bundle),
                "step_index": 0, "final_action": None}

    def _n_dispatch(self, state: GraphState) -> dict:
        steps = self._steps(state)
        run = self._run(state)
        i = state["step_index"]
        # Advance through (and record) any non-action steps, then the next action step.
        while i < len(steps) and not steps[i].produces_action:
            run.current_step = steps[i].step_id
            self.events.emit("workflow_step.entered", run.workflow_run_id, step=steps[i].step_id)
            i += 1
        if i < len(steps):
            run.current_step = steps[i].step_id
            self.events.emit("workflow_step.entered", run.workflow_run_id, step=steps[i].step_id)
            route = "draft"
        else:
            route = "finalize"
        return {"step_index": i, "run": self._dump(run), "route": route}

    def _n_draft(self, state: GraphState) -> dict:
        signal = self._signal(state)
        run = self._run(state)
        step = self._steps(state)[state["step_index"]]
        builder = EvidenceBundleBuilder.from_bundle(self._bundle(state))

        agent = self.agents.get(step.agent_id) if step.agent_id else None
        output = self.agent_runner.run(agent, step, build_context(run, signal), signal)
        if agent:
            builder.record_agent(agent)
        builder.record_model(output.get("model", "stub_model"))
        builder.add_sources(output.get("source_refs", []))

        action = candidate_action(run, step, signal, output)
        self.repo.save_action(action)
        self.events.emit("candidate_action.created", run.workflow_run_id,
                         action_id=action.action_id, action_type=action.action_type)
        # PHI boundary: persist only the hash, never the raw agent payload.
        return {"bundle": self._dump(builder.bundle), "pending_action": self._dump(action),
                "pending_payload_hash": output["payload_hash"]}

    def _n_edena(self, state: GraphState) -> dict:
        run = self._run(state)
        action = CandidateAction.model_validate(state["pending_action"])
        builder = EvidenceBundleBuilder.from_bundle(self._bundle(state))

        decision = self.edena.evaluate_action(action)
        self.repo.save_decision(decision)
        builder.add_decision(decision)
        self.events.emit("edena.decision", run.workflow_run_id, action_id=action.action_id,
                         decision=decision.decision, tier=decision.risk_tier)

        out: dict = {"bundle": self._dump(builder.bundle), "pending_decision": self._dump(decision)}
        if decision.is_terminal_block:
            run.status = (WorkflowRunStatus.STOPPED
                          if decision.decision == EdenaDecisionType.STOP.value
                          else WorkflowRunStatus.BLOCKED)
            builder.flag_incident(f"edena_{decision.decision}:{action.action_id}")
            record_incident(self.repo, run, action.action_id,
                            f"edena_{decision.decision}", decision.rationale,
                            containment_applied=_containment_for(decision))
            self.events.emit("action.blocked", run.workflow_run_id,
                             action_id=action.action_id, decision=decision.decision)
            out.update(bundle=self._dump(builder.bundle), run=self._dump(run),
                       final_action=f"blocked:{decision.decision}", route="finalize")
        elif decision.requires_human:
            run.status = WorkflowRunStatus.AWAITING_HUMAN
            self.repo.save_run(run)
            self.events.emit("human_review.requested", run.workflow_run_id,
                             action_id=action.action_id, required_role=decision.required_human_role)
            out.update(run=self._dump(run), route="await_human")
        else:
            out["route"] = "execute_tool"
        return out

    def _n_await_human(self, state: GraphState) -> dict:
        # NOTHING with side effects may run before interrupt(): on resume this node
        # re-executes from the top. interrupt() suspends here on first pass and
        # returns the reviewer's decision (supplied via Command(resume=...)).
        review_data = interrupt({
            "action_id": CandidateAction.model_validate(state["pending_action"]).action_id,
            "decision_id": EDENADecision.model_validate(state["pending_decision"]).decision_id,
            "required_role": EDENADecision.model_validate(state["pending_decision"]).required_human_role,
        })
        review = HumanReview.model_validate(review_data)
        run = self._run(state)
        builder = EvidenceBundleBuilder.from_bundle(self._bundle(state))
        self.repo.save_review(review)
        builder.add_review(review)
        self.events.emit("human_review.completed", run.workflow_run_id,
                         outcome=review.outcome, reviewer_role=review.reviewer_role)
        if review.outcome in (HumanReviewOutcome.DENY.value, HumanReviewOutcome.STOP.value):
            run.status = WorkflowRunStatus.BLOCKED
            record_incident(self.repo, run, review.action_id, f"human_{review.outcome}",
                            review.note or f"Human {review.outcome} of action.")
            self.events.emit("action.blocked", run.workflow_run_id,
                             action_id=review.action_id, decision=f"human_{review.outcome}")
            return {"bundle": self._dump(builder.bundle), "run": self._dump(run),
                    "final_action": f"human_{review.outcome}", "route": "finalize"}
        run.status = WorkflowRunStatus.RUNNING
        return {"bundle": self._dump(builder.bundle), "run": self._dump(run), "route": "execute_tool"}

    def _n_execute_tool(self, state: GraphState) -> dict:
        run = self._run(state)
        action = CandidateAction.model_validate(state["pending_action"])
        builder = EvidenceBundleBuilder.from_bundle(self._bundle(state))
        with span("florence.tool.execute", action_id=action.action_id,
                  tool_id=action.tool_requested or "noop_executor"):
            tool_id = action.tool_requested or "noop_executor"
            builder.record_tool(ToolCallRecord(
                tool_id=tool_id, action_id=action.action_id, proposed=True,
                executed=True, output_hash=state["pending_payload_hash"]))
            self.events.emit("tool.executed", run.workflow_run_id,
                             tool_id=tool_id, action_id=action.action_id)
        return {"bundle": self._dump(builder.bundle), "final_action": action.action_type,
                "step_index": state["step_index"] + 1}

    def _n_finalize(self, state: GraphState) -> dict:
        run = self._run(state)
        if run.status not in (WorkflowRunStatus.BLOCKED, WorkflowRunStatus.STOPPED,
                              WorkflowRunStatus.AWAITING_HUMAN):
            run.status = WorkflowRunStatus.COMPLETED
        builder = EvidenceBundleBuilder.from_bundle(self._bundle(state))
        bundle = builder.finalize(final_action=state.get("final_action"))
        # A run that paused already persisted a partial bundle under the start id;
        # this completion is a new immutable revision (append-only store keeps both,
        # never shadows). run.evidence_bundle_id points at the latest.
        bundle.bundle_id = f"ev_{uuid.uuid4().hex[:12]}"
        self.repo.save_evidence(bundle)
        run.evidence_bundle_id = bundle.bundle_id
        run.completed_at = bundle.completed_at
        self.repo.save_run(run)
        self.events.emit("evidence_bundle.persisted", run.workflow_run_id,
                         evidence_bundle_id=bundle.bundle_id,
                         final_action=state.get("final_action"), status=run.status)
        return {"run": self._dump(run), "bundle": self._dump(bundle)}

    # -- graph wiring -------------------------------------------------------
    def _build_graph(self) -> StateGraph:
        g = StateGraph(GraphState)
        g.add_node("start", self._n_start)
        g.add_node("dispatch", self._n_dispatch)
        g.add_node("draft", self._n_draft)
        g.add_node("edena", self._n_edena)
        g.add_node("await_human", self._n_await_human)
        g.add_node("execute_tool", self._n_execute_tool)
        g.add_node("finalize", self._n_finalize)

        g.add_edge(START, "start")
        g.add_edge("start", "dispatch")
        g.add_conditional_edges("dispatch", lambda s: s["route"],
                                {"draft": "draft", "finalize": "finalize"})
        g.add_edge("draft", "edena")
        g.add_conditional_edges("edena", lambda s: s["route"],
                                {"finalize": "finalize", "await_human": "await_human",
                                 "execute_tool": "execute_tool"})
        g.add_conditional_edges("await_human", lambda s: s["route"],
                                {"finalize": "finalize", "execute_tool": "execute_tool"})
        g.add_edge("execute_tool", "dispatch")
        g.add_edge("finalize", END)
        return g

    # -- drive loop (shared by run + resume) --------------------------------
    def _cfg(self, run_id: str) -> dict:
        return {"configurable": {"thread_id": run_id}, "recursion_limit": 100}

    def _drive(self, run_id: str, result: dict) -> EvidenceBundle:
        cfg = self._cfg(run_id)
        while "__interrupt__" in result:
            snap = self._app.get_state(cfg).values
            action = CandidateAction.model_validate(snap["pending_action"])
            decision = EDENADecision.model_validate(snap["pending_decision"])
            review = self.reviewer.review(action, decision, {})
            if review is None:
                return self._persist_pause(run_id)
            result = self._app.invoke(Command(resume=review.model_dump(mode="json")), cfg)
        return EvidenceBundle.model_validate(result["bundle"])

    def _persist_pause(self, run_id: str) -> EvidenceBundle:
        snap = self._app.get_state(self._cfg(run_id)).values
        run = WorkflowRun.model_validate(snap["run"])
        builder = EvidenceBundleBuilder.from_bundle(EvidenceBundle.model_validate(snap["bundle"]))
        bundle = builder.finalize(final_action="awaiting_human_review")
        # Distinct revision per persist so the append-only store never shadows a
        # later finalize (incl. repeated pauses in a multi-step run).
        bundle.bundle_id = f"ev_{uuid.uuid4().hex[:12]}"
        self.repo.save_evidence(bundle)
        run.evidence_bundle_id = bundle.bundle_id
        run.status = WorkflowRunStatus.AWAITING_HUMAN
        self.repo.save_run(run)
        self.events.emit("workflow_run.paused", run.workflow_run_id,
                         evidence_bundle_id=bundle.bundle_id)
        return bundle

    # -- public API (mirrors Runtime.run, plus resume) ----------------------
    def run(self, workflow: WorkflowDefinition, signal: Signal,
            run_id: str | None = None) -> EvidenceBundle:
        rid = run_id or f"wfr_{uuid.uuid4().hex[:10]}"
        run = WorkflowRun(workflow_run_id=rid, workflow_id=workflow.workflow_id,
                          signal_id=signal.signal_id, status=WorkflowRunStatus.RUNNING)
        with span("florence.workflow_run", workflow_id=workflow.workflow_id,
                  signal_type=signal.signal_type, workflow_run_id=rid) as sp:
            initial: GraphState = {
                "signal": self._dump(signal),
                "steps": [self._dump(s) for s in ordered_steps(workflow)],
                "run": self._dump(run),
                "step_index": 0, "final_action": None,
            }
            result = self._app.invoke(initial, self._cfg(rid))
            bundle = self._drive(rid, result)
            set_attributes(sp, status=bundle.final_action)
            return bundle

    def resume(self, run_id: str, review: HumanReview) -> EvidenceBundle:
        """Resume a paused run with a human's decision (the durable HITL path)."""
        result = self._app.invoke(Command(resume=review.model_dump(mode="json")),
                                  self._cfg(run_id))
        return self._drive(run_id, result)
