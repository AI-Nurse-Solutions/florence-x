"""Read-only review-page checks; not a nurse study or accessibility certification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

def verify(path: Path, output: Path, executable: str | None=None) -> dict:
    text = path.read_text(encoding='utf-8')
    checks, requests, errors = ([], [], [])
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=executable)
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        page.on('request', lambda r: requests.append(r.url))
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.route('**/*', lambda r: r.abort())
        try:
            page.set_content(text, wait_until='load')
            assert page.locator('article.source').count() == 3
            assert page.locator('article.exercise').count() == 3
            assert page.locator('#review-status').is_visible()
            checks.append('Three sources and balanced exercises retain pending-review status')
            assert page.locator('input,textarea,form,iframe,script').count() == 0
            checks.append('No response collection, scripts or embedded remote frames')
            for selector in ('#exercise\\.trace', '#exercise\\.scope', '#exercise\\.unknown'):
                details = page.locator(selector + ' details.proposal')
                assert details.get_attribute('open') is None
                summary = details.locator('> summary')
                summary.focus()
                page.keyboard.press('Enter')
                assert details.get_attribute('open') is not None
                assert details.locator('details.rationale').get_attribute('open') is None
                checks.append(selector + ': keyboard reveals proposal without revealing reviewer rationale')
            links = page.locator('a[target="_blank"]')
            assert links.count() == 6
            for i in range(links.count()):
                assert links.nth(i).get_attribute('href').startswith('https://')
                assert 'noreferrer' in links.nth(i).get_attribute('rel')
            checks.append('Six explicit external source/terms links; no automatic retrieval')
            assert page.locator('blockquote').count() == 6
            for width in (320, 390, 768, 1280):
                page.set_viewport_size({'width': width, 'height': 900})
                page.locator('details').evaluate_all('els=>els.forEach(e=>e.open=true)')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
                assert page.locator('blockquote').first.is_visible()
                checks.append(str(width) + 'px: expanded source/rights/exercise records reflow')
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(output / 'desktop.png'))
            page.set_viewport_size({'width': 390, 'height': 844})
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(output / 'mobile.png'))
            assert not requests and (not errors), (requests, errors)
            checks.append('No observed requests, page exceptions or CSP/console errors')
            result = {'passed': len(checks), 'checks': checks, 'requests': requests, 'errors': errors, 'chromium': browser.version, 'scope': 'supplied_html_read_only_review', 'participants': 0}
        finally:
            browser.close()
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return result
if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('path', type=Path)
    a.add_argument('output', type=Path)
    a.add_argument('--executable')
    v = a.parse_args()
    verify(v.path, v.output, v.executable)
