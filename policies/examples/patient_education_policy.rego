# Workflow overlay: patient education drafting (MVP 2).
# Draft is Yellow (human-validated, reading-level + citations); external delivery
# to a patient is gated and Red when PHI crosses the boundary unredacted.
package edena.examples.patient_education

import rego.v1

# A draft must declare a reading level and carry source citations.
reading_level_required if input.action_type == "draft"

# Outbound delivery of PHI to a patient without redaction is blocked.
block if {
	input.action_type == "send_message"
	input.phi_present == true
	input.external_boundary_crossed == true
	input.redaction_applied != true
}

# A compliant education artifact is a Yellow, human-validated draft.
compliant if {
	input.action_type == "draft"
	input.phi_present == true
	not block
}
