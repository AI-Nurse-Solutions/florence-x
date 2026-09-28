"""Composition and invariant tests; not human review or persistence evidence."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("teaching_builder", ROOT / "scripts/build_teaching_card_workspace.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def data(text):
    return json.loads(re.search(r'id="bundle">(.*?)</script>', text, re.DOTALL).group(1))


def test_baseline_is_exact():
    assert hashlib.sha256(builder.previous.render().encode()).hexdigest() == builder.BASELINE


def test_no_parallel_canonical_mission():
    assert data(builder.render()) == data(builder.previous.render())


def test_existing_engine_and_note_retained():
    text = builder.render()
    for filename in ("apps/learning-workspace/deliberation.js", "apps/mission-walkthrough/guide.js"):
        assert (ROOT / filename).read_text() in text


@pytest.mark.parametrize("name", ["tc-heading", "tc-compose", "tc-card", "tc-measure", "tc-companion", "tc-json"])
def test_single_required_element(name):
    assert builder.render().count('id="' + name + '"') == 1


@pytest.mark.parametrize("tag", ["script", "style"])
def test_hash_protected_content(tag):
    text = builder.render()
    code = re.search("<" + tag + ">(.*?)</" + tag + ">", text, re.DOTALL).group(1)
    value = base64.b64encode(hashlib.sha256(code.encode()).digest()).decode()
    assert tag + "-src 'sha256-" + value + "'" in text


@pytest.mark.parametrize("rule", ["connect-src 'none'", "form-action 'none'", "base-uri 'none'"])
def test_no_expanded_policy(rule):
    assert rule in builder.render()


def test_build_drift_stops(monkeypatch):
    monkeypatch.setattr(builder.previous, "render", lambda: "unexpected content")
    with pytest.raises(ValueError, match="source drift"):
        builder.render()


def test_repeat_build_and_truthful_metadata(tmp_path):
    first = builder.build(tmp_path / "a")
    second = builder.build(tmp_path / "b")
    assert first == second
    assert first["actual_nurse_participants"] == 0 and first["saving"] is False
    assert first["independent_review"] == "pending" and first["live_model"] is False


@pytest.mark.parametrize("term", ["fetch(", "localStorage", "sessionStorage", "indexedDB", "navigator.clipboard", "window.print", "innerHTML", "XMLHttpRequest"])
def test_no_new_io_or_html_execution(term):
    code = "\n".join((builder.ASSETS / p).read_text() for p in ("card.js", "ui.js"))
    assert term not in code


def test_internal_state_not_visible_json():
    code = (builder.ASSETS / "ui.js").read_text()
    assert "teaching.update(session,view)" in builder.render()
    assert "$('thinking-json')" not in code and "$('note-json')" not in code


def test_no_migration_of_existing_teaching_card_identity():
    text = (builder.ASSETS / "card.js").read_text()
    assert "tc.practice.round." in text and "tc.001" not in text
    assert "catalog_state:'not_registered'" in text
