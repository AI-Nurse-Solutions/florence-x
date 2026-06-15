from florence_connectors.fhir import FhirReadConnector

BUNDLE = "examples/_fixtures/fhir/synthetic_icu_patient_bundle.json"


def test_fhir_connector_returns_refs_not_narrative():
    c = FhirReadConnector(BUNDLE)
    assert "read_patient_summary" in c.list_actions()
    out = c.invoke("read_observations", {})
    assert out["count"] >= 1
    assert all("/" in rid for rid in out["resource_ids"])  # refs, not raw content
