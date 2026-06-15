package edena

import rego.v1

# YELLOW: clinically/operationally relevant but not finalizing care.
# Human validation required.
is_yellow if {
	phi_present
	input.action_type in {"draft", "summarize", "handoff_to_agent"}
}

is_yellow if {
	input.has_clinical_impact == true
	input.action_type in {"draft", "summarize"}
}

yellow_decision := {
	"decision": "require_human",
	"risk_tier": "yellow",
	"required_human_role": role,
	"constraints": [
		"output_must_remain_draft",
		"must_display_missing_data",
		"must_include_source_refs",
	],
	"rationale": "Clinical content may influence care and/or contains PHI; human validation required before use.",
	"evidence_required": ["source_refs"],
} if {
	role := object.get(input, "requester_role", "rn")
}
