# Roadmap & first-contributor guide

Florence-X is built in phases (see `BUILD_PLAN.md`). Phases 0–4 are complete and
on `main`; this is where contributors can help next.

## Status
| Phase | Scope | State |
|---|---|---|
| 0 | Doctrine → spec (objects, contracts, policies) | ✅ |
| 1 | Local runtime (durable LangGraph, persistence, queue, OTel) | ✅ |
| 2 | EDENA gate + policy packs + review queue + containment | ✅ |
| 3 | Steward console (Next.js) | ✅ |
| 4 | Healthcare sandbox (FHIR/CDS/SMART, gateway, redaction, demos) | ✅ |
| 5 | Open-source launch | 🚧 in progress |

## Good first contributions
Each of these is scoped, testable, and respects the invariants in `CLAUDE.md`.

- **Connectors:** harden the MCP connector (`florence_connectors/mcp`) or add an
  OpenAPI connector; each tool stays a `CandidateAction → EDENA` via the gateway.
- **Redaction:** strengthen `florence_model_router/redaction` (clinical NER beyond
  the regex MVP); add cases to `tests/phi_boundary/`.
- **Rego overlays:** add workflow-specific policy overlays + `opa test` cases.
- **Steward console:** accessibility pass, edit-flow polish, evidence diff view.
- **Cross-process live events:** the Redis pub/sub relay so worker-emitted events
  reach the console WebSocket (see `apps/api/app/events_stream.py`).

## Larger efforts (RFC first — see `docs/rfcs/README.md`)
- Registry **editing/persistence** (Phase 3 ships read-only viewers).
- Postgres LangGraph checkpointer wired for cross-process durable resume.
- Real SMART-on-FHIR authorization-code flow (the MVP is a launch-context stub).

## Ground rules
Read `CLAUDE.md` (non-negotiable rules) and `CONTRIBUTING.md`. No change may
bypass `CandidateAction → EDENADecision`, weaken the PHI boundary, or drop the
EvidenceBundle. PRs that do are rejected.
