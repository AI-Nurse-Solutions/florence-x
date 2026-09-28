"""Compose MD-01 from the exact reviewed SS-07B source snapshot; no runtime IO."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path

import build_mission_walkthrough as previous

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "apps/teaching-card"
BASELINE = "461114cd4ca3f68b2faa32591b3610985bb0b69a43625cfe067f460464b5f389"


def render() -> str:
    text = previous.render()
    if hashlib.sha256(text.encode()).hexdigest() != BASELINE:
        raise ValueError("MD-01 source drift: review and pin the new baseline before composition.")
    extension = "\n".join((ASSETS / name).read_text(encoding="utf-8") for name in ("card.js", "ui.js"))
    retained = (ROOT / "apps/mission-walkthrough/guide.js").read_text(encoding="utf-8")
    text = previous.once(text, retained, extension + "\n" + retained)
    text = previous.once(text, "guide.update(session,view);", "guide.update(session,view);teaching.update(session,view);")
    text = previous.once(text, "guide.clear();resetForms();", "guide.clear();teaching.clear();resetForms();")
    anchor = '<section class="card journey" id="review-note"'
    text = previous.once(text, anchor, (ASSETS / "panel.html").read_text(encoding="utf-8") + "\n" + anchor)
    text = previous.once(text, "</style>", (ASSETS / "style.css").read_text(encoding="utf-8") + "\n</style>")
    text = previous.once(text, '<title>Nurse AI OS — Guided Learning Walkthrough</title>',
                         '<title>Nurse AI OS — Teaching-card learning mission</title>')
    text = previous.once(text, 'Speed Sprint / SS-07A / Guided prototype', 'Mission Delivery / MD-01 / Draft prototype')
    text = previous.once(text, '<div class="journey-facts">',
                         '<p><a href="#tc-heading">New · Prepare your teaching card</a></p><div class="journey-facts">')
    for tag in ("script", "style"):
        body = re.search("<" + tag + ">(.*?)</" + tag + ">", text, flags=re.DOTALL).group(1)
        value = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
        text, count = re.subn(tag + r"-src 'sha256-[^']+'", tag + "-src 'sha256-" + value + "'", text, count=1)
        if count != 1:
            raise ValueError("MD-01 CSP composition failed.")
    return text


def build(output: Path) -> dict:
    text = render()
    output.mkdir(parents=True, exist_ok=True)
    (output / "walkthrough.html").write_text(text, encoding="utf-8")
    record = {"increment": "MD-01", "baseline_sha256": BASELINE,
              "walkthrough_sha256": hashlib.sha256(text.encode()).hexdigest(),
              "scope": "offline_memory_only_prototype", "independent_review": "pending",
              "actual_nurse_participants": 0, "live_model": False, "saving": False}
    (output / "build-record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    print(json.dumps(build(parser.parse_args().output), indent=2))
