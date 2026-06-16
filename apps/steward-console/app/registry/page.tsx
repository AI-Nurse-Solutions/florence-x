import { TierBadge } from "@/components/TierBadge";
import { api } from "@/lib/api";
import type { AgentDefinition, ToolUsage } from "@/lib/types";

// Read-only registry viewers. Agents are registered labor (owner, tool boundary,
// NAIO approval, baseline tier). Editing/persistence is a later RFC.
export default async function RegistryPage() {
  let agents: AgentDefinition[] = [];
  let tools: ToolUsage[] = [];
  let error: string | null = null;
  try {
    [agents, tools] = await Promise.all([api.listAgents(), api.listTools()]);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold tracking-tight">Registry</h1>
      {error && (
        <p className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Could not reach the Florence-X API ({error}).
        </p>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Agents (registered labor)</h2>
        <div className="space-y-3">
          {agents.map((a) => (
            <div key={a.agent_id} className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-medium">{a.name}</span>
                  <TierBadge tier={a.edena_baseline_tier} />
                  {a.active ? (
                    <span className="text-xs text-emerald-600">active</span>
                  ) : (
                    <span className="text-xs text-gray-400">inactive</span>
                  )}
                </div>
                <span className="text-xs text-gray-400">{a.agent_id} · v{a.version}</span>
              </div>
              <p className="mt-1 text-sm text-gray-600">{a.purpose}</p>
              <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-500">
                <span>owner: {a.owner_role}</span>
                <span>
                  NAIO approval:{" "}
                  {a.institutional_approval_ref ? (
                    <span className="text-emerald-700">{a.institutional_approval_ref}</span>
                  ) : (
                    <span className="text-red-600">none</span>
                  )}
                </span>
                <span>tools: {a.allowed_tools.join(", ") || "—"}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Tool authorization</h2>
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-400">
              <tr>
                <th className="px-4 py-2">Tool</th>
                <th className="px-4 py-2">Authorized agents</th>
              </tr>
            </thead>
            <tbody>
              {tools.map((t) => (
                <tr key={t.tool_id} className="border-t border-gray-100">
                  <td className="px-4 py-2 font-medium">{t.tool_id}</td>
                  <td className="px-4 py-2 text-gray-600">{t.authorized_agents.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
