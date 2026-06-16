import type { RiskTier } from "./types";

// EDENA tier → presentation. Color-coding is a primary signal in the queue.
export const TIER_META: Record<RiskTier, { label: string; classes: string }> = {
  green: { label: "Green", classes: "bg-emerald-50 text-emerald-700 border-emerald-300" },
  yellow: { label: "Yellow", classes: "bg-amber-50 text-amber-800 border-amber-300" },
  orange: { label: "Orange", classes: "bg-orange-50 text-orange-800 border-orange-400" },
  red: { label: "Red", classes: "bg-red-50 text-red-700 border-red-400" },
  red_blocked: { label: "Red — Blocked", classes: "bg-red-100 text-red-900 border-red-600" },
};

export function tierMeta(tier: RiskTier | null | undefined) {
  return (tier && TIER_META[tier]) || { label: tier ?? "—", classes: "bg-gray-50 text-gray-600 border-gray-300" };
}
