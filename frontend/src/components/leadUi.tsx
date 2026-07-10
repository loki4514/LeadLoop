import type { LeadTier } from "@/lib/api";

/** Colored hot/warm/cold pill (grey "unscored" when the lead has no tier yet). */
export function TierBadge({ tier }: { tier: LeadTier | null }) {
  if (!tier) {
    return (
      <span className="rounded-full bg-neutral-200 px-2 py-0.5 text-xs font-medium text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300">
        unscored
      </span>
    );
  }
  const cls = {
    hot: "bg-red-100 text-red-800 dark:bg-red-500/25 dark:text-red-300",
    warm: "bg-amber-100 text-amber-800 dark:bg-amber-500/25 dark:text-amber-300",
    cold: "bg-sky-100 text-sky-800 dark:bg-sky-500/25 dark:text-sky-300",
  }[tier];
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${cls}`}
    >
      {tier}
    </span>
  );
}

/** Render absolute INR as lakhs/crores the way the team reads prices. */
export function formatINR(v: number | null): string {
  if (v == null) return "—";
  if (v >= 10_000_000)
    return `₹${(v / 10_000_000).toFixed(2).replace(/\.?0+$/, "")} Cr`;
  if (v >= 100_000) return `₹${(v / 100_000).toFixed(1).replace(/\.0$/, "")} L`;
  return `₹${v.toLocaleString("en-IN")}`;
}

/** Compact relative timestamp for activity columns. */
export function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(ms / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
