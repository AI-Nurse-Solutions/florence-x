# RFC 0004 — Tool & Connector Gateway

- **Status:** Accepted (implemented in Phase 4 — `florence_connectors/gateway.py`)
- **Date:** 2026-06-15

## Context
Agents must never call tools directly (OWASP ASI02). A single policy-enforcement
point must front MCP, FHIR, SMART, CDS Hooks, OpenAPI, A2A, RPA, and sandboxes.

## Decision
- `ToolDefinition` requires risk class, explicit allowed actions, review-tier
  trigger, audit rules, and failure mode. Anything not allow-listed is denied.
- Every tool invocation is a `CandidateAction` → EDENA, including A2A handoffs.
- The MCP gateway aggregates servers, manages connection lifecycle, applies
  authz, and health-monitors (Phase 4).

## Consequences
- Uniform governance + audit across heterogeneous tool transports.
