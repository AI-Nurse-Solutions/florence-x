## What & why

## Checklist
- [ ] No action path bypasses `CandidateAction → EDENADecision`
- [ ] No raw PHI logged, persisted, or sent to a cloud model
- [ ] `make test` green (incl. safety/policy/phi_boundary)
- [ ] `opa test policies` green (if EDENA policy touched)
- [ ] Schemas regenerated if models changed (no drift)
- [ ] RFC added/updated if this is an architectural decision
