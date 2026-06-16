# RFC process

Architectural decisions in Florence-X are made through short, durable RFCs.
This keeps the governance substrate auditable: the *why* behind each invariant
and contract lives next to the code.

## When an RFC is required
Open an RFC before merging any change that:
- alters a core contract (a Pydantic model in `schemas/`, especially
  `CandidateAction` / `EDENADecision`), or changes an enum in `schemas/enums.py`
  (API-breaking);
- changes the runtime invariants (EDENA gate, fail-closed, evidence-always,
  PHI boundary, deny-by-default tools);
- introduces a new plane, transport, persistence model, or execution engine
  (e.g. RFC 0007, durable LangGraph execution);
- relaxes or reinterprets any non-negotiable rule in `CLAUDE.md`.

Scoped features and bug fixes do **not** need an RFC — use a feature-request
issue and a PR.

## How to write one
1. Copy `0001-core-object-model.md` (it is also the template).
2. Number it next in sequence; fill in **Status, Date, Deciders, Context,
   Decision, Consequences, Alternatives**.
3. Open a PR with the RFC as `Proposed`. Discussion happens on the PR.
4. On acceptance, set `Status: Accepted` and implement; reference the RFC id in
   the implementing PR/commit. Superseded RFCs are marked, not deleted.

## Index
| RFC | Title | Status |
|---|---|---|
| 0001 | Core object model | Accepted |
| 0002 | EDENA decision API | Accepted |
| 0003 | Agent registry | Accepted |
| 0004 | Tool & connector gateway | Accepted (impl Phase 4) |
| 0005 | Memory governance | Accepted |
| 0006 | PHI boundary | Accepted |
| 0007 | Durable execution via LangGraph | Accepted |
