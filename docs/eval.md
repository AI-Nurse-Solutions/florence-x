# Evaluate Florence-X in 30 minutes

You don't have to trust the README. In about half an hour, on your own machine,
with synthetic data, you can **verify the five governance claims yourself** and
reach a yes/no. No accounts, no PHI, no cloud.

**The claims you're testing** (`CLAUDE.md`):
1. No consequential action runs without an EDENA decision.
2. EDENA fails closed.
3. PHI never leaves the local boundary.
4. Every run yields an immutable EvidenceBundle.
5. Refusal & containment are recorded successes.

---

## 0 · Prerequisites (2 min)
- Python 3.12+ and `git`. (Docker optional — not needed for this eval.)
- That's it. Everything below runs locally on synthetic FHIR.

## 1 · Get it running (5 min)
```bash
git clone https://github.com/AI-Nurse-Solutions/florence-x.git
cd florence-x
make install          # editable packages + api/dev extras
make opa-install      # the real OPA policy engine (repo-local)
```

## 2 · One command to prove it (10 min)
```bash
make eval
```
This runs, in sequence: `demo` → `test` → `policy-test` → `e2e`. Green all the
way through is your answer. If you have only 10 minutes, this is the eval — skip
to §5.

Prefer to watch each piece? Run them individually (§3–§4).

## 3 · See it work, then see it *refuse* (5 min)
```bash
make demo
```
The ICU handoff runs end to end with **no services**. Watch the CloudEvents
stream: `candidate_action.created` → **`edena.decision (require_human, yellow)`** →
`human_review.requested` → `tool.executed` → `evidence_bundle.persisted`. Nothing
executed before EDENA cleared it (claim 1); the run produced evidence (claim 4).

## 4 · Attack the invariants (10 min)
```bash
make test            # full suite (unit/safety/policy/phi_boundary/integration/redteam)
pytest tests/redteam -v   # just the adversarial suite — 31 attacks, all repelled
make e2e             # LIVE: real OPA server + real HTTP API + durable runtime
```
`tests/redteam/` actively *tries* to break each claim:
- **Gate bypass** — incl. a structural proof that the durable graph's tool node is
  reachable *only* via the EDENA gate (`test_gate_bypass`).
- **Fail-closed** — a down/tampered/unreachable EDENA never returns `allow`
  (`test_fail_closed`).
- **PHI exfiltration** — redactor fuzzed; non-local send refused if PHI survives
  (`test_phi_exfiltration`).
- **Evidence integrity** — blocked runs still leave evidence; audit is append-only
  (`test_evidence_integrity`).

`make e2e` does the same against the **real stack** over HTTP (see
[live-e2e.md](live-e2e.md)) — that run once caught a bug the mocked tests missed,
which is the point.

## 5 · Read the receipts (5 min)
- **[assurance.md](assurance.md)** — the invariant ↔ attack ↔ test matrix: every
  claim → the attack → the test that repels it.
- **[architecture.md](architecture.md)** + **[edena-integration.md](edena-integration.md)** —
  how the gate and the three planes fit together.
- **[CHALLENGE.md](CHALLENGE.md)** — still skeptical? Try to break it; a failing
  `tests/redteam/` test or a private advisory is the most useful thing you can send.

---

## What you just proved
| You ran | It demonstrated |
|---|---|
| `make demo` | The governed loop; action gated before execution (1), evidence always (4) |
| `pytest tests/redteam` | All five claims hold under direct attack |
| `make e2e` | The same holds on the **real** OPA + HTTP + durable stack |
| `make policy-test` | The EDENA decision ladder (18 Rego cases) |

## Does it fit *you*? (the real decision)
- **Building agentic clinical workflows?** Your tool calls become
  `CandidateAction → EDENA`; wire connectors behind the gateway
  (`florence_connectors`), policies in `policies/edena/*.rego`.
- **Need an audit story?** Every run's `EvidenceBundle` (decisions, reviewer,
  sources, policy-pack version) is the artifact your compliance team reviews.
- **Have a steward workflow?** The Next.js console (`apps/steward-console`) is the
  anti-rubber-stamp review surface.
- **Extending it?** Read `docs/ROADMAP.md` and `docs/rfcs/README.md`.

Reached a *yes*, or hit a wall? Open an issue, a discussion, or — best — a failing
red-team test. That's how Florence-X gets better and how you get a definitive
answer.
