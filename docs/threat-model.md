# Threat Model

Controls map to **OWASP Top 10 for Agentic Applications 2026** and use
**MITRE ATLAS** as the adversary knowledge base. Treat every prompt, tool call,
memory write, handoff, A2A message, and external API action as a governed event.

| Risk | Code | Florence-X mitigation |
|---|---|---|
| Agent Goal Hijack | ASI01 | CandidateAction gating + EDENA policy evaluation |
| Tool Misuse & Exploitation | ASI02 | Tool gateway w/ risk class + pre-execution EDENA check |
| Identity & Privilege Abuse | ASI03 | Agent registry w/ scoped ownership + Zero Trust |
| Agentic Supply Chain | ASI04 | Versioned agent/tool defs + audit trail |
| Unexpected Code Execution | ASI05 | Code exec requires Orange/Red EDENA + human; prod = blocked |
| Memory & Context Poisoning | ASI06 | Governed memory + provenance + PHI tokenization |
| Insecure Inter-Agent Comms | ASI07 | A2A w/ auth + signed envelopes (Phase 4) |
| Cascading Failures | ASI08 | Incident handler + circuit breaker + fallback engine |
| Human–Agent Trust Exploitation | ASI09 | Meaningful review UI (context, evidence, blast radius) |
| Rogue Agents | ASI10 | Agent registry w/ decommissioning + containment |

## Key invariants
- EDENA fails closed (`tests/safety/`).
- `restricted` data and production code execution are hard-blocked.
- No raw PHI in prompts to external models, memory, or audit payloads (`tests/phi_boundary/`).
- Append-only event + evidence stores.
