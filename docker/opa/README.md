# OPA (EDENA policy engine)

The `opa` service in docker-compose loads `policies/edena/*.rego` and serves a
decision API at `:8181`. To route Florence-X through OPA instead of the
in-process `LocalRuleBackend`, set `EDENA_BASE_URL=http://opa:8181` and wire
`OpaBackend` in the EDENA client.

Local query example:

    opa eval --format pretty --data policies/edena \
      --stdin-input 'data.edena.decision' < action_features.json
