"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { LiveDot } from "@/components/LiveDot";
import { useEventStream } from "@/lib/useEventStream";
import type { CloudEvent } from "@/lib/types";

// Live event feed for a single run. Refreshes the server-rendered evidence when
// the run reaches a terminal/paused state.
const TERMINAL = new Set([
  "florence-x.evidence_bundle.persisted",
  "florence-x.workflow_run.paused",
  "florence-x.action.blocked",
]);

export function LiveRunFeed({ runId }: { runId: string }) {
  const router = useRouter();
  const [events, setEvents] = useState<CloudEvent[]>([]);
  const { connected } = useEventStream((e) => {
    if (e.subject !== runId) return;
    setEvents((prev) => [...prev.slice(-19), e]);
    if (TERMINAL.has(e.type)) router.refresh();
  });

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-gray-400">Live</span>
        <LiveDot connected={connected} />
      </div>
      {events.length === 0 ? (
        <p className="text-xs text-gray-400">Waiting for live events…</p>
      ) : (
        <ul className="space-y-1 text-xs text-gray-600">
          {events.map((e) => (
            <li key={e.id}>
              <span className="text-gray-400">{e.type.replace("florence-x.", "")}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
