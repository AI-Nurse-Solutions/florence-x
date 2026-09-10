"""SS-05A: replay two INVENTED envelopes on the same admitted public/synthetic tasks.

The generated report is test evidence, not model performance. No inference, URL
transport, credentials, learner input, durable portfolio, or model SDK is used.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for package in ("florence-core", "florence-model-router"):
    sys.path.insert(0, str(ROOT / "packages" / package))
from florence_core.schemas.deliberation import parse_pack
from florence_core.schemas.inference import (
    ContextSpan, FixtureModelProfile, InferenceRequest, OfflineAdmission, fingerprint,
)
from florence_core.schemas.learning_evidence import EvidenceRequest, PackAdmission, load_admitted_evidence
from florence_model_router import ModelRouter
from florence_model_router.inference import replay_inference

NOW = datetime.fromisoformat("2026-09-10T00:00:00+00:00")  # Fixed TEST clock, not current authority.


def demo_inputs():
    profiles = tuple(FixtureModelProfile.model_validate(p) for p in json.loads(
        (ROOT / "examples/model_substitution/models.json").read_text()))
    admission = PackAdmission.model_validate_json(
        (ROOT / "examples/learning_evidence/admission.json").read_bytes())
    selection = EvidenceRequest.model_validate(admission.model_dump(exclude={"raw_sha256"}))
    pack = load_admitted_evidence(selection, admission,
        lambda: (ROOT / "examples/learning_evidence/public-pack.json").read_bytes())
    practice = parse_pack((ROOT / "examples/learning_deliberation/practice-pack.json").read_bytes())
    if (practice.mission_sha256, practice.evidence_raw_sha256) != (pack.mission_sha256, admission.raw_sha256):
        raise ValueError("Mismatched fixed learning resources")
    requests = []
    for case in practice.cases:
        spans = tuple(ContextSpan(passage_id=p.passage_id, source=p.source, excerpt=p.quote)
                      for p in pack.passages if p.passage_id in case.passage_ids)
        requests.append(InferenceRequest(schema_version="0.1.0", request_id="request." + case.case_id,
            mission_id=pack.mission_id, mission_sha256=pack.mission_sha256, task_id=case.case_id,
            task=case.question, context=spans, data_classification="public", purpose="professional_learning",
            execution_mode="offline_fixture", output_contract="resource_review_v1",
            required_features=("text", "structured_output"), max_output_tokens=512,
            max_output_bytes=4000, timeout_ms=1000))
    return tuple(requests), profiles


def fixture_admission(request, profiles, destinations=("device", "external_provider")):
    """Construct a test fixture only. This must never be used to authorize a live call."""
    return OfflineAdmission(admission_id="admission.fixture", scope="offline_fixture_only",
        authority="no_deployment_authority", policy_ref="fixture-routing-rules.0.1.0",
        disposition="allow_fixture", request_sha256=fingerprint(request),
        profile_sha256s=tuple(fingerprint(p) for p in profiles), destinations=destinations,
        valid_from=NOW - timedelta(seconds=1), expires_at=NOW + timedelta(hours=1),
        max_cost_units=10, max_attempts=1)


def fixture_wires(request, status="ok"):
    review = {"summary": "Compare the linked evidence with the proposal; retain uncertainties for human review.",
              "limitations": ["Prepared synthetic response, not a model output.",
                              "No nurse-learning benefit or semantic support has been verified."],
              "cited_passages": [p.passage_id for p in request.context],
              "semantic_support": "not_verified", "review_status": "not_independently_reviewed"}
    usage = {"output_tokens": 80, "elapsed_ms": 100, "cost_units": 1,
             "basis": "invented_fixture_values_not_model_performance"}
    return {
        "fixture.device.text": json.dumps({"status": status,
            "text": json.dumps(review) if status == "ok" else None, "usage": usage}).encode(),
        "fixture.cloud.object": json.dumps({"state": status,
            "review": review if status == "ok" else None, "usage": usage}).encode(),
    }


class ReadTrace(dict):
    """Track response access to verify the dispatcher did not consume a fallback."""
    def __init__(self, values):
        super().__init__(values)
        self.reads = []

    def __getitem__(self, key):
        self.reads.append(key)
        return super().__getitem__(key)


def evaluate():
    requests, profiles = demo_inputs()
    rows = []
    for request in requests:
        before = request.model_dump_json()
        results = []
        for profile in profiles:
            admission = fixture_admission(request, (profile,))
            trace = ReadTrace(fixture_wires(request))
            plan = ModelRouter(allow_cloud=True).plan_inference(request, profiles, admission, now=NOW)
            result = replay_inference(request, profiles, admission, trace, now=NOW)
            assert result.outcome == "proposal_ready" and trace.reads == [profile.profile_id]
            assert request.model_dump_json() == before
            results.append({"profile": profile.model_dump(mode="json"), "plan": plan.model_dump(mode="json"),
                            "result": result.model_dump(mode="json"), "response_reads": trace.reads})
        assert results[0]["result"]["proposal"] == results[1]["result"]["proposal"]
        rows.append({"task_id": request.task_id, "task": request.task,
                     "request_sha256": fingerprint(request), "mission_sha256": request.mission_sha256,
                     "outcomes": results, "normalized_fixture_payload_equal": True})
    request = requests[0]
    local_only = fixture_admission(request, profiles, ("device",))
    trace = ReadTrace(fixture_wires(request, "timed_out"))
    failed = replay_inference(request, profiles, local_only, trace, now=NOW)
    assert failed.outcome == "timed_out" and trace.reads == [profiles[0].profile_id]
    deny_trace = ReadTrace(fixture_wires(request))
    denied = replay_inference(request, profiles, None, deny_trace, now=NOW)
    assert denied.outcome == "denied" and not deny_trace.reads
    return {"sprint": "SS-05A", "scope": "offline_contract_test_only", "fixture_clock": NOW.isoformat(),
            "real_model_calls": 0, "network_transports_implemented": 0, "tasks": rows,
            "timeout_probe": {"result": failed.model_dump(mode="json"), "response_reads": trace.reads},
            "missing_admission_probe": {"result": denied.model_dump(mode="json"), "response_reads": deny_trace.reads},
            "live_comparison": "not_performed", "model_quality": "not_evaluated",
            "human_review_cost": "not_measured", "privacy_classifier": "not_implemented",
            "source_scope": "existing admitted SS-02 excerpts; no live currency check or new appraisal"}


def render(report):
    esc = html.escape
    items = "".join(f'<article><h3>{esc(r["task_id"])}</h3><p>{esc(r["task"])}</p>'
        '<p class="ok">Two fixture envelopes → one normalized draft contract</p>'
        f'<code>{esc(r["request_sha256"])}</code></article>' for r in report["tasks"])
    style = '''body{margin:0;background:#f4f3ee;color:#182f3c;font:16px/1.6 system-ui}header{background:#102b3c;color:white;padding:25px 5vw}main{max-width:1080px;margin:auto;padding:28px 20px}h1{font-size:clamp(28px,5vw,44px);line-height:1.15}h2{font-size:24px}.tag{letter-spacing:.13em;font-size:12px;text-transform:uppercase}.note{padding:18px;border-left:4px solid #805a10;background:#fff4d8}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:22px 0}article{padding:22px;background:white;border:1px solid #ccd8d5;border-radius:12px;margin:16px 0}.ok{color:#06675f;font-weight:700}code,pre{font-size:12px;overflow-wrap:anywhere;white-space:pre-wrap}pre{max-height:450px;overflow:auto;background:#102b3c;color:#eff8f5;padding:18px}summary{cursor:pointer;min-height:44px}a{color:#06675f}a:focus-visible,summary:focus-visible{outline:3px solid #825b10;outline-offset:4px}@media(max-width:650px){.grid{grid-template-columns:1fr}}'''
    sh = base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'sha256-{sh}\'; '
        'connect-src \'none\'; form-action \'none\'; base-uri \'none\'">'
        '<title>SS-05A · Model contract evidence</title><style>' + style + '</style>'
        '<header><div class="tag">Nurse AI OS / Speed Sprint SS-05A</div>'
        '<h1>Change the adapter.<br>Keep the boundaries.</h1></header><main>'
        '<p class="note"><strong>Offline fixture report—not a live-model comparison.</strong> '
        'Both adapters run in memory. “Device” and “external provider” are simulated placements. '
        'No model, cloud account, credentials or learner notes are connected.</p>'
        '<div class="grid"><article><h2>What stays the same</h2><p>Mission identity, selected source passages, '
        'task, output contract and the requirement for human review.</p></article>'
        '<article><h2>What cannot change silently</h2><p>Destination, admitted profile or context. '
        'A timeout ends one attempt; it does not redirect work to the cloud.</p></article></div>'
        '<h2>Three fixed tasks, two envelope formats</h2>' + items +
        '<article><h2>Failure probes</h2><p><strong>Missing admission:</strong> denied, zero response reads.</p>'
        '<p><strong>Device fixture timeout:</strong> stopped after one read; cloud fixture not consumed.</p></article>'
        '<p>Identical fixture payloads demonstrate normalization—not equal model quality. '
        'Valid citations do not prove support; all draft output remains unverified. '
        'Live provider compatibility, authenticated authorization, human benefit and review cost remain untested.</p>'
        '<details><summary>Inspect actual replay results</summary><pre>' + esc(json.dumps(report, indent=2)) +
        '</pre></details><p>Knowledge supplies evidence. Judgment challenges the draft. Capability keeps the call bounded. '
        'Contribution preserves provenance and failure evidence.</p></main></html>')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Explicit test-evidence folder; not a portfolio.")
    args = parser.parse_args()
    report = evaluate()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "report.html").write_text(render(report))
    print("3 fixed tasks × 2 fixture envelopes normalized; 2 stop probes passed; zero model calls.")
