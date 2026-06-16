import type { EvidenceBundle, WorkflowRun } from "@/lib/types";

interface Entry {
  label: string;
  detail?: string;
  at?: string | null;
}

// Reconstructed from the run + its evidence bundle (decisions, reviews, tool
// calls). Live events augment this in real time on the client (Phase 3E).
function buildTimeline(run: WorkflowRun, bundle: EvidenceBundle | null): Entry[] {
  const entries: Entry[] = [{ label: "Run started", at: run.started_at }];
  if (bundle) {
    bundle.edena_decisions.forEach((d) =>
      entries.push({ label: `EDENA: ${d.decision}`, detail: `${d.risk_tier} · ${d.action_id}`, at: d.decided_at }),
    );
    bundle.human_reviews.forEach((r) =>
      entries.push({ label: `Human review: ${r.outcome}`, detail: `${r.reviewer_role} (${r.reviewer_ref})`, at: r.reviewed_at }),
    );
    bundle.tool_calls.forEach((t) =>
      entries.push({ label: t.executed ? "Tool executed" : "Tool proposed", detail: t.tool_id }),
    );
    bundle.incident_flags.forEach((f) => entries.push({ label: "Incident flagged", detail: f }));
  }
  entries.push({ label: `Run ${run.status}`, at: run.completed_at });
  return entries;
}

export function RunTimeline({ run, bundle }: { run: WorkflowRun; bundle: EvidenceBundle | null }) {
  const entries = buildTimeline(run, bundle);
  return (
    <ol className="relative space-y-4 border-l border-gray-200 pl-5">
      {entries.map((e, i) => (
        <li key={i} className="relative">
          <span className="absolute -left-[23px] top-1 h-2.5 w-2.5 rounded-full border border-gray-300 bg-white" />
          <div className="text-sm font-medium text-gray-800">{e.label}</div>
          {e.detail && <div className="text-xs text-gray-500">{e.detail}</div>}
          {e.at && <div className="text-xs text-gray-400">{e.at}</div>}
        </li>
      ))}
    </ol>
  );
}
