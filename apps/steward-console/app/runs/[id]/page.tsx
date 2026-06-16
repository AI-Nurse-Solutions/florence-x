import Link from "next/link";
import { notFound } from "next/navigation";
import { DecisionInspector } from "@/components/DecisionInspector";
import { RunTimeline } from "@/components/RunTimeline";
import { api } from "@/lib/api";
import type { EvidenceBundle, WorkflowRun } from "@/lib/types";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="mb-3 text-sm font-semibold text-gray-700">{title}</h2>
      {children}
    </section>
  );
}

// Run detail: evidence viewer + EDENA decision inspector + timeline.
export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let run: WorkflowRun;
  try {
    run = await api.getRun(id);
  } catch {
    notFound();
  }
  let bundle: EvidenceBundle | null = null;
  try {
    bundle = await api.getEvidence(id);
  } catch {
    bundle = null; // run may have no evidence yet (e.g. still pending)
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/" className="text-sm text-gray-500 hover:text-gray-800">
          ← Review queue
        </Link>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">{run.workflow_id}</h1>
        <p className="text-sm text-gray-500">
          Run {run.workflow_run_id} · status {run.status}
          {bundle?.final_action ? ` · final action ${bundle.final_action}` : ""}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="EDENA decisions">
            <DecisionInspector decisions={bundle?.edena_decisions ?? []} />
          </Card>

          <Card title="Evidence bundle">
            {bundle ? (
              <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
                <div><dt className="text-xs uppercase text-gray-400">Bundle</dt><dd>{bundle.bundle_id}</dd></div>
                <div><dt className="text-xs uppercase text-gray-400">Model</dt><dd>{bundle.model_used ?? "—"}</dd></div>
                <div><dt className="text-xs uppercase text-gray-400">Context hash</dt><dd className="truncate">{bundle.context_hash ?? "—"}</dd></div>
                <div className="col-span-2 md:col-span-3">
                  <dt className="text-xs uppercase text-gray-400">Agent versions</dt>
                  <dd>{Object.entries(bundle.agent_versions).map(([a, v]) => `${a}@${v}`).join(", ") || "—"}</dd>
                </div>
                <div className="col-span-2 md:col-span-3">
                  <dt className="text-xs uppercase text-gray-400">Source citations</dt>
                  <dd>
                    {bundle.source_citations.length ? (
                      <ul className="list-inside list-disc text-gray-600">
                        {bundle.source_citations.map((s) => <li key={s}>{s}</li>)}
                      </ul>
                    ) : "—"}
                  </dd>
                </div>
                {bundle.incident_flags.length > 0 && (
                  <div className="col-span-2 md:col-span-3">
                    <dt className="text-xs uppercase text-red-400">Incident flags</dt>
                    <dd className="text-red-700">{bundle.incident_flags.join(", ")}</dd>
                  </div>
                )}
              </dl>
            ) : (
              <p className="text-sm text-gray-400">No evidence bundle yet.</p>
            )}
          </Card>

          {bundle && bundle.tool_calls.length > 0 && (
            <Card title="Tool calls">
              <ul className="space-y-1 text-sm text-gray-700">
                {bundle.tool_calls.map((t, i) => (
                  <li key={i}>
                    <span className="font-medium">{t.tool_id}</span> ·{" "}
                    {t.executed ? "executed" : "proposed"}
                    {t.output_hash ? ` · ${t.output_hash}` : ""}
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>

        <div>
          <Card title="Timeline">
            <RunTimeline run={run} bundle={bundle} />
          </Card>
        </div>
      </div>
    </div>
  );
}
