import Link from "next/link";
import { notFound } from "next/navigation";
import { ApprovalCockpit } from "@/components/ApprovalCockpit";
import { api } from "@/lib/api";
import type { ReviewItem } from "@/lib/types";

// Approval cockpit. Server Component fetches the pending review context; the
// cockpit (Client Component) carries the accountable controls.
export default async function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let item: ReviewItem;
  try {
    item = await api.getReview(id);
  } catch {
    notFound();
  }

  return (
    <div>
      <Link href="/" className="text-sm text-gray-500 hover:text-gray-800">
        ← Review queue
      </Link>
      <h1 className="mb-1 mt-2 text-2xl font-semibold tracking-tight">Approve, edit, or refuse</h1>
      <p className="mb-6 text-sm text-gray-500">
        Run {item.workflow_run_id} · status {item.status}
      </p>
      <ApprovalCockpit item={item} />
    </div>
  );
}
