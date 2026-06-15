# EDENA Integration

EDENA — *Ethical Decision Engine for Nurse-led AI* — is the mandatory gate between
AI intent and action. **AI proposes. EDENA gates. Humans decide. Nurses steward.**

EDENA is a **separate governance service**. Florence-X *invokes* it; it does not
contain it. The MVP ships a co-located reference implementation behind its own
router and a pure-Python backend so the system runs end-to-end from one compose file.

## Contract

`POST /edena/evaluate-action` — request body is a `CandidateAction`; response is an
`EDENADecision`. Full OpenAPI: `packages/florence-edena/edena-openapi.yaml`.
JSON Schemas: `schemas/candidate_action.schema.json`, `schemas/edena_decision.schema.json`.

The client (`florence_edena.EdenaClient`) extracts deterministic risk features
(`risk_features.extract_risk_features`) and passes them to a pluggable backend:

- `LocalRuleBackend` — pure-Python decision ladder (default; no deps).
- `OpaBackend` — shells out to `opa eval` against `policies/edena/*.rego`.
- `CedarBackend` — placeholder for RBAC/ABAC authorization (Phase 4+).

## Eight decisions

| Decision | Meaning | Florence-X action |
|---|---|---|
| `allow` | Proceed automatically | Execute, no pause |
| `allow_with_constraints` | Proceed with guardrails | Execute w/ constraints enforced |
| `require_human` | Human must approve | Pause → review queue |
| `escalate` | Elevated authority needed | Route to named escalation owner |
| `deny` | Prohibited | Block + log, safe refusal |
| `throttle` | Rate/scope limit | Apply constraint |
| `contain` | Restrict agent scope | Activate containment |
| `stop` | Full halt | Terminate run, create incident |

## Tiers (action-risk)

| Tier | Examples | Default |
|---|---|---|
| Green | Policy search, FAQ, formatting | `allow` / `allow_with_constraints` |
| Yellow | Draft handoff, education draft, summary (with PHI) | `require_human` (clinician) |
| Orange | Prior-auth submission, external API, code review | `require_human` (senior + technical steward) |
| Red | EHR write, patient message, medication-adjacent | `require_human` (named clinician + compliance) |
| Red-Blocked | Production code execution, restricted data, billing change | `deny` unless override chain |

## Fail-closed (critical)

EDENA never fails open. If the backend errors or is unreachable, `EdenaClient`
returns a safe non-executing decision: **deny** for irreversible/external actions,
otherwise **require_human**. See `tests/safety/test_edena_blocks.py`.

## Parity

`LocalRuleBackend` and the Rego packs encode the same ladder. `tests/policy/test_parity.py`
asserts the ladder and, when the `opa` binary is present, asserts OPA parity too.
