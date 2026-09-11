"""SS-07B: scripted keyboard handoff checks, not a screen-reader or nurse study."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(html_path: Path, output: Path, executable: str | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    checks, requests, errors = [], [], []
    text = html_path.read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=executable)
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.set_default_timeout(5000)
            page.on("request", lambda r: requests.append(r.url))
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.route("**/*", lambda r: r.abort())
            for outcome in ("accept", "revise", "reject", "withhold"):
                page.set_content(text, wait_until="load")
                assert page.locator("#compose-note").is_disabled()
                assert page.locator("#note-card").is_hidden()
                page.locator("#initial-uncertain").check()
                page.get_by_role("button", name="Record initial view in memory", exact=True).click()
                assert page.locator("#proposal-panel").is_hidden()
                page.locator("#compare-proposal").click()
                assert page.locator('input[name="learning-choice"]:checked').count() == 0
                page.locator('input[value="' + outcome + '"]').check()
                for field, value in (
                    ("reason", "The supplied source does not measure learning outcomes."),
                    ("alternative", "Discuss the limitations with an educator."),
                    ("consequence", "Review requires time; uncertainty remains explicit."),
                ):
                    page.locator("#decision-" + field).fill(value)
                if outcome == "revise":
                    page.locator("#replacement").fill("Use for personal learning, with limitations retained.")
                page.get_by_role("button", name="Record learning choice in memory", exact=True).click()
                page.locator("#compose-note").focus()
                page.keyboard.press("Enter")
                assert page.evaluate("document.activeElement.id") == "note-title", "assembly lost focus"
                heading = page.locator("#note-title")
                assert heading.is_visible() and heading.get_attribute("tabindex") == "-1"
                assert heading.get_attribute("aria-describedby") == "note-status"
                assert heading.evaluate("e => getComputedStyle(e).outlineWidth") == "3px"
                assert "not saved" in page.locator("#note-status").text_content()
                notes = json.loads(page.locator("#note-json").text_content())["notes"]
                assert len(notes) == 1 and notes[0]["choice"] == outcome
                assert notes[0]["saved"] is False and notes[0]["submitted"] is False
                assert page.locator("#compose-note").is_disabled()
                page.keyboard.press("Tab")
                assert page.locator("#note-body button").first.evaluate("e => e === document.activeElement")
                page.keyboard.press("Enter")
                assert page.locator("#passage-nist-scope summary").evaluate("e => e === document.activeElement")
                page.locator("#pause").focus()
                page.keyboard.press("Enter")
                assert page.evaluate("document.activeElement.id") == "pause"
                assert page.locator("#compose-note").is_disabled()
                page.keyboard.press("Enter")
                assert page.evaluate("document.activeElement.id") == "pause"
                assert "current_in_memory" in page.locator("#note-json").text_content()
                page.locator("#evidence-scenario").focus()
                page.locator("#evidence-scenario").select_option("changed")
                assert page.evaluate("document.activeElement.id") == "evidence-scenario"
                before = page.locator("#note-json").text_content()
                assert "historical_in_memory" in before
                # An intentionally dispatched event must still fail the normal eligibility guard.
                page.locator("#compose-note").dispatch_event("click")
                assert page.evaluate("document.activeElement.id") == "evidence-scenario"
                assert page.locator("#note-json").text_content() == before
                checks.append(outcome + ": focus, visible cue, unsaved description, source Tab order, no focus theft, stale refusal")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#note-title").focus()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert page.locator("#note-title").evaluate("e => {const r=e.getBoundingClientRect();return r.top>=0 && r.bottom<=innerHeight;}")
            page.screenshot(path=str(output / "focus-mobile.png"))
            page.set_viewport_size({"width": 1280, "height": 900})
            page.locator("#note-title").focus()
            page.screenshot(path=str(output / "focus-desktop.png"))
            page.set_content(text, wait_until="load")
            assert page.locator("#note-card").is_hidden()
            assert page.evaluate("document.activeElement.id") != "note-title"
            assert not requests and not errors, (requests, errors)
            checks.append("Narrow view preserves visibility; reload has no hidden focus or note; no observed requests/errors")
            result = {"passed": len(checks), "checks": checks, "requests": requests, "errors": errors,
                      "chromium": browser.version, "human_participants": 0,
                      "screen_reader_tested": False, "scope": "scripted_offline_keyboard_regression"}
        finally:
            browser.close()
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_path", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--executable")
    args = parser.parse_args()
    verify(args.html_path, args.output, args.executable)
