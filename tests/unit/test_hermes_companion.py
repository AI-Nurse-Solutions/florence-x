"""SS-04A packaging and refusal checks; no actual Hermes host is used."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('hermes_builder', ROOT / 'scripts/build_hermes_companion.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.fixture
def inputs():
    a = json.loads((ROOT / 'integrations/hermes-desktop/assessment.json').read_text())
    w = (ROOT / 'apps/learning-workspace/index.html').read_bytes()
    return a, w


def test_source_snapshot_is_pinned(inputs):
    a, w = inputs
    assert builder.inspect_inputs(a, w).encode() == w
    assert a['upstream']['commit'] == builder.UPSTREAM
    assert a['separate_records']['deployment_authorization'] is None


@pytest.mark.parametrize('field', ['default_enabled', 'runtime_enabled', 'network_enabled', 'persistence_enabled'])
@pytest.mark.parametrize('bad', [True, 'false', 0, None])
def test_activation_flags_cannot_be_coerced(inputs, field, bad):
    a, w = inputs
    a[field] = bad
    with pytest.raises(ValueError, match=builder.ERROR):
        builder.inspect_inputs(a, w)


@pytest.mark.parametrize('path,value', [
    (('upstream', 'commit'), 'a' * 40),
    (('workspace', 'path'), '../../private.txt'),
    (('workspace', 'mission_id'), 'another.mission'),
    (('separate_records', 'deployment_authorization'), 'self-approved'),
])
def test_unknown_identity_and_authority_refused(inputs, path, value):
    a, w = inputs
    a[path[0]][path[1]] = value
    with pytest.raises(ValueError, match=builder.ERROR):
        builder.inspect_inputs(a, w)


@pytest.mark.parametrize('raw', [b'', b'not a workspace', b'x' * 180001, None])
def test_bad_bytes_refused(inputs, raw):
    a, _ = inputs
    with pytest.raises(ValueError, match=builder.ERROR):
        builder.inspect_inputs(a, raw)


def test_modified_workspace_does_not_repin_itself(inputs):
    a, w = inputs
    old = copy.deepcopy(a)
    with pytest.raises(ValueError, match=builder.ERROR):
        builder.inspect_inputs(a, w + b'PRIVATE_SENTINEL')
    assert a == old


def test_nonpublic_fixture_is_not_packaged_even_with_matching_hash(inputs):
    a, w = inputs
    changed = w.replace(b'"data_classification": "public"', b'"data_classification": "internal"', 1)
    a['workspace']['sha256'] = builder.sha(changed)
    with pytest.raises(ValueError, match=builder.ERROR):
        builder.inspect_inputs(a, changed)


def test_security_policy_change_refused_even_if_rehashed(inputs):
    a, w = inputs
    changed = w.replace(b"connect-src 'none'", b'connect-src *')
    a['workspace']['sha256'] = builder.sha(changed)
    with pytest.raises(ValueError, match=builder.ERROR):
        builder.inspect_inputs(a, changed)


def test_bad_script_hash_refused(inputs):
    a, w = inputs
    changed = w.replace(b"'use strict';", b"'use strict'; /* changed */", 1)
    a['workspace']['sha256'] = builder.sha(changed)
    with pytest.raises(ValueError, match=builder.ERROR):
        builder.inspect_inputs(a, changed)


def test_template_requires_one_embedding_slot(inputs):
    _, w = inputs
    for template in ('no slot', '__WORKSPACE_BASE64____WORKSPACE_BASE64__'):
        with pytest.raises(ValueError, match=builder.ERROR):
            builder.render_plugin(template, w.decode())


def test_build_is_reproducible_and_does_not_install(tmp_path, monkeypatch):
    hermes_home = tmp_path / 'hermes-not-touched'
    monkeypatch.setenv('HERMES_HOME', str(hermes_home))
    first = builder.build(tmp_path / 'a')
    second = builder.build(tmp_path / 'b')
    assert first == second
    assert first['installed'] is False and first['runtime_connected'] is False
    assert not hermes_home.exists()
    for name in ('plugin.js', 'preview.html', 'build-record.json'):
        assert (tmp_path / 'a' / name).read_bytes() == (tmp_path / 'b' / name).read_bytes()


def test_preview_is_not_misrepresented_as_native(inputs):
    _, w = inputs
    p = builder.render_preview(w.decode())
    assert 'not Hermes Desktop' in p
    assert 'sandbox="allow-scripts allow-forms"' in p
    assert 'allow-same-origin' not in p
    assert 'srcdoc=' in p and '<iframe src=' not in p
