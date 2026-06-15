package edena

import rego.v1

# ORANGE: emergent/elevated risk — code execution or crossing an external
# boundary. Senior human + technical steward review.
is_orange if input.action_type == "execute_code"

is_orange if input.external_boundary_crossed == true

is_orange if {
	input.action_type == "call_api"
	input.external_action == true
}

orange_decision := {
	"decision": "require_human",
	"risk_tier": "orange",
	"required_human_role": "technical_steward",
	"constraints": [
		"blast_radius_estimate_required",
		"externality_raises_the_floor",
		"redaction_required_if_phi",
	],
	"rationale": "Code execution or external boundary crossing requires senior + technical steward review.",
	"evidence_required": ["blast_radius_estimate"],
}
