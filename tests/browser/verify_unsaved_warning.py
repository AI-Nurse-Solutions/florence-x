"""MD-01B: conditional leave warning on supplied HTML; no storage or user study."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(html_path: Path, output: Path, executable: str | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    text = html_path.read_text(encoding="utf-8")
    checks, errors, requests, dialogs = [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=executable)
        page = None
        try:
            def load():
                nonlocal page
                if page is not None:
                    page.close()  # Test teardown, not a user-confirmed close.
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                page.set_default_timeout(5000)
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                page.on("request", lambda r: requests.append(r.url))
                page.route("**/*", lambda route: route.abort())
                page.set_content(text, wait_until="load")

            def warning_requested():
                # Synthetic probe checks handler state, not native-dialog delivery.
                return page.evaluate("""() => {
                    const e = new Event('beforeunload', {cancelable:true});
                    window.dispatchEvent(e); return e.defaultPrevented;
                }""")

            def cancel_reload():
                with page.expect_event("dialog") as event:
                    page.evaluate("setTimeout(() => location.reload(), 0)")
                dialog = event.value
                assert dialog.type == "beforeunload"
                dialogs.append({"type": dialog.type, "decision": "cancel"})
                dialog.dismiss()

            def decide(outcome):
                page.locator("#initial-uncertain").check()
                page.get_by_role("button", name="Record initial view in memory", exact=True).click()
                page.locator("#compare-proposal").click()
                page.locator('input[value="' + outcome + '"]').check()
                page.locator("#decision-reason").fill("This source has a limited stated purpose.")
                page.locator("#decision-alternative").fill("Examine the original passage.")
                page.locator("#decision-consequence").fill("Further review may change the draft.")
                if outcome == "revise":
                    page.locator("#replacement").fill("Use as a draft pending source appraisal.")
                page.get_by_role("button", name="Record learning choice in memory", exact=True).click()
                page.locator("#tc-compose").click()
                assert page.locator("#tc-card").is_visible()

            load()
            assert not warning_requested()
            page.locator("#pause").click()
            assert not warning_requested()
            page.locator("#pause").click()
            page.locator("#passage-nist-scope summary").click()
            assert not warning_requested()
            checks.append("Untouched, paused-only and source-inspection states request no leave warning")

            page.locator("#initial-text").fill("Synthetic unsubmitted text.")
            assert warning_requested()
            cancel_reload()
            assert page.locator("#initial-text").input_value() == "Synthetic unsubmitted text."
            assert "Nothing has been saved" in page.locator("#tc-leave-status").text_content()
            checks.append("A real browser reload prompt can be cancelled without losing pending text")

            page.locator("#initial-text").fill("   ")
            assert not warning_requested()
            page.locator("#initial-uncertain").check()
            assert warning_requested()
            page.locator("#initial-uncertain").uncheck()
            assert not warning_requested()
            checks.append("Reverted unsubmitted text/check edits remove the handler; whitespace alone is not work")

            goal = page.locator("#tc-goal").input_value()
            page.locator("#tc-goal").fill("Explain one source limitation.")
            assert warning_requested()
            page.locator("#tc-goal").fill(goal)
            assert not warning_requested()
            page.locator("#tc-audience").select_option("Peer-learning draft")
            assert warning_requested()
            page.locator("#tc-audience").select_option("Personal learning")
            assert not warning_requested()
            checks.append("Objective/audience edits are protected; restoring clean defaults removes warning")

            for outcome in ("accept", "revise", "reject", "withhold"):
                load()
                decide(outcome)
                before = page.locator("#tc-json").text_content()
                assert warning_requested()
                cancel_reload()
                assert page.locator("#tc-json").text_content() == before
                record = json.loads(before)["drafts"][-1]
                assert record["saved"] is False and record["submitted"] is False
                assert record["provenance"]["choice"]["outcome"] == outcome
                checks.append(outcome + ": cancelling native reload retains the exact unsaved card and decision")

            page.locator("#pause").click()
            assert warning_requested()
            page.locator("#pause").click()
            page.locator("#evidence-scenario").select_option("changed")
            assert warning_requested()
            page.locator("#new-round").click()
            assert warning_requested()
            checks.append("Pause, stale context and a new round do not forget retained historical work")

            page.locator("#clear-practice").click()
            page.locator("#cancel-clear").click()
            assert warning_requested()
            page.locator("#clear-practice").click()
            page.locator("#confirm-clear").click()
            assert not warning_requested()
            assert page.locator("#tc-json").text_content() == "No teaching card assembled."
            page.reload(wait_until="load")
            assert page.locator("#tc-card").count() == 0  # about:blank, not an application restore
            checks.append("Cancel-clear retains protection; confirmed clear removes it and permits reload")

            load()
            decide("revise")
            with page.expect_navigation(wait_until="load"):
                with page.expect_event("dialog") as event:
                    page.evaluate("setTimeout(() => location.reload(), 0)")
                dialog = event.value
                assert dialog.type == "beforeunload"
                dialogs.append({"type": dialog.type, "decision": "leave"})
                dialog.accept()
            assert page.locator("#tc-card").count() == 0
            checks.append("Confirming the native prompt permits departure and loses temporary work as disclosed")

            load()
            decide("withhold")
            card = page.locator("#tc-json").text_content()
            page.locator("#tc-card button").first.click()
            assert page.locator("#tc-json").text_content() == card
            assert page.locator("#passage-nist-scope summary").evaluate("e => e === document.activeElement")
            assert "mobile app termination" in page.locator("#teaching-card-workspace").text_content()
            assert page.locator('a[download],button:has-text("Save portfolio")').count() == 0
            assert page.evaluate("typeof window.onbeforeunload") == "object"  # No clobbered global property.
            checks.append("Source navigation stays in-page; limitations visible; no save/download control added")
            page.locator("#tc-leave-status").scroll_into_view_if_needed()
            page.screenshot(path=str(output / "unsaved-desktop.png"))
            for width in (320, 390, 768, 1280):
                page.set_viewport_size({"width": width, "height": 1000})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#tc-leave-status").scroll_into_view_if_needed()
            page.screenshot(path=str(output / "unsaved-mobile.png"))
            assert not errors and not requests, (errors, requests)
            checks.append("Four-width reflow; no observed requests, page exceptions or CSP errors")
            result = {"passed": len(checks), "checks": checks, "native_dialogs": dialogs,
                      "errors": errors, "requests": requests, "chromium": browser.version,
                      "scope": "supplied_html_and_actual_about_blank_reload_not_deployment",
                      "persistence_tested": False, "nurse_participants": 0,
                      "physical_mobile_or_hermes_tested": False}
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
