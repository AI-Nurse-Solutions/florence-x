"""Candidate-asset checks do not establish semantic truth or reviewer authority."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('pack_review', ROOT / 'scripts/build_learning_pack_review.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

@pytest.fixture
def data():
    raw, design = mod.load()
    return (raw, copy.deepcopy(design))

def test_existing_evidence_schema_and_no_admission(data):
    raw, d = data
    result = mod.validate(raw, d)
    assert len(result['passages']) == 3 and len(result['claims']) == 6
    assert all((p['semantic_support'] == 'not_assessed' for p in result['passages']))
    assert d['application_admission']['state'] == 'not_admitted'
    assert d['review']['actual_participants'] == 0

@pytest.mark.parametrize('field,value', [('reviewer', 'invented.person'), ('disposition', 'approved'), ('actual_participants', 3), ('outcomes', {'success': True}), ('independent_status', 'approved')])
def test_no_fabricated_review(data, field, value):
    raw, d = data
    d['review'][field] = value
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

@pytest.mark.parametrize('field', ['training_authorized', 'permissions_granted', 'saving_enabled', 'active_source_pack_changed'])
def test_no_activation(data, field):
    raw, d = data
    d['application_admission'][field] = True
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

@pytest.mark.parametrize('field', ['retrieval', 'excerpt_redistribution', 'adaptation', 'commercial_distribution', 'model_training', 'terms_url', 'conditions'])
def test_each_rights_dimension_required(data, field):
    raw, d = data
    d['rights'][0].pop(field)
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

def test_missing_source_rights_rejected(data):
    raw, d = data
    d['rights'].pop()
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

def test_changed_evidence_not_approved_by_unchanged_design(data):
    raw, d = data
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw + b' ', d)

def test_changed_quote_is_detected_even_with_rebound_file_hash(data):
    raw, d = data
    p = json.loads(raw)
    p['passages'][0]['quote'] = 'Changed source'
    raw = json.dumps(p).encode()
    d['evidence_sha256'] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

def test_unknown_reference_is_not_silently_dropped(data):
    raw, d = data
    d['exercises'][0]['passage_ids'] = ['unknown']
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

def test_balanced_exercises_no_automatic_score(data):
    raw, d = data
    d['exercises'][0]['kind'] = 'material_omission'
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

@pytest.mark.parametrize('field,value', [('auto_score', True), ('choices', ['accept']), ('origin', 'real_patient')])
def test_case_scope_and_choices_preserved(data, field, value):
    raw, d = data
    d['exercises'][0][field] = value
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

def test_source_does_not_validate_editorial_design(data):
    raw, d = data
    d['lessons'][0]['mapping_kind'] = 'validated_intervention'
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

def test_unaccepted_owner_not_fabricated(data):
    raw, d = data
    d['maintenance']['content_steward'] = 'someone'
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

def test_no_automatic_surveillance(data):
    raw, d = data
    d['maintenance']['surveillance_running'] = True
    with pytest.raises(ValueError, match=mod.ERROR):
        mod.validate(raw, d)

def test_repeatable_build(tmp_path):
    a = mod.build(tmp_path / 'a')
    b = mod.build(tmp_path / 'b')
    assert a == b
    assert (tmp_path / 'a/MD02_Learning_Pack.html').read_bytes() == (tmp_path / 'b/MD02_Learning_Pack.html').read_bytes()

def test_render_escapes_authored_text_and_keeps_controls_absent(data):
    raw, d = data
    d['lessons'][0]['activity'] = '<img src=x onerror=alert(1)>'
    text = mod.render(raw, d)
    assert '&lt;img' in text and '<img' not in text
    assert not re.search('<(?:input|textarea|form|script|iframe)\\b', text)
    assert "script-src 'none'" in text and "connect-src 'none'" in text
    assert 'Independent educator review pending.' in text

def test_terms_and_attribution_travel_with_excerpts(data):
    raw, d = data
    text = mod.render(raw, d)
    assert 'Republished courtesy' in text and 'CC BY 4.0' in text
    assert 'Copyright © 2011-2013 W3C' in text
    assert 'Open original source externally' in text
    assert '403' in text and 'not examined' in text
