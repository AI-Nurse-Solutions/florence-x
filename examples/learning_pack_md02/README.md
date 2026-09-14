# Teaching Source Foundations — review candidate 0.1.0

**MD-02B, September 14, 2026. Review handoff, not learner admission.**

This is the exact MD-02A candidate previously supplied as a local package. The purpose of this pull request is to give an educator and content/rights stewards a stable, commentable version with reproducible evidence. No new learning content or professional approval is asserted.

## Start here

Read `evidence-pack.json` for the three excerpts, six claim records and working glossary. Read `learning-design.json` for objectives, activities, balanced exercises, scoped rights observations and pending maintenance responsibilities. The workflow artifact contains `candidate/MD02_Learning_Pack.html`, the same read-only preview as MD-02A. No model or learner account is required to inspect it.

| Candidate identity | SHA-256 |
|---|---|
| evidence-pack.json | f92f18306ea8f5b91207a6621e72c2d11427038903a6d455e1a862102049bbad |
| learning-design.json | e88fe7503bc77805cf903a4b733c7b3387fcdb5ce1768ed4dbfa6defdbef4d2a |
| generated preview | 24d64052bd11e31cd3c20ae282d06b2a41c79cc6a389ad82fbb7a826c2fad8ad |

Dates inside the candidate refer to the original September 11 inspection. Rebuilding today does not refresh source currency, renew rights, extend review dates or establish semantic support. The renderer evaluates its frozen consistency at that original date; it is not a live surveillance service.

## The human decisions still needed

Use the existing [formative kit](../../docs/evaluation/SS07_FORMATIVE_KIT.md), not a new assessment framework. Before participant use, an appropriately qualified reviewer should identify the exact commit and both candidate hashes, state the audience and nonclinical scope examined, and give a reasoned disposition: suitable for a specified bounded formative exercise, revise, or hold. Findings should address source interpretation, omissions, transfer limits, balanced reliance, teaching clarity and burden. The author is not their own independent reviewer.

Record content-steward and rights-steward acceptance separately. No person has been assigned or has accepted those responsibilities in this submission. A code-review approval, a passing test or a GitHub merge is not an educator disposition, content admission, execution permission or institutional authorization.

Use the PR discussion for non-sensitive artifact-specific findings and corrections. Do not post participant worksheets, personal reflections, names from observation sessions, employer records or patient material. Actual participant observations require the kit's agreed custody, access and deletion arrangements outside this repository. No invitations, observation sessions or supplier engagement are initiated here.

## Preserve history when review arrives

The candidate's embedded review fields intentionally stay pending. The validator only checks this frozen candidate; it is not a review-import or approval service. A genuine disposition is a separate attributed record, bound to the exact inspected bytes. Do not falsify an embedded approval to make a build pass. Revised content needs an explicit version and new review binding; no earlier endorsement follows it automatically. Any later active-source admission is a separately reviewed change.

Source notices travel with their excerpts. The root repository's code license does not relicense third-party source text. Published terms and their limits remain in the two JSON files. This submission does not authorize training, whole-book redistribution or clinical use. No inaccessible source was newly fetched or reproduced.

## Reproduce the software evidence

From the repository root with the existing project dependencies installed:

```bash
python -m pytest -q tests/unit/test_learning_pack_review.py
python scripts/build_learning_pack_review.py --output /tmp/naio-pack-review
python tests/browser/verify_learning_pack.py /tmp/naio-pack-review/MD02_Learning_Pack.html /tmp/naio-pack-browser
```

The browser verifier needs the existing Playwright/Chromium test environment. These are developer commands, not the promised one-download nurse installation. The CI workflow also runs the current repository tests and existing teaching-card checks. Repository lint remains blocking; issue #16 is not bypassed.

**Pillar mapping:** Knowledge preserves evidence and limits; Judgment requires a real disposition; Capability makes the review reproducible; Contribution makes the exact asset and corrections maintainable. The risk is paperwork mistaken for useful learning. Human outcomes remain unmeasured.
