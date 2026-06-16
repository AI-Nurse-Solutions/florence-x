import { TierBadge } from "@/components/TierBadge";
import type { EdenaDecision } from "@/lib/types";

// Full EDENA verdict for each gated action — the rationale, constraints, and the
// policy-pack version that produced it (decision provenance).
export function DecisionInspector({ decisions }: { decisions: EdenaDecision[] }) {
  if (decisions.length === 0) {
    return <p className="text-sm text-gray-400">No EDENA decisions recorded.</p>;
  }
  return (
    <div className="space-y-3">
      {decisions.map((d) => (
        <div key={d.decision_id} className="rounded-md border border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <TierBadge tier={d.risk_tier} />
            <span className="text-sm font-medium">{d.decision}</span>
            {d.required_human_role && (
              <span className="text-xs text-gray-400">role: {d.required_human_role}</span>
            )}
          </div>
          <p className="mt-2 text-sm text-gray-700">{d.rationale}</p>
          {d.constraints.length > 0 && (
            <ul className="mt-2 list-inside list-disc text-xs text-gray-600">
              {d.constraints.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          )}
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-gray-400">
            <span>action {d.action_id}</span>
            {d.policy_pack_version && <span>pack {d.policy_pack_version}</span>}
            {d.evidence_required.length > 0 && (
              <span>requires: {d.evidence_required.join(", ")}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
