"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { formatINR, TierBadge, timeAgo } from "@/components/leadUi";
import {
  dismissFollowup,
  editFollowup,
  getLead,
  getToken,
  sendFollowup,
  type FollowupRead,
  type LeadDetail,
} from "@/lib/api";

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase text-neutral-500">{label}</dt>
      <dd className="mt-0.5 text-sm">{value ?? "—"}</dd>
    </div>
  );
}

function FollowupCard({
  followup,
  onChanged,
}: {
  followup: FollowupRead;
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(followup.draft_body);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isDraft = followup.status === "draft";

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const btn =
    "rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50 transition-colors";

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-center justify-between">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            followup.status === "sent"
              ? "bg-green-100 text-green-800 dark:bg-green-500/25 dark:text-green-300"
              : followup.status === "dismissed"
                ? "bg-neutral-200 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-300"
                : "bg-amber-100 text-amber-800 dark:bg-amber-500/25 dark:text-amber-300"
          }`}
        >
          {followup.status}
        </span>
        <span className="text-xs text-neutral-500">
          drafted {timeAgo(followup.created_at)}
        </span>
      </div>

      {editing ? (
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={7}
          className="mt-3 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 dark:border-neutral-700 dark:bg-neutral-950"
        />
      ) : (
        <p className="mt-3 whitespace-pre-wrap text-sm text-neutral-700 dark:text-neutral-300">
          {followup.draft_body}
        </p>
      )}

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

      {isDraft && (
        <div className="mt-3 flex gap-2">
          {editing ? (
            <>
              <button
                disabled={busy}
                onClick={() =>
                  act(async () => {
                    const token = getToken();
                    if (!token) throw new Error("Not authenticated");
                    await editFollowup(token, followup.id, body);
                    setEditing(false);
                  })
                }
                className={`${btn} bg-indigo-600 text-white hover:bg-indigo-500`}
              >
                Save draft
              </button>
              <button
                disabled={busy}
                onClick={() => {
                  setBody(followup.draft_body);
                  setEditing(false);
                }}
                className={`${btn} border border-neutral-300 dark:border-neutral-700`}
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button
                disabled={busy}
                onClick={() =>
                  act(async () => {
                    const token = getToken();
                    if (!token) throw new Error("Not authenticated");
                    await sendFollowup(token, followup.id);
                  })
                }
                className={`${btn} bg-green-600 text-white hover:bg-green-500`}
              >
                Approve & send
              </button>
              <button
                disabled={busy}
                onClick={() => setEditing(true)}
                className={`${btn} border border-neutral-300 dark:border-neutral-700`}
              >
                Edit
              </button>
              <button
                disabled={busy}
                onClick={() =>
                  act(async () => {
                    const token = getToken();
                    if (!token) throw new Error("Not authenticated");
                    await dismissFollowup(token, followup.id);
                  })
                }
                className={`${btn} border border-neutral-300 text-neutral-500 dark:border-neutral-700`}
              >
                Dismiss
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function LeadDetailPage() {
  const params = useParams<{ id: string }>();
  const leadId = Number(params.id);
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = getToken();
    if (!token || Number.isNaN(leadId)) return;
    try {
      setLead(await getLead(token, leadId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load lead");
    }
  }, [leadId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <AppShell>
      {() => (
        <div className="mx-auto max-w-5xl px-4 py-8">
          <Link
            href="/leads"
            className="text-sm text-indigo-600 hover:underline dark:text-indigo-400"
          >
            ← All leads
          </Link>

          {error && (
            <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-300">
              {error}
            </p>
          )}

          {lead && (
            <>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <h1 className="text-xl font-semibold">
                  {lead.name ?? `Lead #${lead.id}`}
                </h1>
                <TierBadge tier={lead.tier} />
                {lead.score != null && (
                  <span className="text-sm text-neutral-500">
                    score {lead.score}/100
                  </span>
                )}
                <span className="text-sm capitalize text-neutral-500">
                  · {lead.status}
                </span>
              </div>

              <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_360px]">
                {/* Conversation transcript */}
                <div className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
                  <h2 className="text-sm font-semibold">Conversation</h2>
                  <div className="mt-3 flex max-h-[32rem] flex-col gap-2 overflow-y-auto">
                    {lead.messages.length === 0 && (
                      <p className="text-sm text-neutral-500">No messages yet.</p>
                    )}
                    {lead.messages.map((m) => (
                      <div
                        key={m.id}
                        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                          m.sender === "lead"
                            ? "self-start bg-neutral-100 dark:bg-neutral-800"
                            : "self-end bg-indigo-50 dark:bg-indigo-500/15"
                        }`}
                      >
                        <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-400">
                          {m.sender === "lead" ? "Lead" : "AI agent"}
                        </div>
                        <div className="whitespace-pre-wrap">{m.body}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex flex-col gap-6">
                  {/* Qualification summary */}
                  <div className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
                    <h2 className="text-sm font-semibold">Qualification</h2>
                    <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3">
                      <Field label="Email" value={lead.email} />
                      <Field label="Phone" value={lead.phone} />
                      <Field label="Location" value={lead.location} />
                      <Field
                        label="Config"
                        value={lead.bhk ? `${lead.bhk}BHK` : null}
                      />
                      <Field
                        label="Budget"
                        value={
                          lead.budget_min || lead.budget_max
                            ? `${formatINR(lead.budget_min)} – ${formatINR(lead.budget_max)}`
                            : null
                        }
                      />
                      <Field
                        label="Timeline"
                        value={lead.timeline?.replaceAll("_", " ")}
                      />
                      <Field
                        label="Purpose"
                        value={lead.purpose?.replaceAll("_", " ")}
                      />
                      <Field
                        label="Financing"
                        value={lead.financing?.replaceAll("_", " ")}
                      />
                      <Field
                        label="Owner"
                        value={lead.assigned_employee?.name}
                      />
                      <Field label="Ad source" value={lead.ad_source} />
                    </dl>
                  </div>

                  {/* Follow-up drafts */}
                  <div>
                    <h2 className="text-sm font-semibold">Follow-ups</h2>
                    <div className="mt-3 flex flex-col gap-3">
                      {lead.followups.length === 0 && (
                        <p className="text-sm text-neutral-500">
                          None yet — drafts appear here automatically when the
                          lead goes quiet.
                        </p>
                      )}
                      {lead.followups.map((f) => (
                        <FollowupCard key={f.id} followup={f} onChanged={load} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </AppShell>
  );
}
