"""Offline Chromium frame checks; never a native Hermes/Electron safety claim."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(page_path: Path, out: Path, executable: str | None = None) -> dict:
    """Record settled outcomes, including the loss caused by rejected navigation."""
    out.mkdir(parents=True, exist_ok=True)
    source = page_path.read_text(encoding='utf-8')
    checks, requests, errors, messages, navigations = [], [], [], [], []
    result = {'native_hermes_test': False, 'completed': False, 'checks': checks,
              'network_requests': requests, 'errors': errors, 'console': messages,
              'navigations': navigations, 'failure': None}

    def passed(name: str) -> None:
        checks.append(name)
        print('PASS ' + name)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=executable, headless=True)
            result['chromium_version'] = browser.version
            try:
                page = browser.new_page(viewport={'width': 1440, 'height': 1080})
                page.set_default_timeout(6000)
                page.on('request', lambda req: requests.append(req.url))
                page.on('pageerror', lambda err: errors.append(str(err)))
                page.on('console', lambda msg: messages.append({'type': msg.type, 'text': msg.text}))
                page.on('framenavigated', lambda f: navigations.append(f.url))
                # An attempted request is counted BEFORE this backstop aborts it.
                # An empty count is required; interception is never evidence of CSP success.
                page.route('**/*', lambda route: route.abort())
                page.set_content(source, wait_until='load')
                frame = page.frame_locator('#companion')
                title = 'Browser integration preview — not Hermes Desktop.'
                assert page.get_by_text(title, exact=True).is_visible()
                assert frame.locator('#thinking-heading').text_content() == 'Think first. Compare deliberately.'
                passed('Preview opens retained workbench; it does not impersonate native Hermes')
                assert frame.locator('#mission-id').text_content() == 'mission.public-learning.0001'
                original = frame.locator('#mission-json').text_content()
                assert frame.locator('#source-cards details').count() == 3
                passed('Same mission and three primary excerpts are present')
                assert frame.locator('#compare-proposal').is_disabled()
                frame.locator('#initial-text').fill('I need evidence of usefulness, not just a polished answer.')
                frame.get_by_role('button', name='Record initial view in memory', exact=True).click()
                assert frame.locator('#proposal-panel').is_hidden()
                frame.locator('#compare-proposal').click()
                assert frame.locator('#proposal-panel').is_visible()
                assert frame.locator('input[name="learning-choice"]:checked').count() == 0
                passed('Initial view precedes deliberate reveal; no verdict is selected')
                frame.locator('input[value="withhold"]').check()
                frame.locator('#decision-reason').fill('No observed nurse-learning outcomes in this pack.')
                frame.locator('#decision-alternative').fill('Run a small formative evaluation.')
                frame.locator('#decision-consequence').fill('More review effort, less unsupported certainty.')
                frame.get_by_role('button', name='Record learning choice in memory', exact=True).click()
                record = json.loads(frame.locator('#thinking-json').text_content())
                assert record['rounds'][0]['decision']['outcome'] == 'withhold'
                assert record['authority'] == 'no_execution_permission'
                passed('Withhold records a learning choice, not execution permission')
                frame.locator('#evidence-scenario').select_option('missing')
                assert frame.locator('#thinking-stale').is_visible()
                assert frame.locator('#reflection-text').is_disabled()
                passed('Changed evidence closes the comparison')
                child = page.locator('#companion').element_handle().content_frame()
                page.evaluate("window.__privateTestSentinel='PARENT_PRIVATE_SENTINEL'")
                outcome = child.evaluate("""() => {
                  try { return { leaked: parent.__privateTestSentinel }; }
                  catch (e) { return { blocked: e.name }; }
                }""")
                assert outcome == {'blocked': 'SecurityError'}
                passed('Child cannot read the parent-origin test sentinel')
                storage = child.evaluate("""() => {
                  try { localStorage.setItem('test','fixture'); return 'unexpected-storage'; }
                  catch(e) { return e.name; }
                }""")
                assert storage == 'SecurityError'
                passed('Opaque-origin child cannot use localStorage')
                before = len(requests)
                denied = child.evaluate("""async () => {
                  try { await fetch('https://example.invalid/blocked-fixture'); return false; }
                  catch (_) { return true; }
                }""")
                assert denied and len(requests) == before
                passed('Synthetic fetch is rejected before a request reaches the test backstop')
                assert page.locator('#companion').get_attribute('sandbox') == 'allow-scripts allow-forms'
                parent_url = page.url
                assert child.evaluate("""() => {
                  try { top.location.hash='escape'; return false; }
                  catch(e) { return e.name==='SecurityError'; }
                }""")
                assert page.url == parent_url
                passed('Top navigation is denied in the live child, before the destructive form probe')
                assert frame.locator('#mission-json').text_content() == original
                assert not requests and not errors
                passed('Mission preserved; ordinary workflow causes no observed requests or page errors')
                page.screenshot(path=str(out / 'companion-desktop.png'))
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
                assert child.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
                frame.locator('#thinking-workbench').scroll_into_view_if_needed()
                page.screenshot(path=str(out / 'companion-mobile.png'))
                passed('390px parent and child layouts have no horizontal overflow')

                # Rejected form navigation can replace srcdoc with a browser error document.
                # Observe that commit before evaluating anything in the replaced child.
                # No ignored exception, unconditional retry, or immediate-count-only assertion.
                before = len(requests)
                with page.expect_event('framenavigated', predicate=lambda f: f == child):
                    child.evaluate("""() => {
                      const f=document.createElement('form');
                      f.action='https://example.invalid/blocked-form'; f.method='POST';
                      document.body.appendChild(f); f.submit(); f.remove();
                    }""")
                child.wait_for_load_state('load')
                assert child.url == 'chrome-error://chromewebdata/', child.url
                assert len(requests) == before
                assert any("form-action 'none'" in m['text'] and 'blocked-form' in m['text']
                           for m in messages)
                assert any("frame-src 'self'" in m['text'] for m in messages)
                assert page.url == parent_url
                assert page.get_by_text(title, exact=True).is_visible()
                result['form_probe'] = {'settled_url': child.url, 'new_requests': len(requests) - before,
                                        'parent_preserved': True, 'practice_document_preserved': False}
                passed('Rejected form navigation settles on a local error document; no observed request')
                assert child.locator('#thinking-workbench').count() == 0
                passed('Availability loss is recorded, not mislabeled as workbench completion')

                # Explicit test-driver reload; not an implemented auto-recovery feature.
                page.set_content(source, wait_until='load')
                restored = page.frame_locator('#companion')
                assert restored.locator('#mission-json').text_content() == original
                record = json.loads(restored.locator('#thinking-json').text_content())
                assert record['rounds'][0]['initial'] is None
                assert record['rounds'][0]['decision'] is None
                assert restored.locator('#compare-proposal').is_disabled()
                assert not requests and not errors
                result['recovery'] = {'method': 'explicit_test_driver_reload',
                                      'mission_restored': True, 'unsaved_practice_lost': True}
                passed('Explicit reload restores fixed mission and clears unsaved practice as disclosed')
                result['completed'] = True
            finally:
                browser.close()
    except Exception as exc:
        # Persist evidence and then re-raise. A failing probe never becomes a pass.
        result['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        result['passed'] = len(checks)
        (out / 'browser-results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--chromium', default=shutil.which('chromium'),
                        help='Existing browser path; otherwise use the installed Playwright Chromium.')
    args = parser.parse_args()
    verify(args.page, args.output, args.chromium)
