"use client";

import { useRouter } from "next/navigation";
import { LiveDot } from "@/components/LiveDot";
import { useEventStream } from "@/lib/useEventStream";

// Events that change the review queue's contents; on any of them, re-fetch the
// Server-Component queue so it reflects live run state.
const QUEUE_EVENTS = new Set([
  "florence-x.human_review.requested",
  "florence-x.human_review.completed",
  "florence-x.workflow_run.paused",
  "florence-x.evidence_bundle.persisted",
  "florence-x.action.blocked",
]);

export function LiveRefresh() {
  const router = useRouter();
  const { connected } = useEventStream((e) => {
    if (QUEUE_EVENTS.has(e.type)) router.refresh();
  });
  return <LiveDot connected={connected} />;
}
