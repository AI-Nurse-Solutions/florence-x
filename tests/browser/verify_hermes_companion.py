"""Offline Chromium frame checks. This is NOT a Hermes Desktop/Electron test."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

page_path = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
checks = []


def passed(name):
    checks.append(name)
    print('PASS ' + name)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1080})
    page.set_default_timeout(6000)
    requests, errors = [], []
    page.on('request', lambda req: requests.append(req.url))
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.route('**/*', lambda route: route.abort())
    page.set_content(page_path.read_text(), wait_until='load')
    frame = page.frame_locator('#companion')
    assert page.get_by_text('Browser integration preview — not Hermes Desktop.', exact=True).is_visible()
    assert frame.locator('#thinking-heading').text_content() == 'Think first. Compare deliberately.'
    passed('Presentation preview opens the actual retained workbench, not a Hermes impersonation')
    assert frame.locator('#mission-id').text_content() == 'mission.public-learning.0001'
    original = frame.locator('#mission-json').text_content()
    assert frame.locator('#source-cards details').count() == 3
    passed('Same mission and three source excerpts are present')
    assert frame.locator('#compare-proposal').is_disabled()
    frame.locator('#initial-text').fill('I need evidence of usefulness, not just a polished answer.')
    frame.get_by_role('button', name='Record initial view in memory', exact=True).click()
    assert frame.locator('#proposal-panel').is_hidden()
    frame.locator('#compare-proposal').click()
    assert frame.locator('#proposal-panel').is_visible()
    assert frame.locator('input[name="learning-choice"]:checked').count() == 0
    passed('Commit before deliberate reveal works inside the sandbox without a default verdict')
    frame.locator('input[value="withhold"]').check()
    frame.locator('#decision-reason').fill('No observed nurse-learning outcomes in this pack.')
    frame.locator('#decision-alternative').fill('Run a small formative evaluation.')
    frame.locator('#decision-consequence').fill('Added review effort, with less unsupported certainty.')
    frame.get_by_role('button', name='Record learning choice in memory', exact=True).click()
    data = json.loads(frame.locator('#thinking-json').text_content())
    assert data['rounds'][0]['decision']['outcome'] == 'withhold'
    assert data['authority'] == 'no_execution_permission'
    passed('Withhold is a recorded learning choice, not execution permission')
    frame.locator('#evidence-scenario').select_option('missing')
    assert frame.locator('#thinking-stale').is_visible()
    assert frame.locator('#reflection-text').is_disabled()
    passed('Changed evidence still closes the comparison')
    child = page.frames[1]
    page.evaluate("window.__privateTestSentinel='PARENT_PRIVATE_SENTINEL'")
    outcome = child.evaluate("""() => {
      try { return { leaked: parent.__privateTestSentinel }; }
      catch (e) { return { blocked: e.name }; }
    }""")
    assert outcome == {'blocked': 'SecurityError'}
    passed('Child cannot read the parent renderer origin in this browser test')
    storage = child.evaluate("""() => {
      try { localStorage.setItem('test','fixture'); return 'unexpected-storage'; }
      catch(e) { return e.name; }
    }""")
    assert storage == 'SecurityError'
    passed('Opaque-origin frame cannot use localStorage')
    before = len(requests)
    denied = child.evaluate("""async () => {
      try { await fetch('https://example.invalid/blocked-fixture'); return false; }
      catch (_) { return true; }
    }""")
    assert denied and len(requests) == before
    passed('Child CSP blocks the synthetic fetch before any network request')
    # Form events are permitted for the existing JS workflow; transmission is not.
    child.evaluate("""() => {
      const f=document.createElement('form'); f.action='https://example.invalid/blocked-form';
      f.method='POST'; document.body.appendChild(f); f.submit(); f.remove();
    }""")
    assert len(requests) == before
    passed('Form-action CSP blocks synthetic form transmission despite internal form-event permission')
    assert page.locator('#companion').get_attribute('sandbox') == 'allow-scripts allow-forms'
    assert child.evaluate("() => { try { top.location.hash='escape'; return false; } catch(e) { return e.name==='SecurityError'; } }")
    passed('Top navigation denied without broadening sandbox permissions')
    assert frame.locator('#mission-json').text_content() == original
    assert not requests and not errors
    passed('Mission unchanged; no ordinary network requests or page exceptions')
    page.screenshot(path=str(out / 'companion-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    assert child.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    frame.locator('#thinking-workbench').scroll_into_view_if_needed()
    page.screenshot(path=str(out / 'companion-mobile.png'))
    passed('390px parent and child layouts do not overflow horizontally')
    page.set_content(page_path.read_text(), wait_until='load')
    record = json.loads(page.frame_locator('#companion').locator('#thinking-json').text_content())
    assert record['rounds'][0]['initial'] is None
    assert record['rounds'][0]['decision'] is None
    passed('Reload discards temporary practice entries as disclosed')
    browser.close()

(out / 'browser-results.json').write_text(json.dumps({'checks': checks, 'passed': len(checks),
    'native_hermes_test': False, 'network_requests': requests, 'errors': errors}, indent=2))
