# Workflow-specific overlay for the ICU handoff synthesizer (MVP 1).
# Baseline tier is Yellow: may draft, may not chart, may not send.
package edena.examples.icu_handoff

import rego.v1

deny_reason contains "agent_may_not_write_to_ehr" if input.action_type == "write_record"
deny_reason contains "agent_may_not_send_messages" if input.action_type == "send_message"

# A compliant ICU handoff draft is a Yellow, human-validated action.
compliant if {
	input.action_type == "draft"
	input.phi_present == true
	count(deny_reason) == 0
}
