"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import AppShell from "@/components/AppShell";
import ConfirmModal from "@/components/ConfirmModal";
import RichText from "@/components/RichText";
import { formatINR, TierBadge, timeAgo } from "@/components/leadUi";
import {
  deleteLead,
  dismissFollowup,
  editFollowup,
  getLead,
  getLeadActivity,
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
            {m.sender === "lead" ? (
              <div className="whitespace-pre-wrap">{m.body}</div>
            ) : (
              <RichText text={m.body} />
            )}
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

function LockedConversation({ ownerName }: { ownerName?: string | null }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-neutral-300 bg-neutral-50/60 p-10 text-center dark:border-neutral-700 dark:bg-neutral-900/40">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-neutral-200 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-400">
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-6 w-6"
          aria-hidden
        >
          <path
            fillRule="evenodd"
            d="M10 1a4 4 0 0 0-4 4v2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-1V5a4 4 0 0 0-4-4Zm2 6V5a2 2 0 1 0-4 0v2h4Z"
            clipRule="evenodd"
          />
        </svg>
      </div>
      <h2 className="mt-4 text-sm font-semibold">Conversation is private</h2>
      <p className="mt-1.5 max-w-xs text-sm leading-relaxed text-neutral-500">
        This lead is assigned to{" "}
        <span className="font-medium text-neutral-700 dark:text-neutral-300">
          {ownerName ?? "another team member"}
        </span>
        . Only the assigned owner and admins can view the chat and manage this
        lead.
      </p>
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

  const currentOwnerId = lead.assigned_employee?.id ?? null;
  // Pending (unsaved) assignment selection — only applied when "Save
  // assignment" is pressed, never on change.
  const [pendingOwnerId, setPendingOwnerId] = useState<number | null>(
    currentOwnerId,
  );

  // Keep the dropdown in sync if the lead's owner changes underneath us
  // (e.g. after a successful save reloads the lead).
  useEffect(() => {
    setPendingOwnerId(currentOwnerId);
  }, [currentOwnerId]);

  // Admins need the employee list for the reassign dropdown.
  useEffect(() => {
    if (!isAdmin) return;
    const token = getToken();
    if (!token) return;
    listEmployees(token)
      .then(setEmployees)
      .catch(() => {});
  }, [isAdmin]);

  const assignmentDirty =
    pendingOwnerId !== null && pendingOwnerId !== currentOwnerId;
  const pendingOwnerName =
    employees.find((e) => e.id === pendingOwnerId)?.name ?? "this employee";
  // A conversation already exists with the lead — changing owner/tier touches
  // an in-progress chat.
  const hasChat = lead.messages.length > 0;

  // Pending (unsaved) tier selection — like the assignment, applied only when
  // "Save tier" is pressed.
  const [pendingTier, setPendingTier] = useState<LeadTier | null>(lead.tier);
  useEffect(() => {
    setPendingTier(lead.tier);
  }, [lead.tier]);
  const tierDirty = pendingTier !== null && pendingTier !== lead.tier;

  // Which confirmation modal is open, if any.
  const [modal, setModal] = useState<"tier" | "assign" | "delete" | null>(null);

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

  // Warnings shown together inside the modal (replacing the two sequential
  // window.confirm dialogs). The second only appears when a chat exists.
  const chatWarning =
    "An employee is already engaged with this user in the chat.";

  function confirmTier() {
    const token = getToken();
    setModal(null);
    if (!token || !tierDirty || pendingTier === null) return;
    void apply(() => updateLead(token, lead.id, { tier: pendingTier }));
  }

  function confirmAssignment() {
    const token = getToken();
    setModal(null);
    if (!token || !assignmentDirty || pendingOwnerId === null) return;
    void apply(() =>
      updateLead(token, lead.id, { assigned_employee_id: pendingOwnerId }),
    );
  }

  async function confirmDelete() {
    const token = getToken();
    setModal(null);
    if (!token) return;
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

      {/* Tier — owner or admin. Pills stage a choice; applied on "Save tier". */}
      <div className="mt-3">
        <div className="text-xs uppercase text-neutral-500">Tier</div>
        <div className="mt-1.5 flex gap-1.5">
          {TIERS.map((t) => (
            <button
              key={t}
              disabled={busy}
              onClick={() => setPendingTier(t)}
              className={`rounded-full px-3 py-1 text-xs font-medium capitalize transition-colors disabled:opacity-50 ${
                pendingTier === t
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

        {tierDirty && (
          <>
            <p className="mt-2 flex items-start gap-1.5 text-xs text-amber-600 dark:text-amber-400">
              <span aria-hidden>⚠</span>
              <span>
                Changing the tier may impact the live chat
                {hasChat
                  ? " — an employee is already engaged with this user."
                  : "."}
              </span>
            </p>
            <div className="mt-2 flex gap-2">
              <button
                disabled={busy}
                onClick={() => setModal("tier")}
                className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
              >
                {busy ? "Saving…" : "Save tier"}
              </button>
              <button
                disabled={busy}
                onClick={() => setPendingTier(lead.tier)}
                className="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-medium disabled:opacity-50 dark:border-neutral-700"
              >
                Cancel
              </button>
            </div>
          </>
        )}
      </div>

      {/* Reassign — admin only. The dropdown only stages a choice; the change
          is applied when "Save assignment" is pressed (with confirmations). */}
      {isAdmin && (
        <div className="mt-4">
          <div className="text-xs uppercase text-neutral-500">Assign to</div>
          <select
            disabled={busy}
            value={pendingOwnerId ?? ""}
            onChange={(e) =>
              setPendingOwnerId(e.target.value ? Number(e.target.value) : null)
            }
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

          {assignmentDirty && (
            <>
              <p className="mt-2 flex items-start gap-1.5 text-xs text-amber-600 dark:text-amber-400">
                <span aria-hidden>⚠</span>
                <span>
                  Reassigning may impact the live chat
                  {hasChat
                    ? " — an employee is already engaged with this user."
                    : "."}
                </span>
              </p>
              <div className="mt-2 flex gap-2">
                <button
                  disabled={busy}
                  onClick={() => setModal("assign")}
                  className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
                >
                  {busy ? "Saving…" : "Save assignment"}
                </button>
                <button
                  disabled={busy}
                  onClick={() => setPendingOwnerId(currentOwnerId)}
                  className="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-medium disabled:opacity-50 dark:border-neutral-700"
                >
                  Cancel
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}

      {/* Delete — admin only */}
      {isAdmin && (
        <button
          disabled={busy}
          onClick={() => setModal("delete")}
          className="mt-4 w-full rounded-md border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-500/40 dark:hover:bg-red-500/10"
        >
          Delete lead
        </button>
      )}

      {/* In-app confirmations (replacing browser confirm/alert) */}
      <ConfirmModal
        open={modal === "tier"}
        title="Change tier?"
        message={
          <>
            Set this lead&apos;s tier to{" "}
            <span className="font-semibold capitalize">{pendingTier}</span>.
          </>
        }
        warnings={[
          "Changing the tier may impact the live chat.",
          ...(hasChat ? [chatWarning] : []),
        ]}
        confirmLabel="Change tier"
        onConfirm={confirmTier}
        onCancel={() => setModal(null)}
      />

      <ConfirmModal
        open={modal === "assign"}
        title="Reassign lead?"
        message={
          <>
            Assign this lead to{" "}
            <span className="font-semibold">{pendingOwnerName}</span>.
          </>
        }
        warnings={[
          "Reassigning may impact the live chat.",
          ...(hasChat ? [chatWarning] : []),
        ]}
        confirmLabel="Reassign"
        onConfirm={confirmAssignment}
        onCancel={() => setModal(null)}
      />

      <ConfirmModal
        open={modal === "delete"}
        title="Delete lead?"
        message="This permanently deletes the lead and its entire conversation. This cannot be undone."
        tone="danger"
        confirmLabel="Delete now"
        countdownSeconds={5}
        onConfirm={confirmDelete}
        onCancel={() => setModal(null)}
      />
    </div>
  );
}

const STATUSES: LeadDetail["status"][] = [
  "new",
  "qualifying",
  "qualified",
  "assigned",
  "closed",
];

/** A labelled input used inside the edit form. */
function EditField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-xs uppercase text-neutral-500">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

const inputCls =
  "w-full rounded-md border border-neutral-300 bg-white px-2.5 py-1.5 text-sm outline-none focus:border-indigo-500 dark:border-neutral-700 dark:bg-neutral-950";

/**
 * Qualification details: read-only for non-owners, editable (Edit → Save/Cancel)
 * for owners and admins. Only changed fields are sent to the API.
 */
function QualificationCard({
  lead,
  canEdit,
  onChanged,
}: {
  lead: LeadDetail;
  canEdit: boolean;
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Draft state, seeded from the lead. Strings for text inputs; numbers as text
  // so an empty field clears the value.
  const [form, setForm] = useState({
    name: lead.name ?? "",
    email: lead.email ?? "",
    phone: lead.phone ?? "",
    location: lead.location ?? "",
    bhk: lead.bhk?.toString() ?? "",
    budget_min: lead.budget_min?.toString() ?? "",
    budget_max: lead.budget_max?.toString() ?? "",
    timeline: lead.timeline ?? "",
    purpose: lead.purpose ?? "",
    financing: lead.financing ?? "",
    status: lead.status,
  });

  function startEdit() {
    setForm({
      name: lead.name ?? "",
      email: lead.email ?? "",
      phone: lead.phone ?? "",
      location: lead.location ?? "",
      bhk: lead.bhk?.toString() ?? "",
      budget_min: lead.budget_min?.toString() ?? "",
      budget_max: lead.budget_max?.toString() ?? "",
      timeline: lead.timeline ?? "",
      purpose: lead.purpose ?? "",
      financing: lead.financing ?? "",
      status: lead.status,
    });
    setError(null);
    setEditing(true);
  }

  const set = (k: keyof typeof form) => (v: string) =>
    setForm((f) => ({ ...f, [k]: v }));

  async function save() {
    const token = getToken();
    if (!token) return;

    // Build a diff: only include fields that actually changed.
    const changes: Record<string, unknown> = {};
    const text = (v: string) => (v.trim() === "" ? null : v.trim());
    const num = (v: string) => (v.trim() === "" ? null : Number(v));

    if (text(form.name) !== lead.name) changes.name = text(form.name);
    if (text(form.email) !== lead.email) changes.email = text(form.email);
    if (text(form.phone) !== lead.phone) changes.phone = text(form.phone);
    if (text(form.location) !== lead.location)
      changes.location = text(form.location);
    if (num(form.bhk) !== lead.bhk) changes.bhk = num(form.bhk);
    if (num(form.budget_min) !== lead.budget_min)
      changes.budget_min = num(form.budget_min);
    if (num(form.budget_max) !== lead.budget_max)
      changes.budget_max = num(form.budget_max);
    if (text(form.timeline) !== lead.timeline)
      changes.timeline = text(form.timeline);
    if (text(form.purpose) !== lead.purpose)
      changes.purpose = text(form.purpose);
    if (text(form.financing) !== lead.financing)
      changes.financing = text(form.financing);
    if (form.status !== lead.status) changes.status = form.status;

    if (Object.keys(changes).length === 0) {
      setEditing(false);
      return;
    }

    // Guard the numeric fields.
    for (const k of ["bhk", "budget_min", "budget_max"] as const) {
      if (changes[k] != null && Number.isNaN(changes[k] as number)) {
        setError(`${k.replaceAll("_", " ")} must be a number`);
        return;
      }
    }

    setBusy(true);
    setError(null);
    try {
      await updateLead(token, lead.id, changes);
      setEditing(false);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Qualification</h2>
        {canEdit && !editing && (
          <button
            onClick={startEdit}
            className="inline-flex items-center gap-1 rounded-md border border-neutral-300 px-2.5 py-1 text-xs font-medium text-neutral-600 transition hover:border-indigo-400 hover:text-neutral-900 dark:border-neutral-700 dark:text-neutral-300 dark:hover:border-indigo-500 dark:hover:text-white"
          >
            <svg
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-3.5 w-3.5"
              aria-hidden
            >
              <path d="M13.586 3.586a2 2 0 1 1 2.828 2.828l-.793.793-2.828-2.828.793-.793ZM11.379 5.793 3 14.172V17h2.828l8.38-8.379-2.83-2.828Z" />
            </svg>
            Edit
          </button>
        )}
      </div>

      {editing ? (
        <>
          <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2.5">
            <EditField label="Name">
              <input
                className={inputCls}
                value={form.name}
                onChange={(e) => set("name")(e.target.value)}
              />
            </EditField>
            <EditField label="Email">
              <input
                type="email"
                className={inputCls}
                value={form.email}
                onChange={(e) => set("email")(e.target.value)}
              />
            </EditField>
            <EditField label="Phone">
              <input
                className={inputCls}
                value={form.phone}
                onChange={(e) => set("phone")(e.target.value)}
              />
            </EditField>
            <EditField label="Location">
              <input
                className={inputCls}
                value={form.location}
                onChange={(e) => set("location")(e.target.value)}
              />
            </EditField>
            <EditField label="BHK">
              <input
                inputMode="numeric"
                className={inputCls}
                value={form.bhk}
                onChange={(e) => set("bhk")(e.target.value)}
              />
            </EditField>
            <EditField label="Status">
              <select
                className={inputCls}
                value={form.status}
                onChange={(e) =>
                  set("status")(e.target.value as LeadDetail["status"])
                }
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s} className="capitalize">
                    {s}
                  </option>
                ))}
              </select>
            </EditField>
            <EditField label="Budget min (₹)">
              <input
                inputMode="numeric"
                className={inputCls}
                value={form.budget_min}
                onChange={(e) => set("budget_min")(e.target.value)}
              />
            </EditField>
            <EditField label="Budget max (₹)">
              <input
                inputMode="numeric"
                className={inputCls}
                value={form.budget_max}
                onChange={(e) => set("budget_max")(e.target.value)}
              />
            </EditField>
            <EditField label="Timeline">
              <input
                className={inputCls}
                value={form.timeline}
                onChange={(e) => set("timeline")(e.target.value)}
              />
            </EditField>
            <EditField label="Purpose">
              <input
                className={inputCls}
                value={form.purpose}
                onChange={(e) => set("purpose")(e.target.value)}
              />
            </EditField>
            <EditField label="Financing">
              <input
                className={inputCls}
                value={form.financing}
                onChange={(e) => set("financing")(e.target.value)}
              />
            </EditField>
          </div>

          {error && <p className="mt-3 text-xs text-red-600">{error}</p>}

          <div className="mt-4 flex gap-2">
            <button
              disabled={busy}
              onClick={save}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
            >
              {busy ? "Saving…" : "Save changes"}
            </button>
            <button
              disabled={busy}
              onClick={() => {
                setEditing(false);
                setError(null);
              }}
              className="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-medium disabled:opacity-50 dark:border-neutral-700"
            >
              Cancel
            </button>
          </div>
        </>
      ) : (
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3">
          <Field label="Email" value={lead.email} />
          <Field label="Phone" value={lead.phone} />
          <Field label="Location" value={lead.location} />
          <Field label="Config" value={lead.bhk ? `${lead.bhk}BHK` : null} />
          <Field
            label="Budget"
            value={
              lead.budget_min || lead.budget_max
                ? `${formatINR(lead.budget_min)} – ${formatINR(lead.budget_max)}`
                : null
            }
          />
          <Field label="Timeline" value={lead.timeline?.replaceAll("_", " ")} />
          <Field label="Purpose" value={lead.purpose?.replaceAll("_", " ")} />
          <Field
            label="Financing"
            value={lead.financing?.replaceAll("_", " ")}
          />
          <Field label="Owner" value={lead.assigned_employee?.name} />
          <Field label="Ad source" value={lead.ad_source} />
        </dl>
      )}
    </div>
  );
}

/**
 * A card whose body collapses behind a header toggle. Collapsed by default so
 * secondary panels (follow-ups, activity) don't force long scrolling.
 */
function CollapsibleCard({
  title,
  count,
  defaultOpen = false,
  children,
}: {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between rounded-xl px-4 py-3 text-left transition hover:bg-neutral-50 dark:hover:bg-neutral-800/40"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          <h2 className="text-sm font-semibold">{title}</h2>
          {count != null && count > 0 && (
            <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-500 dark:bg-neutral-800">
              {count}
            </span>
          )}
        </span>
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-4 w-4 text-neutral-400 transition-transform ${
            open ? "rotate-180" : ""
          }`}
          aria-hidden
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.17l3.71-3.94a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z"
            clipRule="evenodd"
          />
        </svg>
      </button>
      {/* Smooth height transition (grid-rows 0fr→1fr) avoids the abrupt reflow
          that made the layout jitter on toggle. */}
      <div
        className={`grid transition-[grid-template-rows] duration-200 ease-out ${
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
          <div className="max-h-80 overflow-y-auto px-4 pb-4">{children}</div>
        </div>
      </div>
    </div>
  );
}

function AuditEntry({ a }: { a: AuditLogRead }) {
  return (
    <li className="flex gap-2.5">
      <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-neutral-300 dark:bg-neutral-600" />
      <div className="min-w-0 flex-1">
        <p className="text-xs leading-relaxed text-neutral-600 dark:text-neutral-400">
          <span className="font-medium text-neutral-800 dark:text-neutral-200">
            {a.actor?.name ?? "System"}
          </span>{" "}
          {AUDIT_VERB[a.action]}
          {a.field && a.action !== "deleted" ? (
            <>
              {" "}
              <span className="text-neutral-500">
                {a.field.replaceAll("_", " ")}
              </span>
            </>
          ) : a.action === "deleted" ? (
            <> {a.old_value}</>
          ) : null}
        </p>
        {a.field &&
          a.action !== "deleted" &&
          (a.old_value != null || a.new_value != null) && (
            <p className="mt-0.5 flex items-center gap-1.5 text-xs">
              <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-neutral-500 line-through dark:bg-neutral-800">
                {a.old_value ?? "—"}
              </span>
              <span className="text-neutral-400">→</span>
              <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-medium text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300">
                {a.new_value ?? "—"}
              </span>
            </p>
          )}
        <span className="text-[11px] text-neutral-400">
          {timeAgo(a.created_at)}
        </span>
      </div>
    </li>
  );
}

/**
 * Collapsible activity/audit trail. Seeds from the bundled `initial` entries and
 * re-queries `GET /leads/{id}/activity` when the actor filter changes. The actor
 * options are derived from whoever appears in the initial history.
 */
function AuditTrail({
  leadId,
  initial,
}: {
  leadId: number;
  initial: AuditLogRead[];
}) {
  const [entries, setEntries] = useState<AuditLogRead[]>(initial);
  const [actorId, setActorId] = useState<number | "all">("all");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setEntries(initial);
  }, [initial]);

  // Distinct actors seen in the full (unfiltered) history, for the dropdown.
  const actors = Array.from(
    new Map(
      initial
        .filter((a) => a.actor)
        .map((a) => [a.actor!.id, a.actor!] as const),
    ).values(),
  );

  async function applyFilter(next: number | "all") {
    setActorId(next);
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      setEntries(
        await getLeadActivity(token, leadId, {
          actorId: next === "all" ? undefined : next,
        }),
      );
    } catch {
      /* keep previous entries on failure */
    } finally {
      setLoading(false);
    }
  }

  return (
    <CollapsibleCard title="Activity" count={initial.length}>
      {actors.length > 0 && (
        <div className="mb-3 flex items-center gap-2">
          <label className="text-xs text-neutral-500">Filter by</label>
          <select
            value={actorId}
            onChange={(e) =>
              applyFilter(
                e.target.value === "all" ? "all" : Number(e.target.value),
              )
            }
            className="rounded-md border border-neutral-300 bg-white px-2 py-1 text-xs outline-none focus:border-indigo-500 dark:border-neutral-700 dark:bg-neutral-950"
          >
            <option value="all">Everyone</option>
            {actors.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-neutral-400">Loading…</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-neutral-500">
          {actorId === "all"
            ? "No changes recorded yet."
            : "No changes by this person."}
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {entries.map((a) => (
            <AuditEntry key={a.id} a={a} />
          ))}
        </ul>
      )}
    </CollapsibleCard>
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

              <div className="mt-6 grid items-start gap-6 lg:grid-cols-[1fr_360px]">
                {/* Conversation transcript + live human takeover — owner/admin
                    only. Non-owners see a locked notice with the assignee. */}
                {lead.can_edit ? (
                  <Conversation
                    leadId={lead.id}
                    initialMessages={lead.messages}
                    botActive={lead.is_bot_active}
                    onTookOver={load}
                  />
                ) : (
                  <LockedConversation ownerName={lead.assigned_employee?.name} />
                )}

                <div className="flex flex-col gap-6">
                  {/* Manage: tier (owner/admin), reassign + delete (admin).
                      Hidden entirely for non-owner employees. */}
                  {lead.can_edit && (
                    <LeadControls
                      lead={lead}
                      isAdmin={me.role === "admin"}
                      onChanged={load}
                    />
                  )}

                  {/* Qualification — read-only for non-owners, editable for
                      owners/admins (Edit → Save/Cancel). */}
                  <QualificationCard
                    lead={lead}
                    canEdit={lead.can_edit}
                    onChanged={load}
                  />

                  {/* Follow-up drafts — owner/admin only, collapsible */}
                  {lead.can_edit && (
                    <CollapsibleCard
                      title="Follow-ups"
                      count={lead.followups.length}
                      defaultOpen={lead.followups.length > 0}
                    >
                      <div className="flex flex-col gap-3">
                        {lead.followups.length === 0 && (
                          <p className="text-sm text-neutral-500">
                            None yet — drafts appear here automatically when the
                            lead goes quiet.
                          </p>
                        )}
                        {lead.followups.map((f) => (
                          <FollowupCard
                            key={f.id}
                            followup={f}
                            onChanged={load}
                          />
                        ))}
                      </div>
                    </CollapsibleCard>
                  )}

                  {/* Audit trail — owner/admin only, collapsible + filterable */}
                  {lead.can_edit && (
                    <AuditTrail leadId={lead.id} initial={lead.audit} />
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </AppShell>
  );
}
