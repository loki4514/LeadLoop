"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import AppShell from "@/components/AppShell";
import RichText from "@/components/RichText";
import {
  askChat,
  getConversation,
  getToken,
  listConversations,
  type ChatMessage,
  type ConversationSummary,
  type SearchHit,
} from "@/lib/api";

function Sources({ sources }: { sources: SearchHit[] }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
      >
        <span>{open ? "▾" : "▸"}</span>
        {open ? "Hide" : "Show"} {sources.length} source
        {sources.length > 1 ? "s" : ""}
      </button>
      {open && (
        <ol className="mt-2 space-y-2">
          {sources.map((s, i) => (
            <li
              key={`${s.document_id}-${s.chunk_index}`}
              className="rounded-lg border border-neutral-200 bg-neutral-50/80 p-3 text-xs dark:border-neutral-800 dark:bg-neutral-800/40"
            >
              <div className="mb-1 flex items-center justify-between text-neutral-500">
                <span className="font-medium text-neutral-700 dark:text-neutral-300">
                  [{i + 1}] {s.filename}
                </span>
                <span className="rounded-full bg-neutral-200 px-2 py-0.5 text-[10px] dark:bg-neutral-700">
                  {s.score.toFixed(3)}
                </span>
              </div>
              <p className="whitespace-pre-wrap text-neutral-600 dark:text-neutral-400">
                {s.content.length > 400
                  ? `${s.content.slice(0, 400)}…`
                  : s.content}
              </p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Avatar({ role }: { role: ChatMessage["sender"] }) {
  const isAgent = role === "agent";
  return (
    <div
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold shadow-sm ${
        isAgent
          ? "bg-gradient-to-br from-indigo-500 to-violet-600 text-white ring-1 ring-inset ring-white/20"
          : "bg-neutral-200 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200"
      }`}
    >
      {isAgent ? "AI" : "You"}
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

const SUGGESTIONS = [
  "What are the eligibility criteria for a home loan in India?",
  "How much is stamp duty when buying property?",
  "What documents should a buyer verify before purchase?",
  "How does lead scoring work in LeadLoop?",
];

export default function ChatPage() {
  const [convos, setConvos] = useState<ConversationSummary[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const refreshConvos = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    try {
      setConvos(await listConversations(token));
    } catch {
      /* non-fatal */
    }
  }, []);

  useEffect(() => {
    refreshConvos();
  }, [refreshConvos]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);

  async function openConversation(id: number) {
    const token = getToken();
    if (!token || id === activeId) return;
    setLoadingHistory(true);
    setActiveId(id);
    try {
      const detail = await getConversation(token, id);
      setMessages(detail.messages);
    } catch {
      setMessages([]);
    } finally {
      setLoadingHistory(false);
    }
  }

  function newChat() {
    setActiveId(null);
    setMessages([]);
    setQuestion("");
  }

  async function send(text: string) {
    const token = getToken();
    const q = text.trim();
    if (!token || !q || busy) return;

    const optimistic: ChatMessage = {
      id: Date.now(),
      sender: "employee",
      body: q,
      sources: null,
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, optimistic]);
    setQuestion("");
    setBusy(true);
    try {
      const res = await askChat(token, q, activeId ?? undefined);
      setMessages((m) => [
        ...m,
        {
          id: Date.now() + 1,
          sender: "agent",
          body: res.answer,
          sources: res.sources,
          created_at: new Date().toISOString(),
        },
      ]);
      const wasNew = activeId === null;
      setActiveId(res.conversation_id);
      if (wasNew) refreshConvos();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      setMessages((m) => [
        ...m,
        {
          id: Date.now() + 1,
          sender: "agent",
          body: `⚠️ ${message}`,
          sources: null,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      {() => (
        <div className="grid h-[calc(100vh-9rem)] grid-cols-1 gap-4 md:grid-cols-[260px_1fr]">
          {/* Sidebar */}
          <aside className="hidden flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm md:flex dark:border-neutral-800 dark:bg-neutral-900">
            <div className="p-3">
              <button
                onClick={newChat}
                className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 px-3 py-2.5 text-sm font-medium text-white shadow-sm transition hover:from-indigo-500 hover:to-violet-500 hover:shadow-md active:scale-[0.98]"
              >
                <svg
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-4 w-4"
                  aria-hidden
                >
                  <path d="M10 4a.75.75 0 0 1 .75.75v4.5h4.5a.75.75 0 0 1 0 1.5h-4.5v4.5a.75.75 0 0 1-1.5 0v-4.5h-4.5a.75.75 0 0 1 0-1.5h4.5v-4.5A.75.75 0 0 1 10 4Z" />
                </svg>
                New chat
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-2 pb-2">
              <p className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
                History
              </p>
              {convos.length === 0 && (
                <p className="px-2 py-2 text-xs text-neutral-400">
                  No conversations yet.
                </p>
              )}
              <ul className="space-y-0.5">
                {convos.map((c) => {
                  const isActive = c.id === activeId;
                  return (
                    <li key={c.id}>
                      <button
                        onClick={() => openConversation(c.id)}
                        className={`group flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition ${
                          isActive
                            ? "bg-indigo-50 font-medium text-indigo-900 dark:bg-indigo-500/10 dark:text-indigo-200"
                            : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800/60"
                        }`}
                        title={c.title ?? "Untitled"}
                      >
                        <svg
                          viewBox="0 0 20 20"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          className={`h-4 w-4 shrink-0 ${
                            isActive
                              ? "text-indigo-500"
                              : "text-neutral-400 group-hover:text-neutral-500"
                          }`}
                          aria-hidden
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M4 5.5A1.5 1.5 0 0 1 5.5 4h9A1.5 1.5 0 0 1 16 5.5v6A1.5 1.5 0 0 1 14.5 13H8l-3.5 3v-3H5.5"
                          />
                        </svg>
                        <span className="truncate">{c.title ?? "Untitled"}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          </aside>

          {/* Chat panel */}
          <section className="flex flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
            <div
              ref={scrollRef}
              className="flex-1 space-y-6 overflow-y-auto p-6"
            >
              {messages.length === 0 && !loadingHistory && (
                <div className="mx-auto flex h-full max-w-md flex-col justify-center pb-8 text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-lg font-bold text-white shadow-lg shadow-indigo-500/25">
                    AI
                  </div>
                  <h2 className="text-xl font-semibold tracking-tight">
                    Ask your knowledge base
                  </h2>
                  <p className="mt-1.5 text-sm leading-relaxed text-neutral-500">
                    Answers are grounded in your uploaded documents, with
                    citations back to the source passages.
                  </p>
                  <div className="mt-6 grid gap-2 text-left">
                    {SUGGESTIONS.map((s) => (
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

              {loadingHistory && (
                <p className="pt-10 text-center text-sm text-neutral-400">
                  Loading conversation…
                </p>
              )}

              {messages.map((m) => {
                const isAgent = m.sender === "agent";
                return (
                  <div
                    key={m.id}
                    className={`flex gap-3 ${isAgent ? "" : "flex-row-reverse"}`}
                  >
                    <Avatar role={m.sender} />
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
                        isAgent
                          ? "rounded-tl-sm border border-neutral-200/60 bg-neutral-50 text-neutral-800 dark:border-neutral-700/50 dark:bg-neutral-800 dark:text-neutral-100"
                          : "rounded-tr-sm bg-gradient-to-br from-indigo-500 to-violet-600 text-white"
                      }`}
                    >
                      {isAgent ? (
                        <>
                          <RichText text={m.body} />
                          {m.sources && <Sources sources={m.sources} />}
                        </>
                      ) : (
                        <p className="whitespace-pre-wrap">{m.body}</p>
                      )}
                    </div>
                  </div>
                );
              })}

              {busy && (
                <div className="flex gap-3">
                  <Avatar role="agent" />
                  <div className="rounded-2xl rounded-tl-sm border border-neutral-200/60 bg-neutral-50 px-4 py-3 dark:border-neutral-700/50 dark:bg-neutral-800">
                    <TypingDots />
                  </div>
                </div>
              )}
            </div>

            {/* Composer */}
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
                  placeholder="Ask a question…  (Enter to send, Shift+Enter for newline)"
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
                Responses are generated from your documents and may need
                verification.
              </p>
            </form>
          </section>
        </div>
      )}
    </AppShell>
  );
}
