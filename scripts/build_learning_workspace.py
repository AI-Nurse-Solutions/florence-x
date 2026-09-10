"""Build a self-contained preview from canonical validated fixtures; no network."""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/florence-core"))
from florence_core.schemas.deliberation import digest_record, parse_pack
from florence_core.schemas.learning_evidence import (
    EvidenceRequest,
    PackAdmission,
    inspect_evidence,
    load_admitted_evidence,
)
from florence_core.schemas.mission import mission_digest, parse_workspace


def render() -> str:
    bundle = parse_workspace((ROOT / "examples/portable_learning/workspace.json").read_bytes())
    data = {"bundle": bundle.model_dump(mode="json"), "mission_sha256": mission_digest(bundle.mission)}
    # Selection checks precede the fixed corpus reader; caller text is never a path.
    admission = PackAdmission.model_validate_json(
        (ROOT / "examples/learning_evidence/admission.json").read_bytes())
    request = EvidenceRequest(pack_id=admission.pack_id, version=admission.version,
                              mission_id=bundle.mission.mission_id,
                              mission_sha256=mission_digest(bundle.mission),
                              data_classification="public", purpose="professional_learning")
    pack = load_admitted_evidence(request, admission,
        lambda: (ROOT / "examples/learning_evidence/public-pack.json").read_bytes())
    as_of = datetime.fromisoformat("2026-09-09T21:48:24-07:00")
    data["evidence"] = inspect_evidence(pack, as_of=as_of)
    # Diagnostic scenarios are explicitly synthetic copies, never canonical changes.
    data["evidence_scenarios"] = {}
    for scenario, field, value in (("missing", "passage", "absent-passage"),
                                    ("revision", "expected_revision", "deliberately-old"),
                                    ("changed", "expected_excerpt_sha256", "0" * 64)):
        changed = copy.deepcopy(pack.model_dump(mode="json"))
        changed["claims"][0]["citations"][0][field] = value
        data["evidence_scenarios"][scenario] = inspect_evidence(changed, as_of=as_of)["claims"][0]
    practice = parse_pack((ROOT / "examples/learning_deliberation/practice-pack.json").read_bytes())
    if (practice.mission_id, practice.mission_sha256, practice.evidence_pack_id,
            practice.evidence_version, practice.evidence_raw_sha256) != (
            request.mission_id, request.mission_sha256, admission.pack_id,
            admission.version, admission.raw_sha256):
        raise ValueError("Practice pack does not bind the admitted mission and evidence.")
    passage_ids = {p.passage_id for p in pack.passages}
    if any(pid not in passage_ids for case in practice.cases for pid in case.passage_ids):
        raise ValueError("Unknown practice passage.")
    data["deliberation"] = {"pack": practice.model_dump(mode="json"),
                            "pack_sha256": digest_record(practice),
                            "case_digests": {c.case_id: digest_record(c) for c in practice.cases}}
    html = (ROOT / "apps/learning-workspace/index.template.html").read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))
    html = html.replace("__DELIBERATION_ENGINE__",
                        (ROOT / "apps/learning-workspace/deliberation.js").read_text(encoding="utf-8"))
    html = html.replace("__DELIBERATION_UI__",
                        (ROOT / "apps/learning-workspace/deliberation-ui.js").read_text(encoding="utf-8"))
    for kind, placeholder in (("script", "__SCRIPT_HASH__"), ("style", "__STYLE_HASH__")):
        code = re.search(r"<" + kind + r">(.*?)</" + kind + r">", html, flags=re.DOTALL).group(1)
        digest = base64.b64encode(hashlib.sha256(code.encode("utf-8")).digest()).decode("ascii")
        html = html.replace(placeholder, digest)
    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare output without writing it.")
    args = parser.parse_args()
    target = ROOT / "apps/learning-workspace/index.html"
    output = render()
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != output:
            raise SystemExit("Workspace snapshot drift; rebuild from validated fixtures.")
        print("Workspace snapshot matches validated fixtures.")
    else:
        target.write_text(output, encoding="utf-8")
        print("Built portable learning preview; no model or service invoked.")
