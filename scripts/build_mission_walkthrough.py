"""Build an additive, offline guided view. Existing mission and Hermes bytes stay unchanged."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'apps/mission-walkthrough'
BASELINE_SHA256 = '7309a1167202377e649e183c621937725cc4c047f009bdd7ef39591a7ad1e060'
ERROR = 'Walkthrough source drift; rebuild only after an explicit source review.'


def once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(ERROR)
    return text.replace(old, new, 1)


def render() -> str:
    raw = (ROOT / 'apps/learning-workspace/index.html').read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASELINE_SHA256:
        raise ValueError(ERROR)
    text = raw.decode('utf-8')
    ui = (ROOT / 'apps/learning-workspace/deliberation-ui.js').read_text(encoding='utf-8')
    # Explicit build-time composition points in a pinned UI, not runtime screen scraping.
    updated = once(ui, '  function render(){',
        (ASSETS / 'guide.js').read_text(encoding='utf-8') + '\n  function render(){')
    updated = once(updated, '  }\n  function showCase(){',
        '    guide.update(session,view);\n  }\n  function showCase(){')
    updated = once(updated, "      resetForms();showCase();render();$('thinking-notice')",
        "      guide.clear();resetForms();showCase();render();$('thinking-notice')")
    text = once(text, ui, updated)
    text = once(text, '<div class="layout" id="workspace">',
        (ASSETS / 'guide.html').read_text(encoding='utf-8') + '\n<div class="layout" id="workspace">')
    anchor = '<details class="card record" id="record">'
    text = once(text, anchor, (ASSETS / 'note.html').read_text(encoding='utf-8') + '\n' + anchor)
    text = once(text, '</style>', (ASSETS / 'style.css').read_text(encoding='utf-8') + '\n</style>')
    text = once(text, 'Speed Sprint / SS-03 / Prototype', 'Speed Sprint / SS-07A / Guided prototype')
    text = once(text, '<title>Nurse AI OS — Portable Learning Mission</title>',
        '<title>Nurse AI OS — Guided Learning Walkthrough</title>')
    for tag in ('script', 'style'):
        body = re.search('<' + tag + '>(.*?)</' + tag + '>', text, flags=re.DOTALL).group(1)
        sha = base64.b64encode(hashlib.sha256(body.encode('utf-8')).digest()).decode('ascii')
        text, count = re.subn(tag + r"-src 'sha256-[^']+'", tag + "-src 'sha256-" + sha + "'", text, count=1)
        if count != 1:
            raise ValueError(ERROR)
    return text


def build(output: Path) -> dict:
    text = render()
    output.mkdir(parents=True, exist_ok=True)
    (output / 'walkthrough.html').write_text(text, encoding='utf-8')
    evidence = {'source_workspace_sha256':BASELINE_SHA256,
        'walkthrough_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
        'artifact':'derived_offline_walkthrough', 'native_hermes_tested':False,
        'live_inference':False, 'portfolio_save_enabled':False,
        'observed_nurse_participants':0, 'human_evaluation':'not_performed'}
    (output / 'build-record.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(json.dumps(build(parser.parse_args().output), indent=2))
