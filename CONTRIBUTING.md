# Contributing to Florence-X

Thank you for helping build governed AI infrastructure for clinical care.

## Ground rules
1. Read `CLAUDE.md` and `docs/architecture.md` first.
2. **No action path may bypass EDENA.** PRs that add a fast-path around
   `CandidateAction → EDENADecision` will be rejected.
3. **No raw PHI** anywhere it can be logged, persisted, or sent to a cloud model.
4. New architectural decisions need an RFC (`docs/rfcs/`, template `0001`).

## Dev setup
```bash
make install        # editable installs + extras
make demo           # ICU handoff demo (no services required)
make test           # pytest
make lint           # ruff
```

## Before you open a PR
- Run `make test`. Safety/policy/phi_boundary tests must pass.
- If you touched EDENA policy: run `tests/policy/` (and `opa test policies` if you have OPA).
- If you touched context/model/memory: run `tests/phi_boundary/`.
- Add/extend tests for new behavior. Evidence-affecting changes need an evidence assertion.

## Style
- Python 3.12+, Pydantic v2 models with `extra="forbid"`.
- Keep `CandidateAction` carrying a payload hash, never the payload.
- Prefer open standards (MCP, FHIR, SMART, CDS Hooks, A2A, OpenAPI, OTel, CloudEvents).
