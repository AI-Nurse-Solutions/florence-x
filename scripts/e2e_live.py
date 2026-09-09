"""Live end-to-end proof — the real stack, not mocks.

Boots a real OPA policy server and the real FastAPI app (uvicorn) wired to:
  * EDENA  -> the OPA server over HTTP (EDENA_BASE_URL)
  * runtime-> the durable LangGraph engine with a SQLite checkpointer
  * state  -> PostgresRepository over SQLite (Alembic-migrated)
…then drives the full human-authority loop over HTTP and asserts the governance
invariants on the responses. Only the model (deterministic stub agent) and Redis
(in-process queue) are not "real" — neither is needed to prove governance.

Usage:  make e2e   (or)   python scripts/e2e_live.py
Exit 0 = all scenarios passed. Requires the `opa` binary (make opa-install).
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_PATHS = [
    "packages/florence-core", "packages/florence-edena", "packages/florence-connectors",
    "packages/florence-model-router", "packages/florence-cli", "apps/api",
]
PYTHONPATH = os.pathsep.join(str(ROOT / p) for p in PKG_PATHS)
OPA = ROOT / ".tooling" / "bin" / "opa"
HEADERS = {"Content-Type": "application/json",
           "X-Florence-Identity": "steward-1", "X-Florence-Role": "rn"}

_passed, _failed = 0, 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    mark = "✅" if ok else "❌"
    print(f"  {mark} {label}" + (f"  — {detail}" if detail else ""))
    if ok:
        _passed += 1
    else:
        _failed += 1


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def wait_for(url: str, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except OSError:
            time.sleep(0.3)
    return False


SIGNAL = {
    "signal_id": "sig-e2e", "source": "live-demo", "signal_type": "icu_handoff_needed",
    "requester": {"role": "rn", "unit": "micu"}, "data_classification": "phi_local",
    "patient_context_present": True,
}


def scenario_approve(api: str) -> None:
    print("\n▶ Scenario A — pause at EDENA(require_human), steward APPROVES, run resumes")
    code, bundle = http("POST", f"{api}/signals?sync=true", SIGNAL)
    run_id = bundle.get("workflow_run_id")
    check("signal accepted, run paused for human", code == 200 and bundle.get("final_action") == "awaiting_human_review", f"run={run_id}")

    code, reviews = http("GET", f"{api}/reviews")
    item = next((r for r in reviews if r["workflow_run_id"] == run_id), None)
    check("paused run appears in the review queue", item is not None)
    check("EDENA decision came back require_human / yellow (via the OPA server)",
          bool(item) and item["decision"] == "require_human" and item["risk_tier"] == "yellow",
          f"tier={item and item['risk_tier']}")
    check("review carries anti-rubber-stamp context", bool(item) and bool(item["rationale"]) and item["reversible"] is not None and bool(item["source_citations"]))

    code, final = http("POST", f"{api}/reviews/{run_id}", {"outcome": "approve", "reviewer_ref": "steward-1"})
    check("approval resumes the run to completion", code == 200 and final.get("final_action") == "draft")

    code, run = http("GET", f"{api}/runs/{run_id}")
    check("run status is completed", run.get("status") == "completed")

    code, ev = http("GET", f"{api}/runs/{run_id}/evidence")
    decisions = ev.get("edena_decisions", [])
    reviews_rec = ev.get("human_reviews", [])
    cites = ev.get("source_citations", [])
    check("evidence bundle records the EDENA decision", any(d["risk_tier"] == "yellow" for d in decisions))
    check("evidence bundle records the human approval", [r["outcome"] for r in reviews_rec] == ["approve"])
    check("source citations are references, not raw content", bool(cites) and all(":" in c for c in cites), str(cites))


def scenario_deny(api: str) -> None:
    print("\n▶ Scenario B — steward DENIES, run is blocked and an Incident is recorded")
    code, bundle = http("POST", f"{api}/signals?sync=true", {**SIGNAL, "signal_id": "sig-e2e-2"})
    run_id = bundle["workflow_run_id"]
    code, final = http("POST", f"{api}/reviews/{run_id}",
                       {"outcome": "deny", "reviewer_ref": "steward-1", "note": "unsafe handoff"})
    check("denial blocks the run", final.get("final_action") == "human_deny")
    code, run = http("GET", f"{api}/runs/{run_id}")
    check("run status is blocked", run.get("status") == "blocked")
    code, incidents = http("GET", f"{api}/incidents")
    mine = [i for i in incidents if i["workflow_run_id"] == run_id]
    check("an Incident was created (refusal is a recorded success)",
          code == 200 and bool(mine) and mine[0]["triggered_by"] == "human_deny")


def main() -> int:
    if not OPA.exists():
        print(f"opa binary not found at {OPA} — run `make opa-install` first.")
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="florence-e2e-"))
    db, ckpt = tmp / "state.db", tmp / "ckpt.db"
    opa_port, api_port = free_port(), free_port()
    api_url = f"http://127.0.0.1:{api_port}"
    env = {
        **os.environ, "PYTHONPATH": PYTHONPATH,
        "FLORENCE_DATABASE_URL": f"sqlite:///{db}",
        "EDENA_BASE_URL": f"http://127.0.0.1:{opa_port}",
        "FLORENCE_RUNTIME": "graph",
        "FLORENCE_LANGGRAPH_CHECKPOINT": f"sqlite:///{ckpt}",
        "FLORENCE_EVENT_LOG": str(tmp / "events.jsonl"),
        "FLORENCE_REQUIRE_IDENTITY": "true",
    }
    procs: list[subprocess.Popen] = []
    print("Florence-X live end-to-end — real OPA + real HTTP API + durable runtime")
    print(f"  OPA :{opa_port}  ·  API :{api_port}  ·  DB sqlite  ·  runtime=graph(sqlite checkpoint)")
    try:
        # 1. real OPA policy server
        procs.append(subprocess.Popen([str(OPA), "run", "--server", "--addr", f"127.0.0.1:{opa_port}",
                                       "policies/edena"], cwd=ROOT,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        check("OPA policy server is up", wait_for(f"http://127.0.0.1:{opa_port}/health"))

        # 2. migrate the real schema (Alembic)
        mig = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                             cwd=ROOT / "apps" / "api", env=env, capture_output=True, text=True, check=False)
        check("Alembic migrated a fresh database", mig.returncode == 0, mig.stderr.strip().splitlines()[-1] if mig.returncode else "")

        # 3. the real FastAPI app under uvicorn
        procs.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                                       "--host", "127.0.0.1", "--port", str(api_port)],
                                      cwd=ROOT, env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        check("FastAPI app is serving (/healthz)", wait_for(f"{api_url}/healthz"))

        # 4. Zero Trust: no identity => denied
        req = urllib.request.Request(f"{api_url}/reviews", method="GET")
        try:
            urllib.request.urlopen(req, timeout=5)
            denied = False
        except urllib.error.HTTPError as e:
            denied = e.code == 401
        check("Zero Trust denies a request with no identity (401)", denied)

        scenario_approve(api_url)
        scenario_deny(api_url)
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=5)
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{'='*60}\n  RESULT: {_passed} passed, {_failed} failed\n{'='*60}")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
