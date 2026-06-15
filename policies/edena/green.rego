package edena

import rego.v1

# GREEN: low-risk, bounded, reversible, informational.
is_green_constrained if input.action_type in {"retrieve", "summarize"}

green_constrained := {
	"decision": "allow_with_constraints",
	"risk_tier": "green",
	"constraints": ["must_cite_source", "no_extrapolation_beyond_source"],
	"rationale": "Bounded, reversible informational task; allowed with source-citation constraints.",
}

green_allow := {
	"decision": "allow",
	"risk_tier": "green",
	"rationale": "Low-risk, bounded, reversible action.",
}
