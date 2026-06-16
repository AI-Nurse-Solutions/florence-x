import Link from "next/link";
import { api } from "@/lib/api";
import type { Incident } from "@/lib/types";

const SEV: Record<string, string> = {
  sev1: "bg-red-100 text-red-900",
  sev2: "bg-orange-100 text-orange-800",
  sev3: "bg-amber-100 text-amber-800",
  sev4: "bg-gray-100 text-gray-700",
};

// Refusal and containment are successful governance outcomes (CLAUDE.md rule 9).
export default async function IncidentsPage() {
  let incidents: Incident[] = [];
  let error: string | null = null;
  try {
    incidents = await api.listIncidents();
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Incidents</h1>
      {error && (
        <p className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Could not reach the Florence-X API ({error}).
        </p>
      )}
      {!error && incidents.length === 0 && (
        <p className="rounded-md border border-gray-200 bg-white px-4 py-8 text-center text-sm text-gray-500">
          No incidents recorded. Deny / stop / contain outcomes appear here.
        </p>
      )}
      <div className="space-y-3">
        {incidents.map((i) => (
          <div key={i.incident_id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center gap-3">
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${SEV[i.severity] ?? "bg-gray-100"}`}>
                {i.severity.toUpperCase()}
              </span>
              <span className="text-sm font-medium">{i.category}</span>
              <span className="text-xs text-gray-400">triggered by {i.triggered_by}</span>
            </div>
            <p className="mt-1 text-sm text-gray-700">{i.summary}</p>
            <div className="mt-2 flex flex-wrap gap-x-6 text-xs text-gray-500">
              {i.containment_applied.length > 0 && (
                <span>containment: {i.containment_applied.join(", ")}</span>
              )}
              {i.workflow_run_id && (
                <Link href={`/runs/${i.workflow_run_id}`} className="text-sky-700 underline">
                  run {i.workflow_run_id}
                </Link>
              )}
              <span>{i.created_at}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
