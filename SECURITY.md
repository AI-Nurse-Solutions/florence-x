# Security Policy

Florence-X is safety-critical infrastructure for high-trust clinical environments.
Treat every prompt, tool call, memory write, handoff, agent-to-agent message, and
external API action as a **governed event**.

## Reporting a vulnerability
Email **security@florence-x.example** with details and a PoC if possible. Do not
open a public issue for security reports. We aim to acknowledge within 3 business
days. Coordinated disclosure preferred.

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
