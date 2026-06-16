# Florence-X — Architecture Code Plan (Claude Code Handoff)

**Version:** 0.1 · **Date:** 2026-06-15 · **Target:** Claude Code

> *Florence-X orchestrates. EDENA gates. Humans decide. Nurses steward.*

This is the **executable build plan**. It assumes the repository you are looking at
— a working Phase 0 + partial Phase 1 scaffold — and tells you exactly what to build
next, in what order, with acceptance criteria and test gates. Read `CLAUDE.md` first
(non-negotiable rules), then this file, then `docs/architecture.md`.

---

## 0. How to use this document

1. Start from **"Current state"** below — much of Phase 0 and the Phase 1 core are
   already implemented and tested. **Do not rebuild them.**
2. Work the **task tables** top to bottom. Each task has an ID, a concrete
   deliverable, file paths, and acceptance criteria.
3. A phase is "done" only when its **Definition of Done** gate passes (tests green).
4. Any new architectural decision → write an RFC in `docs/rfcs/` (template: `0001`).
5. Never bypass the runtime invariants in `CLAUDE.md` (EDENA gate, PHI boundary,
   evidence, fail-closed). PRs that add a fast-path around EDENA are rejected.

## 1. Current state (what already exists and passes tests)

| Area | Status | Where |
|---|---|---|
| Repo scaffold (packages/apps/docs/policies/examples/tests/docker) | ✅ done | tree |
| Core object model (Pydantic v2, all 15 objects + enums) | ✅ done | `packages/florence-core/florence_core/schemas/` |
| JSON Schema artifacts (CandidateAction, EDENADecision) | ✅ done | `schemas/` |
| EDENA client (fail-closed) + risk features + LocalRuleBackend + OpaBackend (CLI) + OpaHttpBackend + config toggle | ✅ done | `packages/florence-edena/` |
| EDENA OpenAPI contract | ✅ done | `packages/florence-edena/edena-openapi.yaml` |
| Rego policy packs (green/yellow/orange/red/blocked + 4 examples) | ✅ done | `policies/` |
| Canonical runtime loop (Signal→…→EvidenceBundle) | ✅ done | `florence_core/workflows/runtime.py` |
| Append-only CloudEvents log (JSONL sink + Postgres `events` sink when DB set) | ✅ done | `florence_core/events/`, `apps/api/app/db/event_sink.py` |
| OpenTelemetry tracing (run/step/EDENA/tool spans; graceful no-op; OTLP export) | ✅ done | `florence_core/observability/`, `apps/api/app/telemetry.py` |
| In-memory repository (Repository protocol) | ✅ done | `florence_core/state/` |
| Evidence bundle builder | ✅ done | `florence_core/evidence/` |
| Dispatcher (signal_type → workflow) | ✅ done | `florence_core/dispatcher/` |
| 5 MVP workflows + ICU agent + synthetic FHIR | ✅ done | `examples/` |
| FastAPI app: `/signals`, `/runs`, `/edena/evaluate-action`, Zero Trust mw | ✅ done | `apps/api/app/` |
| CLI (`florence run …`) | ✅ done | `packages/florence-cli/` |
| Tests: unit / safety / policy / phi_boundary / integration (81 pass w/ opa+otel+langgraph; Postgres+Redis legs gated/skip when deps absent) | ✅ done | `tests/` |
| Canonical runtime loop — minimal step runner **and** durable LangGraph runtime (`FLORENCE_RUNTIME` toggle, evidence parity) | ✅ done | `workflows/runtime.py`, `workflows/graph_runtime.py` |
| Async signal intake: 202 enqueue + worker drain (Redis or in-process), pre-allocated pollable run | ✅ done (P1-8) | `apps/api/app/queue/`, `apps/api/app/worker.py` |
| Example agents for all 5 MVP workflows + agent_id-resolution test | ✅ done (P0-8) | `examples/*/agent.yaml`, `tests/unit/test_example_definitions_load.py` |
| OPA parity green + native Rego decision-ladder tests (`opa test policies` = 8/8) | ✅ done (P0-9) | `policies/edena/decision_test.rego`; `make opa-install` |
| PostgresRepository (SQLAlchemy 2.0) behind `Repository`; restart-safe + parity | ✅ done (P1-6) | `apps/api/app/db/repository.py`, `tests/integration/test_postgres_repo.py` |
| Alembic migrations (all 7 tables); `alembic upgrade head` in Dockerfile.api | ✅ done (P1-7) | `apps/api/alembic/`, `tests/integration/test_alembic_migration.py` |
| SQLAlchemy models (Postgres schema of record) — now wired + `human_reviews` + run `payload` added | ✅ wired | `apps/api/app/db/models.py` |
| Docs: architecture, EDENA, PHI, safety, threat, memory, zero-trust, CDS Hooks, deploy + 7 RFCs (0007 = durable execution) | ✅ done | `docs/` |
| docker-compose (postgres/redis/opa/api) + Dockerfile | ✅ done | `docker/` |

**Verified end-to-end:** `make demo` runs the ICU handoff (Signal → context →
draft → EDENA `require_human`/yellow → approval → tool exec → EvidenceBundle).
EDENA fail-closed, deny, and tier ladder all covered by tests.

## 2. Operating rules (summary — full list in `CLAUDE.md`)

1. No action executes without an `EDENADecision`. 2. EDENA fails closed.
3. PHI stays local; pass hashes/refs, not content. 4. Agents are registered labor.
5. Every run yields an `EvidenceBundle`. 6. Human review is meaningful.
7. Memory needs class + provenance + expiry; no raw PHI. 8. Tools are deny-by-default.
9. Refusal/containment are successes. 10. Open standards over lock-in.

---

## 3. Phase 0 — Doctrine to Specification (Days 1–10)

**Goal:** every core object, contract, policy, and the scaffold exist and validate.
**Status: essentially COMPLETE in this scaffold.** Remaining items are polish.

| ID | Task | Status | Acceptance |
|---|---|---|---|
| P0-1 | Pydantic schemas for all core objects + enums | ✅ | `python -c "import florence_core.schemas"` OK; `extra=forbid` |
| P0-2 | `CandidateAction` + `EDENADecision` (Phase 0 priority) | ✅ | Round-trip validate; JSON Schemas generated in `schemas/` |
| P0-3 | EDENA `/evaluate-action` OpenAPI contract | ✅ | `edena-openapi.yaml` parses; matches models |
| P0-4 | 5 workflow YAML defs + ICU agent def | ✅ | All load via `load_workflow`/`load_agent` |
| P0-5 | Rego packs (5 tiers) + 4 example policies | ✅ | Files present; ladder mirrored in `LocalRuleBackend` |
| P0-6 | Repo scaffold + `CLAUDE.md` + governance files | ✅ | Tree matches `docs/architecture.md` repo map |
| P0-7 | Threat model + PHI boundary + safety + RFCs | ✅ | `docs/threat-model.md`, `docs/phi-boundary-model.md`, `docs/rfcs/0001–0006` |
| **P0-8** | agent defs for the other 4 workflows (patient_education, policy_retrieval, code_safety_reviewer, prior_auth) | ✅ done | Each `examples/*/agent.yaml` validates; `agent_id`s resolve (`tests/unit/test_example_definitions_load.py`) |
| **P0-9** | `opa test policies` green (install OPA; fix any Rego that diverges from `LocalRuleBackend`) | ✅ done | OPA parity leg of `tests/policy/test_parity.py` un-skips; `opa test policies` = 8/8 (`policies/edena/decision_test.rego`) |

**Phase 0 Definition of Done:** `make test` green; `schemas/*.json` generated;
all example workflows + agents load; `opa test policies` green (P0-9). ✅ **MET** —
install a repo-local OPA with `make opa-install` (CI uses `open-policy-agent/setup-opa`).

---

## 4. Phase 1 — Local Runtime Skeleton (Days 11–25)

**Goal:** durable `Signal → WorkflowRun → CandidateAction → EDENADecision` path with
persistence, queueing, observability, and a CLI. **Core loop is COMPLETE; the
durability/observability layers remain.**

| ID | Task | Status | Files | Acceptance |
|---|---|---|---|---|
| P1-1 | Canonical runtime loop | ✅ | `workflows/runtime.py` | `tests/unit/test_runtime_loop.py` green |
| P1-2 | Append-only event log (CloudEvents) | ✅ | `events/cloudevents.py` | JSONL emitted; 11 events for ICU demo |
| P1-3 | In-memory repository | ✅ | `state/repository.py` | Run + evidence retrievable |
| P1-4 | FastAPI: signals/runs/edena + Zero Trust | ✅ | `apps/api/app/` | TestClient: 401 w/o identity; signal→evidence 200 |
| P1-5 | CLI `florence run` (auto/queue reviewers) | ✅ | `florence-cli/main.py` | Demo prints decision + evidence; writes artifacts |
| **P1-6** | **PostgresRepository** implementing `Repository` (SQLAlchemy 2.0); swap in when `FLORENCE_DATABASE_URL` set | ✅ done | `apps/api/app/db/repository.py`, `db/__init__.py` (`make_repository`), orchestrator wired | Run survives restart + in-memory parity (`tests/integration/test_postgres_repo.py`) |
| **P1-7** | **Alembic** migrations for `db/models.py`; `alembic upgrade head` in compose | ✅ done | `apps/api/alembic/` + `alembic.ini`; Dockerfile.api runs `upgrade head` | Fresh DB migrates clean + matches models (`tests/integration/test_alembic_migration.py`) |
| **P1-8** | **Redis task queue** for async signal intake + durable run state (`/signals` enqueues; worker drains) | ✅ done | `apps/api/app/queue/`, `app/worker.py`; compose `worker` service | `/signals` → 202 + pollable run; worker drains to evidence; reliable reserve/ack/recover (`tests/integration/test_signal_queue.py`, `test_api_signals.py`) |
| **P1-9** | **Durable execution** via LangGraph v1.0 (replace the minimal step runner; keep the same invariants + interrupts) | ✅ done (RFC `docs/rfcs/0007`) | `workflows/graph_runtime.py`; `apps/api/app/checkpoint.py`; orchestrator `FLORENCE_RUNTIME` toggle | Evidence parity vs minimal runner across 5 workflows; pause→resume from a fresh runtime on the same checkpoint (`tests/unit/test_graph_parity.py`, `tests/integration/test_graph_resume.py`) |
| **P1-10** | **OpenTelemetry** traces across loop, EDENA call, tool exec | ✅ done | `florence_core/observability/`, `apps/api/app/telemetry.py` | Spans (run/step/edena/tool) export via OTLP; per-step latency recorded (`tests/unit/test_tracing.py`) |
| **P1-11** | **Persist events + evidence to Postgres** (append-only tables) in addition to JSONL | ✅ done | `apps/api/app/db/event_sink.py`, `db/__init__.py` (`make_event_sinks`), orchestrator wired | `events`/`evidence_bundles` rows written + append-only (`tests/integration/test_event_persistence.py`) |
| **P1-12** | **Wire OPA backend** behind `EDENA_BASE_URL`/config so prod uses OPA, MVP uses LocalRule | ✅ done | `florence-edena` `OpaHttpBackend` + `make_backend`; orchestrator wired | Config toggles backend; HTTP parity vs LocalRule + fail-closed (`tests/policy/test_opa_http.py`) |

### P1-6 PostgresRepository — concrete guidance
- Implement the existing `Repository` Protocol (`florence_core/state/repository.py`)
  against `apps/api/app/db/models.py` using `SessionLocal`.
- Serialize Pydantic objects to the `payload` JSON columns; keep typed columns for
  query/index fields (status, signal_type, decision, risk_tier).
- Append-only for `events` + `evidence_bundles` (insert new rows; never update).
- Add `tests/integration/test_postgres_repo.py`: same assertions as the in-memory
  repo plus a "survives a new `OrchestratorService`" restart test (use a test DB or
  testcontainers).

### Phase 1 Definition of Done — ✅ MET (P0-8/9, P1-6→12 complete)
- `make up` brings up postgres + redis + opa + api **+ worker**; `/healthz` OK.
- Submitting a signal via API runs the workflow, persists run + evidence to
  Postgres, emits OTel spans, and (queue mode) survives an API restart; durable
  LangGraph runtime resumes a paused run from its checkpoint after restart.
- `tests/` green (81 pass w/ opa+otel+langgraph) including `tests/integration/`
  Postgres, event-persistence, queue, graph-resume tests.
- `EDENA_BASE_URL=http://opa:8181` routes decisions through OPA with parity intact.

**Remaining before this gate is fully exercised in CI/compose** (code complete,
needs an environment with the services): boot `make up` and hit the live API +
worker against real Postgres/Redis/OPA; add the Postgres LangGraph checkpointer to
the API service env for cross-process durable resume. Next: **Phase 2** — the
human review-queue API (`GET /reviews`, `POST /reviews/{id}` → `orchestrator.resume`),
`PolicyPack`/`HumanReview`/`Incident` persistence, and the containment path.

---

## 5. Phase 2 — EDENA Gate + Policy Packs (Days 26–40)

**Goal:** production-shaped governance + meaningful human interrupt + evidence.

Deliverables: harden the OPA adapter as the default in compose; expand Rego packs
to cover all 5 MVP workflows with workflow-specific overlays (`policies/examples/`);
implement the **human review interrupt** as a LangGraph checkpoint that persists an
`AWAITING_HUMAN` run and resumes on a `HumanReview`; `PolicyPack` versioning +
`HumanReview` + `Incident` persistence; containment path for `contain`/`stop`.

**Status: ✅ COMPLETE.**
- ✅ Human review interrupt + resume — LangGraph checkpoint (P1-9 / RFC 0007).
- ✅ Review-queue API: `GET /reviews`, `GET /reviews/{id}`, `POST /reviews/{id}` →
  `orchestrator.submit_review` → resume; `GET /incidents`; `GET /policy-packs`.
  Anti-rubber-stamp `ReviewItem` context (tier, rationale, reversibility, blast
  radius, sources). `apps/api/app/routes/reviews.py`, `app/review.py`.
- ✅ `Incident` persistence on `deny`/`stop`/`contain` (EDENA terminal block + human
  deny/stop), both runtimes; `IncidentRow` + Alembic `0002`; repo `list_runs`/
  `get_action`/`save_incident`/`list_incidents`.
- ✅ Containment ladder: `deny`/`stop`/`contain` block (+ incident; contain records
  containment actions), `escalate` pauses for a human, `throttle` proceeds.
  `tests/safety/test_containment.py` (both runtimes).
- ✅ Rego overlays for all 5 MVP workflows (`policies/examples/*_policy.rego`) +
  `opa test policies` = 18/18 (8 tier + 10 overlay; `overlays_test.rego`).
- ✅ `PolicyPack` versioning/persistence (`PolicyPackRow` + Alembic `0003`; seeded at
  orchestrator init, stamped on decisions, exposed at `GET /policy-packs`).
- ✅ OPA hardened as the compose default (`EDENA_BASE_URL=http://opa:8181` for api+worker).

Acceptance: a Yellow+ action pauses the run, appears in a review queue API
(`GET /reviews`), and resumes to completion on `POST /reviews/{id}` with an approval ✅;
`deny`/`stop` create an `Incident` ✅; `opa test policies` covers every tier + overlay
(18/18) ✅; `tests/safety/` extended for contain/stop/escalate ✅. **MET** (95 pass /
2 skipped). Live-services exercise of the review API + OPA-server path needs `make up`.

## 6. Phase 3 — Steward Console (Days 41–55)

**Goal:** the human authority interface (Next.js 15 / React; `apps/steward-console`).

Deliverables: review queue with EDENA tier color-coding; evidence viewer with source
citations; EDENA decision inspector (full rationale); workflow run timeline (from the
event log); agent + tool registry editors with NAIO approval status; approval cockpit
showing **blast radius + reversibility + source evidence**; real-time WebSocket
updates from the CloudEvents stream.

**Status: ✅ COMPLETE (verified by build/typecheck; live e2e needs `make up`).**
- ✅ Backend (3A): `GET /events/ws` live CloudEvents stream (in-process hub +
  BroadcastSink, Zero-Trust identity check) + read-only registry endpoints
  `GET /agents`/`GET /tools`. Cross-process (worker→console) live updates need a
  Redis pub/sub relay — deferred until testable. Tested in
  `tests/integration/test_api_events_registry.py`.
- ✅ Console (`apps/steward-console`, Next.js 15 / React 19 / Tailwind v4):
  review queue with tier color-coding + live refresh (`/`); approval cockpit with
  the anti-rubber-stamp context + Approve/Edit/Escalate/Deny/Stop → `POST /reviews/{id}`
  (`/reviews/[id]`); evidence viewer + EDENA decision inspector + timeline + live
  feed (`/runs/[id]`); incidents (`/incidents`); read-only agent/tool registry
  viewers with NAIO approval status (`/registry`).
- ⬜ Deferred (per approval): registry **editing/persistence** → later RFC.

Acceptance: a reviewer can Approve / Edit / Escalate / Deny / Stop a paused run and
see it resume ✅ (cockpit → review API → durable resume); the review screen shows all
required context (anti-rubber-stamp checklist) ✅; WebSocket reflects live run state ✅.
Verified by `next build` + `tsc` (frontend) and the Python review/WS tests (backend);
the live browser click-through requires `make up` + `npm run dev` (not run headlessly).

## 7. Phase 4 — Healthcare Sandbox (Days 56–75)

**Goal:** all 5 MVP workflows runnable on synthetic FHIR via real connectors.

Deliverables: FHIR R4 connector (read-only) + SMART on FHIR launch + CDS Hooks
service; MCP gateway fronting tools; expand synthetic FHIR fixtures; ICU handoff,
patient education, prior auth, policy retrieval, and agentic software review demos —
**local model route only, no real PHI**; model router with Ollama adapter + redaction
pipeline; latency budget instrumentation (≤2–3s point-of-care).

**Status: ✅ COMPLETE (verified by tests; live Ollama model + real EHR/SMART need a server).**
- ✅ 4A ToolGateway (RFC 0004): every tool invocation is a CandidateAction → EDENA,
  executes only on allow, deny-by-default for unregistered tools. FHIR connector
  expanded (+ AllergyIntolerance/Procedure fixtures). `florence_connectors/gateway.py`.
- ✅ 4B Redaction (HMAC-SHA256 tokenization) + Ollama adapter (local, mock-tested) +
  `prepare_prompt` PHI boundary (non-local sends redacted + refused if PHI survives).
- ✅ 4C CDS Hooks (`/cds-services`) — hook → governed Signal → CDS cards; SMART launch
  context (`/smart/launch`).
- ✅ 4D 5 workflow demos through gateway + connectors (FHIR/local/A2A), local route
  only, no PHI: reads execute, external submit + prod code-exec refused. A2A handoffs
  are CandidateActions. `examples/sandbox/run_sandbox.py`, `tests/integration/test_sandbox_demos.py`.
- ✅ 4E Latency budget (`LatencyBudget`, ≤2–3s point-of-care) + test.

Acceptance: each demo runs through the gateway + connectors with EDENA gating ✅;
PHI never leaves local (`tests/phi_boundary/` extended; connectors return refs only,
PHI work routes local) ✅; A2A handoffs are CandidateActions ✅. **MET** — 122 pass /
2 skipped, opa 18/18. The live Ollama call + a real EHR SMART/CDS handshake are
mock/fixture-verified here (need a model server + EHR sandbox).

## 8. Phase 5 — Open-Source Launch (Days 76–90)

Deliverables: public GitHub repo; docs site; install guide; demo video; issue/PR
templates (`.github/`); safety disclaimers; first-contributor roadmap; RFC process
live; CI (lint + tests + `opa test` + schema generation check); SBOM.

**Status: ✅ COMPLETE (launch-ready; repo stays PRIVATE until you flip it).**
- ✅ Issue/PR templates: feature-request + `ISSUE_TEMPLATE/config.yml` (security →
  private advisory, safety → CLINICAL_SAFETY, questions → discussions).
- ✅ Install guide (`docs/install.md`) + DEMO walkthrough (`docs/DEMO.md`, text
  storyboard standing in for a recorded video) + README launch polish.
- ✅ First-contributor roadmap (`docs/ROADMAP.md`) + RFC process (`docs/rfcs/README.md`).
- ✅ CI hardened: `test` (ruff + pytest + schema-drift) · `opa` · **`console`**
  (next build) · **`sbom`** (CycloneDX artifact via `make sbom`). Packaging fix
  (build-system + `py-modules=[]`) makes `pip install .` / clean-clone work.
- ✅ Docs site: mkdocs-material (`mkdocs.yml`) + Pages workflow (`.github/workflows/docs.yml`,
  build-strict gate now; deploy dormant until `ENABLE_PAGES=true`).
- ⬜ **Public flip + demo video deferred** to you (repo intentionally private;
  private-repo Pages needs a paid plan). `gh repo edit --visibility public` when ready.

Acceptance: clean clone → `make install && make demo && make test` works ✅
(packaging fixed; CI green on PRs); CONTRIBUTING + GOVERNANCE + SECURITY +
CLINICAL_SAFETY in place ✅. **MET** except the (deliberately deferred) public flip.

---

## 9. Verification & CI (add in Phase 1/5)

`.github/workflows/ci.yml` should run:
1. `ruff check .` and `mypy` (type gate).
2. `pytest` with the path config in `pyproject.toml` (unit/safety/policy/phi_boundary).
3. `opa test policies` (install OPA in CI) — un-skips the parity tests.
4. **Schema drift check:** regenerate `schemas/*.json` and `git diff --exit-code`.
5. **PHI scan:** `tests/phi_boundary/` must pass; add a grep gate for obvious raw-PHI
   patterns in logs/fixtures.
6. Build the API image; boot compose; hit `/healthz`.

## 10. Definition of Done — per phase (gate summary)

- **P0:** schemas import; OpenAPI parses; all workflows/agents load; `opa test` green.
- **P1:** compose up; signal→persisted evidence in Postgres; OTel spans; restart-safe
  (queue + LangGraph); OPA backend toggle; integration tests green.
- **P2:** human interrupt pause/resume; review queue API; containment incidents; full Rego coverage.
- **P3:** steward console approve/edit/deny/escalate/stop; anti-rubber-stamp context; live WS.
- **P4:** 5 demos via FHIR/SMART/CDS Hooks/MCP, local model, no real PHI.
- **P5:** clean-clone bootstrap; CI green; launch docs + templates.

---

## 11. Paste-ready kickoff prompt for Claude Code

> Copy everything in the block below into Claude Code, run from the `florence-x/` repo root.

```
You are continuing Florence-X, an open-source, local-first, governance-first AI
orchestration control plane for high-trust clinical environments. Doctrine:
"Florence-X orchestrates. EDENA gates. Humans decide. Nurses steward."

FIRST: read CLAUDE.md (non-negotiable rules), BUILD_PLAN.md (the plan + current
state), and docs/architecture.md. Then run `make install && make demo && make test`
to confirm the baseline is green before changing anything.

Phase 0 and the Phase 1 core loop are already implemented and tested. Your job is to
complete Phase 1 in this order, opening a focused PR per task with tests:

  P0-8  Add agent.yaml for patient_education, policy_retrieval, agentic_software_review,
        and prior_authorization; ensure agent_ids match the workflows.
  P0-9  Install OPA; make `opa test policies` and the OPA parity leg of
        tests/policy/test_parity.py pass (fix any Rego that diverges from
        florence_edena LocalRuleBackend — the Python backend is the source of truth).
  P1-6  Implement PostgresRepository (SQLAlchemy 2.0) against apps/api/app/db/models.py,
        behind the existing Repository protocol; default to in-memory when
        FLORENCE_DATABASE_URL is empty. Add tests/integration/test_postgres_repo.py.
  P1-7  Add Alembic migrations for db/models.py; run them in docker-compose.
  P1-8  Add a Redis-backed task queue: POST /signals enqueues (202) and a worker
        drains it; runs are restart-safe.
  P1-9  Replace the minimal step runner in workflows/runtime.py with LangGraph v1.0
        durable execution, PRESERVING every invariant (EDENA gate, fail-closed,
        evidence-always, PHI boundary) and turning the human interrupt into a
        LangGraph checkpoint.
  P1-10 Add OpenTelemetry tracing across the loop, the EDENA call, and tool execution.
  P1-11 Persist events + evidence to append-only Postgres tables.
  P1-12 Wire OpaBackend behind config (EDENA_BASE_URL) so prod uses OPA, MVP uses
        LocalRuleBackend.

HARD RULES (never violate):
  - No action path may bypass CandidateAction -> EDENADecision. No fast-paths.
  - EDENA fails closed: deny irreversible/external, else require_human. Never allow.
  - PHI never leaves local; objects carry hashes/refs, never raw content.
  - Every workflow run produces an EvidenceBundle.
  - New architectural decisions require an RFC in docs/rfcs/ (template: 0001).

After each task: run `make test` (and `opa test policies`), keep tests green, and
update BUILD_PLAN.md's "Current state" table. When Phase 1's Definition of Done
passes, stop and summarize what remains for Phase 2.
```
