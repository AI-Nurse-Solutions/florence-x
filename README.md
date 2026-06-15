# Florence-X

**A governance-first, local-first AI orchestration control plane for high-trust clinical environments.**

> **Florence-X orchestrates. EDENA gates. Humans decide. Nurses steward.**

Florence-X turns institutional signals into bounded, auditable, human-stewarded
workflows. It routes tasks to registered agents, assigns tools and memory, selects
local or external models, pauses for human review, invokes **EDENA** for action
gating, records evidence, and prevents AI systems from acting outside their
authorized scope.

Florence-X is **not another agent framework**. Most frameworks help you *build*
agents; Florence-X helps an institution *govern AI labor*. It is closer to an
operating system for clinical AI work than a chatbot.

---

## The problem

AI has moved from answering questions to *taking actions* — calling tools, writing
records, sending messages, coordinating other agents. The hard question is no
longer "Can AI answer?" but:

> *How does a high-trust organization safely route AI-generated work through
> agents, tools, humans, policy, evidence, and action?*

LangGraph, MCP, A2A, FHIR, and OPA each solve a piece. None of them is a
governance-first clinical orchestration plane. Florence-X is the missing layer
that combines them under EDENA authority.

## Three planes

| Plane | Role | Core question |
|---|---|---|
| **Florence-X** | Orchestration runtime | How should this work move through agents, tools, models, humans, systems? |
| **EDENA** | Governance / action-gating authority | Should this AI action be allowed, reviewed, constrained, escalated, blocked, or stopped? |
| **NAIO** | Institutional oversight | Which AI systems are approved, monitored, audited, decommissioned? |
| **Nurse / clinician** | Stewardship authority | How do we supervise governed AI labor safely in practice? |

**EDENA is a separate governance service that Florence-X calls** — not a module
inside it. EDENA owns the action gate.

## The canonical runtime loop

```
Signal → WorkflowRun → AgentInvocation → CandidateAction
       → EDENADecision → HumanReview | SystemBlock | ToolExecution
       → EvidenceBundle → EvaluationFeedback
```

No consequential action executes until a `CandidateAction` has passed EDENA
evaluation. Every run produces an `EvidenceBundle`. PHI stays local by default.

## Quickstart

```bash
# 1. Install (editable) + dev/api extras
make install

# 2. Run the ICU handoff demo end-to-end — no services required
make demo
#   Signal → context classified → draft → EDENA(require_human, yellow)
#   → simulated approval → tool executes → EvidenceBundle persisted

# 3. Run the test suite (unit / safety / policy / phi_boundary)
make test

# 4. Bring up the full local stack (Postgres + Redis + OPA + API)
make up
```

Call the API (Zero Trust requires identity headers):

```bash
curl -s localhost:8000/healthz

curl -s -X POST 'localhost:8000/signals?auto_approve=true' \
  -H 'content-type: application/json' \
  -H 'x-florence-identity: u-123' -H 'x-florence-role: rn' \
  -d '{"signal_id":"sig1","source":"demo","signal_type":"icu_handoff_needed",
       "requester":{"role":"rn","unit":"micu"},"data_classification":"phi_local",
       "patient_context_present":true}'
```

## What's in this release (Phase 0 + Phase 1)

- **Core object model** — Pydantic v2 schemas for every governed object
  (`CandidateAction`, `EDENADecision`, `Signal`, `EvidenceBundle`, …).
- **EDENA client + reference policy engine** — fail-closed client, a pure-Python
  `LocalRuleBackend`, an `OpaBackend`, and Rego policy packs
  (`green/yellow/orange/red/blocked`).
- **The canonical runtime loop** — `Signal → … → EvidenceBundle`, with an
  append-only CloudEvents log and a human-review interrupt.
- **FastAPI surface** — signal intake, run/evidence retrieval, reference EDENA
  endpoint, Zero Trust middleware.
- **CLI** — `florence run examples/icu_handoff/workflow.yaml`.
- **5 MVP workflows** + synthetic FHIR fixtures (no real PHI).

See [`BUILD_PLAN.md`](./BUILD_PLAN.md) for the full phased plan and what comes next.

## Repository map

```
packages/florence-core/        # schemas, dispatcher, state, events, evidence, memory, workflows (the loop)
packages/florence-edena/       # EDENA client, risk features, policy adapters (OPA/local/Cedar)
packages/florence-connectors/  # MCP, FHIR, SMART, CDS Hooks, OpenAPI, A2A (Phase 4+)
packages/florence-model-router/# local/cloud adapters, redaction, routing rules, cost controls
packages/florence-cli/         # the `florence` CLI
apps/api/                      # FastAPI service (+ reference EDENA endpoint)
apps/steward-console/          # human authority interface (Phase 3, Next.js)
policies/edena/                # Rego policy packs
examples/                      # 5 MVP workflows + synthetic FHIR
schemas/                       # JSON Schema artifacts (CandidateAction, EDENADecision)
docs/                          # architecture, EDENA integration, PHI boundary, threat model, RFCs
tests/                         # unit / integration / policy / safety / phi_boundary
```

## Documentation

- [`CLAUDE.md`](./CLAUDE.md) — session constitution + non-negotiable rules
- [`BUILD_PLAN.md`](./BUILD_PLAN.md) — phased build plan + acceptance gates
- [`docs/architecture.md`](./docs/architecture.md) — the 9-layer reference architecture
- [`docs/edena-integration.md`](./docs/edena-integration.md) — EDENA API contract + policy model
- [`docs/phi-boundary-model.md`](./docs/phi-boundary-model.md) · [`docs/safety-model.md`](./docs/safety-model.md) · [`docs/threat-model.md`](./docs/threat-model.md)

## Licensing

- **Code:** Apache-2.0 (`LICENSE`).
- **Governance docs & standards:** CC BY 4.0 (so institutions can adapt with attribution).

## Safety

This is research/infrastructure software. It is **not** a medical device and **not**
cleared for clinical use. The open-source release uses synthetic data only. See
[`CLINICAL_SAFETY.md`](./CLINICAL_SAFETY.md).
