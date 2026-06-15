# Agentic software safety review (MVP 4): inspect, never auto-execute.
package edena.examples.code_execution

import rego.v1

# Execution on production is hard-blocked.
hard_block if {
	input.action_type == "execute_code"
	contains(lower(input.action_id), "prod")
}

# Non-production execution is Orange: senior + technical steward + blast radius.
require_dual_control if {
	input.action_type == "execute_code"
	not hard_block
}
