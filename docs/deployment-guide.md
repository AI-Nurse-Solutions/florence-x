# Deployment Guide

## Local development
```bash
make install          # editable installs + extras
make demo             # ICU handoff demo (no services)
make test             # pytest
make up               # docker compose: postgres + redis + opa + api
make down             # tear down (removes volumes)
```

## Compose stack (`docker/docker-compose.yml`)
- `postgres:16` — durable state (set `FLORENCE_DATABASE_URL` to enable; MVP defaults to in-memory)
- `redis:7` — queues/locks (Phase 1 finalization)
- `opa` — EDENA policy engine serving `policies/edena` at `:8181`
- `api` — Florence-X FastAPI service at `:8000`

## Configuration (`.env`, see `.env.example`)
- `FLORENCE_DATABASE_URL` — empty → in-memory repository
- `EDENA_BASE_URL` — empty → in-process `LocalRuleBackend`; `http://opa:8181` → OPA
- `FLORENCE_REQUIRE_IDENTITY` — Zero Trust header enforcement (default true)

## Production (not Phase 0/1)
Kubernetes, OPA as sidecar/daemon, immutable audit storage, OpenTelemetry collector,
split EDENA into its own deployment with an independent policy lifecycle, BAA-backed
model endpoints. See `MODEL_RISK.md` and `GOVERNANCE.md`.
