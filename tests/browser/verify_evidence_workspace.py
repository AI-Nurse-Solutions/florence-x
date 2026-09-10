"""Offline DOM tests only; no browser-to-server, real model or nurse evaluation."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".evidence-workspace-tests"
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
    assert page.get_by_role("heading", name="Inspect the evidence, not just the answer.").is_visible()
    assert page.locator("#source-cards details").count() == 3
    assert page.locator("#claim-cards article").count() == 7
    assert not errors
    passed("Three source excerpts and seven claim records render")
    original = page.locator("#mission-json").text_content()
    assert json.loads(original)["mission_id"]
    assert "not automatically verified" in page.locator("#evidence-workspace").inner_text()
    passed("The workspace discloses the difference between integrity and semantic support")
    for kind, count in (("retrieved_evidence", 3), ("generated_synthesis", 1), ("inference", 2), ("missing_information", 1)):
        page.get_by_label("Show claim type", exact=True).select_option(kind)
        assert page.locator("#claim-cards article").count() == count
        assert page.locator("#claim-cards article").first.get_attribute("data-kind") == kind
    passed("All four claim-type filters select the intended records")
    assert "no observed nurse-learning" in page.locator("#claim-cards").inner_text()
    passed("Missing outcome evidence remains an explicit gap")
    page.get_by_label("Show claim type", exact=True).select_option("all")
    page.get_by_role("button", name="Read linked excerpt", exact=True).first.click()
    assert page.locator("#passage-nist-scope").get_attribute("open") is not None
    assert page.locator("#passage-nist-scope summary").evaluate("e=>e===document.activeElement")
    assert "MEASURE 2.5" in page.locator("#passage-nist-scope").inner_text()
    passed("A claim opens its exact linked passage and gives keyboard focus")
    assert "not appraised" in page.locator("#passage-nist-scope").inner_text()
    assert "not an evidence-expiry date" in page.locator("#passage-nist-scope").inner_text()
    passed("Source quality and maintenance dates are not presented as appraisal")
    for scenario, state in (("missing", "reference_missing"), ("revision", "revision_changed"), ("changed", "excerpt_changed")):
        page.get_by_label("Inspect a diagnostic scenario").select_option(scenario)
        assert page.locator("#scenario-note").is_visible()
        card = page.locator('[data-claim-id="quote-nist-scope"]')
        assert state in card.inner_text()
        assert "Reference needs attention" in card.inner_text()
        assert card.locator("button").count() == 0
        assert page.locator("#mission-json").text_content() == original
    passed("Missing, changed-revision and changed-hash scenarios flag the claim without changing the mission")
    page.get_by_label("Inspect a diagnostic scenario").select_option("baseline")
    assert page.locator("#scenario-note").is_hidden()
    assert "Quote matches" in page.locator('[data-claim-id="quote-nist-scope"]').inner_text()
    passed("Restoring the baseline restores inspection, not a fabricated repair")
    assert "Unsupported" in page.locator('[data-claim-id="exercise-unsupported"]').inner_text()
    assert "support not verified" in page.locator('[data-claim-id="synthesis-check"]').inner_text()
    passed("An uncited teaching example and linked synthesis never gain verified support")
    page.get_by_text("Working glossary · definitions are not permissions", exact=True).click()
    assert page.locator("#glossary dt").count() == 6
    assert "independent review pending" in page.locator("#glossary").inner_text()
    passed("Six working glossary entries expose review status")
    for profile in ("hybrid", "hosted_test", "local"):
        page.get_by_label("Architecture preview").select_option(profile)
        assert page.locator("#mission-json").text_content() == original
        assert page.locator("#source-cards details").count() == 3
    passed("All deployment previews retain the same mission and evidence pack")
    page.locator("#evidence-workspace").screenshot(path=str(OUT / "evidence-desktop.png"))
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#evidence-workspace").screenshot(path=str(OUT / "evidence-mobile.png"))
    passed("Evidence cards and controls reflow at 390px without horizontal overflow")
    assert not requests, requests
    passed("All ordinary interactions issue zero network requests")
    payload = json.loads(re.search(r'<script type="application/json" id="bundle">(.*?)</script>', html, re.DOTALL).group(1))
    payload["evidence"]["passages"][0]["quote"] = '<img src="https://unapproved.invalid" onerror="alert(1)">'
    hostile = re.sub(r'(<script type="application/json" id="bundle">).*?(</script>)',
                     lambda m: m.group(1) + json.dumps(payload).replace("<", "\\u003c") + m.group(2), html, flags=re.DOTALL)
    page.set_content(hostile, wait_until="load")
    assert page.locator("#source-cards img").count() == 0
    assert page.locator("#passage-nist-scope blockquote").text_content().startswith("<img")
    assert not requests
    passed("Source text is rendered as text, not executable HTML")
    payload["evidence"]["mission_id"] = "other-mission"
    invalid = re.sub(r'(<script type="application/json" id="bundle">).*?(</script>)',
                     lambda m: m.group(1) + json.dumps(payload).replace("<", "\\u003c") + m.group(2), html, flags=re.DOTALL)
    page.set_content(invalid, wait_until="load")
    assert page.locator("#error").is_visible()
    assert page.locator("#source-cards details").count() == 0
    passed("Evidence bound to another mission is not displayed")
    assert not errors
    browser.close()

(OUT / "browser-evidence.json").write_text(json.dumps({"passed": len(checks), "checks": checks,
    "network_requests": requests, "page_errors": errors,
    "scope": "Offline supplied-HTML Chromium checks; network blocked by test routes",
    "not_verified": ["Browser-to-localhost integration", "Live source refresh", "Semantic entailment", "WCAG conformance", "Nurse understanding"]}, indent=2) + "\n")
