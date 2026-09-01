"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import Logo from "@/components/Logo";
import RichText from "@/components/RichText";
import { askDemo, getDemoSuggestions, type DemoTurn } from "@/lib/api";

interface DemoMessage extends DemoTurn {
  id: number;
  /** Set on an assistant turn that failed — rendered as a warning, and kept
   *  out of the history sent back to the API. */
  error?: boolean;
}

// Shown until /demo/suggestions responds, so the empty state never flashes bare.
const FALLBACK_SUGGESTIONS = [
  "What are the eligibility criteria for a home loan in India?",
  "How much is stamp duty when buying property?",
  "What documents should a buyer verify before purchase?",
  "What is RERA and how does it protect buyers?",
];

function Avatar({ role }: { role: DemoTurn["role"] }) {
  const isAssistant = role === "assistant";
  return (
    <div
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold shadow-sm ${
        isAssistant
          ? "bg-gradient-to-br from-indigo-500 to-violet-600 text-white ring-1 ring-inset ring-white/20"
          : "bg-neutral-200 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200"
      }`}
    >
      {isAssistant ? "AI" : "You"}
    </div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex gap-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}

export default function DemoPage() {
  const [messages, setMessages] = useState<DemoMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(FALLBACK_SUGGESTIONS);
  const scrollRef = useRef<HTMLDivElement>(null);
  // Read inside send() so a rapid second question sees the first one's turns —
  // state updates are async and wouldn't be visible yet.
  const historyRef = useRef<DemoMessage[]>([]);

  useEffect(() => {
    getDemoSuggestions()
      .then((s) => {
        if (s.length) setSuggestions(s);
      })
      .catch(() => {
        /* fallback list is already in place */
      });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);

  function push(msg: DemoMessage) {
    historyRef.current = [...historyRef.current, msg];
    setMessages(historyRef.current);
  }

  function reset() {
    historyRef.current = [];
    setMessages([]);
    setQuestion("");
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;

    // Snapshot before the new question — this is the context for *this* turn.
    // Failed turns carry no real answer, so they'd only confuse the model.
    const history: DemoTurn[] = historyRef.current
      .filter((m) => !m.error)
      .map(({ role, content }) => ({ role, content }));

    push({ id: Date.now(), role: "user", content: q });
    setQuestion("");
    setBusy(true);
    try {
      const res = await askDemo(q, history);
      push({ id: Date.now() + 1, role: "assistant", content: res.answer });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      push({
        id: Date.now() + 1,
        role: "assistant",
        content: message,
        error: true,
      });
    } finally {
      setBusy(false);
    }
  }

  const empty = messages.length === 0;

  return (
    <div className="flex min-h-screen flex-col bg-neutral-50 dark:bg-neutral-950">
      <header className="sticky top-0 z-10 border-b border-neutral-200 bg-white/80 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/80">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Logo href="/" size="sm" />
          <div className="flex items-center gap-3">
            {!empty && (
              <button
                onClick={reset}
                className="rounded-lg px-2.5 py-1.5 text-sm text-neutral-500 transition hover:bg-neutral-100 hover:text-neutral-800 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
              >
                Reset
              </button>
            )}
            <Link
              href="/login"
              className="rounded-lg bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-neutral-700 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
            >
              Sign in
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-4">
        <section className="flex flex-1 flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
          <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto p-6">
            {empty && (
              <div className="mx-auto flex h-full max-w-md flex-col justify-center pb-8 text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-lg font-bold text-white shadow-lg shadow-indigo-500/25">
                  AI
                </div>
                <h1 className="text-xl font-semibold tracking-tight">
                  Ask about buying property in India
                </h1>
                <p className="mt-1.5 text-sm leading-relaxed text-neutral-500">
                  A live demo of LeadLoop&apos;s assistant. It answers from a
                  curated real-estate knowledge base — home loans, stamp duty,
                  registration, RERA and more.
                </p>
                <div className="mt-6 grid gap-2 text-left">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="group flex items-center gap-2.5 rounded-xl border border-neutral-200 bg-neutral-50/50 px-3.5 py-2.5 text-sm text-neutral-600 transition hover:border-indigo-300 hover:bg-white hover:text-neutral-900 hover:shadow-sm dark:border-neutral-800 dark:bg-neutral-800/30 dark:text-neutral-300 dark:hover:border-indigo-500/50 dark:hover:bg-neutral-800 dark:hover:text-white"
                    >
                      <span className="text-indigo-400 transition group-hover:text-indigo-500">
                        ✦
                      </span>
                      <span className="flex-1">{s}</span>
                      <span className="text-neutral-300 opacity-0 transition group-hover:opacity-100 dark:text-neutral-600">
                        →
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => {
              const isAssistant = m.role === "assistant";
              return (
                <div
                  key={m.id}
                  className={`flex gap-3 ${isAssistant ? "" : "flex-row-reverse"}`}
                >
                  <Avatar role={m.role} />
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
                      !isAssistant
                        ? "rounded-tr-sm bg-gradient-to-br from-indigo-500 to-violet-600 text-white"
                        : m.error
                          ? "rounded-tl-sm border border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200"
                          : "rounded-tl-sm border border-neutral-200/60 bg-neutral-50 text-neutral-800 dark:border-neutral-700/50 dark:bg-neutral-800 dark:text-neutral-100"
                    }`}
                  >
                    {isAssistant ? (
                      <RichText text={m.error ? `⚠️ ${m.content}` : m.content} />
                    ) : (
                      <p className="whitespace-pre-wrap">{m.content}</p>
                    )}
                  </div>
                </div>
              );
            })}

            {busy && (
              <div className="flex gap-3">
                <Avatar role="assistant" />
                <div className="rounded-2xl rounded-tl-sm border border-neutral-200/60 bg-neutral-50 px-4 py-3 dark:border-neutral-700/50 dark:bg-neutral-800">
                  <TypingDots />
                </div>
              </div>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(question);
            }}
            className="border-t border-neutral-200 bg-white/60 p-3 backdrop-blur dark:border-neutral-800 dark:bg-neutral-900/60"
          >
            <div className="flex items-end gap-2 rounded-2xl border border-neutral-300 bg-white px-3 py-2 shadow-sm transition focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 dark:border-neutral-700 dark:bg-neutral-900">
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(question);
                  }
                }}
                rows={1}
                maxLength={1000}
                placeholder="Ask about home loans, stamp duty, RERA…"
                className="max-h-32 flex-1 resize-none bg-transparent py-1 text-sm outline-none placeholder:text-neutral-400"
              />
              <button
                type="submit"
                disabled={busy || !question.trim()}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-sm transition hover:shadow-md active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
                aria-label="Send message"
              >
                <svg
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                  aria-hidden
                >
                  <path d="M3.4 2.6a.75.75 0 0 0-.98.98l2.1 5.67L11 10l-6.48.75-2.1 5.67a.75.75 0 0 0 .98.98c.06-.02 14.4-6.42 14.4-6.42a.75.75 0 0 0 0-1.36S3.46 2.62 3.4 2.6Z" />
                </svg>
              </button>
            </div>
            <p className="mt-1.5 px-1 text-center text-[11px] text-neutral-400">
              Answers come only from the knowledge base and may need
              verification. Not legal or financial advice.
            </p>
          </form>
        </section>
      </main>
    </div>
  );
}
