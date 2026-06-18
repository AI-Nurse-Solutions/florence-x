# Break the gate

Florence-X stakes its credibility on a few invariants. We don't want you to take
them on faith — we want you to *try to break them*. If you can, that's the most
valuable contribution you can make.

## The claims
1. **No consequential action executes without an `EDENADecision`.** Make a tool
   run (or any consequential action complete) without a clearing EDENA decision.
2. **EDENA fails closed.** Get an `allow` / `allow_with_constraints` (or a tool
   execution) out of the system while the governance plane is down, unreachable,
   or returning garbage.
3. **PHI never leaves the local boundary.** Get raw PHI to a non-local model, into
   memory, or into an audit/evidence payload.
4. **The audit trail is append-only.** Mutate or delete a persisted
   `EvidenceBundle`, event, or `Incident` through the system's own paths.
5. **Tools are deny-by-default.** Invoke a tool that isn't explicitly registered.

## The rules
- In scope: the runtime, the tool gateway, the EDENA client/policies, the model
  router/redaction, the API, and the persistence layer — on **synthetic data only**.
- Fair game: prompt injection, adversarial action fields, race conditions,
  restart/replay, malformed input, config abuse.
- Out of scope: DoS, attacks on GitHub/CI infra, social engineering, anything
  needing real PHI (don't — the project is synthetic-only by design).

## How to report
- **A clean bypass / leak / tamper** is a security issue → open a **private GitHub
  security advisory** (see `SECURITY.md`), not a public issue.
- A weaker finding (e.g., a missed redaction pattern) → a normal issue is fine.
- Best of all: a **failing test in `tests/redteam/`** that demonstrates it. That's
  the format we already use to prove the invariants
  (see [assurance.md](assurance.md)), and it turns your finding into a permanent
  regression guard.

## Where to start
- The adversarial suite: `tests/redteam/` — extend it.
- The structural gate proof:
  `tests/redteam/test_gate_bypass.py::test_execute_tool_is_only_reachable_through_the_edena_gate`.
- The invariant ↔ attack ↔ test matrix: [assurance.md](assurance.md).
- A live, runnable target: `make e2e` ([live-e2e.md](live-e2e.md)).

Found one? We'll credit you, fix it, and add your test. Refusing a clever attack
is the product working — *proving* it refuses is the point.
