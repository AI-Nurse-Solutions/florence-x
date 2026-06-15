# Native OPA tests for the per-workflow EDENA overlays (one per MVP workflow).
# Run with `opa test policies`. These lock the workflow-specific rules alongside
# the core decision-ladder tests in policies/edena/decision_test.rego.
package edena.examples_test

import data.edena.examples.code_execution
import data.edena.examples.icu_handoff
import data.edena.examples.patient_education
import data.edena.examples.patient_message
import data.edena.examples.policy_retrieval
import data.edena.examples.prior_auth
import rego.v1

# MVP 1 — ICU handoff: a PHI draft is compliant; charting/sending are denied.
test_icu_handoff_draft_compliant if {
	icu_handoff.compliant with input as {"action_type": "draft", "phi_present": true}
}

test_icu_handoff_write_record_denied if {
	icu_handoff.deny_reason["agent_may_not_write_to_ehr"] with input as {"action_type": "write_record"}
}

# MVP 2 — patient education: draft needs a reading level; unredacted PHI send is blocked.
test_patient_education_reading_level_required if {
	patient_education.reading_level_required with input as {"action_type": "draft"}
}

test_patient_education_blocks_unredacted_phi_send if {
	patient_education.block with input as {
		"action_type": "send_message", "phi_present": true,
		"external_boundary_crossed": true, "redaction_applied": false,
	}
}

# MVP 3 — policy retrieval: retrieve/summarize must cite; it is compliant.
test_policy_retrieval_must_cite if {
	policy_retrieval.must_cite with input as {"action_type": "retrieve"}
	policy_retrieval.compliant with input as {"action_type": "summarize"}
}

# MVP 4 — agentic software review: prod execution is hard-blocked; else dual control.
test_code_execution_prod_hard_block if {
	code_execution.hard_block with input as {"action_type": "execute_code", "action_id": "deploy-prod"}
}

test_code_execution_nonprod_requires_dual_control if {
	code_execution.require_dual_control with input as {"action_type": "execute_code", "action_id": "sandbox-run"}
}

# MVP 5 — prior auth: draft is Yellow; external submission is Orange + evidence review.
test_prior_auth_draft_yellow if {
	prior_auth.tier == "yellow" with input as {"action_type": "draft"}
}

test_prior_auth_external_submission_orange if {
	prior_auth.tier == "orange" with input as {
		"action_type": "call_api", "external_boundary_crossed": true,
	}
	prior_auth.submission_requires_clinical_evidence_review with input as {
		"action_type": "call_api", "external_boundary_crossed": true,
	}
}

# Patient messaging baseline: unredacted external PHI message is blocked.
test_patient_message_blocks_unredacted_external_phi if {
	patient_message.block with input as {
		"action_type": "send_message", "phi_present": true,
		"external_boundary_crossed": true, "redaction_applied": false,
	}
}
