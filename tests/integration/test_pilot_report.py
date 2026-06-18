"""The pilot evidence report (`make pilot-report`) must keep passing its own
acceptance gates — it's a believer-facing artifact, so guard it in CI."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("langgraph")

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "pilot_report.py"


def _load():
    spec = importlib.util.spec_from_file_location("pilot_report", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pilot_report_passes_all_gates():
    mod = _load()
    assert mod.main() == 0
    report = (mod.ROOT / "pilot-report.md").read_text()  # written next to the repo root
    assert "Overall: PASS" in report
    assert "❌" not in report  # no failed gate
