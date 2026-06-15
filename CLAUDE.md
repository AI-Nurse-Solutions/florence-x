# Florence-X — CLAUDE.md

> Session constitution for Claude Code. Keep this file short and stable. It is a
> router, not an encyclopedia. Detailed material lives in `docs/` and `BUILD_PLAN.md`.

## Project Constitution
Florence-X is an open-source, **local-first, governance-first** AI orchestration
control plane for high-trust clinical environments.

**Canonical doctrine:** *Florence-X orchestrates. EDENA gates. Humans decide. Nurses steward.*

Florence-X is **not** another agent framework. It is a *governed orchestration
substrate*: it routes work through agents, tools, models, memory, and humans, and
calls **EDENA** (a separate governance service) before any consequential action.

## Three planes (never collapse them)
- **Florence-X** — orchestration plane ("how should this work move?")
- **EDENA** — governance plane ("should this action be allowed/reviewed/blocked?")
- **NAIO** — institutional oversight plane ("which AI systems are approved?")
- **Nurse / clinician** — stewardship authority (approves, edits, escalates, denies)

## Where to look (progressive disclosure)
- `BUILD_PLAN.md` — the phased build plan + acceptance gates (**read this to know what to build next**)
- `docs/architecture.md` — the 9-layer reference architecture
- `docs/edena-integration.md` — EDENA API contract + policy model
- `docs/phi-boundary-model.md` — PHI classification + data-boundary rules
- `docs/safety-model.md` — human oversight + containment
- `docs/threat-model.md` — OWASP ASI 2026 + MITRE ATLAS
- `docs/rfcs/` — architectural decisions (new decisions require an RFC)

## Tech stack
- Python 3.12+, FastAPI, Pydantic v2
- PostgreSQL 16+ (durable state), Redis 7+ (queues/locks) — MVP defaults to in-memory
- LangGraph v1.0 (durable workflow execution — engine + HITL-interrupt mechanism land in P1-9 per RFC 0007; the review-queue API + containment follow in Phase 2. A minimal runner remains behind `FLORENCE_RUNTIME=minimal`.)
- OPA / Rego (EDENA policy engine; a pure-Python `LocalRuleBackend` mirrors it for the MVP)
- OpenTelemetry (observability), CloudEvents (event envelopes)
- Next.js 15 / React (steward console, Phase 3)
- Docker Compose (local dev)

## Core objects (start here)
- `packages/florence-core/florence_core/schemas/` — all Pydantic models (single source of truth)
- **`CandidateAction` + `EDENADecision` are the most important objects.**
- No action executes without a `CandidateAction` passing EDENA evaluation.

## Non-negotiable rules
1. **No action executes without EDENA evaluation.** No exceptions, no fast-paths.
2. **EDENA fails closed.** If governance is unreachable, deny irreversible/external work; otherwise require a human. Never fail open.
3. **PHI never leaves the local boundary** without explicit redaction + policy approval. Pass hashes/refs, not raw content.
4. **Agents are registered labor.** Every agent has an owner, scope, tool boundary, memory rule, eval rubric, EDENA baseline tier, and decommission path. No orphaned agents.
5. **Every workflow run generates an `EvidenceBundle`.** Not optional — it is the compliance artifact.
6. **Human review must be meaningful.** The console shows blast radius, reversibility, source evidence, EDENA rationale. Never a bare "approve" button.
7. **Memory writes require class + provenance + expiration.** No raw PHI in memory (HMAC-SHA256 tokenize upstream).
8. **Tools are dangerous until proven bounded.** Every tool has a risk class, explicit allowed actions, review trigger, audit rules, and failure mode.
9. **Refusal and containment are successful outcomes**, not failures.

## Build & run
```bash
make install                      # editable installs + api/dev extras
make demo                         # run the ICU handoff demo end-to-end (no services needed)
make test                         # pytest (unit/safety/policy/phi_boundary)
make up                           # docker compose: postgres + redis + opa + api
# API: uvicorn app.main:app --reload   (from apps/api; needs X-Florence-Identity + X-Florence-Role headers)
```

## Testing gates (run before merging)
- `tests/policy/` — EDENA decision-ladder + OPA parity (run before any policy change)
- `tests/phi_boundary/` — PHI leak detection (run on any context/model/memory change)
- `tests/safety/` — EDENA deny/contain + fail-closed scenarios
- `tests/unit/` — runtime loop invariants

## RFC process
New architectural decisions require an RFC in `docs/rfcs/`. Use `0001-core-object-model.md`
as the template. Changing an enum in `schemas/enums.py` is API-breaking → RFC required.

## Conventions
- Pydantic models are the contract; `extra="forbid"` everywhere (no silent field drops).
- Keep `CandidateAction` carrying a payload **hash**, never the payload.
- Prefer open standards: MCP, FHIR R4, SMART, CDS Hooks, A2A, OpenAPI, OpenTelemetry, CloudEvents.
- Latency is a clinical safety concern: point-of-care paths target ≤ 2–3s end to end.
