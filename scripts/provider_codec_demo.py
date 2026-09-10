"""SS-05B: reproduce documented wire-format tests. No provider request is sent."""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for package in ("florence-core", "florence-model-router"):
    sys.path.insert(0, str(ROOT / "packages" / package))

from florence_core.schemas.inference import fingerprint
from florence_core.schemas.provider_codec import ProviderCodecSpec
from florence_model_router.provider_codecs import decode_fixture, prepare_request
from model_contract_demo import demo_inputs


def evaluate():
    fixtures = json.loads((ROOT / "examples/provider_codecs/responses.json").read_text())
    baseline = json.loads((ROOT / "examples/provider_codecs/interface-baseline.json").read_text())
    rows = []
    for request in demo_inputs()[0]:
        original = request.model_dump_json()
        outputs = []
        for protocol in ("ollama_chat_v1", "openai_chat_completions_v1"):
            spec = ProviderCodecSpec(profile_id="codec.test", protocol=protocol,
                request_model=fixtures["model"], expected_response_model=fixtures["model"])
            prepared = prepare_request(request, spec)
            wire = copy.deepcopy(fixtures[protocol])
            proposal = copy.deepcopy(fixtures["proposal"])
            proposal["cited_passages"] = [span.passage_id for span in request.context]
            msg = wire["message"] if protocol == "ollama_chat_v1" else wire["choices"][0]["message"]
            msg["content"] = json.dumps(proposal)
            response = decode_fixture(request, prepared, json.dumps(wire).encode())
            assert response.outcome == "proposal_ready" and response.transport_calls == 0
            outputs.append({"prepared": prepared.model_dump(mode="json"),
                            "result": response.model_dump(mode="json")})
        assert outputs[0]["result"]["proposal"] == outputs[1]["result"]["proposal"]
        assert request.model_dump_json() == original
        rows.append({"task": request.task, "task_id": request.task_id,
            "canonical_request_sha256": fingerprint(request), "outputs": outputs})
    return {"sprint": "SS-05B", "scope": "documented_provider_subset_offline_only",
        "transport_calls": 0, "live_provider_compatibility": "not_tested",
        "real_model_performance": "not_measured", "authored_fixtures": True,
        "fallback": "no_routing_or_fallback_interface", "cases": rows,
        "source_baseline": baseline,
        "limitations": ["Equal outputs were authored to match; this is not evidence of equal model quality.",
            "A valid citation and response structure do not establish semantic support or authority.",
            "Missing token usage remains unknown; no price, latency or zero-retention claim is made.",
            "Offline codecs accept already supplied records; they are not authenticated admission or network containment."]}


def render(report):
    style = ('body{margin:0;background:#f4f3ee;color:#182f3c;font:16px/1.55 system-ui}'
        'header{background:#102b3c;color:white;padding:30px max(24px,5vw)}'
        'main{max-width:1120px;margin:auto;padding:26px 22px}h1{font-size:clamp(30px,5vw,47px);line-height:1.1}'
        'h2{font-size:24px}.tag{letter-spacing:.15em;font-size:12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}'
        'article{background:white;border:1px solid #cad8d4;border-radius:14px;padding:22px;margin:18px 0}'
        '.warning{padding:18px;background:#fff3d4;border-left:4px solid #825b10}.ok{color:#06675f;font-weight:700}'
        'code,pre{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}pre{max-height:500px;overflow:auto;'
        'background:#102b3c;color:#eff8f5;padding:18px;border-radius:10px}summary{cursor:pointer;min-height:44px;align-content:center}'
        'summary:focus-visible{outline:3px solid #825b10;outline-offset:3px}@media(max-width:650px){.grid{grid-template-columns:1fr}}')
    digest = base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
    cards = "".join('<article class="case"><h3>' + html.escape(row["task_id"]) + '</h3><p>' +
        html.escape(row["task"]) + '</p><p class="ok">Two documented formats → the same unverified review record</p>' +
        '<code>' + row["canonical_request_sha256"] + '</code></article>' for row in report["cases"])
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'sha256-{digest}\'; '
        'connect-src \'none\'; form-action \'none\'; base-uri \'none\'">'
        '<title>SS-05B · Documented provider codecs</title><style>' + style + '</style></head><body>'
        '<header><div class="tag">NURSE AI OS / SPEED SPRINT SS-05B</div><h1>Different provider formats.<br>The same professional record.</h1></header>'
        '<main><p class="warning"><strong>Offline codec verification—not live inference.</strong> '
        'The formats come from inspected official interfaces. Responses and model names are authored fixtures. '
        'No credentials, models or learner notes are connected.</p><div class="grid">'
        '<article><h2>Ollama Chat</h2><code>/api/chat</code><p>Explicit non-streaming, schema in format, and an output-token option. '
        'Only complete text replies become proposals. Thinking is discarded and disclosed.</p></article>'
        '<article><h2>OpenAI Chat Completions</h2><code>/v1/chat/completions</code><p>Explicit non-streaming, strict schema, '
        'one choice, store=false, and a completion-token limit. Refusal and truncation remain distinct outcomes.</p></article></div>'
        '<h2>Three retained learning tasks</h2>' + cards +
        '<article><h2>What does not change</h2><p>The mission and request hashes, selected sources, source limitations, '
        'and required human review remain in Nurse AI OS. No codec grants permission or selects a fallback provider.</p></article>'
        '<p class="warning">Ollama Cloud structured outputs are excluded by the inspected guide. OpenAI store=false is '
        'not a zero-retention guarantee. Neither provider has been contacted for inference.</p>'
        '<details><summary>Inspect requests, normalized results and interface sources</summary><pre id="results">' +
        html.escape(json.dumps(report, indent=2)) + '</pre></details>'
        '<p>Knowledge preserves evidence. Judgment challenges the proposal. Capability bounds translation. '
        'Contribution preserves reviewable results. Live substitution, human benefit and deployment remain unverified.</p>'
        '</main></body></html>')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = evaluate()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "report.html").write_text(render(report))
    print("Three fixed tasks x two documented codec subsets passed; zero provider transport calls.")
