# Nurse AI OS learning companion — review candidate

**Do not install this candidate yet.** SS-04A provides a pinned interface assessment and a presentation-only prototype. The browser isolation verifier is incomplete, native Hermes has not been tested, and review/release gates are open.

Build for inspection from the repository root:

```bash
python scripts/build_hermes_companion.py --output /tmp/naio-companion-review
```

The explicit development folder receives `plugin.js`, `preview.html`, and `build-record.json`. The command does not search for Hermes, write to HERMES_HOME, install a plugin, obtain credentials, launch a runtime, invoke a model, or call a network endpoint. Generated files are build artifacts, not hand-edited parallel sources.

`preview.html` is a plain browser frame experiment, **not Hermes Desktop**. The unchanged standalone workbench remains `apps/learning-workspace/index.html`. Entries are temporary; closing, reloading or remounting can lose them. No portfolio save is available.

The upstream native disk-plugin contract uses a `plugin.js` file in a plugin-ID directory and a default-exported HermesPlugin. This candidate's ID is `naio-learning-companion` and it is disabled by default. Review, exact installed-host identification, full isolation checks and native smoke testing must precede any installation. There is deliberately no automatic installation helper.

The frame's script/form-event permissions exist only to operate the current learning forms. It retains form-action/connect-src denial and no same-origin access. Its parent plugin remains privileged under Hermes's current loader; do not describe the entire host as sandboxed.

Tests:

```bash
pytest -q tests/unit/test_hermes_companion.py
node --experimental-vm-modules tests/javascript/test_hermes_companion.cjs /tmp/naio-companion-review/plugin.js
python tests/browser/verify_hermes_companion.py /tmp/naio-companion-review/preview.html /tmp/naio-companion-browser
```

The Node host and JSX module are explicit test substitutes, not native-host verification. The last browser command reproduces an outstanding navigation/context-reset failure; it is not a release test that passed. It requires the existing Playwright/Chromium test setup. Do not disable browser security policy to make a test pass.

See `assessment.json` and `docs/rfcs/ss04a-hermes-presentation-boundary.md` for inspected interfaces, separate rights, authority limits, findings, failure history and next gates.
