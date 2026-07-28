"use client";

/**
 * Public (unauthenticated) chat widget — what a lead sees after clicking an ad.
 * Standalone page, no AppShell, so it can be linked or embedded in an iframe:
 *   /widget?source=facebook_ad_july
 * The `source` query param is stored on the lead for ad attribution.
 */
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  createWidgetSession,
  sendWidgetMessage,
  widgetStreamUrl,
  type WidgetSession,
} from "@/lib/api";

interface Turn {
  from: "lead" | "agent";
  text: string;
}

function WidgetChat() {
  const searchParams = useSearchParams();
  const [session, setSession] = useState<WidgetSession | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return; // React 18 strict-mode double-mount guard
    startedRef.current = true;
    const source = searchParams.get("source");
    createWidgetSession(source)
      .then((s) => {
        setSession(s);
        setTurns([{ from: "agent", text: s.greeting }]);
      })
      .catch(() => setError("Could not start the chat. Please refresh."));
  }, [searchParams]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, busy]);

  // Live channel: once a session exists, subscribe to the conversation stream so
  // human (employee) replies appear without the lead sending another message.
  // We only surface `employee` messages here — the lead's own turns and the AI
  // agent's replies are already rendered by send(); this avoids duplicates.
  useEffect(() => {
    if (!session) return;
    const seen = new Set<number>();
    const es = new EventSource(
      widgetStreamUrl(session.conversation_id, 0),
    );
    es.addEventListener("message", (ev) => {
      const m = JSON.parse((ev as MessageEvent).data) as {
        id: number;
        sender: "lead" | "agent" | "employee";
        body: string;
      };
      if (m.sender !== "employee" || seen.has(m.id)) return;
      seen.add(m.id);
      setTurns((t) => [...t, { from: "agent", text: m.body }]);
    });
    es.onerror = () => {
      /* EventSource auto-reconnects; nothing to do. */
    };
    return () => es.close();
  }, [session]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || !session || busy) return;
    setInput("");
    setError(null);
    setTurns((t) => [...t, { from: "lead", text }]);
    setBusy(true);
    try {
      const reply = await sendWidgetMessage(session.conversation_id, text);
      // Empty reply = the bot is intentionally silent (human takeover, already
      // acked). Don't render a blank bubble; the human's reply arrives via SSE.
      if (reply.trim()) {
        setTurns((t) => [...t, { from: "agent", text: reply }]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Message failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-dvh flex-col bg-neutral-50 dark:bg-neutral-950">
      <header className="border-b border-neutral-200 bg-white px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900">
        <div className="mx-auto flex max-w-2xl items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white">
            L
          </span>
          <div>
            <div className="text-sm font-semibold">LeadLoop Properties</div>
            <div className="text-xs text-green-600 dark:text-green-400">
              ● Online — typically replies instantly
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-2 overflow-y-auto px-4 py-4">
        {turns.map((t, i) => (
          <div
            key={i}
            className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${
              t.from === "lead"
                ? "self-end rounded-br-sm bg-indigo-600 text-white"
                : "self-start rounded-bl-sm bg-white shadow-sm dark:bg-neutral-800"
            }`}
          >
            {t.text}
          </div>
        ))}
        {busy && (
          <div className="self-start rounded-2xl rounded-bl-sm bg-white px-4 py-2.5 text-sm text-neutral-400 shadow-sm dark:bg-neutral-800">
            typing…
          </div>
        )}
        {error && (
          <p className="self-center text-xs text-red-600">{error}</p>
        )}
        <div ref={bottomRef} />
      </main>

      <form
        onSubmit={send}
        className="border-t border-neutral-200 bg-white px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900"
      >
        <div className="mx-auto flex max-w-2xl gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              session ? "Type your message…" : "Connecting…"
            }
            disabled={!session}
            className="flex-1 rounded-full border border-neutral-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-indigo-500 dark:border-neutral-700 dark:bg-neutral-950"
          />
          <button
            type="submit"
            disabled={!session || busy || !input.trim()}
            className="rounded-full bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}

export default function WidgetPage() {
  return (
    <Suspense>
      <WidgetChat />
    </Suspense>
  );
}
