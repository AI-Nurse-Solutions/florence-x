# RFC 0003 — Agent Registry

- **Status:** Accepted
- **Date:** 2026-06-15

## Context
Agents must be registered labor, not free-floating scripts (OWASP ASI03/ASI10).

## Decision
- `AgentDefinition` carries owner, allowed/prohibited tasks, allowed tools, memory
  rule, model route (+ `phi_rule`), EDENA baseline tier, eval rubric, fallback,
  decommission path, and `institutional_approval_ref` (NAIO).
- Agents are authored as YAML (`examples/*/agent.yaml`) and loaded/validated at boot.
- Phase 2 adds a persistent registry (versioning, capability lookup, audit log).

## Consequences
- Every agent is inspectable and decommissionable; no orphaned agents.

## Alternatives considered
- Code-defined agents only: rejected (harder for clinical stewards to review/approve).
