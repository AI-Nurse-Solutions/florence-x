"""SS-06A authored save scenarios. Report creation is NOT a portfolio write."""
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
sys.path.insert(0, str(ROOT / "packages/florence-core"))
from florence_core.portfolio_contract import assess_save_fixture
from florence_core.schemas.catalog import CatalogManifest
from florence_core.schemas.portfolio import (
    PortfolioEnvelope,
    SaveApprovalFixture,
    SaveAttemptFixture,
    SaveIntentFixture,
    SavePolicyFixture,
    SaveReadBackFixture,
    SaveScenario,
    digest,
)

NOW = datetime.fromisoformat("2026-09-10T12:00:00+00:00")  # Fixed simulation clock.


def replace(record, **changes):
    return type(record).model_validate({**record.model_dump(), **changes})


def example():
    catalog = CatalogManifest.model_validate_json(
        (ROOT / "examples/artifact_catalog/catalog.json").read_bytes())
    artifact = catalog.artifacts[0]
    content = (ROOT / "examples/artifact_catalog/source-checking-guide.md").read_text()
    mission = json.loads((ROOT / "examples/portable_learning/workspace.json").read_text())["mission"]
    mission_hash = hashlib.sha256(json.dumps(mission, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode()).hexdigest()
    entry = PortfolioEnvelope(mission_id=mission["mission_id"], mission_sha256=mission_hash,
        owner_ref=artifact.owner_ref, workspace_ref="workspace.synthetic.demo",
        destination_ref="portfolio.synthetic.private", artifact=artifact,
        learning_decision_sha256=hashlib.sha256(b"synthetic learning choice, not save approval").hexdigest(),
        purpose="Inspect what would be required before saving a source-linked learning guide.")
    intent = SaveIntentFixture(intent_id="intent.synthetic.save", actor_ref=entry.owner_ref,
        envelope_sha256=digest(entry), logical_key=entry.logical_key(), capability_version="0.1.0",
        policy_ref="fixture.save.rules", policy_version="0.1.0")
    policy = SavePolicyFixture(intent_sha256=digest(intent), policy_ref=intent.policy_ref,
        policy_version=intent.policy_version, disposition="allow_in_simulation",
        valid_from=NOW - timedelta(hours=1), expires_at=NOW + timedelta(hours=1))
    approval = SaveApprovalFixture(intent_sha256=digest(intent), policy_sha256=digest(policy),
        approver_ref=entry.owner_ref, disposition="confirm_in_simulation",
        approved_at=NOW - timedelta(minutes=20), expires_at=NOW + timedelta(minutes=20))
    return SaveScenario(envelope=entry, content_utf8=content, intent=intent, policy=policy,
                        approval=approval, audit_available_now=True, as_of=NOW)


def attempted(s, reported_state="reported_success"):
    attempt = SaveAttemptFixture(operation_ref="operation.synthetic.one", intent_sha256=digest(s.intent),
        policy_sha256=digest(s.policy), approval_sha256=digest(s.approval),
        logical_key=s.envelope.logical_key(), envelope_sha256=digest(s.envelope),
        dispatched_at=NOW - timedelta(minutes=10), reported_state=reported_state, audit_recorded=True)
    return replace(s, attempt=attempt)


def matched(s):
    s = attempted(s)
    return replace(s, readback=SaveReadBackFixture(operation_ref=s.attempt.operation_ref,
        observed_at=NOW - timedelta(minutes=5), state="found", envelope=s.envelope, content_utf8=s.content_utf8))


def scenarios():
    s = example()
    m = matched(s)
    yield "missing-approval", "No approval is not permission", replace(s, approval=None)
    yield "ready-disabled", "Even matching preflight cannot enable this prototype", s
    yield "claimed-save", "Reported success without read-back stays unknown", attempted(s)
    yield "matching-readback", "Matching supplied bytes are fixture evidence, not a real save", m
    yield "repeat-request", "Repeating the same observation issues no duplicate write", m
    yield "corrupt-readback", "Changed content cannot inherit a matching envelope", replace(m,
        readback=replace(m.readback, content_utf8="Different content"))
    yield "metadata-conflict", "Changed purpose conflicts at the same create-only target", replace(m,
        envelope=replace(m.envelope, purpose="Changed purpose"))
    yield "interrupted", "An interrupted attempt must reconcile, not automatically retry", attempted(s, "outcome_unknown")
    yield "in-flight", "An in-flight operation is not a completed save", attempted(s, "in_flight")
    yield "expired-now", "Current expiry does not erase earlier matching evidence", replace(m,
        as_of=NOW + timedelta(hours=2))
    yield "revoked-after", "Later revocation stops new work without rewriting history", replace(m,
        approval_revoked_at=NOW - timedelta(minutes=2))
    yield "audit-lost", "Missing audit remains visible alongside byte evidence", replace(m, audit_available_now=False)
    yield "failure-with-bytes", "A failure report can conflict with read-back evidence", replace(m,
        attempt=replace(m.attempt, reported_state="reported_failure"))
    yield "absent-read", "An absent read does not prove an in-flight write cannot later commit", replace(m,
        readback=replace(m.readback, state="absent", envelope=None, content_utf8=None))


def evaluate():
    cases = [{"id": key, "title": title, "result": assess_save_fixture(s).model_dump(mode="json")}
             for key, title, s in scenarios()]
    assert all(x["result"]["storage_operations"] == 0 and not x["result"]["successful_receipt_issued"] for x in cases)
    return {"sprint": "SS-06A", "scope": "offline contract and failure evidence only",
            "real_persistence": "not_observed", "operational_saving": "disabled", "cases": cases,
            "example_envelope": example().envelope.model_dump(mode="json")}


def render(report):
    style = ("body{margin:0;background:#f4f3ee;color:#182f3c;font:16px/1.55 system-ui}"
        "header{padding:30px max(22px,5vw);background:#102b3c;color:white}"
        "main{max-width:1120px;margin:auto;padding:24px}h1{font-size:clamp(30px,5vw,48px);line-height:1.1}"
        ".grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}article{background:white;padding:20px;"
        "border:1px solid #ccd9d4;border-radius:12px}h2{font-size:21px}.tag{font-size:12px;letter-spacing:.12em}"
        ".warning{padding:18px;background:#fff3d4;border-left:4px solid #825b10}.state{font-weight:700;color:#06675f}"
        "code,pre{font-size:12px;overflow-wrap:anywhere;white-space:pre-wrap}pre{padding:18px;background:#102b3c;"
        "color:#eef8f5;max-height:460px;overflow:auto}summary{min-height:44px;align-content:center;cursor:pointer}"
        "summary:focus-visible{outline:3px solid #825b10}@media(max-width:650px){.grid{grid-template-columns:1fr}}")
    sha = base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
    cards = "".join('<article class="scenario"><h2>' + html.escape(row["title"]) + '</h2><p class="state">' +
        html.escape(row["result"]["evidence_state"].replace('_', ' ')) + '</p><p>' +
        html.escape(row["result"]["next_step"].replace('_', ' ')) + '</p><details><summary>Inspect checks</summary><pre>' +
        html.escape(json.dumps(row["result"], indent=2)) + '</pre></details></article>' for row in report["cases"])
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'sha256-{sha}\'; '
        'connect-src \'none\'; base-uri \'none\'; form-action \'none\'"><title>SS-06A · Truthful save contract</title>'
        '<style>' + style + '</style></head><body><header><div class="tag">NURSE AI OS / SPEED SPRINT SS-06A</div>'
        '<h1>A save claim needs evidence.</h1><p>Owner. Destination. Exact artifact. Separate approval. Read-back.</p></header><main>'
        '<p class="warning"><strong>No portfolio has been saved.</strong> Every scenario is authored test data. '
        'This report performs no storage, model or network operation. Matching fixture bytes are not proof of persistence.</p>'
        '<p>Current permission checks and historical observations answer different questions. A later revocation cannot erase '
        'what was observed; a matching record cannot grant permission to act again.</p><div class="grid">' + cards + '</div>'
        '<p class="warning">Successful receipts issued: 0. Operational saving: disabled. Independent review, authenticated '
        'identity, real storage and recovery testing remain pending.</p><details><summary>Inspect full report and example envelope</summary>'
        '<pre id="results">' + html.escape(json.dumps(report, indent=2)) + '</pre></details>'
        '<p>Contribution preserves provenance. Knowledge carries sources and limits. Judgment keeps approval separate. '
        'Capability requires observable outcomes and recovery.</p></main></body></html>')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.output / "report.html").write_text(render(report), encoding="utf-8")
    print(f"{len(report['cases'])} authored scenarios evaluated; zero storage operations or successful receipts.")
