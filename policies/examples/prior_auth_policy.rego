# Prior authorization: Yellow to draft, Orange to submit externally (MVP 5).
package edena.examples.prior_auth

import rego.v1

tier := "yellow" if input.action_type == "draft"
tier := "orange" if {
	input.action_type == "call_api"
	input.external_boundary_crossed == true
}

submission_requires_clinical_evidence_review if {
	input.action_type == "call_api"
	input.external_boundary_crossed == true
}
