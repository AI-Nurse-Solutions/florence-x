# EDENA decision entrypoint.
#
# Consumes the feature document produced by
# florence_edena.risk_features.extract_risk_features(action) and returns the
# governance decision. Precedence (Ambiguity escalates upward):
#   blocked > red > orange > yellow > green
#
# Parity with the pure-Python LocalRuleBackend is enforced by
# tests/policy/test_parity.py.
package edena

import rego.v1

decision := blocked_decision if is_blocked
else := red_decision if is_red
else := orange_decision if is_orange
else := yellow_decision if is_yellow
else := green_constrained if is_green_constrained
else := green_allow

# Shared helpers ------------------------------------------------------------
phi_present if input.phi_present == true

requester := input.requester_role
