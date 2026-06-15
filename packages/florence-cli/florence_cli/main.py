"""florence — CLI for running simulated, governed Florence-X workflows.

Examples:
  python -m florence_cli run examples/icu_handoff/workflow.yaml \
      --agent examples/icu_handoff/agent.yaml --reviewer auto
  python -m florence_cli run examples/prior_authorization/workflow.yaml --reviewer queue
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from florence_core.events import EventLog, JsonlSink, StdoutSink
from florence_core.schemas import RequesterContext, Signal
from florence_core.workflows import (
    AutoApproveReviewer,
    QueueReviewer,
    Runtime,
    load_agent,
    load_workflow,
)
from florence_edena import EdenaClient


def _build_signal(signal_type: str, data_classification: str, role: str) -> Signal:
    return Signal(
        signal_id=f"sig_{uuid.uuid4().hex[:10]}",
        source="cli.simulated",
        signal_type=signal_type,
        requester=RequesterContext(role=role, unit="demo_unit"),
        data_classification=data_classification,
        patient_context_present=data_classification.startswith("phi"),
    )


def cmd_run(args: argparse.Namespace) -> int:
    workflow = load_workflow(args.workflow)
    agents = {}
    for ap in args.agent or []:
        a = load_agent(ap)
        agents[a.agent_id] = a

    signal_type = args.signal_type or (workflow.signal_types[0] if workflow.signal_types else "unknown")
    signal = _build_signal(signal_type, args.data_classification, args.role)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    sinks = [JsonlSink(out_dir / "events.jsonl")]
    if not args.quiet:
        sinks.append(StdoutSink())

    reviewer = QueueReviewer() if args.reviewer == "queue" else AutoApproveReviewer()
    rt = Runtime(EdenaClient(), events=EventLog(*sinks), agents=agents, reviewer=reviewer)

    bundle = rt.run(workflow, signal)
    run = rt.repo.get_run(bundle.workflow_run_id)

    (out_dir / "evidence.json").write_text(bundle.model_dump_json(indent=2))

    print("\n" + "=" * 64)
    print(f" RUN {bundle.workflow_run_id}  [{run.status if run else '?'}]")
    print("=" * 64)
    print(f" workflow        : {workflow.workflow_id} (baseline {workflow.baseline_tier})")
    print(f" signal          : {signal.signal_type}  data={signal.data_classification}")
    for d in bundle.edena_decisions:
        print(f" EDENA           : {d.decision} (tier={d.risk_tier}, human={d.required_human_role})")
        if d.constraints:
            print(f"   constraints   : {', '.join(d.constraints)}")
    for r in bundle.human_reviews:
        print(f" human review    : {r.outcome} by {r.reviewer_role} ({r.reviewer_ref})")
    print(f" final action    : {bundle.final_action}")
    print(f" sources         : {', '.join(bundle.source_citations) or '-'}")
    print(f" evidence bundle : {bundle.bundle_id}")
    print(f" artifacts       : {out_dir / 'events.jsonl'} , {out_dir / 'evidence.json'}")
    if args.reviewer == "queue" and run and run.status == "awaiting_human":
        print("\n NOTE: paused awaiting human review (Phase 3 steward console handles this).")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="florence", description="Florence-X simulated workflow runner")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="Run a simulated governed workflow")
    r.add_argument("workflow", help="Path to a workflow.yaml")
    r.add_argument("--agent", action="append", help="Path to an agent.yaml (repeatable)")
    r.add_argument("--signal-type", default=None, help="Override the signal type")
    r.add_argument("--data-classification", default="phi_local",
                   choices=["public", "internal", "phi_local", "phi_redacted", "restricted"])
    r.add_argument("--role", default="rn", help="Requester role")
    r.add_argument("--reviewer", default="auto", choices=["auto", "queue"])
    r.add_argument("--out", default=".florence", help="Output dir for events + evidence")
    r.add_argument("--quiet", action="store_true", help="Suppress the event stream")
    r.set_defaults(func=cmd_run)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
