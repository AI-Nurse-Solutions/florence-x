# Public AI-resource learning pack, version 0.1.0

Purpose: inspect an AI-generated educational resource. This tiny curated pack is
not clinical guidance, a systematic review, or a demonstrated learning intervention.
The same synthetic mission remains unchanged. Actual public sources are distinct
from the synthetic learner identity and deliberately unsupported teaching example.

## Inspected primary sources
- NIST, AI RMF 1.0: official AIRC HTML, section 5.3, MEASURE 2.5.
  https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
  Guidance, not empirical outcome evidence. Only its second-sentence excerpt is
  reproduced; the package pins captured excerpt bytes, not the entire live page.
- Lebo, Sahoo and McGuinness (editors), PROV-O, W3C Recommendation 30 April 2013,
  section 3.1. https://www.w3.org/TR/2013/REC-prov-o-20130430/
  A provenance representation standard, not assurance of truth or our conformance.
- Buçinca, Malaya and Gajos (2021), To Trust or to Think,
  https://arxiv.org/abs/2102.09692v1 ; related DOI 10.1145/3449287.
  Versioned author abstract, including the stated tradeoffs, and its CC BY 4.0
  license link were inspected. The full study methods were not appraised here.

The source-capture records use Pacific time 2026-09-09. Full attributions, exact
locators, short unchanged quotations, rights notes, limitations and inspection
scope are in public-pack.json. No figures or full third-party texts are distributed.
AI-assisted explanations are separately labeled. No outside organization endorses
this pack. Rights for source material remain distinct from repository code rights.

## Architecture
admission.json is application-owned build configuration, not user-provided policy.
Its SHA-256 pins public-pack.json; modifying the pack requires an explicit pin
update and fresh tests. No file or URL specified within content is dereferenced.
The mission digest binds the pack to the stable SS-01 goal. The original mission
stage remains goal_identified: viewing a source does not certify learning or claim
that a human made a reviewed decision.

Rebuild from repository root with `python scripts/build_learning_workspace.py`;
check with `python scripts/build_learning_workspace.py --check`. Preview the result
with `python scripts/serve_learning_workspace.py`, or open the generated HTML.
No install or execution permission for Hermes/cloud/models is implied.

## Human walkthrough: not yet performed
Ask the nurse to find a specific supporting excerpt, identify whether its source
is research or guidance, state one applicability limit, distinguish an unverified
synthesis from an exact quote, and identify the deliberately unsupported example.
Record observed success, confusion, reading time and suggested correction. No
pass/fail result is recorded until an actual participant performs the tasks.
