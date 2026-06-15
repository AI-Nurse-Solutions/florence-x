"""Make the path-based packages importable when running pytest from the repo root."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for rel in (
    "packages/florence-core",
    "packages/florence-edena",
    "packages/florence-cli",
    "apps/api",
):
    sys.path.insert(0, str(ROOT / rel))
