# Workflow overlay: policy & protocol retrieval (MVP 3).
# Green/Yellow: retrieve + summarize local policy, always cite the source section,
# version, and date; never extrapolate beyond the cited text.
package edena.examples.policy_retrieval

import rego.v1

informational if input.action_type in {"retrieve", "summarize"}

# Constraints that must ride along with any allow.
must_cite if informational

no_extrapolation_beyond_source := true

# A compliant retrieval is bounded + reversible + citation-constrained.
compliant if {
	informational
	must_cite
}
