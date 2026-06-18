# Demo walkthrough

A narrated tour of the governed loop. To **record** a screen-capture demo, use the
shot-by-shot + voiceover script: [demo-script.md](demo-script.md).

## 1. The governed run (no services)
```bash
make demo
```
Watch the CloudEvents stream: `workflow_run.started` → `context.classified`
(`phi_present=true`) → `candidate_action.created` (`draft`) → **`edena.decision`
(`require_human`, tier `yellow`)** → `human_review.requested` → (simulated)
`human_review.completed` → `tool.executed` → `evidence_bundle.persisted`.

The point: nothing executed until EDENA cleared a `CandidateAction`, and the run
produced an `EvidenceBundle`.

## 2. Refusal is a success
```bash
PYTHONPATH=… python examples/sandbox/run_sandbox.py
```
- ICU read, education templates, policy retrieval → **EXECUTED** (green) through
  the FHIR / local connectors, returning *references* (no raw PHI).
- External payer submission → **REFUSED (require_human)**.
- Production code execution → **REFUSED (deny)** → an Incident is recorded.

PHI-bearing work routes to a **local** model; non-local routes are redacted and
refused if PHI survives.

## 3. Human authority (API + console)
1. `POST /signals` (async) → `202` + `workflow_run_id`; the worker runs it and it
   pauses at `require_human`.
2. `GET /reviews` → the paused run with full context (tier, rationale, blast
   radius, reversibility, sources).
3. In the **steward console** (`npm run dev`), open the run → the approval cockpit
   shows that context and the **Approve / Edit / Escalate / Deny / Stop** controls.
4. Approve → the run resumes from its checkpoint to completion (live via
   WebSocket). Deny/Stop → the run is blocked and an Incident appears at
   `GET /incidents`.

## 4. Evidence & provenance
`GET /runs/{id}/evidence` (or the console run page) shows the EDENA decisions with
rationale, the human review, tool calls, source citations, and the
`policy_pack_version` that produced the decision.
