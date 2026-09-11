"""Offline report checks. No actual save, live account, or accessibility certification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(report_dir: Path, output: Path, executable: str | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    expected = json.loads((report_dir / "report.json").read_text())
    checks, requests, errors = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=executable, headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1050})
            page.set_default_timeout(5000)
            page.on("request", lambda r: requests.append(r.url))
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.route("**/*", lambda r: r.abort())
            page.set_content((report_dir / "report.html").read_text(), wait_until="load")
            assert page.get_by_text("No portfolio has been saved.", exact=True).is_visible()
            checks.append("No-save disclosure is visible")
            assert page.locator("article.scenario").count() == 14
            checks.append("All fourteen synthetic cases are displayed")
            assert json.loads(page.locator("#results").text_content()) == expected
            checks.append("Displayed evidence exactly matches evaluated JSON")
            assert page.locator("form, input, textarea, script").count() == 0
            checks.append("No input, executable script or saving form exists")
            first = page.locator("summary").first
            first.focus()
            page.keyboard.press("Enter")
            assert page.locator("details").first.get_attribute("open") is not None
            checks.append("Evidence detail is keyboard-operable")
            page.screenshot(path=str(output / "desktop.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            checks.append("390px layout has no horizontal overflow")
            page.screenshot(path=str(output / "mobile.png"))
            assert not requests and not errors
            checks.append("No observed requests or browser errors")
            assert all(not x["result"]["successful_receipt_issued"] for x in expected["cases"])
            checks.append("No fixture is labeled as a successful save receipt")
            result = {"passed": len(checks), "checks": checks, "requests": requests, "errors": errors,
                      "chromium": browser.version, "real_store_tested": False}
        finally:
            browser.close()
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--executable")
    args = parser.parse_args()
    verify(args.report_dir, args.output, args.executable)
