# Install & run

Florence-X is local-first. The demo and tests need no external services; the full
stack runs under Docker Compose.

## Requirements
- Python 3.12+
- (optional) `opa` for the policy-parity tests — `make opa-install` fetches a
  repo-local binary into `.tooling/bin`
- (optional) Docker + Compose for the full stack
- (optional) Node 20+ for the steward console

## Clean-clone bootstrap
```bash
git clone https://github.com/AI-Nurse-Solutions/florence-x.git
cd florence-x

make install        # editable installs of packages/* + .[api,dev] extras
make opa-install     # repo-local OPA (so the OPA parity tests run, not skip)
make demo            # ICU handoff end-to-end — no services required
make test            # unit / safety / policy / phi_boundary / integration
make policy-test     # opa test policies (18 cases)
```

`make test` and `make policy-test` automatically put `.tooling/bin` on PATH.

## Configuration (environment)
All optional — empty values keep the in-memory / local-first defaults.

| Variable | Default | Effect |
|---|---|---|
| `FLORENCE_DATABASE_URL` | _(empty)_ | Set a Postgres URL to use PostgresRepository (else in-memory). |
| `FLORENCE_REDIS_URL` | _(empty)_ | Set to enable the Redis intake queue (else in-process). |
| `EDENA_BASE_URL` | _(empty)_ | Set to an OPA server (e.g. `http://opa:8181`) to gate via OPA. |
| `FLORENCE_RUNTIME` | `graph` | `graph` = durable LangGraph runtime; `minimal` = in-process runner. |
| `FLORENCE_LANGGRAPH_CHECKPOINT` | _(empty)_ | `sqlite:///path` or a Postgres URL for durable resume. |
| `FLORENCE_REQUIRE_IDENTITY` | `true` | Zero Trust: require `X-Florence-Identity`/`X-Florence-Role`. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | _(empty)_ | Export traces to an OTLP collector. |

## Full stack (Docker Compose)
```bash
make up      # postgres + redis + opa + api + worker
curl -s localhost:8000/healthz
```
The API applies Alembic migrations on start and routes EDENA decisions through
the OPA server (`EDENA_BASE_URL=http://opa:8181`).

## API (Zero Trust requires identity headers)
```bash
curl -s -X POST 'localhost:8000/signals?sync=true&auto_approve=true' \
  -H 'content-type: application/json' \
  -H 'x-florence-identity: u-123' -H 'x-florence-role: rn' \
  -d '{"signal_id":"sig1","source":"demo","signal_type":"icu_handoff_needed",
       "requester":{"role":"rn","unit":"micu"},"data_classification":"phi_local"}'
```
Async intake (`POST /signals`) returns `202` + a pollable `workflow_run_id`; the
worker drains the queue. Paused runs appear at `GET /reviews`.

## Steward console (Next.js)
```bash
cd apps/steward-console
npm install
NEXT_PUBLIC_FLORENCE_API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

## Healthcare sandbox demo
```bash
PYTHONPATH=packages/florence-core:packages/florence-edena:packages/florence-connectors:packages/florence-model-router:packages/florence-cli:apps/api \
  python examples/sandbox/run_sandbox.py
```
