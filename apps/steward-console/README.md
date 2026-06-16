# Florence-X Steward Console (Phase 3)

The human authority interface — **not** a passive dashboard. Next.js 15 (App
Router) · React 19 · Tailwind v4. It consumes the Florence-X API and the live
CloudEvents WebSocket.

Every review screen shows enough context to *challenge* the AI: the proposed
action + what it touches, source evidence + provenance, EDENA tier + decision
rationale + constraints, blast radius, reversibility, the accountable human, and
Approve / Edit / Escalate / Deny / Stop controls. See `docs/safety-model.md`.

## Screens
- `/` — review queue (paused runs, EDENA tier color-coding, live-updating).
- `/reviews/[id]` — approval cockpit (anti-rubber-stamp context + the 5 controls).
- `/runs/[id]` — evidence viewer + EDENA decision inspector + run timeline + live feed.
- `/incidents` — refusals / containment (deny / stop / contain).
- `/registry` — agents (with NAIO approval status) + tool authorization (read-only).

## Run it
The console talks to the API (default `http://localhost:8000`). Start the API
(`uvicorn app.main:app` from `apps/api`, with `X-Florence-*` identity) and a
worker, then:

```bash
cd apps/steward-console
npm install
NEXT_PUBLIC_FLORENCE_API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

Config: `NEXT_PUBLIC_FLORENCE_API_URL`, `NEXT_PUBLIC_FLORENCE_IDENTITY`,
`NEXT_PUBLIC_FLORENCE_ROLE` (the dev identity stand-in; real OIDC later).

## Verify
`npm run build` (type-checks + compiles). Live approve→resume is verified by
running the API + console together (the API-side review/WS flow is covered by
`tests/integration/test_api_reviews.py` and `test_api_events_registry.py`).
