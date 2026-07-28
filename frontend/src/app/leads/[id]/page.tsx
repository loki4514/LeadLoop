"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import AppShell from "@/components/AppShell";
import { formatINR, TierBadge, timeAgo } from "@/components/leadUi";
import {
  deleteLead,
  dismissFollowup,
  editFollowup,
  getLead,
  getToken,
  leadStreamUrl,
  listEmployees,
  replyToLead,
  sendFollowup,
  updateLead,
  type AuditLogRead,
  type Employee,
  type FollowupRead,
  type LeadDetail,
  type LeadMessage,
  type LeadTier,
} from "@/lib/api";

const TIERS: LeadTier[] = ["hot", "warm", "cold"];

const AUDIT_VERB: Record<AuditLogRead["action"], string> = {
  edited: "edited",
  tier_changed: "changed tier",
  reassigned: "reassigned",
  deleted: "deleted",
};

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

const SENDER_LABEL: Record<LeadMessage["sender"], string> = {
  lead: "Lead",
  agent: "AI agent",
  employee: "You / team",
};

function Conversation({
  leadId,
  initialMessages,
  botActive,
  onTookOver,
}: {
  leadId: number;
  initialMessages: LeadMessage[];
  botActive: boolean;
  onTookOver: () => void;
}) {
  const [messages, setMessages] = useState<LeadMessage[]>(initialMessages);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Live updates via SSE — appends any message newer than the last one we hold.
  useEffect(() => {
    const token = getToken();
    if (!token || Number.isNaN(leadId)) return;
    const lastId = messages.length ? messages[messages.length - 1].id : 0;
    const es = new EventSource(leadStreamUrl(token, leadId, lastId));
    es.addEventListener("message", (ev) => {
      const msg = JSON.parse((ev as MessageEvent).data) as LeadMessage;
      setMessages((prev) =>
        prev.some((m) => m.id === msg.id) ? prev : [...prev, msg],
      );
    });
    es.onerror = () => {
      /* EventSource auto-reconnects; nothing to do. */
    };
    return () => es.close();
    // Re-subscribe only when the lead changes, not on every new message.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leadId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const body = input.trim();
    if (!body || busy) return;
    setBusy(true);
    setError(null);
    try {
      const token = getToken();
      if (!token) throw new Error("Not authenticated");
      const msg = await replyToLead(token, leadId, body);
      setMessages((prev) =>
        prev.some((m) => m.id === msg.id) ? prev : [...prev, msg],
      );
      setInput("");
      if (botActive) onTookOver(); // first reply flips the lead out of bot mode
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Conversation</h2>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            botActive
              ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-500/25 dark:text-indigo-300"
              : "bg-green-100 text-green-800 dark:bg-green-500/25 dark:text-green-300"
          }`}
        >
          {botActive ? "🤖 AI handling" : "🧑 Human takeover"}
        </span>
      </div>

      <div className="mt-3 flex max-h-[28rem] flex-col gap-2 overflow-y-auto">
        {messages.length === 0 && (
          <p className="text-sm text-neutral-500">No messages yet.</p>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
              m.sender === "lead"
                ? "self-start bg-neutral-100 dark:bg-neutral-800"
                : m.sender === "employee"
                  ? "self-end bg-green-50 dark:bg-green-500/15"
                  : "self-end bg-indigo-50 dark:bg-indigo-500/15"
            }`}
          >
            <div className="mb-0.5 text-[10px] uppercase tracking-wide text-neutral-400">
              {SENDER_LABEL[m.sender]}
            </div>
            <div className="whitespace-pre-wrap">{m.body}</div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

      <form onSubmit={send} className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            botActive
              ? "Reply to take over from the assistant…"
              : "Type your reply…"
          }
          className="flex-1 rounded-full border border-neutral-300 bg-white px-4 py-2 text-sm outline-none focus:border-indigo-500 dark:border-neutral-700 dark:bg-neutral-950"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}

function LeadControls({
  lead,
  isAdmin,
  onChanged,
}: {
  lead: LeadDetail;
  isAdmin: boolean;
  onChanged: () => void;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [employees, setEmployees] = useState<Employee[]>([]);

  // Admins need the employee list for the reassign dropdown.
  useEffect(() => {
    if (!isAdmin) return;
    const token = getToken();
    if (!token) return;
    listEmployees(token)
      .then(setEmployees)
      .catch(() => {});
  }, [isAdmin]);

  async function apply(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  function setTier(tier: LeadTier) {
    const token = getToken();
    if (!token || tier === lead.tier) return;
    void apply(() => updateLead(token, lead.id, { tier }));
  }

  function reassign(employeeId: number) {
    const token = getToken();
    if (!token || employeeId === (lead.assigned_employee?.id ?? 0)) return;
    void apply(() =>
      updateLead(token, lead.id, { assigned_employee_id: employeeId }),
    );
  }

  async function remove() {
    const token = getToken();
    if (!token) return;
    if (!window.confirm("Delete this lead and its entire conversation? This cannot be undone.")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteLead(token, lead.id);
      router.push("/leads");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <h2 className="text-sm font-semibold">Manage</h2>

      {/* Tier — owner or admin */}
      <div className="mt-3">
        <div className="text-xs uppercase text-neutral-500">Tier</div>
        <div className="mt-1.5 flex gap-1.5">
          {TIERS.map((t) => (
            <button
              key={t}
              disabled={busy}
              onClick={() => setTier(t)}
              className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors disabled:opacity-50 ${
                lead.tier === t
                  ? t === "hot"
                    ? "bg-red-600 text-white"
                    : t === "warm"
                      ? "bg-amber-500 text-white"
                      : "bg-sky-600 text-white"
                  : "border border-neutral-300 text-neutral-600 hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Reassign — admin only */}
      {isAdmin && (
        <div className="mt-4">
          <div className="text-xs uppercase text-neutral-500">Assign to</div>
          <select
            disabled={busy}
            value={lead.assigned_employee?.id ?? ""}
            onChange={(e) => reassign(Number(e.target.value))}
            className="mt-1.5 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 dark:border-neutral-700 dark:bg-neutral-950"
          >
            <option value="" disabled>
              Select an employee…
            </option>
            {employees.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name} ({e.role})
              </option>
            ))}
          </select>
        </div>
      )}

      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}

      {/* Delete — admin only */}
      {isAdmin && (
        <button
          disabled={busy}
          onClick={remove}
          className="mt-4 w-full rounded-md border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-500/40 dark:hover:bg-red-500/10"
        >
          Delete lead
        </button>
      )}
    </div>
  );
}

function AuditTrail({ entries }: { entries: AuditLogRead[] }) {
  if (entries.length === 0) return null;
  return (
    <div>
      <h2 className="text-sm font-semibold">Activity</h2>
      <ul className="mt-3 flex flex-col gap-2.5">
        {entries.map((a) => (
          <li key={a.id} className="text-xs text-neutral-600 dark:text-neutral-400">
            <span className="font-medium text-neutral-800 dark:text-neutral-200">
              {a.actor?.name ?? "System"}
            </span>{" "}
            {AUDIT_VERB[a.action]}
            {a.field && a.action !== "deleted" ? (
              <>
                {" "}
                <span className="text-neutral-500">{a.field.replaceAll("_", " ")}</span>
                {a.old_value != null || a.new_value != null ? (
                  <>
                    : <span className="line-through opacity-70">{a.old_value ?? "—"}</span>{" "}
                    → <span>{a.new_value ?? "—"}</span>
                  </>
                ) : null}
              </>
            ) : a.action === "deleted" ? (
              <> {a.old_value}</>
            ) : null}
            <span className="ml-1 text-neutral-400">· {timeAgo(a.created_at)}</span>
          </li>
        ))}
      </ul>
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
      {(me) => (
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
                {/* Conversation transcript + live human takeover */}
                <Conversation
                  leadId={lead.id}
                  initialMessages={lead.messages}
                  botActive={lead.is_bot_active}
                  onTookOver={load}
                />

                <div className="flex flex-col gap-6">
                  {/* Manage: tier (owner/admin), reassign + delete (admin) */}
                  <LeadControls
                    lead={lead}
                    isAdmin={me.role === "admin"}
                    onChanged={load}
                  />

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

                  {/* Audit trail */}
                  <AuditTrail entries={lead.audit} />
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </AppShell>
  );
}
