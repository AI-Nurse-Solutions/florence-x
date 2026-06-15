# Native OPA tests for the EDENA decision ladder.
#
# These mirror the CASES in tests/policy/test_parity.py and lock the Rego packs
# independently of the Python LocalRuleBackend. Run with: `opa test policies`.
# Precedence under test (Ambiguity escalates upward):
#   blocked > red > orange > yellow > green
package edena_test

import data.edena
import rego.v1

# GREEN — bounded, reversible, informational retrieval.
test_green_retrieve_allow_with_constraints if {
	d := edena.decision with input as {
		"action_type": "retrieve",
		"data_classification": "internal",
		"phi_present": false,
		"external_boundary_crossed": false,
		"external_action": false,
		"has_clinical_impact": false,
		"requester_role": "rn",
		"action_id": "a",
	}
	d.decision == "allow_with_constraints"
	d.risk_tier == "green"
}

# YELLOW — PHI-bearing clinical draft requires human validation.
test_yellow_phi_draft_require_human if {
	d := edena.decision with input as {
		"action_type": "draft",
		"data_classification": "phi_local",
		"phi_present": true,
		"external_boundary_crossed": false,
		"external_action": false,
		"has_clinical_impact": true,
		"requester_role": "rn",
		"action_id": "a",
	}
	d.decision == "require_human"
	d.risk_tier == "yellow"
}

# RED — writing to the clinical record.
test_red_write_record_require_human if {
	d := edena.decision with input as {
		"action_type": "write_record",
		"data_classification": "phi_local",
		"phi_present": true,
		"reversible": false,
		"external_boundary_crossed": false,
		"external_action": false,
		"has_clinical_impact": true,
		"requester_role": "rn",
		"action_id": "a",
	}
	d.decision == "require_human"
	d.risk_tier == "red"
}

# RED — outbound message crossing a trust boundary.
test_red_send_message_require_human if {
	d := edena.decision with input as {
		"action_type": "send_message",
		"data_classification": "phi_local",
		"phi_present": true,
		"external_boundary_crossed": true,
		"external_action": true,
		"has_clinical_impact": true,
		"requester_role": "rn",
		"action_id": "a",
	}
	d.decision == "require_human"
	d.risk_tier == "red"
}

# ORANGE — external API call elevates the floor.
test_orange_external_call_api_require_human if {
	d := edena.decision with input as {
		"action_type": "call_api",
		"data_classification": "internal",
		"phi_present": false,
		"external_boundary_crossed": true,
		"external_action": true,
		"has_clinical_impact": false,
		"requester_role": "rn",
		"action_id": "a",
	}
	d.decision == "require_human"
	d.risk_tier == "orange"
}

# RED-BLOCKED — code execution against production is a hard stop.
test_blocked_execute_code_on_prod_deny if {
	d := edena.decision with input as {
		"action_type": "execute_code",
		"data_classification": "internal",
		"phi_present": false,
		"reversible": false,
		"external_boundary_crossed": false,
		"external_action": false,
		"has_clinical_impact": false,
		"requester_role": "rn",
		"action_id": "run-on-prod",
	}
	d.decision == "deny"
	d.risk_tier == "red_blocked"
}

# RED-BLOCKED — restricted data may never be used in an action.
test_blocked_restricted_data_deny if {
	d := edena.decision with input as {
		"action_type": "retrieve",
		"data_classification": "restricted",
		"phi_present": false,
		"external_boundary_crossed": false,
		"external_action": false,
		"has_clinical_impact": false,
		"requester_role": "rn",
		"action_id": "a",
	}
	d.decision == "deny"
	d.risk_tier == "red_blocked"
}

# Precedence — restricted data outranks an otherwise-Yellow PHI draft.
test_blocked_outranks_yellow if {
	d := edena.decision with input as {
		"action_type": "draft",
		"data_classification": "restricted",
		"phi_present": true,
		"external_boundary_crossed": false,
		"external_action": false,
		"has_clinical_impact": true,
		"requester_role": "rn",
		"action_id": "a",
	}
	d.risk_tier == "red_blocked"
}
