import Link from "next/link";
import { TierBadge } from "@/components/TierBadge";
import { api } from "@/lib/api";
import type { ReviewItem } from "@/lib/types";

// Review queue. Server Component: fetches the paused runs awaiting a human.
export default async function ReviewQueuePage() {
  let reviews: ReviewItem[] = [];
  let error: string | null = null;
  try {
    reviews = await api.listReviews();
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div>
      <div className="mb-6 flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Review queue</h1>
        <span className="text-sm text-gray-500">{reviews.length} awaiting a human</span>
      </div>

      {error && (
        <p className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Could not reach the Florence-X API ({error}). Is it running?
        </p>
      )}

      {!error && reviews.length === 0 && (
        <p className="rounded-md border border-gray-200 bg-white px-4 py-8 text-center text-sm text-gray-500">
          Nothing awaiting review. Paused runs (Yellow and above) appear here.
        </p>
      )}

      <ul className="space-y-3">
        {reviews.map((r) => (
          <li key={r.workflow_run_id}>
            <Link
              href={`/reviews/${r.workflow_run_id}`}
              className="block rounded-lg border border-gray-200 bg-white p-4 hover:border-gray-300 hover:shadow-sm"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <TierBadge tier={r.risk_tier} />
                  <span className="font-medium">{r.workflow_id}</span>
                  <span className="text-sm text-gray-400">{r.action_type}</span>
                </div>
                <span className="text-xs text-gray-400">{r.workflow_run_id}</span>
              </div>
              {r.rationale && <p className="mt-2 text-sm text-gray-600">{r.rationale}</p>}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
