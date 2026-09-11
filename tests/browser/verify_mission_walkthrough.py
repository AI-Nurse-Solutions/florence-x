"""Exercise the whole available practice journey. Scripted agents are not participants."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(html_path: Path, output: Path, executable: str | None = None) -> dict:
    checks, requests, errors = [], [], []
    output.mkdir(parents=True, exist_ok=True)
    text = html_path.read_text(encoding='utf-8')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=executable)
        try:
            page = browser.new_page(viewport={'width':1440,'height':1080})
            page.set_default_timeout(5000)
            page.on('request', lambda r: requests.append(r.url))
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.route('**/*', lambda r: r.abort())
            def load():
                page.set_content(text, wait_until='load')
            def decide(outcome):
                page.locator('#initial-text').fill('PRIVATE_INITIAL_SENTINEL')
                page.get_by_role('button', name='Record initial view in memory', exact=True).click()
                assert page.locator('#proposal-panel').is_hidden()
                page.locator('#compare-proposal').click()
                assert page.locator('input[name="learning-choice"]:checked').count() == 0
                page.locator('input[value="' + outcome + '"]').check()
                page.locator('#decision-reason').fill('The source scope is limited. <img src=x onerror=alert(1)>')
                page.locator('#decision-alternative').fill('Request a small formative evaluation.')
                page.locator('#decision-consequence').fill('Review takes effort; unsupported certainty is avoided.')
                if outcome == 'revise':
                    page.locator('#replacement').fill('Use only as a draft for personal learning pending review.')
                page.get_by_role('button', name='Record learning choice in memory', exact=True).click()
                page.locator('#reflection-text').fill('PRIVATE_REFLECTION_SENTINEL')
                page.get_by_role('button', name='Record self-reflection in memory', exact=True).click()
            load()
            assert not errors
            assert page.get_by_role('navigation', name='Learning journey').locator('a').count() == 5
            assert page.locator('#compose-note').is_disabled()
            assert page.locator('#note-card').is_hidden()
            checks.append('Initial view guides one mission and cannot assemble before a learning choice')
            initial_mission = page.locator('#mission-json').text_content()
            assert json.loads(initial_mission)['mission_id'] == 'mission.public-learning.0001'
            assert page.locator('#source-cards details').count() == 3
            checks.append('Retained canonical mission and all three public passages are present')
            for outcome in ('accept','revise','reject','withhold'):
                load();decide(outcome)
                assert page.locator('#compose-note').is_enabled()
                assert page.locator('#note-card').is_hidden()
                page.locator('#compose-note').click()
                note = json.loads(page.locator('#note-json').text_content())['notes'][-1]
                assert note['choice'] == outcome and note['saved'] is False and note['submitted'] is False
                assert note['content_review'] == 'not_independently_reviewed'
                assert note['competence'] == 'not_assessed'
                assert note['mission_sha256'] == json.loads(page.locator('#bundle').text_content())['mission_sha256']
                assert page.locator('#note-body img').count() == 0
                assert '<img' in page.locator('#note-body').text_content()
                checks.append(outcome + ': recorded choice transfers to an unsaved note without preselection or HTML execution')
                raw = page.locator('#note-json').text_content()
                assert 'PRIVATE_INITIAL_SENTINEL' not in raw and 'PRIVATE_REFLECTION_SENTINEL' not in raw
                assert 'proposal' not in note and 'reflection' not in note
                checks.append(outcome + ': private initial view/reflection and prepared assertion are not copied')
            assert page.locator('#compose-note').is_disabled()
            page.get_by_role('button', name='Inspect nist-scope', exact=True).click()
            assert page.locator('#passage-nist-scope').get_attribute('open') is not None
            checks.append('Source link opens the retained passage rather than a new context')
            page.locator('#profile').select_option('hosted_test')
            assert page.locator('#mission-json').text_content() == initial_mission
            assert 'current_in_memory' in page.locator('#note-json').text_content()
            checks.append('Hosted placement preview does not move the mission or mutate its note')
            page.locator('#pause').click()
            assert page.locator('#compose-note').is_disabled()
            page.locator('#pause').click()
            assert 'current_in_memory' in page.locator('#note-json').text_content()
            checks.append('Pause disables new assembly; resume preserves this in-memory choice')
            page.locator('#evidence-scenario').select_option('changed')
            assert page.locator('#compose-note').is_disabled()
            assert 'historical_in_memory' in page.locator('#note-json').text_content()
            page.locator('#evidence-scenario').select_option('baseline')
            assert page.locator('#compose-note').is_disabled()
            checks.append('Changed evidence stales the note; switching back cannot reactivate the choice')
            page.locator('#new-round').click();decide('revise');page.locator('#compose-note').click()
            notes = json.loads(page.locator('#note-json').text_content())['notes']
            assert len(notes) == 2 and notes[0]['display_state'] == 'historical_in_memory'
            assert notes[1]['display_state'] == 'current_in_memory'
            checks.append('New comparison retains the earlier note as historical, not overwritten approval')
            page.locator('#clear-practice').click();page.locator('#cancel-clear').click()
            assert len(json.loads(page.locator('#note-json').text_content())['notes']) == 2
            page.locator('#clear-practice').click();page.locator('#confirm-clear').click()
            assert page.locator('#note-card').is_hidden()
            assert page.locator('#note-json').text_content() == 'No note assembled.'
            assert page.locator('#compose-note').is_disabled()
            checks.append('Cancelled clear preserves notes; confirmed clear erases practice and derived notes')
            decide('withhold');page.locator('#compose-note').click()
            page.locator('#review-note').scroll_into_view_if_needed()
            page.screenshot(path=str(output/'desktop-note.png'))
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('#note-heading').scroll_into_view_if_needed()
            page.screenshot(path=str(output/'mobile-note.png'))
            checks.append('390px integrated note view has no horizontal overflow')
            load()
            page.get_by_role('link', name='4 · Prepare a note', exact=True).focus();page.keyboard.press('Enter')
            assert page.locator('#note-heading').is_visible()
            assert page.locator('#note-json').text_content() == 'No note assembled.'
            checks.append('Reload clears notes; journey navigation is keyboard-operable')
            assert page.get_by_text('Blocked: live operation', exact=True).is_visible()
            assert 'No command or learning choice' in page.locator('#limits-heading').locator('..').text_content()
            assert not requests and not errors, (requests,errors)
            checks.append('Blocked stages remain visible; no observed network requests or page errors')
            result = {'passed':len(checks),'checks':checks,'network_requests':requests,'page_errors':errors,
                      'chromium':browser.version,'observed_nurse_participants':0,
                      'test_scope':'scripted_offline_browser_not_live_mission','native_hermes':False,
                      'live_model':False,'real_portfolio':False}
        finally:
            browser.close()
    (output/'results.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html_path', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--executable')
    args = parser.parse_args()
    verify(args.html_path,args.output,args.executable)
