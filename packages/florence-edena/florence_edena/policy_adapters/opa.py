"""OPA decision backends.

Two flavours, both returning the same decision dict shape as LocalRuleBackend so
they are interchangeable (parity asserted in tests/policy/):

  * OpaBackend      — evaluates policies/edena/*.rego via the local `opa` CLI
                      (sidecar / dev box with the binary on PATH).
  * OpaHttpBackend  — queries a running OPA server's Data API (the production
                      path used by docker-compose: EDENA_BASE_URL=http://opa:8181).

Both raise on failure so EdenaClient's fail-closed guard turns an unreachable or
erroring governance plane into a safe non-executing decision — never fail-open.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

# Default OPA Data API path for the EDENA decision entrypoint (package `edena`,
# rule `decision` -> /v1/data/edena/decision).
DEFAULT_OPA_DECISION_PATH = "v1/data/edena/decision"


class OpaHttpBackend:
    """Query a running OPA server over HTTP (the OPA Data API)."""

    def __init__(self, base_url: str, decision_path: str = DEFAULT_OPA_DECISION_PATH,
                 timeout_s: float = 2.0) -> None:
        self.url = base_url.rstrip("/") + "/" + decision_path.lstrip("/")
        self.timeout_s = timeout_s

    def evaluate(self, features: dict) -> dict:
        body = json.dumps({"input": features}).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if "result" not in payload:
            # Undefined result => the policy produced no decision. Treat as an
            # error so the client fails closed rather than guessing.
            raise RuntimeError(f"OPA returned no decision for {self.url}")
        return payload["result"]


class OpaBackend:
    def __init__(self, policy_dir: str, query: str = "data.edena.decision") -> None:
        self.policy_dir = Path(policy_dir)
        self.query = query
        if shutil.which("opa") is None:
            raise RuntimeError("opa binary not found on PATH; use LocalRuleBackend instead.")

    def evaluate(self, features: dict) -> dict:
        proc = subprocess.run(
            ["opa", "eval", "--format", "json", "--data", str(self.policy_dir),
             "--stdin-input", self.query],
            input=json.dumps(features), text=True, capture_output=True, timeout=5, check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"opa eval failed: {proc.stderr.strip()}")
        payload = json.loads(proc.stdout)
        # opa eval returns {"result":[{"expressions":[{"value": <decision>}]}]}
        return payload["result"][0]["expressions"][0]["value"]
