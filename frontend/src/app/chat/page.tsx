"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import AppShell from "@/components/AppShell";
import {
  askChat,
  getConversation,
  getToken,
  listConversations,
  type ChatMessage,
  type ConversationSummary,
  type SearchHit,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Lightweight answer formatting (no markdown dependency): paragraphs, bullet
// lists, and **bold** — enough to render the LLM's output cleanly.
// ---------------------------------------------------------------------------
function renderInline(text: string, keyPrefix: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return <strong key={`${keyPrefix}-${i}`}>{p.slice(2, -2)}</strong>;
    }
    return <span key={`${keyPrefix}-${i}`}>{p}</span>;
  });
}

function FormattedAnswer({ text }: { text: string }) {
  const lines = text.split("\n");
  const blocks: React.ReactNode[] = [];
  let bullets: string[] = [];

  const flushBullets = (key: string) => {
    if (bullets.length === 0) return;
    blocks.push(
      <ul key={key} className="my-2 list-disc space-y-1 pl-5">
        {bullets.map((b, i) => (
          <li key={i}>{renderInline(b, `${key}-${i}`)}</li>
        ))}
      </ul>,
    );
    bullets = [];
  };

  lines.forEach((raw, i) => {
    const line = raw.trim();
    const bullet = line.match(/^[-*]\s+(.*)$/);
    if (bullet) {
      bullets.push(bullet[1]);
      return;
    }
    flushBullets(`ul-${i}`);
    if (line) {
      blocks.push(
        <p key={`p-${i}`} className="my-1.5 leading-relaxed">
          {renderInline(line, `p-${i}`)}
        </p>,
      );
    }
  });
  flushBullets("ul-end");
  return <div>{blocks}</div>;
}

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
      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
        isAgent
          ? "bg-indigo-600 text-white"
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
        <div className="grid h-[calc(100vh-9rem)] grid-cols-1 gap-4 md:grid-cols-[240px_1fr]">
          {/* Sidebar */}
          <aside className="hidden flex-col rounded-xl border border-neutral-200 bg-white md:flex dark:border-neutral-800 dark:bg-neutral-900">
            <div className="p-3">
              <button
                onClick={newChat}
                className="w-full rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
              >
                + New chat
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-2 pb-2">
              <p className="px-2 py-1 text-xs font-medium uppercase tracking-wide text-neutral-400">
                History
              </p>
              {convos.length === 0 && (
                <p className="px-2 py-2 text-xs text-neutral-400">
                  No conversations yet.
                </p>
              )}
              <ul className="space-y-0.5">
                {convos.map((c) => (
                  <li key={c.id}>
                    <button
                      onClick={() => openConversation(c.id)}
                      className={`w-full truncate rounded-md px-2 py-1.5 text-left text-sm transition ${
                        c.id === activeId
                          ? "bg-neutral-100 font-medium text-neutral-900 dark:bg-neutral-800 dark:text-white"
                          : "text-neutral-600 hover:bg-neutral-50 dark:text-neutral-300 dark:hover:bg-neutral-800/60"
                      }`}
                      title={c.title ?? "Untitled"}
                    >
                      {c.title ?? "Untitled"}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </aside>

          {/* Chat panel */}
          <section className="flex flex-col overflow-hidden rounded-xl border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
            <div
              ref={scrollRef}
              className="flex-1 space-y-5 overflow-y-auto p-5"
            >
              {messages.length === 0 && !loadingHistory && (
                <div className="mx-auto max-w-md pt-10 text-center">
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 text-lg font-bold text-white">
                    AI
                  </div>
                  <h2 className="text-lg font-semibold">
                    Ask your knowledge base
                  </h2>
                  <p className="mt-1 text-sm text-neutral-500">
                    Answers are grounded in your uploaded documents, with
                    citations back to the source passages.
                  </p>
                  <div className="mt-5 grid gap-2">
                    {SUGGESTIONS.map((s) => (
                      <button
                        key={s}
                        onClick={() => send(s)}
                        className="rounded-lg border border-neutral-200 px-3 py-2 text-left text-sm text-neutral-600 transition hover:border-indigo-400 hover:text-neutral-900 dark:border-neutral-800 dark:text-neutral-300 dark:hover:border-indigo-500 dark:hover:text-white"
                      >
                        {s}
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
                      className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                        isAgent
                          ? "rounded-tl-sm bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-100"
                          : "rounded-tr-sm bg-indigo-600 text-white"
                      }`}
                    >
                      {isAgent ? (
                        <>
                          <FormattedAnswer text={m.body} />
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
                  <div className="rounded-2xl rounded-tl-sm bg-neutral-100 px-4 py-3 dark:bg-neutral-800">
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
              className="border-t border-neutral-200 p-3 dark:border-neutral-800"
            >
              <div className="flex items-end gap-2 rounded-xl border border-neutral-300 bg-white px-3 py-2 focus-within:border-indigo-500 dark:border-neutral-700 dark:bg-neutral-900">
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
                  className="max-h-32 flex-1 resize-none bg-transparent text-sm outline-none"
                />
                <button
                  type="submit"
                  disabled={busy || !question.trim()}
                  className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-40"
                >
                  Send
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </AppShell>
  );
}
