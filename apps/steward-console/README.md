# Florence-X Steward Console (Phase 3)

The human authority interface — **not** a passive dashboard. Built in Phase 3
(Next.js 15 / React). It consumes the Phase 1 API (`/runs`, `/runs/{id}/evidence`)
and a WebSocket stream of the CloudEvents log.

Every review screen MUST show enough context to *challenge* the AI:
AI output + confidence, source evidence + provenance, missing-data flags,
EDENA tier + decision rationale, the proposed action + what it will do, blast
radius, reversibility, the accountable human, and Approve / Edit / Escalate /
Deny / Stop controls. See docs/safety-model.md.

Scaffold (Phase 3):
    npx create-next-app@latest steward-console --typescript --app --tailwind
