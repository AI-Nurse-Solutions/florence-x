"""Scripted MD-01 UI checks. No participants, live AI or storage are involved."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(html_path: Path, output: Path, executable: str | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    text = html_path.read_text(encoding="utf-8")
    checks, requests, errors = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=executable)
        page = None
        try:
            def load():
                nonlocal page
                if page:
                    page.close()
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                page.set_default_timeout(5000)
                page.on("request", lambda r: requests.append(r.url))
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                page.route("**/*", lambda r: r.abort())
                page.set_content(text, wait_until="load")

            def decide(outcome="withhold", reason="A working link alone does not establish support."):
                page.locator("#initial-text").fill("PRIVATE_INITIAL_SENTINEL")
                page.get_by_role("button", name="Record initial view in memory", exact=True).click()
                assert page.locator("#proposal-panel").is_hidden()
                page.locator("#compare-proposal").click()
                assert page.locator('input[name="learning-choice"]:checked').count() == 0
                page.locator('input[value="' + outcome + '"]').check()
                page.locator("#decision-reason").fill(reason)
                page.locator("#decision-alternative").fill("Read the original passage before teaching.")
                page.locator("#decision-consequence").fill("Additional review takes time and may change the draft.")
                if outcome == "revise":
                    page.locator("#replacement").fill("Treat the resource as a candidate pending source appraisal.")
                page.get_by_role("button", name="Record learning choice in memory", exact=True).click()
                page.locator("#reflection-text").fill("PRIVATE_REFLECTION_SENTINEL")
                page.get_by_role("button", name="Record self-reflection in memory", exact=True).click()

            def assemble():
                page.locator("#tc-compose").focus()
                page.keyboard.press("Enter")
                assert page.locator("#tc-card").is_visible(), page.locator("#tc-status").text_content()
                assert page.evaluate("document.activeElement.id") == "tc-title"
                return json.loads(page.locator("#tc-json").text_content())["drafts"]

            load()
            assert page.locator("#tc-compose").is_disabled()
            assert page.locator("#tc-card").is_hidden()
            checks.append("No teaching card before a recorded learning choice")
            for outcome in ("accept", "revise", "reject", "withhold"):
                load()
                decide(outcome)
                assert page.locator("#tc-compose").is_enabled()
                assert page.locator("#tc-card").is_hidden()
                drafts = assemble()
                raw = page.locator("#tc-json").text_content()
                card = drafts[-1]
                assert card["provenance"]["choice"]["outcome"] == outcome
                assert card["saved"] is False and card["submitted"] is False
                assert card["independent_review"] == "pending"
                assert card["display_state"] == "current_in_memory"
                assert "PRIVATE_INITIAL_SENTINEL" not in raw and "PRIVATE_REFLECTION_SENTINEL" not in raw
                proposal = page.locator("#proposal-text").text_content()
                assert proposal not in page.locator("#tc-card").text_content()
                assert "Independent review pending" in page.locator("#tc-card").text_content()
                assert page.locator("#tc-card").evaluate("e => e.getBoundingClientRect().height <= 960")
                assert page.locator("#tc-compose").is_disabled()
                page.keyboard.press("Tab")
                assert page.locator("#tc-card button").first.evaluate("e => e === document.activeElement")
                page.keyboard.press("Enter")
                assert page.locator("#passage-nist-scope summary").evaluate("e => e === document.activeElement")
                page.locator("#compose-note").click()
                note = json.loads(page.locator("#note-json").text_content())["notes"][-1]
                assert note["choice"] == outcome
                assert note["reason"] == card["provenance"]["choice"]["reason"]
                checks.append(outcome + ": exact choice, one-page target, private-field exclusion, honest status, source focus, retained note")
            page.locator("#tc-audience").select_option("Peer-learning draft")
            assert "historical_in_memory" in page.locator("#tc-json").text_content()
            page.locator("#tc-audience").select_option("Personal learning")
            assert "historical_in_memory" in page.locator("#tc-json").text_content()
            drafts = assemble()
            assert len(drafts) == 2 and drafts[0]["display_state"] == "historical_in_memory"
            checks.append("Audience edits invalidate drafts permanently; reassembly retains history")
            original_goal = page.locator("#tc-goal").input_value()
            page.locator("#tc-goal").fill("Explain a different source limitation.")
            page.locator("#tc-goal").fill(original_goal)
            assert "current_in_memory" not in page.locator("#tc-json").text_content()
            assemble()
            checks.append("Objective change and change-back cannot reactivate an old card")
            page.locator("#pause").click()
            assert page.locator("#tc-compose").is_disabled()
            assert page.locator("#tc-goal").is_disabled()
            assert page.evaluate("document.activeElement.id") == "pause"
            page.locator("#pause").click()
            assert "current_in_memory" in page.locator("#tc-json").text_content()
            checks.append("Pause blocks assembly without stealing focus; resume preserves draft")
            page.locator("#evidence-scenario").select_option("changed")
            raw = page.locator("#tc-json").text_content()
            assert "current_in_memory" not in raw
            assert page.locator("#tc-compose").is_disabled()
            page.locator("#tc-compose").dispatch_event("click")
            assert page.locator("#tc-json").text_content() == raw
            page.locator("#evidence-scenario").select_option("baseline")
            assert page.locator("#tc-compose").is_disabled()
            checks.append("Changed evidence and synthetic bypass cannot produce a current card")
            page.locator("#new-round").click()
            decide("revise")
            assert len(assemble()) == 4
            checks.append("A fresh comparison produces a new linked card, not overwritten review")
            page.locator("#clear-practice").click()
            page.locator("#cancel-clear").click()
            assert len(json.loads(page.locator("#tc-json").text_content())["drafts"]) == 4
            page.locator("#clear-practice").click()
            page.locator("#confirm-clear").click()
            assert page.locator("#tc-card").is_hidden()
            assert page.locator("#tc-json").text_content() == "No teaching card assembled."
            assert page.locator("#tc-compose").is_disabled()
            checks.append("Cancelled clear retains drafts; confirmed clear removes both card and practice")
            load()
            decide("withhold", '<img src=x onerror=alert(1)> [not a link](https://example.invalid)')
            assemble()
            assert page.locator("#tc-card img, #tc-card a").count() == 0
            assert "<img" in page.locator("#tc-card").text_content()
            checks.append("Untrusted input renders as text without HTML, link, or script execution")
            load()
            decide("withhold", "x" * 1700)
            page.locator("#tc-compose").click()
            assert page.locator("#tc-card").is_hidden()
            assert "exceeds the readable one-page" in page.locator("#tc-status").text_content()
            assert len(page.locator("#decision-reason").input_value()) == 1700
            checks.append("Overlong content is refused explicitly without truncating original input")
            load()
            decide("withhold", "Line\n" * 180)
            page.locator("#tc-compose").click()
            assert page.locator("#tc-card").is_hidden()
            assert "exceeds the readable one-page" in page.locator("#tc-status").text_content()
            checks.append("Actual geometry rejects tall text inside the character budget")
            load()
            decide("revise")
            assemble()
            for width in (320, 390, 768, 1280):
                page.set_viewport_size({"width": width, "height": 1000})
                page.locator("#tc-companion").evaluate("e => e.open = true")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
                assert page.locator("#tc-card").evaluate("e => e.scrollWidth <= e.clientWidth"), width
                checks.append(str(width) + "px: full card and expanded source companion reflow without horizontal clipping")
            page.locator("#tc-companion").evaluate("e => e.open = false")
            page.locator("#tc-card").screenshot(path=str(output / "teaching-card.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#tc-card").scroll_into_view_if_needed()
            page.screenshot(path=str(output / "mobile.png"))
            load()
            assert page.locator("#tc-card").is_hidden()
            assert page.locator("#tc-json").text_content() == "No teaching card assembled."
            assert page.locator('a[download],button:has-text("Save portfolio")').count() == 0
            assert not requests and not errors, (requests, errors)
            checks.append("Reload loses temporary drafts; no observed requests, console errors or save interface")
            result = {"passed": len(checks), "checks": checks, "requests": requests, "errors": errors,
                      "chromium": browser.version, "nurse_participants": 0,
                      "scope": "scripted_supplied_html_not_operational_portfolio"}
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
