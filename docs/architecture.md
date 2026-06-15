# Florence-X Reference Architecture

Florence-X is a **governed orchestration substrate**. This document is the primary
architecture reference; the full doctrine lives in the canonical handoff document
in the project root canon. The non-negotiable rules are in `../CLAUDE.md`.

## Mental model: three planes

```
NAIO        = institutional oversight plane   (which AI is approved?)
Florence-X  = orchestration plane             (how should work move?)
EDENA       = governance plane                (should this action happen?)
Nurse       = stewardship authority           (human judgment + environment)
```

EDENA is a **separate service** Florence-X calls before any consequential action.

## The nine layers

1. **Signal layer** — every input (EHR event, nurse request, handoff, lab result,
   CDS Hooks call, scheduled job, external agent) becomes a typed `Signal`.
2. **Context & data-boundary layer** — PHI classification, local-vs-cloud routing,
   redaction, minimum-necessary selection, consent, provenance. *PHI stays local by default.*
3. **Orchestration core** — workflow graph engine, dispatcher, agent registry, tool
   registry, model router, memory broker, task queue, human-checkpoint manager,
   retry/fallback, incident handler, append-only event log. Supervisor pattern.
4. **Agent layer** — agents are *registered labor*: owner, scope, tool boundary,
   memory rule, eval rubric, EDENA baseline tier, decommission path.
5. **Tool & connector gateway** — no agent calls a tool directly. Every tool has a
   risk class, explicit allowed actions, review trigger, audit rules, failure mode.
6. **Model routing layer** — local SLM/LLM vs approved cloud, by PHI status, risk,
   latency, cost. Records a `ModelRoute` decision.
7. **EDENA governance runtime** — evaluates every `CandidateAction`; returns one of
   8 decisions; OPA/Rego (or Cedar) policy engine. See `edena-integration.md`.
8. **Human stewardship console** — the human authority interface (Phase 3). Shows
   evidence, blast radius, reversibility, EDENA rationale; approve/edit/escalate/deny/stop.
9. **Evidence & audit layer** — every run yields an `EvidenceBundle`; OpenTelemetry
   traces; CloudEvents envelopes; immutable audit storage mapped to control frameworks.

## The canonical runtime loop

```
1. Signal received          7. Agent drafts plan/output
2. Context classified       8. CandidateAction created
3. Workflow selected        9. EDENA evaluates CandidateAction
4. Agent assigned          10. Human review (when required)
5. Model routed            11. Tool/action executes or blocks
6. Tool permissions checked 12. EvidenceBundle persists
                           13. Feedback updates policy/eval/learning
```

Object flow:
```
Signal → WorkflowRun → AgentInvocation → CandidateAction
       → EDENADecision → HumanReview | SystemBlock | ToolExecution
       → EvidenceBundle → EvaluationFeedback
```

Implemented in `packages/florence-core/florence_core/workflows/runtime.py`.

## Core object model

| Object | Purpose | Phase |
|---|---|---|
| `Signal` | Typed input event | 1 |
| `WorkflowDefinition` / `WorkflowRun` | Orchestration graph + live run | 1 |
| `AgentDefinition` / `AgentInvocation` | Registered agent + invocation | 1 |
| `ToolDefinition` | Registered tool, risk class, allowed actions | 1 |
| `ModelRoute` | Model-selection decision + rationale | 1 |
| `ContextBundle` | Approved context (PHI status, hash, refs) | 1 |
| `CandidateAction` | Proposed action requiring governance | **0** |
| `EDENADecision` | allow/deny/require-human/constrain/stop | **0** |
| `HumanReview` | Named human approval/edit/deny/escalate | 2 |
| `EvidenceBundle` | Full traceability artifact | 1 |
| `Incident` | Safety/security/privacy/perf event | 2 |
| `PolicyPack` | Versioned governance rules | 2 |
| `MemoryEntry` | Governed memory (class/provenance/expiry) | 2 |
| `EvaluationRun` | Post-run quality/safety/drift | 3 |

## Regulatory alignment

| Regulation | Florence-X mechanism |
|---|---|
| HIPAA Security Rule | PHI boundary, local-first routing, audit logs, BAA on cloud adapters |
| ONC HTI-1 | Evidence bundles w/ source citations, EDENA tiering, policy versioning |
| EU AI Act (Aug 2026) | Steward console (human oversight), EvidenceBundle as tech documentation |
| FDA PCCP | PolicyPack versioning, EvaluationRun feedback, RFC process |
| OWASP ASI 2026 | Tool gateway, agent scoping, memory governance, EDENA containment, Zero Trust |

## Tech stack

Python 3.12+ · FastAPI · Pydantic v2 · PostgreSQL 16+ · Redis 7+ · LangGraph v1.0
(Phase 2) · OPA/Rego or Cedar · OpenTelemetry · CloudEvents · Next.js 15 (console)
· Docker Compose. Local models: Ollama / llama.cpp / vLLM.
