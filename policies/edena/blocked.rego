package edena

import rego.v1

# RED-BLOCKED: prohibited under current authority. Hard stop.
is_blocked if input.data_classification == "restricted"

is_blocked if {
	input.action_type == "execute_code"
	contains(lower(input.action_id), "prod")
}

blocked_decision := {
	"decision": "deny",
	"risk_tier": "red_blocked",
	"rationale": "Prohibited under current authority (restricted data or production code execution). Requires explicit override chain.",
}
