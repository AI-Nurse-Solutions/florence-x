# Live end-to-end proof

Most "it works" claims are unit tests against mocks. This one isn't. `make e2e`
(driver: `scripts/e2e_live.py`) boots the **real** stack and drives the full
human-authority loop over HTTP, asserting the governance invariants on the live
responses:

- **real OPA policy server** — EDENA decisions are computed by `opa` over
  `policies/edena`, queried via HTTP (`EDENA_BASE_URL`), not the in-process backend;
- **real FastAPI app under uvicorn** — every step is an actual HTTP request through
  the Zero-Trust middleware;
- **durable LangGraph runtime** — the pause is a real checkpoint (SQLite saver) and
  the resume reloads it;
- **real persistence** — `PostgresRepository` over an Alembic-migrated SQLite DB.

Only the model (deterministic stub agent) and Redis (in-process queue) are not
"real" — neither is needed to prove governance.

## Run it
```bash
make opa-install        # one-time: the OPA binary
make e2e                # boots OPA + uvicorn, runs the scenarios, tears down
```

## What it checks (sample run)
```text
Florence-X live end-to-end — real OPA + real HTTP API + durable runtime
  OPA :64335  ·  API :64336  ·  DB sqlite  ·  runtime=graph(sqlite checkpoint)
  ✅ OPA policy server is up
  ✅ Alembic migrated a fresh database
  ✅ FastAPI app is serving (/healthz)
  ✅ Zero Trust denies a request with no identity (401)

▶ Scenario A — pause at EDENA(require_human), steward APPROVES, run resumes
  ✅ signal accepted, run paused for human  — run=wfr_441ffe1471
  ✅ paused run appears in the review queue
  ✅ EDENA decision came back require_human / yellow (via the OPA server)  — tier=yellow
  ✅ review carries anti-rubber-stamp context
  ✅ approval resumes the run to completion
  ✅ run status is completed
  ✅ evidence bundle records the EDENA decision
  ✅ evidence bundle records the human approval
  ✅ source citations are references, not raw content  — ['fhir:Bundle/synthetic-icu-001', 'policy:icu_handoff_sop_v3']

▶ Scenario B — steward DENIES, run is blocked and an Incident is recorded
  ✅ denial blocks the run
  ✅ run status is blocked
  ✅ an Incident was created (refusal is a recorded success)

============================================================
  RESULT: 16 passed, 0 failed
============================================================
```

!!! note "This run found a real bug"
    The first live run failed one check — the resumed evidence bundle didn't
    record the human approval. Cause: with the append-only **durable** repo, the
    partial pause-bundle shadowed the final one (the in-memory repo overwrote, so
    unit tests never saw it). Fixed by minting a fresh immutable bundle revision per
    `finalize()`; locked by a durable-repo regression test
    (`tests/integration/test_graph_resume.py::test_resumed_evidence_records_the_review_on_a_durable_repo`).
    That is exactly why the live run exists.
