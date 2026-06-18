# Security Policy

Florence-X is safety-critical infrastructure for high-trust clinical environments.
Treat every prompt, tool call, memory write, handoff, agent-to-agent message, and
external API action as a **governed event**.

## Reporting a vulnerability
**Preferred:** open a private [GitHub security advisory](https://github.com/AI-Nurse-Solutions/florence-x/security/advisories/new)
— it stays confidential and threads the fix + disclosure in one place. As a
backup you may email **great.ai.nurses@gmail.com**. Do not open a public issue for
security reports. We aim to acknowledge within 3 business days; coordinated
disclosure preferred.

## Scrutiny welcome
Florence-X stakes its credibility on five invariants — no consequential action
executes without an EDENA decision; EDENA fails closed; PHI never leaves the local
boundary; the audit trail is append-only; tools are deny-by-default. We don't ask
you to take them on faith:

- **The claims, and how to break them:** [`docs/CHALLENGE.md`](docs/CHALLENGE.md).
- **What's already proven, adversarially:** [`docs/assurance.md`](docs/assurance.md)
  — the invariant ↔ attack ↔ test matrix.
- **The attacks themselves:** [`tests/redteam/`](tests/redteam/) — 31 tests that try
  to violate each invariant (incl. a structural proof that the runtime's
  tool-execution step is unreachable except through the gate). `make eval`
  reproduces the whole proof in minutes.

If you can make an action run without a decision, get an `allow` while governance
is down, leak PHI to a non-local model, or mutate a sealed evidence record — on
**synthetic data** — that's our most valuable bug. Report it via a private advisory
(above); we credit you, fix it, and add your case as a permanent regression test.

## Threat model
See `docs/threat-model.md`. Florence-X maps controls to **OWASP Top 10 for Agentic
Applications 2026 (ASI01–ASI10)** and uses **MITRE ATLAS** as the adversary
knowledge base.

## Security invariants
- **EDENA fails closed.** Governance unavailability denies irreversible/external work.
- **Zero Trust:** every request verifies agent identity, user role, PHI class, and action scope.
- **No raw PHI** in prompts to external models, in memory, or in event/audit payloads.
- **Tools are deny-by-default:** only explicitly allow-listed actions may run.
- **Secrets/credentials** (`data_classification: restricted`) are never persisted and never used in actions (hard block).
- **Append-only audit:** events and evidence are never updated in place.
