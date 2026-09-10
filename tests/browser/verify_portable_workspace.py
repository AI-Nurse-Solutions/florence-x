"""Offline supplied-HTML checks, NOT browser-to-localhost or hosted verification."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".workspace-evidence"
OUT.mkdir(parents=True, exist_ok=True)
html = (ROOT / "apps/learning-workspace/index.html").read_text(encoding="utf-8")
checks = []


def ok(name: str) -> None:
    checks.append(name)
    print("PASS " + name)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1050})
    page.set_default_timeout(5000)
    errors = []
    requests = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: requests.append(request.url))
    page.route("**/*", lambda route: route.abort())
    page.set_content(html, wait_until="load")
    assert page.get_by_role("heading", name="The mission stays yours.").is_visible()
    assert not errors, errors
    assert "evaluate an AI-generated" in page.locator("#goal").inner_text()
    ok("Desktop shell renders the bundled learning mission without script errors")
    identity = page.locator("#mission-id").inner_text()
    digest = page.locator("#digest").inner_text()
    record = page.locator("#mission-json").text_content()
    assert json.loads(record)["mission_id"] == identity
    assert page.locator("#p-inference").inner_text() == "Your device"
    ok("Local target distinguishes device inference from actual inactive processing")
    page.get_by_label("Architecture preview").select_option("hybrid")
    assert page.locator("#p-inference").inner_text() == "External model provider"
    assert page.locator("#p-storage").inner_text() == "Your device"
    ok("Hybrid target shows external inference with device-authoritative records")
    page.get_by_label("Architecture preview").select_option("hosted_test")
    assert page.locator("#p-harness").inner_text() == "Personal cloud workspace"
    assert page.locator("#p-storage").inner_text() == "Personal cloud workspace"
    assert page.locator("#mission-id").inner_text() == identity
    assert page.locator("#digest").inner_text() == digest
    assert page.locator("#mission-json").text_content() == record
    ok("Hosted target comparison preserves mission identity, digest and record bytes")
    page.get_by_role("button", name="Inspect portable record").click()
    assert page.locator("#record").get_attribute("open") is not None
    assert page.locator("#record summary").evaluate("node => node === document.activeElement")
    ok("Record control reveals JSON and moves keyboard focus")
    page.get_by_role("button", name="Pause inspection", exact=True).click()
    assert page.get_by_label("Architecture preview").is_disabled()
    assert "no work was saved" in page.locator("#notice").inner_text()
    ok("Pause is labeled as temporary inspection, not saved work or job cancellation")
    page.get_by_role("button", name="Resume inspection", exact=True).click()
    assert page.get_by_label("Architecture preview").is_enabled()
    assert page.locator("#mission-json").text_content() == record
    ok("Resume preserves the same unsaved fixture record")
    page.evaluate("""() => { const s=document.getElementById('profile');
        const o=document.createElement('option'); o.value='unapproved'; o.textContent='unapproved';
        s.append(o); s.value='unapproved'; s.dispatchEvent(new Event('change')); }""")
    assert page.locator("#error").is_visible()
    assert page.locator("#p-inference").inner_text() == "Unavailable"
    assert page.locator("#mission-json").text_content() == record
    ok("Tampered profile selection refuses the view without changing the mission")
    page.get_by_label("Architecture preview").select_option("local")
    assert page.locator("#error").is_hidden()
    ok("A valid preview can recover from a rejected selection")
    page.locator("#record").evaluate("node => node.open=false")
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(OUT / "workspace-desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("window.scrollTo(0,0)")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.get_by_role("heading", name="Your learning mission", exact=True).is_visible()
    page.screenshot(path=str(OUT / "workspace-mobile.png"), full_page=True)
    ok("390px viewport keeps the goal readable without horizontal overflow")
    assert not requests, requests
    ok("Rendering and all preview interactions issue zero network requests")
    payload = json.loads(re.search(r'<script type="application/json" id="bundle">(.*?)</script>', html, re.DOTALL).group(1))
    payload["bundle"]["mission"]["goal"] = '<img src="unapproved.invalid" onerror="alert(1)">'
    hostile = re.sub(r'(<script type="application/json" id="bundle">).*?(</script>)',
                     lambda m: m.group(1) + json.dumps(payload).replace("<", "\\u003c") + m.group(2), html, flags=re.DOTALL)
    page.set_content(hostile, wait_until="load")
    assert page.locator("#goal img").count() == 0
    assert page.locator("#goal").inner_text().startswith("<img")
    assert not requests
    ok("Hostile-looking record text renders as text, not HTML or resource requests")
    assert not errors, errors
    browser.close()

(OUT / "browser-tests.json").write_text(json.dumps({"passed": len(checks), "checks": checks,
    "network_requests": requests, "page_errors": errors,
    "scope": "Chromium supplied-HTML DOM checks with network routes denied",
    "not_verified": ["Browser-to-localhost integration", "Hermes integration", "Cloud hosting", "WCAG conformance", "Nurse usability or learning outcomes"]}, indent=2)+"\n")
