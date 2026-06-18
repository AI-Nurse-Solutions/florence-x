# Assurance: invariant ↔ attack ↔ test

Florence-X makes five non-negotiable promises (`CLAUDE.md`). This page is the
evidence that they hold — not by assertion, but by an **adversarial suite that
tries to violate each one and fails** (`tests/redteam/`). Attacks are keyed to the
**OWASP Top 10 for Agentic Applications 2026** codes used in
[`threat-model.md`](threat-model.md); MITRE ATLAS is the adversary knowledge base.

## How to run
```bash
make opa-install                  # optional; OPA leg of the policy tests
PYTHONPATH=packages/florence-core:packages/florence-edena:packages/florence-connectors:packages/florence-model-router:packages/florence-cli:apps/api \
  pytest tests/redteam -v          # the adversarial suite (31 tests)
pytest -q                          # full suite (unit/safety/policy/phi_boundary/integration/redteam)
opa test policies                  # policy decision-ladder (18)
```
The red-team suite runs in CI on every PR (the `test` job).

## The matrix

| # | Invariant (CLAUDE.md) | Attack attempted | OWASP ASI | Repelled by (`tests/redteam/`) |
|---|---|---|---|---|
| 1 | No action executes without an EDENA decision | Reach tool execution without clearing the gate; injection in action fields to relax gating | ASI01, ASI02 | `test_gate_bypass::test_execute_tool_is_only_reachable_through_the_edena_gate` · `::test_prompt_injection_in_action_fields_does_not_relax_gating` · `::test_require_human_action_is_not_auto_executed` |
| 2 | Tools are deny-by-default | Invoke an unregistered/exfiltration tool on a clearable action | ASI02 | `test_gate_bypass::test_unregistered_tool_is_denied_by_default` |
| 3 | Code execution on prod is hard-blocked | Run code against production | ASI05 | `test_gate_bypass::test_production_code_execution_is_hard_blocked` |
| 4 | EDENA fails closed (never fail-open) | Take EDENA down / tamper / point at a dead OPA server | ASI08 | `test_fail_closed::test_backend_failure_never_returns_allow` (6 shapes) · `::test_irreversible_or_external_is_denied_when_governance_down` · `::test_unreachable_opa_server_fails_closed` · `::test_gateway_does_not_execute_when_governance_is_down` |
| 5 | PHI never leaves the local boundary | Smuggle PHI into an external-bound prompt; pull raw narrative from a connector; use restricted data | ASI06 | `test_phi_exfiltration::test_redactor_leaves_no_phi_for_external_send` (8 samples) · `::test_non_local_route_refuses_when_phi_survives_redaction` · `::test_phi_work_is_pinned_to_local_models` · `::test_connectors_return_references_not_raw_narrative` · `::test_restricted_data_cannot_be_used_in_an_action` |
| 6 | Every run yields an EvidenceBundle | Make a blocked/denied run escape without evidence | ASI04 | `test_evidence_integrity::test_completed_run_yields_persisted_evidence` · `::test_denied_run_still_yields_evidence_and_an_incident` |
| 7 | Audit stores are append-only | Tamper with / replay evidence, events, incidents after the fact | ASI04 | `test_evidence_integrity::test_evidence_bundle_is_tamper_resistant` · `::test_event_log_is_append_only` · `::test_incident_record_is_append_only` |
| 8 | Refusal & containment are successful outcomes | (covariant) deny/stop/contain block + record an Incident, never execute | ASI10 | `tests/safety/test_containment.py` (deny/stop/contain/escalate/throttle) |

**The strongest result is #1's structural proof:** in the durable LangGraph
runtime the tool-execution node has *no inbound edge* except from the EDENA node
and the post-approval human node. Bypassing the gate isn't blocked by a policy
check that could regress — it's absent from the graph. The test asserts the edge
set directly, so a future refactor that wires a shortcut fails CI.

## What this proves — and what it doesn't
**Proves:** the implementation upholds its stated invariants under direct attack,
on synthetic data, in-process and against the durable runtime. Each promise has a
test that *fails if the promise is broken*.

**Does not prove (yet) — the honest gaps:**
- **Live stack.** The suite exercises the code paths; it does not stand up real
  Postgres/Redis/OPA/Ollama via `make up`. (Tracked: live end-to-end scenario.)
- **Redaction recall.** The PHI redactor is a pattern + known-identifier MVP, not
  clinical NER — it will miss novel identifier formats. The boundary is
  *fail-closed on what it detects*; detection coverage is a known limitation.
- **Real adversaries & real workflows.** Synthetic FHIR, no design-partner pilot,
  no external security review yet. Those are the next rungs (see
  [`ROADMAP.md`](ROADMAP.md)).

We invite scrutiny: if you can make a consequential action execute without an
EDENA decision, leak PHI to a non-local model, or mutate an evidence record, open
a security advisory (see `SECURITY.md`) — that's exactly the bug we want. See
[CHALLENGE.md](CHALLENGE.md) for the rules, and [live-e2e.md](live-e2e.md) for a
runnable target (`make e2e`).

!!! note "The matrix is exercised live, not just in unit tests"
    `make e2e` boots a real OPA server + the real HTTP API + the durable runtime and
    re-checks these invariants end-to-end. That live run already caught a real bug
    the mocked tests missed (append-only evidence shadowing on resume) — see
    [live-e2e.md](live-e2e.md).
