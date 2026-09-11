"""SS-07A composition checks; no live models, user study or portfolio store."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('walkthrough_builder', ROOT / 'scripts/build_mission_walkthrough.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def bundle(text):
    return json.loads(re.search(r'<script type="application/json" id="bundle">(.*?)</script>',
                               text, flags=re.DOTALL).group(1))


def test_same_canonical_data_not_a_parallel_record():
    old = (ROOT / 'apps/learning-workspace/index.html').read_text()
    assert bundle(builder.render()) == bundle(old)


def test_source_pin_and_original_engine_preserved():
    source = (ROOT / 'apps/learning-workspace/index.html').read_bytes()
    assert hashlib.sha256(source).hexdigest() == builder.BASELINE_SHA256
    assert (ROOT / 'apps/learning-workspace/deliberation.js').read_text() in builder.render()


@pytest.mark.parametrize('anchor', ['journey-heading','mission-heading','evidence-heading',
                                   'thinking-heading','note-heading','limits-heading'])
def test_journey_has_distinct_usable_anchors(anchor):
    assert builder.render().count('id="' + anchor + '"') == 1


@pytest.mark.parametrize('rule', ["connect-src 'none'", "form-action 'none'", "base-uri 'none'"])
def test_existing_boundary_directives_not_relaxed(rule):
    assert rule in builder.render()


def test_csp_hashes_cover_actual_code():
    import base64
    text = builder.render()
    for tag in ('script','style'):
        code = re.search('<' + tag + '>(.*?)</' + tag + '>', text, flags=re.DOTALL).group(1)
        digest = base64.b64encode(hashlib.sha256(code.encode()).digest()).decode()
        assert tag + "-src 'sha256-" + digest + "'" in text


def test_composition_refuses_missing_or_duplicate_anchor():
    for value in ('no match','twice twice'):
        with pytest.raises(ValueError, match='source drift'):
            builder.once(value, 'twice', 'replacement')


def test_changed_workspace_refuses_build(tmp_path, monkeypatch):
    target = tmp_path / 'apps/learning-workspace/index.html'
    target.parent.mkdir(parents=True)
    target.write_text('different source')
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    with pytest.raises(ValueError, match='source drift'):
        builder.render()


def test_repeat_build_is_identical_and_human_results_remain_unknown(tmp_path):
    a = builder.build(tmp_path / 'a'); b = builder.build(tmp_path / 'b')
    assert a == b
    assert a['observed_nurse_participants'] == 0
    assert a['human_evaluation'] == 'not_performed'
    assert a['portfolio_save_enabled'] is False and a['live_inference'] is False
    assert (tmp_path/'a/walkthrough.html').read_bytes() == (tmp_path/'b/walkthrough.html').read_bytes()


def test_guide_reuses_internal_state_not_visible_json():
    guide = (ROOT/'apps/mission-walkthrough/guide.js').read_text()
    assert 'guide.update(session,view)' in builder.render()
    assert "$('thinking-json')" not in guide
    assert 'currentSession.rounds.at(-1)' in guide


def test_note_data_excludes_initial_and_reflection():
    guide = (ROOT/'apps/mission-walkthrough/guide.js').read_text()
    assert 'r.initial' not in guide and 'r.reflection' not in guide
    assert 'r.case.proposal' not in guide  # Reject/withhold do not re-publish the proposed assertion.
    for prohibited in ('fetch(', 'localStorage','sessionStorage','XMLHttpRequest','innerHTML','postMessage','clipboard'):
        assert prohibited not in guide


def test_kit_retains_unknown_results_and_separate_review():
    kit = (ROOT/'docs/evaluation/SS07_FORMATIVE_KIT.md').read_text()
    assert 'Actual participants observed: **0**' in kit
    assert 'not a validated assessment instrument' in kit
    assert 'No employee ranking' in kit
    assert 'independent' in kit and 'prompted' in kit and 'not observed' in kit
    assert 'not SUS or NASA-TLX scores' in kit
