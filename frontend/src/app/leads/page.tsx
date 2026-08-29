"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { formatINR, TierBadge, timeAgo } from "@/components/leadUi";
import { TableSkeleton } from "@/components/Skeleton";
import {
  getToken,
  listLeads,
  type LeadStatus,
  type LeadSummary,
  type LeadTier,
} from "@/lib/api";

const TIERS: (LeadTier | "all")[] = ["all", "hot", "warm", "cold"];
const STATUSES: (LeadStatus | "all")[] = [
  "all",
  "new",
  "qualifying",
  "qualified",
  "assigned",
  "closed",
];

export default function LeadsPage() {
  const [leads, setLeads] = useState<LeadSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tier, setTier] = useState<LeadTier | "all">("all");
  const [status, setStatus] = useState<LeadStatus | "all">("all");
  const [mine, setMine] = useState(false);

  const load = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    setError(null);
    setLeads(null); // re-shimmer on filter change instead of showing stale rows
    try {
      setLeads(
        await listLeads(token, {
          tier: tier === "all" ? undefined : tier,
          status: status === "all" ? undefined : status,
          mine,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load leads");
    }
  }, [tier, status, mine]);

  useEffect(() => {
    void load();
  }, [load]);

  const selectCls =
    "rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-900";

  return (
    <AppShell>
      {() => (
        <div className="mx-auto max-w-6xl px-4 py-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold">Leads</h1>
              <p className="mt-1 text-sm text-neutral-500">
                Inbound leads from the chat widget — scored, tiered, and
                auto-assigned.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={tier}
                onChange={(e) => setTier(e.target.value as LeadTier | "all")}
                className={selectCls}
              >
                {TIERS.map((t) => (
                  <option key={t} value={t}>
                    {t === "all" ? "All tiers" : t}
                  </option>
                ))}
              </select>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as LeadStatus | "all")}
                className={selectCls}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s === "all" ? "All statuses" : s}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={mine}
                  onChange={(e) => setMine(e.target.checked)}
                />
                My leads
              </label>
            </div>
          </div>

          {error && (
            <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">
              {error}
            </p>
          )}

          <div className="mt-6 overflow-x-auto rounded-xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200 text-left text-xs uppercase text-neutral-500 dark:border-neutral-800">
                  <th className="px-4 py-3">Lead</th>
                  <th className="px-4 py-3">Looking for</th>
                  <th className="px-4 py-3">Budget</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Owner</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Activity</th>
                </tr>
              </thead>
              <tbody>
                {leads === null && <TableSkeleton rows={6} cols={8} />}
                {leads?.map((lead) => (
                  <tr
                    key={lead.id}
                    className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50 dark:border-neutral-800/60 dark:hover:bg-neutral-800/40"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/leads/${lead.id}`}
                        className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                      >
                        {lead.name ?? `Lead #${lead.id}`}
                      </Link>
                      <div className="text-xs text-neutral-500">
                        {lead.email ?? lead.phone ?? "no contact yet"}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {lead.bhk ? `${lead.bhk}BHK` : "—"}
                      {lead.location ? ` · ${lead.location}` : ""}
                    </td>
                    <td className="px-4 py-3">
                      {lead.budget_min || lead.budget_max
                        ? `${formatINR(lead.budget_min)} – ${formatINR(lead.budget_max)}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <TierBadge tier={lead.tier} />
                        {lead.score != null && (
                          <span className="text-xs text-neutral-500">
                            {lead.score}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 capitalize">{lead.status}</td>
                    <td className="px-4 py-3">
                      {lead.assigned_employee?.name ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-neutral-500">
                      {lead.ad_source ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-neutral-500">
                      {timeAgo(lead.last_activity_at)}
                    </td>
                  </tr>
                ))}
                {leads && leads.length === 0 && (
                  <tr>
                    <td
                      colSpan={8}
                      className="px-4 py-10 text-center text-neutral-500"
                    >
                      No leads yet. Open the{" "}
                      <Link href="/widget" className="text-indigo-600 hover:underline">
                        chat widget
                      </Link>{" "}
                      to create one.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </AppShell>
  );
}
