# Public learning artifact catalog — synthetic demonstration

This example is a **non-executable artifact catalog**, not a tool registry,
portfolio store, policy engine or credential. It makes source/claim links,
AI assistance, known gaps and declared review metadata inspectable.

From a repository checkout with `florence-core` available:

```python
from datetime import UTC, datetime
from pathlib import Path
from florence_core.catalog import content_matches, inspect_artifact, parse_catalog

root = Path("examples/artifact_catalog")
catalog = parse_catalog((root / "catalog.json").read_bytes())
view = inspect_artifact(catalog, "source-checking-guide", "0.1.0",
                        at=datetime(2026, 9, 9, 12, tzinfo=UTC))
print(view.review_state)       # unreviewed
print(view.authorization)      # not_assessed_no_execution_interface
print(view.warnings)           # draft; unverified source support; known gaps
print(content_matches(view.artifact,
                      (root / "source-checking-guide.md").read_bytes()))  # True
```

The example caller reads these explicitly selected public fixture files. The
catalog API itself reads no files and follows no URLs. Comparing supplied bytes
does not change `view.content_integrity`; the view remains an immutable snapshot
of what was known when inspected. A content match is byte-integrity evidence,
not clinical correctness, approval, or proof of learning.

The source is explicitly synthetic and establishes no real-world finding.
No review is fabricated for this fixture. Content-review test records use
synthetic identities; their structure is not evidence of reviewer credentials.

Run `pytest tests/unit/test_catalog.py -q`. The acceptance criteria and limits are
in `docs/rfcs/h003-read-only-artifact-catalog.md`.
