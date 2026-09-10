"""Build a self-contained preview from canonical validated fixtures; no network."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/florence-core"))
from florence_core.schemas.mission import mission_digest, parse_workspace


def render() -> str:
    bundle = parse_workspace((ROOT / "examples/portable_learning/workspace.json").read_bytes())
    data = {"bundle": bundle.model_dump(mode="json"), "mission_sha256": mission_digest(bundle.mission)}
    html = (ROOT / "apps/learning-workspace/index.template.html").read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))
    for kind, placeholder in (("script", "__SCRIPT_HASH__"), ("style", "__STYLE_HASH__")):
        code = re.search(r"<" + kind + r">(.*?)</" + kind + r">", html, flags=re.DOTALL).group(1)
        digest = base64.b64encode(hashlib.sha256(code.encode("utf-8")).digest()).decode("ascii")
        html = html.replace(placeholder, digest)
    return html


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare output without writing it.")
    args = parser.parse_args()
    target = ROOT / "apps/learning-workspace/index.html"
    output = render()
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != output:
            raise SystemExit("Workspace snapshot drift; rebuild from validated fixtures.")
        print("Workspace snapshot matches validated fixtures.")
    else:
        target.write_text(output, encoding="utf-8")
        print("Built portable learning preview; no model or service invoked.")
