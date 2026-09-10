# Portable learning workspace — SS-01

Development preview only: no account, model, Hermes connection or portfolio save.
Open `index.html` directly, or from the repository root run:

    python scripts/serve_learning_workspace.py

Then open http://127.0.0.1:8766/ in a local browser. The launcher uses the Python
standard library, binds loopback only and exposes no write or upload endpoint.
No device installation or external hosting is performed by this repository.

The synthetic goal is deliberately not editable in this first slice. Inspect its
stable mission ID and record, compare the three target placements, and pause or
resume the view. Profile selection does not move data or grant authority. In the
actual preview, state is temporary browser memory; no persistent workspace exists.

`index.template.html` is the interface source. The portable contracts are in
`florence_core/schemas/mission.py`; the canonical synthetic example and three
manifests are in `examples/portable_learning/workspace.json`. To rebuild after a
reviewed source change, with project dependencies installed:

    python scripts/build_learning_workspace.py
    python scripts/build_learning_workspace.py --check
    pytest -q tests/unit/test_portable_mission.py tests/unit/test_catalog.py

The build inserts validated JSON and hashes the executable inline script and style
for a restrictive CSP. Its output is a derived snapshot, not a professional review.
Browser checks are separately run with Playwright and Chromium installed:

    python tests/browser/verify_portable_workspace.py /tmp/workspace-evidence

Those checks supply offline HTML and deny network routes; they do not establish
browser-to-localhost, remote hosting, accessibility conformance or nurse outcomes.

SS-02 adds an inspected public evidence pack; SS-03 adds learner-first deliberation.
The pre-existing release hold (issue #16) remains. No independent review or release
is implied by successful prototype tests.
