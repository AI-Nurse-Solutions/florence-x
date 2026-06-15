# Patient-facing messaging is Red by default; external delivery is gated.
package edena.examples.patient_message

import rego.v1

requires_compliance if input.action_type == "send_message"

block if {
	input.action_type == "send_message"
	input.phi_present == true
	input.external_boundary_crossed == true
	input.redaction_applied != true
}
