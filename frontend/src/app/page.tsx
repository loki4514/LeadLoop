"use client";

import Link from "next/link";

import Logo from "@/components/Logo";

const FEATURES = [
  {
    title: "Qualify automatically",
    body: "An AI agent greets every inbound lead and asks the right questions — location, configuration, budget, timeline, purpose, financing.",
    icon: (
      <path d="M9 2a7 7 0 1 0 4.19 12.607l3.6 3.6a1 1 0 0 0 1.414-1.414l-3.6-3.6A7 7 0 0 0 9 2ZM4 9a5 5 0 1 1 10 0A5 5 0 0 1 4 9Z" />
    ),
  },
  {
    title: "Answer from your docs",
    body: "Retrieval-augmented answers grounded in your own listings and knowledge base — with citations back to the source.",
    icon: (
      <path d="M4 3a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2H4Zm2 4h8v1.5H6V7Zm0 3.5h8V12H6v-1.5Z" />
    ),
  },
  {
    title: "Score & assign",
    body: "Deterministic rules score each lead Hot / Warm / Cold, then auto-assign to the right rep — load-balanced and priority-weighted.",
    icon: (
      <path d="M10 1.5 12.7 7l6.05.88-4.38 4.27L15.4 18 10 15.15 4.6 18l1.03-5.85L1.25 7.88 7.3 7 10 1.5Z" />
    ),
  },
  {
    title: "Never go cold",
    body: "When a conversation stalls for 2 days, the agent drafts a follow-up and pings the owner — approve, edit, or send.",
    icon: (
      <path d="M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm.75 4a.75.75 0 0 0-1.5 0v4c0 .27.14.52.38.65l3 1.75a.75.75 0 1 0 .74-1.3L10.75 9.6V6Z" />
    ),
  },
  {
    title: "Human takeover",
    body: "Any rep can jump into a live chat at any moment — the AI steps back and the conversation continues seamlessly.",
    icon: (
      <path d="M10 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm-6 6a6 6 0 1 1 12 0v.5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V16Z" />
    ),
  },
  {
    title: "Track every source",
    body: "Ad source is tagged on every lead for attribution, so you know which campaigns actually drive revenue.",
    icon: (
      <path d="M3 3h2v14H3V3Zm4 8h2v6H7v-6Zm4-4h2v10h-2V7Zm4-3h2v13h-2V4Z" />
    ),
  },
];

const FLOW = [
  "Ad click (web widget)",
  "AI qualifies: location, BHK, budget",
  "Shows matching properties (RAG)",
  "Captures email + phone",
  "Scores → Hot / Warm / Cold",
  "Auto-assigns to a rep",
  "Rep follows up (chat / email / call)",
  "Stalled 2 days? → AI drafts follow-up",
];

const STACK = [
  "FastAPI",
  "Next.js",
  "PostgreSQL + pgvector",
  "Redis + Celery",
  "Native tool-use agent",
  "JWT + RBAC",
  "Docker",
];

function BrandMark() {
  return <Logo href="/" size="md" />;
}

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
      {/* Nav */}
      <header className="sticky top-0 z-20 border-b border-neutral-200/70 bg-white/80 backdrop-blur dark:border-neutral-800/70 dark:bg-neutral-950/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <BrandMark />
          <div className="flex items-center gap-2">
            <Link
              href="/widget"
              className="hidden rounded-lg px-3.5 py-2 text-sm font-medium text-neutral-600 transition hover:bg-neutral-100 sm:inline-block dark:text-neutral-300 dark:hover:bg-neutral-800"
            >
              Live demo
            </Link>
            <Link
              href="/login"
              className="hidden rounded-lg px-3.5 py-2 text-sm font-medium text-neutral-600 transition hover:bg-neutral-100 sm:inline-block dark:text-neutral-300 dark:hover:bg-neutral-800"
            >
              Sign in
            </Link>
            {/* The header CTA follows the hero: the no-login assistant is what
                a visitor can act on right now, so it keeps the solid button.
                Labelled by what it answers, not by the fact that it's AI. */}
            <Link
              href="/demo"
              className="rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md active:scale-[0.98]"
            >
              Property Q&amp;A
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-40 left-1/2 h-96 w-[42rem] -translate-x-1/2 rounded-full bg-gradient-to-br from-indigo-500/20 to-violet-600/10 blur-3xl"
        />
        <div className="relative mx-auto max-w-3xl px-6 pb-16 pt-20 text-center sm:pt-28">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-medium text-neutral-600 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-300">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
            AI Lead Qualification & Follow-up Agent
          </span>
          <h1 className="mt-6 text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            Turn inbound leads into{" "}
            <span className="bg-gradient-to-br from-indigo-500 to-violet-600 bg-clip-text text-transparent">
              closed deals
            </span>{" "}
            — automatically.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-neutral-500 dark:text-neutral-400">
            LeadLoop qualifies, scores, assigns, and follows up on every
            prospect — so a human closes, and no high-value lead ever goes cold.
            Built for real-estate teams, works for any high-ticket sales.
          </p>
          {/* A first-time visitor has no account, so the thing they can
              actually try — the no-login assistant — takes the primary slot;
              sign-in drops to a quiet link for the team. Both labels are short
              verb phrases of similar length, and whitespace-nowrap keeps each
              on one line so the pair stays balanced. */}
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/demo"
              className="inline-flex w-full items-center justify-center gap-2.5 whitespace-nowrap rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 px-7 py-4 text-base font-semibold text-white shadow-lg shadow-indigo-500/30 ring-1 ring-inset ring-white/20 transition hover:shadow-xl hover:shadow-indigo-500/40 active:scale-[0.98] sm:w-auto"
            >
              <svg
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-5 w-5"
                aria-hidden
              >
                <path d="M10 2c-4.42 0-8 2.99-8 6.67 0 1.9.96 3.6 2.5 4.82V17a.5.5 0 0 0 .76.43l2.72-1.63c.66.13 1.33.2 2.02.2 4.42 0 8-2.99 8-6.67C18 4.99 14.42 2 10 2Z" />
              </svg>
              Ask about buying property
            </Link>
            {/* Secondary, but not a flat outline — a solid dark surface with
                its own icon so it reads as a real button beside the gradient. */}
            <Link
              href="/widget"
              className="inline-flex w-full items-center justify-center gap-2.5 whitespace-nowrap rounded-xl bg-neutral-900 px-7 py-4 text-base font-semibold text-white shadow-lg shadow-neutral-900/20 ring-1 ring-inset ring-white/10 transition hover:bg-neutral-800 hover:shadow-xl active:scale-[0.98] sm:w-auto dark:bg-white dark:text-neutral-900 dark:shadow-black/30 dark:ring-black/5 dark:hover:bg-neutral-200"
            >
              <svg
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-5 w-5"
                aria-hidden
              >
                <path d="M10 1.5 12.7 7l6.05.88-4.38 4.27L15.4 18 10 15.15 4.6 18l1.03-5.85L1.25 7.88 7.3 7 10 1.5Z" />
              </svg>
              Watch a lead get qualified
            </Link>
          </div>
          <p className="mt-4 text-sm text-neutral-500">
            Home loans, stamp duty, registration, RERA — answered from a real
            Indian real-estate knowledge base. No sign-up needed.
          </p>
          <p className="mt-6 text-sm text-neutral-500">
            Already a customer?{" "}
            <Link
              href="/login"
              className="font-medium text-indigo-600 underline-offset-4 hover:underline dark:text-indigo-400"
            >
              Sign in to your dashboard
            </Link>
          </p>
        </div>
      </section>

      {/* Flow strip */}
      <section className="border-y border-neutral-200 bg-neutral-50 py-12 dark:border-neutral-800 dark:bg-neutral-900/40">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-center text-sm font-semibold uppercase tracking-wider text-neutral-400">
            The agent flow
          </h2>
          <ol className="mt-6 flex flex-wrap items-center justify-center gap-2 text-sm">
            {FLOW.map((step, i) => (
              <li key={step} className="flex items-center gap-2">
                <span className="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-neutral-700 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300">
                  {step}
                </span>
                {i < FLOW.length - 1 && (
                  <span className="text-neutral-300 dark:text-neutral-600">
                    →
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight">
            One agent. Every step of the funnel.
          </h2>
          <p className="mt-3 text-neutral-500 dark:text-neutral-400">
            A single conversational AI that uses tools — not a pile of
            disconnected bots. Deterministic scoring and assignment keep it
            predictable.
          </p>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-neutral-200 bg-white p-6 transition hover:border-indigo-300 hover:shadow-sm dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-indigo-500/40"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-300">
                <svg
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="h-5 w-5"
                  aria-hidden
                >
                  {f.icon}
                </svg>
              </span>
              <h3 className="mt-4 font-semibold">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-neutral-500 dark:text-neutral-400">
                {f.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Tech stack */}
      <section className="border-t border-neutral-200 bg-neutral-50 py-16 dark:border-neutral-800 dark:bg-neutral-900/40">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-neutral-400">
            Built with
          </h2>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-2.5">
            {STACK.map((t) => (
              <span
                key={t}
                className="rounded-full border border-neutral-200 bg-white px-4 py-1.5 text-sm font-medium text-neutral-700 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-300"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-4xl px-6 py-20 text-center">
        <h2 className="text-3xl font-semibold tracking-tight">
          Ready to see it work?
        </h2>
        <p className="mx-auto mt-3 max-w-lg text-neutral-500 dark:text-neutral-400">
          Ask a real question about buying property in India — no sign-up
          needed. Or step through the chat widget as an inbound lead and watch
          the qualifier work.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/demo"
            className="inline-flex w-full items-center justify-center gap-2.5 whitespace-nowrap rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 px-7 py-4 text-base font-semibold text-white shadow-lg shadow-indigo-500/30 ring-1 ring-inset ring-white/20 transition hover:shadow-xl hover:shadow-indigo-500/40 active:scale-[0.98] sm:w-auto"
          >
            <svg
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5"
              aria-hidden
            >
              <path d="M10 2c-4.42 0-8 2.99-8 6.67 0 1.9.96 3.6 2.5 4.82V17a.5.5 0 0 0 .76.43l2.72-1.63c.66.13 1.33.2 2.02.2 4.42 0 8-2.99 8-6.67C18 4.99 14.42 2 10 2Z" />
            </svg>
            Ask about buying property
          </Link>
          <Link
            href="/widget"
            className="inline-flex w-full items-center justify-center gap-2.5 whitespace-nowrap rounded-xl bg-neutral-900 px-7 py-4 text-base font-semibold text-white shadow-lg shadow-neutral-900/20 ring-1 ring-inset ring-white/10 transition hover:bg-neutral-800 hover:shadow-xl active:scale-[0.98] sm:w-auto dark:bg-white dark:text-neutral-900 dark:shadow-black/30 dark:ring-black/5 dark:hover:bg-neutral-200"
          >
            <svg
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5"
              aria-hidden
            >
              <path d="M10 1.5 12.7 7l6.05.88-4.38 4.27L15.4 18 10 15.15 4.6 18l1.03-5.85L1.25 7.88 7.3 7 10 1.5Z" />
            </svg>
            Watch a lead get qualified
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-neutral-200 py-8 dark:border-neutral-800">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 text-sm text-neutral-400 sm:flex-row">
          <BrandMark />
          <p>
            © {new Date().getFullYear()} LeadLoop · AI Lead Qualification &
            Follow-up
          </p>
        </div>
      </footer>
    </main>
  );
}
