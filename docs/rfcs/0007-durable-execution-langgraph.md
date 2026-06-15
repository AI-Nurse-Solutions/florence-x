# RFC 0007 — Durable Execution via LangGraph

- **Status:** Accepted (P1-9 implementation; contract fixed here)
- **Date:** 2026-06-15
- **Deciders:** Technical + clinical stewards

## Context
The MVP runtime (`florence_core/workflows/runtime.py`) executes the canonical loop
as a single in-process `for` loop. It is correct and fully governed, but it is
**not durable**:

- When EDENA returns `require_human` and the reviewer is the production-shaped
  `QueueReviewer`, the loop persists an `AWAITING_HUMAN` run + partial
  `EvidenceBundle` and **returns** (`runtime.py` ~L240–246). There is no way to
  *resume from the pause point*. A later approval has nowhere to land; re-running
  the signal would re-execute the workflow from the top — re-drafting, re-calling
  EDENA, duplicating side effects.
- A process restart mid-run loses all in-flight execution state. P1-8 made the
  *queue* and *run record* restart-safe, but not the *position within a run*.

P1-9 requires durable, resumable execution: a run can pause at a human-review
interrupt, survive a restart, and resume exactly where it left off — **without
weakening any runtime invariant** (EDENA gate, fail-closed, evidence-always, PHI
boundary). CLAUDE.md names LangGraph v1.0 as the intended engine. This RFC fixes
how we adopt it.

## Decision
Adopt **LangGraph v1.0** as the durable execution engine for the canonical loop,
behind the same governance invariants.

1. **Model the loop as a `StateGraph`.** Nodes mirror today's loop stages so the
   governance shape is unchanged:
   `load_context → draft (agent) → build_candidate_action → edena_evaluate →`
   branch on the decision to `terminal_block` | `await_human` | `execute_tool`,
   then `finalize_evidence`. Multi-step workflows iterate these per step.

2. **EDENA stays a hard gate between generation and action.** `execute_tool` is
   only reachable through an edge out of `edena_evaluate` whose condition is
   "decision is allow/allow_with_constraints, or a human approved." There is no
   edge from `draft`/`build_candidate_action` directly to `execute_tool`. The
   gate is a graph-topology invariant, not a convention.

3. **Human review = a LangGraph interrupt + checkpoint.** At `require_human`/
   `escalate`, the `await_human` node calls LangGraph `interrupt(...)`, which
   checkpoints the run and suspends. The run is persisted `AWAITING_HUMAN`. A
   `HumanReview` resumes execution via `Command(resume=<review>)` on the same
   `thread_id`. The review-queue **API** that drives this (`GET /reviews`,
   `POST /reviews/{id}`) and containment for `deny`/`stop` are **Phase 2**
   (BUILD_PLAN §5); P1-9 delivers the *mechanism* and an internal resume call.

4. **`thread_id == workflow_run_id`.** The pre-allocated run id from P1-8 async
   intake is the LangGraph thread id, so the queue, the durable run record, the
   checkpoint, and the evidence bundle are all keyed the same way.

5. **Checkpointer = Postgres when configured, SQLite/in-memory otherwise**
   (`langgraph-checkpoint-postgres` / `SqliteSaver` / `MemorySaver`), mirroring
   the `make_repository()` / `make_queue()` toggle. The worker (P1-8) invokes the
   graph with the run's `thread_id`; on interrupt it returns; on resume it
   re-invokes with the same id.

6. **The checkpoint is execution state, not the compliance record.** The
   `EvidenceBundle`, the append-only event log, and the durable run row remain the
   system of record (RFC 0001, P1-11). The LangGraph checkpoint is volatile
   execution state that can be rebuilt/discarded; it never replaces evidence.

7. **PHI boundary holds in checkpoints.** Graph state carries the same
   hashes/refs that `CandidateAction` carries — never raw payloads (RFC 0006).
   The checkpoint store is inside the local boundary and contains no raw PHI.

8. **Same outward surface.** `Runtime.run(workflow, signal, run_id=...)` stays the
   entry point; internally it builds/compiles the graph and invokes it. Callers
   (orchestrator, worker, CLI) are unchanged. The reviewer collaborator protocol
   is preserved: `AutoApproveReviewer` maps to an auto-resume, `QueueReviewer`
   maps to "interrupt and wait."

## Consequences
- New dependencies: `langgraph` (+ `langgraph-checkpoint-postgres` in the `api`
  extra). Added to `pyproject.toml`, the API image, and compose.
- `runtime.py` is rewritten around `StateGraph`. The existing minimal runner is
  retained behind a config flag (`FLORENCE_RUNTIME=minimal|graph`, default `graph`
  once parity passes) so we can fall back and so tests can diff the two.
- **Evidence parity is the acceptance gate.** A new `tests/unit/` parity test
  asserts the graph runtime and the minimal runner produce equivalent
  `EvidenceBundle`s (same decisions, reviews, final_action, citations) for all 5
  MVP workflows. Safety tests (deny/stop/contain) and PHI-boundary tests must stay
  green unchanged.
- **Resumability test:** a run paused at `await_human`, then resumed after a fresh
  process/checkpointer reload, completes to the same evidence — the durability
  property P1-9 must guarantee.
- Latency: graph + checkpoint overhead must stay within the ≤2–3s point-of-care
  budget; the OTel spans from P1-10 measure per-node latency to verify this.
- The `interrupt`/resume path replaces the current "pause = return partial
  evidence and stop." Partial evidence on pause is still written (compliance), but
  the run is now genuinely *suspended*, not *ended*.

## Alternatives considered
- **Keep the minimal runner + bolt on manual resume.** Rejected: we would be
  reimplementing checkpointing, replay, and interrupt semantics that LangGraph
  provides and that CLAUDE.md already commits to.
- **Temporal / durable-task external workflow engine.** Powerful, but adds a
  heavyweight external server and a second programming model; overkill for the
  local-first MVP and harder to keep inside the PHI boundary.
- **Celery + hand-rolled state machine.** Celery covers task transport (already
  served by the P1-8 queue) but not graph checkpointing/HITL interrupts; we would
  still hand-roll the durable state machine.
- **Put EDENA evaluation inside a node with no topological gate.** Rejected: the
  gate must be a structural property of the graph, not a line of code a future
  node could skip (CLAUDE.md rule 1, no fast-paths).

## Open questions (resolve during implementation)
- Postgres checkpointer schema vs. our Alembic-owned schema: keep LangGraph's
  checkpoint tables separate (its own migrations) from `db/models.py`.
- Exact `interrupt()` payload shape (what blast-radius/evidence context is handed
  to the reviewer) — coordinate with the Phase 3 steward console contract.
- Reconcile CLAUDE.md ("LangGraph adopted in Phase 2") with BUILD_PLAN P1-9
  (Phase 1): the **engine swap + interrupt mechanism** lands in P1-9; the
  **human-facing review-queue API + containment** lands in Phase 2. Update
  CLAUDE.md's stack note accordingly when this RFC is accepted.
