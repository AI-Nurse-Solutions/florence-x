"""Wires the dispatcher + runtime + loaded example workflows for the API."""
from __future__ import annotations

import glob
import uuid
from functools import lru_cache
from pathlib import Path

from florence_core.dispatcher import Dispatcher
from florence_core.events import EventLog, JsonlSink
from florence_core.schemas import (
    AgentDefinition,
    EvidenceBundle,
    HumanReview,
    Incident,
    PolicyPack,
    Signal,
    WorkflowRun,
)
from florence_core.schemas.enums import WorkflowRunStatus
from florence_core.workflows import (
    AutoApproveReviewer,
    QueueReviewer,
    Runtime,
    load_agent,
    load_workflow,
)
from florence_edena import EdenaClient, EdenaConfig

from ..checkpoint import make_checkpointer
from ..config import settings
from ..db import make_event_sinks, make_repository
from ..events_stream import BroadcastSink
from ..queue import SignalAccepted, SignalTask, make_queue
from ..review import ReviewDecisionRequest, ReviewItem


class OrchestratorService:
    def __init__(self) -> None:
        # Durable Postgres repo when FLORENCE_DATABASE_URL is set; else in-memory.
        self.repo = make_repository()
        # Redis-backed intake queue when FLORENCE_REDIS_URL is set; else in-process.
        self.queue = make_queue()
        self.dispatcher = Dispatcher()
        self.agents = {}
        self._load_examples(Path(settings.examples_dir))
        # Always emit to append-only JSONL; also to the Postgres events table when
        # a DB is configured (P1-11).
        self.events = EventLog(JsonlSink(settings.event_log_path), *make_event_sinks(),
                               BroadcastSink())
        # EDENA backend: OPA server when EDENA_BASE_URL is set, else LocalRuleBackend (P1-12).
        self._edena = EdenaClient(EdenaConfig(base_url=settings.edena_base_url or None))
        # Execution engine (P1-9): durable LangGraph runtime, or the minimal runner.
        # A single shared checkpointer makes paused runs resumable (incl. across a
        # restart with a durable checkpoint store).
        self.runtime_kind = settings.runtime
        self._checkpointer = make_checkpointer() if self.runtime_kind == "graph" else None
        self._register_policy_pack()

    def _register_policy_pack(self) -> None:
        """Record provenance of the live EDENA policy pack (versioning, Phase 2).

        The version matches what EdenaClient stamps on every EDENADecision, so an
        evidence bundle can be traced to the exact rules that produced it.
        """
        self.repo.save_policy_pack(PolicyPack(
            pack_id="edena-policies-0.1.0",
            name="EDENA MVP policy pack",
            version="edena-policies-0.1.0",
            tiers_covered=["green", "yellow", "orange", "red", "red_blocked"],
            rego_module_refs=[
                "policies/edena/decision.rego",
                "policies/edena/green.rego", "policies/edena/yellow.rego",
                "policies/edena/orange.rego", "policies/edena/red.rego",
                "policies/edena/blocked.rego",
                "policies/examples/icu_handoff_policy.rego",
                "policies/examples/patient_education_policy.rego",
                "policies/examples/policy_retrieval_policy.rego",
                "policies/examples/code_execution_policy.rego",
                "policies/examples/prior_auth_policy.rego",
            ],
            institutional_approval_ref="NAIO-POLICY-2026-001",
        ))

    def policy_packs(self) -> list[PolicyPack]:
        return self.repo.list_policy_packs()

    # -- registry viewers (read-only; write/persistence deferred to a later RFC) --
    def list_agents(self) -> list[AgentDefinition]:
        return list(self.agents.values())

    def list_tools(self) -> list[dict]:
        """Authorization view: each tool the registered agents may use, and which
        agents are scoped to it. (No standalone tool registry is persisted yet.)"""
        by_tool: dict[str, list[str]] = {}
        for agent in self.agents.values():
            for tool_id in agent.allowed_tools:
                by_tool.setdefault(tool_id, []).append(agent.agent_id)
        return [{"tool_id": t, "authorized_agents": sorted(a)} for t, a in sorted(by_tool.items())]

    def _load_examples(self, examples_dir: Path) -> None:
        if not examples_dir.exists():
            return
        for wf_path in glob.glob(str(examples_dir / "**" / "workflow.yaml"), recursive=True):
            try:
                self.dispatcher.register(load_workflow(wf_path))
            except Exception:  # noqa: BLE001 - skip malformed examples at boot
                continue
        for ag_path in glob.glob(str(examples_dir / "**" / "agent.yaml"), recursive=True):
            try:
                a = load_agent(ag_path)
                self.agents[a.agent_id] = a
            except Exception:  # noqa: BLE001
                continue

    def submit(self, signal: Signal, auto_approve: bool = False) -> EvidenceBundle:
        """Run the workflow synchronously and return the EvidenceBundle (sync path)."""
        workflow = self._select(signal)
        return self._runtime_for(auto_approve).run(workflow, signal)

    def enqueue(self, signal: Signal, auto_approve: bool = False) -> SignalAccepted:
        """Accept a signal for async processing (P1-8).

        Validates a workflow exists, pre-allocates a pollable run in PENDING, then
        enqueues the task. The worker picks it up and runs it with that run_id.
        """
        self._select(signal)  # 404 early if no workflow handles this signal_type
        run_id = f"wfr_{uuid.uuid4().hex[:10]}"
        self.repo.save_signal(signal)
        self.repo.save_run(WorkflowRun(
            workflow_run_id=run_id,
            workflow_id=self.dispatcher.select(signal).workflow_id,
            signal_id=signal.signal_id,
            status=WorkflowRunStatus.PENDING,
        ))
        self.queue.enqueue(SignalTask(
            signal=signal, workflow_run_id=run_id, auto_approve=auto_approve))
        return SignalAccepted(workflow_run_id=run_id, signal_id=signal.signal_id)

    def run_queued(self, task: SignalTask) -> EvidenceBundle:
        """Run a dequeued task against its pre-allocated run_id (worker path)."""
        workflow = self._select(task.signal)
        return self._runtime_for(task.auto_approve).run(
            workflow, task.signal, run_id=task.workflow_run_id)

    def resume(self, run_id: str, review: HumanReview) -> EvidenceBundle:
        """Resume a paused run with a human's decision (durable HITL, P1-9).

        Requires the graph runtime; the minimal runner cannot resume mid-run.
        """
        if self.runtime_kind != "graph":
            raise RuntimeError("resume requires FLORENCE_RUNTIME=graph")
        return self._graph_runtime(QueueReviewer()).resume(run_id, review)

    # -- review queue (Phase 2) --------------------------------------------
    def list_reviews(self) -> list[ReviewItem]:
        """All runs awaiting a human decision, with anti-rubber-stamp context."""
        return [self._review_item(r)
                for r in self.repo.list_runs(status=WorkflowRunStatus.AWAITING_HUMAN.value)]

    def get_review(self, run_id: str) -> ReviewItem:
        run = self.repo.get_run(run_id)
        if run is None or run.status != WorkflowRunStatus.AWAITING_HUMAN.value:
            raise KeyError(f"No pending review for run {run_id!r}")
        return self._review_item(run)

    def submit_review(self, run_id: str, req: ReviewDecisionRequest) -> EvidenceBundle:
        """Apply a human decision to a paused run and resume it. deny/stop block the
        run and record an Incident (handled inside the durable runtime)."""
        item = self.get_review(run_id)  # validates the run is awaiting a human
        review = HumanReview(
            review_id=f"hr_{uuid.uuid4().hex[:10]}",
            action_id=item.action_id,
            decision_id=item.decision_id,
            reviewer_role=req.reviewer_role or item.required_human_role or "rn",
            reviewer_ref=req.reviewer_ref,
            outcome=req.outcome,
            note=req.note,
            edited_payload_hash=req.edited_payload_hash,
        )
        return self.resume(run_id, review)

    def incidents(self) -> list[Incident]:
        return self.repo.list_incidents()

    def _review_item(self, run: WorkflowRun) -> ReviewItem:
        bundle = self.repo.get_evidence(run.evidence_bundle_id) if run.evidence_bundle_id else None
        decision = bundle.edena_decisions[-1] if (bundle and bundle.edena_decisions) else None
        action = self.repo.get_action(decision.action_id) if decision else None
        return ReviewItem(
            workflow_run_id=run.workflow_run_id,
            workflow_id=run.workflow_id,
            status=run.status,
            action_id=action.action_id if action else (decision.action_id if decision else None),
            action_type=action.action_type if action else None,
            intended_target=action.intended_target if action else None,
            data_classification=action.data_classification if action else None,
            reversible=action.reversible if action else None,
            external_boundary_crossed=action.external_boundary_crossed if action else None,
            blast_radius_estimate=action.blast_radius_estimate if action else None,
            decision_id=decision.decision_id if decision else None,
            decision=decision.decision if decision else None,
            risk_tier=decision.risk_tier if decision else None,
            required_human_role=decision.required_human_role if decision else None,
            rationale=decision.rationale if decision else None,
            constraints=decision.constraints if decision else [],
            evidence_bundle_id=run.evidence_bundle_id,
            source_citations=bundle.source_citations if bundle else [],
        )

    # -- helpers ------------------------------------------------------------
    def _select(self, signal: Signal):
        workflow = self.dispatcher.select(signal)
        if workflow is None:
            raise KeyError(f"No workflow registered for signal_type={signal.signal_type!r}")
        return workflow

    def _runtime_for(self, auto_approve: bool):
        reviewer = AutoApproveReviewer() if auto_approve else QueueReviewer()
        if self.runtime_kind == "graph":
            return self._graph_runtime(reviewer)
        return Runtime(self._edena, repo=self.repo, events=self.events,
                       agents=self.agents, reviewer=reviewer)

    def _graph_runtime(self, reviewer):
        # Imported lazily so florence_core stays usable without LangGraph when the
        # minimal runner is selected. All instances share self._checkpointer, so a
        # run paused by one is resumable by another (the durable state lives there).
        from florence_core.workflows.graph_runtime import GraphRuntime

        return GraphRuntime(self._edena, repo=self.repo, events=self.events,
                            agents=self.agents, reviewer=reviewer,
                            checkpointer=self._checkpointer)


@lru_cache(maxsize=1)
def get_orchestrator() -> OrchestratorService:
    return OrchestratorService()
