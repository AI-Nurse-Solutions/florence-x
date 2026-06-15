# Project Governance

## Planes of authority
- **NAIO** — institutional oversight: approves AI systems, defines policy packs,
  monitors outcomes/drift, audits incidents, decommissions unsafe AI.
- **EDENA** — runtime governance: classifies action risk, gates execution, routes
  human review, escalates, blocks, contains.
- **Florence-X** — orchestration: receives signals, routes workflows, assigns
  agents, selects models, manages tools, pauses for humans, records evidence.
- **Nurse / clinician** — stewardship authority over the environment, not just the task.

## Decision process
- Architectural changes require an **RFC** in `docs/rfcs/` (see `0001`).
- Changes to EDENA tiers, policy packs, or the PHI boundary require an RFC **and**
  passing `tests/policy/` + `tests/phi_boundary/` + `tests/safety/`.
- Code is dual-licensed in spirit: **code = Apache-2.0**, **governance docs/standards
  = CC BY 4.0** (so hospitals, schools, and agencies can adapt with attribution).

## Maintainers & roles
- Technical stewards own the orchestration core, EDENA client, and connectors.
- Clinical stewards own workflow definitions, tier baselines, and safety review.
- A change to a `RED`/`RED_BLOCKED` rule requires sign-off from both.

## Releases
SemVer. Safety- or PHI-affecting changes are called out in the changelog and
mapped to the relevant control framework.
