"""Supplied-HTML UI checks. No professional identity or learning-effect claim."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".deliberation-browser-tests"
OUT.mkdir(parents=True, exist_ok=True)
html = (ROOT / "apps/learning-workspace/index.html").read_text(encoding="utf-8")
checks = []


def passed(name):
    checks.append(name)
    print("PASS " + name)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1050})
    page.set_default_timeout(5000)
    errors, requests = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda r: requests.append(r.url))
    page.route("**/*", lambda route: route.abort())
    page.set_content(html, wait_until="load")

    def record():
        return json.loads(page.locator("#thinking-json").text_content())

    def initial(text="I need to examine scope, not just citations."):
        page.get_by_label("What do you notice, and what remains uncertain?", exact=True).fill(text)
        page.get_by_role("button", name="Record initial view in memory", exact=True).click()

    def reveal():
        page.get_by_role("button", name="Reveal prepared proposal", exact=True).click()

    def choose(outcome):
        page.locator(f'input[name="learning-choice"][value="{outcome}"]').check()
        page.get_by_label("What supports your choice?", exact=True).fill("No nurse outcomes are available in this pack.")
        page.get_by_label("What alternative did you consider?", exact=True).fill("A small evaluation before relying on the guide.")
        page.get_by_label("What could follow from your choice?", exact=True).fill("Review effort and remaining uncertainty need attention.")
        if outcome == "revise":
            page.get_by_label("Your revised wording", exact=True).fill("A draft resource for evaluation, not a validated intervention.")
        page.get_by_role("button", name="Record learning choice in memory", exact=True).click()

    def restart():
        page.get_by_role("button", name="Start new comparison with baseline evidence", exact=True).click()

    assert page.get_by_role("heading", name="Think first. Compare deliberately.").is_visible()
    assert page.locator("#proposal-panel").is_hidden()
    assert page.locator("#proposal-text").text_content() == ""
    assert "ready to rely on because" not in page.locator("#thinking-json").text_content()
    assert page.locator("#compare-proposal").is_disabled()
    passed("Initial UI and inspection view do not expose the prepared proposal")

    original_mission = page.locator("#mission-json").text_content()
    assert json.loads(original_mission)["mission_id"]
    page.get_by_role("button", name="Record initial view in memory", exact=True).click()
    assert page.locator("#thinking-error").is_visible()
    assert record()["rounds"][0]["initial"] is None
    passed("Blank initial submission is refused without changing the practice record")

    initial()
    assert page.locator("#proposal-panel").is_hidden()
    assert record()["rounds"][0]["initial"]["text"]
    assert page.locator("#compare-proposal").evaluate("e=>e===document.activeElement")
    passed("Recording an initial interpretation does not automatically reveal advice")
    reveal()
    assert page.locator("#proposal-panel").is_visible()
    assert page.locator("#proposal-heading").evaluate("e=>e===document.activeElement")
    assert page.locator('input[name="learning-choice"]:checked').count() == 0
    assert record()["rounds"][0]["decision"] is None
    passed("Explicit reveal moves focus to the prepared proposal with no preselected verdict")

    page.get_by_role("button", name="Examine nist-scope", exact=True).click()
    assert page.locator("#passage-nist-scope").get_attribute("open") is not None
    assert page.locator("#passage-nist-scope summary").evaluate("e=>e===document.activeElement")
    passed("Comparison links open the exact evidence passage and move keyboard focus")

    choose("withhold")
    first_decision = record()["rounds"][0]["decision"]
    assert first_decision["outcome"] == "withhold"
    assert record()["authority"] == "no_execution_permission"
    assert "No execution permission" in page.locator("#decision-snapshot").inner_text()
    page.get_by_label("What changed your thinking—or what would change it? (Optional)", exact=True).fill("An actual evaluation would change my confidence.")
    page.get_by_role("button", name="Record self-reflection in memory", exact=True).click()
    assert record()["rounds"][0]["reflection"]
    passed("Withholding and optional reflection are normal non-authoritative outcomes")

    page.get_by_label("Choose a synthetic exercise", exact=True).select_option("case.tradeoff")
    assert page.locator("#thinking-stale").is_visible()
    assert page.locator("#decision-form button").is_disabled()
    assert page.locator('input[name="learning-choice"]').first.is_disabled()
    assert record()["rounds"][0]["decision"] == first_decision
    restart()
    state = record()
    assert len(state["rounds"]) == 2
    assert state["rounds"][0]["decision"] == first_decision
    assert state["rounds"][1]["initial"] is None
    assert page.locator("#proposal-panel").is_hidden()
    passed("Exercise change preserves earlier choice and requires another initial view")

    page.get_by_label("I am uncertain or not ready to form an interpretation.", exact=True).check()
    page.get_by_role("button", name="Record initial view in memory", exact=True).click()
    assert record()["rounds"][-1]["initial"] == {"text": None, "uncertain": True}
    reveal()
    assert "long written explanation" in page.locator("#proposal-text").text_content()
    passed("Explicit uncertainty enables comparison without forcing a fabricated opinion")

    page.get_by_label("Inspect a diagnostic scenario", exact=True).select_option("revision")
    assert page.locator("#thinking-stale").is_visible()
    assert page.locator("#decision-form button").is_disabled()
    assert page.locator('input[name="learning-choice"]').first.is_disabled()
    page.get_by_label("Inspect a diagnostic scenario", exact=True).select_option("baseline")
    assert page.locator("#thinking-stale").is_visible()
    assert record()["rounds"][-1]["closed_reason"] == "evidence_view_changed"
    passed("Returning an evidence selector to baseline does not silently reactivate a stale round")

    restart()
    initial()
    reveal()
    page.locator('input[name="learning-choice"][value="revise"]').check()
    page.get_by_label("What supports your choice?", exact=True).fill("Missing applicability.")
    page.get_by_label("What alternative did you consider?", exact=True).fill("A small trial.")
    page.get_by_label("What could follow from your choice?", exact=True).fill("More review effort.")
    page.get_by_role("button", name="Record learning choice in memory", exact=True).click()
    assert record()["rounds"][-1]["decision"] is None
    page.get_by_label("Your revised wording", exact=True).fill("Test a shorter comparison prompt before adopting a universal requirement.")
    page.get_by_role("button", name="Record learning choice in memory", exact=True).click()
    assert record()["rounds"][-1]["decision"]["outcome"] == "revise"
    assert record()["rounds"][0]["decision"] == first_decision
    passed("Revision requires new wording and never overwrites the earlier decision")

    for outcome in ("accept", "reject"):
        restart()
        initial()
        reveal()
        choose(outcome)
        assert record()["rounds"][-1]["decision"]["outcome"] == outcome
    passed("Accept and reject work through the same explicit non-executing route")

    restart()
    initial()
    page.get_by_role("button", name="Pause inspection", exact=True).click()
    assert record()["paused"] is True
    assert page.locator("#compare-proposal").is_disabled()
    assert page.locator("#new-round").is_disabled()
    page.get_by_role("button", name="Resume inspection", exact=True).click()
    assert record()["paused"] is False
    reveal()
    passed("Pause blocks deliberation transitions; resume retains the initial interpretation")

    before = record()
    for profile in ("hybrid", "hosted_test", "local"):
        page.get_by_label("Architecture preview", exact=True).select_option(profile)
        assert record() == before
        assert page.locator("#mission-json").text_content() == original_mission
    passed("Deployment previews neither move nor modify the practice or mission records")

    page.get_by_role("button", name="Clear practice entries", exact=True).click()
    assert page.get_by_role("dialog").is_visible()
    page.keyboard.press("Escape")
    assert page.get_by_role("dialog").is_hidden()
    assert record() == before
    passed("Escape cancels clearing without losing entries")
    page.get_by_role("button", name="Clear practice entries", exact=True).click()
    page.get_by_role("button", name="Clear entries now", exact=True).click()
    assert len(record()["rounds"]) == 1 and record()["rounds"][0]["initial"] is None
    assert "cleared" in page.locator("#thinking-notice").inner_text()
    assert page.locator("#mission-json").text_content() == original_mission
    passed("Explicit clear erases practice only and reports the absence of a saved copy")

    page.get_by_label("What do you notice, and what remains uncertain?", exact=True).focus()
    page.keyboard.press("Tab")
    assert page.locator("#initial-uncertain").evaluate("e=>e===document.activeElement")
    page.keyboard.press("Space")
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")
    assert record()["rounds"][0]["initial"]["uncertain"] is True
    page.keyboard.press("Enter")
    assert page.locator("#proposal-panel").is_visible()
    passed("Keyboard-only uncertainty, commitment and reveal paths work")

    restart()
    initial('<img src="unapproved.invalid" onerror="alert(1)">')
    assert page.locator("#initial-snapshot img").count() == 0
    assert '<img src=' in page.locator("#initial-snapshot").text_content()
    assert not requests
    passed("Hostile-looking learner text remains text with no resource request")

    page.locator("#practice-case").evaluate("e=>{e.add(new Option('Bad','unknown'));e.value='unknown';e.dispatchEvent(new Event('change'));}")
    assert page.locator("#new-round").is_disabled()
    assert page.locator("#thinking-stale").is_visible()
    passed("An unknown exercise cannot start or continue a decision round")
    page.get_by_label("Choose a synthetic exercise", exact=True).select_option("case.certainty")
    restart()
    initial("I would distinguish software test results from learning and deployment evidence.")
    reveal()
    page.locator("#thinking-record").evaluate("e=>e.open=false")
    page.locator("#thinking-workbench").screenshot(path=str(OUT / "judgment-desktop.png"))
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#thinking-workbench").screenshot(path=str(OUT / "judgment-mobile.png"))
    passed("Thinking and decision controls reflow at 390px without horizontal overflow")

    assert not requests and not errors, (requests, errors)
    passed("All ordinary practice interactions produce no network requests or page errors")
    page.set_content(html, wait_until="load")
    assert record()["rounds"][0]["initial"] is None
    assert page.locator("#proposal-panel").is_hidden()
    assert not errors
    passed("Document reload starts a fresh practice session rather than claiming persistence")
    browser.close()

(OUT / "browser-deliberation.json").write_text(json.dumps({"passed": len(checks), "checks": checks,
    "network_requests": requests, "page_errors": errors,
    "scope": "Offline supplied-HTML Chromium checks; no actual professional identity or outcome",
    "not_verified": ["Browser-to-localhost integration", "WCAG conformance", "Real-model effects",
                     "Nurse understanding", "Durable records", "Tamper-proof audit"]}, indent=2)+"\n")
