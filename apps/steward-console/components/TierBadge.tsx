import { tierMeta } from "@/lib/tiers";
import type { RiskTier } from "@/lib/types";

export function TierBadge({ tier }: { tier: RiskTier | null | undefined }) {
  const meta = tierMeta(tier);
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${meta.classes}`}>
      {meta.label}
    </span>
  );
}
