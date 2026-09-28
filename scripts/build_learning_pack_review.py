"""MD-02A: validate a fixed candidate content pack and render a read-only review page.

Reuses EvidencePack. This does not admit content to the application, establish
rights by itself, authenticate a review, or create an execution permission.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from florence_core.schemas.learning_evidence import inspect_evidence, parse_evidence
from florence_core.schemas.mission import _no_constant, _unique_object

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'examples/learning_pack_md02'
ERROR = 'Candidate learning pack failed inspection; nothing was admitted.'

def validate(raw: bytes, design: dict) -> dict:
    """Check consistency only. A successful result is not human or legal review."""
    try:
        pack = parse_evidence(raw)
        if (design['pack_id'], design['version'], design['evidence_sha256']) != (pack.pack_id, pack.version, hashlib.sha256(raw).hexdigest()):
            raise ValueError('binding')
        if design['state'] != 'candidate_for_independent_review':
            raise ValueError('state')
        if design['review'] != {'independent_status': 'pending', 'reviewer': None, 'disposition': None, 'reviewed_evidence_sha256': None, 'actual_participants': 0, 'outcomes': None}:
            raise ValueError('this reviewer preview is not an approval importer')
        if design['application_admission'] != {'state': 'not_admitted', 'active_source_pack_changed': False, 'permissions_granted': False, 'training_authorized': False, 'saving_enabled': False}:
            raise ValueError('admission')
        m = design['maintenance']
        if m['state'] != 'owner_acceptance_pending' or any(m[k] is not None for k in ('content_steward', 'rights_steward', 'independent_reviewer')) or m['surveillance_running'] is not False:
            raise ValueError('maintenance not established')
        when = datetime.fromisoformat(design['created_at'])
        if datetime.fromisoformat(m['proposed_review_due_at']) <= when or not m['triggers']:
            raise ValueError('maintenance dates')
        inspected = inspect_evidence(pack, as_of=when)
        if any(p['integrity'] != 'excerpt_match' for p in inspected['passages']):
            raise ValueError('changed excerpt')
        if any(c['status'] not in ('quoted_excerpt_match', 'linked_not_verified', 'missing_information') for c in inspected['claims']):
            raise ValueError('unresolved claim')
        known = {p.passage_id for p in pack.passages}
        sources = {p.source.source_id for p in pack.passages}
        if len(design['rights']) != len(sources) or {r['source_id'] for r in design['rights']} != sources:
            raise ValueError('missing rights record')
        for r in design['rights']:
            for key in ('basis', 'terms_url', 'terms_locator', 'checked_at', 'retrieval', 'excerpt_redistribution', 'adaptation', 'commercial_distribution', 'model_training', 'conditions'):
                if not r.get(key):
                    raise ValueError('rights gap')
            if r['disposition'] != 'short_excerpt_candidate':
                raise ValueError('not an all-content license')
            if urlparse(r['terms_url']).scheme != 'https':
                raise ValueError('terms URL')
        if {e['kind'] for e in design['exercises']} != {'supported_agreement', 'material_omission', 'genuine_uncertainty'}:
            raise ValueError('exercise balance')
        for section in ('lessons', 'exercises'):
            items = design[section]
            if len({x['id'] for x in items}) != len(items):
                raise ValueError('duplicate')
            for item in items:
                if not item['passage_ids'] or not set(item['passage_ids']) <= known:
                    raise ValueError('unknown source')
        for item in design['lessons']:
            if item['mapping_kind'] != 'authored_instructional_design':
                raise ValueError('borrowed validation')
        for item in design['exercises']:
            if item['auto_score'] is not False or item['choices'] != ['accept', 'revise', 'reject', 'withhold']:
                raise ValueError('scoring or coerced choice')
            if item['origin'] != 'authored_synthetic_nonclinical':
                raise ValueError('case scope')
        return inspected
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ValueError(ERROR) from None

def load(directory: Path=PACK) -> tuple[bytes, dict]:
    raw = (directory / 'evidence-pack.json').read_bytes()
    aux = (directory / 'learning-design.json').read_bytes()
    if len(aux) > 131072:
        raise ValueError(ERROR)
    design = json.loads(aux.decode('utf-8'), object_pairs_hook=_unique_object, parse_constant=_no_constant)
    validate(raw, design)
    return (raw, design)
STYLE = '*{box-sizing:border-box}body{margin:0;background:#f6f4ee;color:#172b40;font:17px/1.6 system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:36px 24px}h1{font-size:clamp(29px,5vw,48px);line-height:1.12;max-width:800px}h2{margin-top:42px;font-size:28px}h3{font-size:21px}a{color:#005d67;overflow-wrap:anywhere}a:focus-visible,summary:focus-visible{outline:3px solid #005d67;outline-offset:4px}nav{display:flex;flex-wrap:wrap;gap:12px}nav a{padding:10px;border:1px solid #005d67;border-radius:8px}section,article,details{min-width:0}article{background:#fff;border:1px solid #cad4d7;border-radius:12px;padding:22px;margin:20px 0}.eyebrow{font-size:13px;letter-spacing:.12em;text-transform:uppercase;font-weight:750;color:#005d67}.status{background:#fff0cf;border-left:5px solid #97661b;padding:18px}.meta{color:#495968;font-size:14px}blockquote{margin:18px 0;padding:14px;border-left:4px solid #005d67;background:#f0f6f5}summary{cursor:pointer;font-weight:650;padding:12px 0;min-height:44px}details{border-top:1px solid #cad4d7;padding:8px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}p,li,dd{overflow-wrap:anywhere}dt{font-weight:700}dd{margin:0 0 16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:18px}.grid article{margin:0}.scope{font-size:15px;background:#eaf2f2;padding:14px}.notice{font-size:13px} :target{scroll-margin-top:18px}@media(max-width:440px){main{padding:24px 16px}article{padding:16px}}'

def render(raw: bytes, d: dict) -> str:
    v = validate(raw, d)
    e = html.escape

    def para(label: str, text: str) -> str:
        return '<p><strong>' + e(label) + ':</strong> ' + e(text) + '</p>'

    def links(ids: list[str]) -> str:
        return ' · '.join('<a href="#' + e(x) + '">Inspect ' + e(x) + '</a>' for x in ids)
    parts = ['<main><div class="eyebrow">Nurse AI OS / MD-02A / Candidate 0.1.0</div>', '<h1>Teach from sources.<br>Keep the limits visible.</h1>', '<p>A compact source-and-learning pack for the one-page teaching-card mission.</p>', '<div class="status" id="review-status"><strong>Independent educator review pending.</strong> Three excerpts have been checked by the development agent; that is not content approval. No participants or learning outcomes are recorded. This pack is not admitted to the application.</div>', '<p class="meta">Inspection: ' + e(d['created_at']) + ' · Source hashes identify excerpts, not truth or authority.</p>', '<nav aria-label="Review sections"><a href="#sources">Sources</a><a href="#lessons">Learning activities</a><a href="#exercises">Balanced exercises</a><a href="#maintenance">Review and maintenance</a></nav>', '<p class="scope">No patient or employer-confidential information. No responses are collected here. This is an authoring/review preview, not a scored assessment or a gated learner workflow. External links explicitly open the publisher; otherwise this file needs no network.</p>', '<section id="sources"><h2>Three sources, three different questions</h2>']
    by_id = {r['source_id']: r for r in d['rights']}
    for p in v['passages']:
        r = by_id[p['source']['source_id']]
        url = p['source']['locator'].split(' | ')[0]
        parts += ['<article class="source" id="' + e(p['passage_id']) + '"><div class="eyebrow">' + e(p['kind']) + '</div>', '<h3>' + e(p['title']) + '</h3><blockquote>' + e(p['quote']) + '</blockquote>', para('Attribution', p['attribution']), para('Inspected scope', p['inspection_scope']), '<ul>' + ''.join('<li>' + e(x) + '</li>' for x in p['limitations']) + '</ul>', '<a rel="noreferrer noopener" target="_blank" href="' + e(url) + '">Open original source externally</a>', '<details class="rights"><summary>Version, reuse terms and evidence limits</summary>', para('Source revision', p['source']['revision']), para('Rights notice', p['rights_note'])]
        for key in ('retrieval', 'excerpt_redistribution', 'adaptation', 'commercial_distribution', 'model_training'):
            parts.append(para(key.replace('_', ' ').capitalize(), r[key]))
        parts += ['<p><a rel="noreferrer noopener" target="_blank" href="' + e(r['terms_url']) + '">Read terms externally</a></p>', '<p class="notice">Rights observations are scoped developer checks, not legal advice or blanket release approval. Underlying licensed rights are unchanged.</p></details></article>']
    parts += ['</section><section id="lessons"><h2>From reading to understanding</h2><p>Original instructional design; effectiveness not established.</p><div class="grid">']
    for x in d['lessons']:
        parts += ['<article><h3>' + e(x['title']) + '</h3>', para('Objective', x['objective']), '<p>' + e(x['teaching_point']) + '</p>', para('Try', x['activity']), para('Explain back', x['teach_back']), links(x['passage_ids']), '</article>']
    parts += ['</div></section><section id="exercises"><h2>Agreement, omission, uncertainty</h2>', '<p>Form your own interpretation before opening a proposal. The reviewer discussion is an authored rationale, not an answer key or independent endorsement. No responses or choices are stored.</p>']
    for x in d['exercises']:
        parts += ['<article class="exercise" id="' + e(x['id']) + '"><h3>' + e(x['title']) + '</h3>', para('Consider first', x['prompt_before_reveal']), links(x['passage_ids']), '<details class="proposal"><summary>Reveal prepared proposal</summary><blockquote>' + e(x['proposal']) + '</blockquote>', '<p>Accept · Revise · Reject · Withhold — explain your grounds; no choice is automatically a pass.</p>', '<details class="rationale"><summary>Open authored reviewer discussion</summary><p>' + e(x['reviewer_rationale']) + '</p>', para('What could change the choice', x['what_would_change_the_choice']), para('Explain back', x['teach_back']), para('Maps to teaching-card fields', ', '.join(x['card_mapping'])), '</details></details></article>']
    parts += ['</section><section id="maintenance"><h2>Review before admission. Maintain after use.</h2>', para('Goal', d['goal']), para('Proposed audience', d['audience']), para('Owner status', 'No content steward, rights steward or independent reviewer has accepted responsibility.'), para('Next review checkpoint', d['maintenance']['proposed_review_due_at']), para('Meaning', d['maintenance']['review_window_basis']), '<p>Also review immediately when a source, license, audience or claim changes, or a material omission is reported. No surveillance job is running.</p>', '<p>Use the existing formative kit to examine source fidelity, omissions, applicability, warranted reliance, workload and understandable controls. Keep any actual feedback out of the public repository.</p>', '<details><summary>Inspect source exclusions and candidate records</summary><pre>' + e(json.dumps(d, ensure_ascii=False, indent=2)) + '</pre></details>', '<details><summary>Inspect claim and glossary records</summary><pre>' + e(json.dumps(json.loads(raw), ensure_ascii=False, indent=2)) + '</pre></details></section>', '<footer><p class="meta">Public-source review artifact. No authorizing policy, catalog admission, live model, portfolio writer or clinical function. Existing MD-01 remains unchanged.</p></footer></main>']
    sha = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    policy = "default-src 'none'; style-src 'sha256-" + sha + "'; script-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'none'"
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="' + policy + '"><title>Nurse AI OS — Teaching source pack for review</title><style>' + STYLE + '</style></head><body>' + ''.join(parts) + '</body></html>'

def build(output: Path, directory: Path=PACK) -> dict:
    raw, d = load(directory)
    text = render(raw, d)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'MD02_Learning_Pack.html').write_text(text, encoding='utf-8')
    record = {'pack_id': d['pack_id'], 'version': d['version'], 'evidence_sha256': hashlib.sha256(raw).hexdigest(), 'design_sha256': hashlib.sha256((directory / 'learning-design.json').read_bytes()).hexdigest(), 'html_sha256': hashlib.sha256(text.encode()).hexdigest(), 'independent_review': 'pending', 'application_admission': 'not_admitted', 'participants': 0, 'sources': 3, 'exercises': 3}
    (output / 'build-record.json').write_text(json.dumps(record, indent=2) + '\n')
    return record
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(build(parser.parse_args().output), indent=2))
