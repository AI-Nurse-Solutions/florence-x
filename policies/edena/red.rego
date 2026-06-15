package edena

import rego.v1

# RED: high-risk, irreversible, clinical/legal/financial, PHI-sensitive,
# or external-action risk. Approval-gated by a named clinician + compliance.
is_red if input.action_type == "write_record"

is_red if input.action_type == "send_message"

red_decision := {
	"decision": "require_human",
	"risk_tier": "red",
	"required_human_role": "clinician",
	"constraints": [
		"human_must_approve_before_execute",
		"no_phi_to_external_without_redaction",
		"compliance_cosign_required",
	],
	"rationale": "Record writes and outbound messages are high-risk and may be irreversible; named clinician + compliance must approve.",
	"evidence_required": ["source_refs", "reviewer_identity"],
}
