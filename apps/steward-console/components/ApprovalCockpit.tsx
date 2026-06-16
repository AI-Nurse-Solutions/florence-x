"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { TierBadge } from "@/components/TierBadge";
import { api } from "@/lib/api";
import type { ReviewItem, ReviewOutcome } from "@/lib/types";

const REVIEWER_REF = process.env.NEXT_PUBLIC_FLORENCE_IDENTITY ?? "steward-console";

// The five accountable controls. Deny/Stop are destructive (block + incident).
const ACTIONS: { outcome: ReviewOutcome; label: string; classes: string }[] = [
  { outcome: "approve", label: "Approve", classes: "bg-emerald-600 hover:bg-emerald-700 text-white" },
  { outcome: "edit", label: "Edit", classes: "bg-sky-600 hover:bg-sky-700 text-white" },
  { outcome: "escalate", label: "Escalate", classes: "bg-amber-500 hover:bg-amber-600 text-white" },
  { outcome: "deny", label: "Deny", classes: "bg-red-600 hover:bg-red-700 text-white" },
  { outcome: "stop", label: "Stop", classes: "bg-red-800 hover:bg-red-900 text-white" },
];

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-gray-400">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-800">{children}</dd>
    </div>
  );
}

export function ApprovalCockpit({ item }: { item: ReviewItem }) {
  const router = useRouter();
  const [note, setNote] = useState("");
  const [pending, setPending] = useState<ReviewOutcome | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(outcome: ReviewOutcome) {
    setPending(outcome);
    setError(null);
    try {
      const bundle = await api.submitReview(item.workflow_run_id, {
        outcome,
        reviewer_ref: REVIEWER_REF,
        reviewer_role: item.required_human_role,
        note: note || null,
      });
      setResult(`Run resolved — final action: ${bundle.final_action ?? "—"}`);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(null);
    }
  }

  if (result) {
    return (
      <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">
        {result}{" "}
        <button onClick={() => router.push("/")} className="ml-2 underline">
          back to queue
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Anti-rubber-stamp context: enough to challenge the AI, not a bare button. */}
      <section className="rounded-lg border border-gray-200 bg-white p-5">
        <div className="mb-4 flex items-center gap-3">
          <TierBadge tier={item.risk_tier} />
          <span className="font-medium">{item.workflow_id}</span>
          <span className="text-sm text-gray-400">{item.decision}</span>
        </div>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Field label="Proposed action">{item.action_type ?? "—"}</Field>
          <Field label="Target">{item.intended_target ?? "—"}</Field>
          <Field label="Data class">{item.data_classification ?? "—"}</Field>
          <Field label="Reversible">
            {item.reversible === null ? "—" : item.reversible ? "Yes" : "No — irreversible"}
          </Field>
          <Field label="Crosses external boundary">
            {item.external_boundary_crossed ? "Yes" : "No"}
          </Field>
          <Field label="Blast radius">{item.blast_radius_estimate ?? "not estimated"}</Field>
          <Field label="Accountable role">{item.required_human_role ?? "—"}</Field>
          <Field label="Action id">{item.action_id ?? "—"}</Field>
          <Field label="Decision id">{item.decision_id ?? "—"}</Field>
        </dl>
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="mb-2 text-sm font-semibold text-gray-700">EDENA rationale</h2>
        <p className="text-sm text-gray-700">{item.rationale ?? "—"}</p>
        {item.constraints.length > 0 && (
          <ul className="mt-3 list-inside list-disc text-sm text-gray-600">
            {item.constraints.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="mb-2 text-sm font-semibold text-gray-700">Source evidence</h2>
        {item.source_citations.length === 0 ? (
          <p className="text-sm text-gray-400">No citations recorded.</p>
        ) : (
          <ul className="list-inside list-disc text-sm text-gray-600">
            {item.source_citations.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        )}
        {item.evidence_bundle_id && (
          <a
            href={`/runs/${item.workflow_run_id}`}
            className="mt-3 inline-block text-sm text-sky-700 underline"
          >
            View full evidence bundle →
          </a>
        )}
      </section>

      {/* Decision */}
      <section className="rounded-lg border border-gray-200 bg-white p-5">
        <label className="mb-1 block text-xs uppercase tracking-wide text-gray-400">
          Reviewer note (required for deny / stop)
        </label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          className="mb-4 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          placeholder="Why are you making this decision?"
        />
        {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
        <div className="flex flex-wrap gap-2">
          {ACTIONS.map((a) => {
            const needsNote = (a.outcome === "deny" || a.outcome === "stop") && !note.trim();
            return (
              <button
                key={a.outcome}
                onClick={() => decide(a.outcome)}
                disabled={pending !== null || needsNote}
                className={`rounded-md px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-40 ${a.classes}`}
                title={needsNote ? "A note is required to deny or stop" : undefined}
              >
                {pending === a.outcome ? "…" : a.label}
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
