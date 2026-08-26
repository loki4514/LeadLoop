"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import Logo from "@/components/Logo";
import { login, setToken } from "@/lib/api";

const FEATURES = [
  {
    title: "Qualify automatically",
    body: "An AI agent asks the right questions — location, budget, timeline — and captures every inbound lead.",
    icon: (
      <path d="M9 2a7 7 0 1 0 4.19 12.607l3.6 3.6a1 1 0 0 0 1.414-1.414l-3.6-3.6A7 7 0 0 0 9 2ZM4 9a5 5 0 1 1 10 0A5 5 0 0 1 4 9Z" />
    ),
  },
  {
    title: "Score & assign",
    body: "Leads are scored Hot / Warm / Cold and routed to the right rep — load-balanced and priority-weighted.",
    icon: (
      <path d="M10 1.5 12.7 7l6.05.88-4.38 4.27L15.4 18 10 15.15 4.6 18l1.03-5.85L1.25 7.88 7.3 7 10 1.5Z" />
    ),
  },
  {
    title: "Never go cold",
    body: "When a conversation stalls, the agent drafts a follow-up and pings the owner — approve, edit, or send.",
    icon: (
      <path d="M10 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm.75 4a.75.75 0 0 0-1.5 0v4c0 .27.14.52.38.65l3 1.75a.75.75 0 1 0 .74-1.3L10.75 9.6V6Z" />
    ),
  },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await login(email, password);
      setToken(token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      {/* Left: brand / marketing panel */}
      <section className="relative hidden flex-col justify-between overflow-hidden bg-neutral-950 p-10 text-white lg:flex">
        {/* Decorative gradient glow */}
        <div
          aria-hidden
          className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-gradient-to-br from-indigo-500/40 to-violet-600/30 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-40 -left-24 h-96 w-96 rounded-full bg-gradient-to-tr from-indigo-600/20 to-fuchsia-500/20 blur-3xl"
        />

        <div className="relative z-10">
          <Logo href="/" size="md" />
        </div>

        <div className="relative z-10 max-w-md">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            Turn inbound leads into closed deals — automatically.
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-neutral-400">
            An AI agent that qualifies, scores, assigns, and follows up on every
            prospect — so no high-value lead ever goes cold.
          </p>

          <ul className="mt-8 space-y-5">
            {FEATURES.map((f) => (
              <li key={f.title} className="flex gap-3">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 text-indigo-300 ring-1 ring-inset ring-white/10">
                  <svg
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="h-4 w-4"
                    aria-hidden
                  >
                    {f.icon}
                  </svg>
                </span>
                <div>
                  <p className="text-sm font-medium">{f.title}</p>
                  <p className="mt-0.5 text-sm leading-relaxed text-neutral-400">
                    {f.body}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative z-10 text-xs text-neutral-500">
          © {new Date().getFullYear()} LeadLoop · AI Lead Qualification &
          Follow-up
        </p>
      </section>

      {/* Right: sign-in form */}
      <section className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          {/* Compact brand for small screens (left panel is hidden) */}
          <div className="mb-8 lg:hidden">
            <Logo href="/" size="md" />
          </div>

          <form
            onSubmit={handleSubmit}
            className="rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm dark:border-neutral-800 dark:bg-neutral-900"
          >
            <h2 className="text-xl font-semibold tracking-tight">
              Welcome back
            </h2>
            <p className="mt-1 text-sm text-neutral-500">
              Sign in to your LeadLoop dashboard.
            </p>

            <div className="mt-6 space-y-3">
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-neutral-500">
                  Email
                </span>
                <input
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-neutral-700 dark:bg-neutral-800"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-neutral-500">
                  Password
                </span>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-neutral-700 dark:bg-neutral-800"
                />
              </label>
            </div>

            {error && (
              <p className="mt-3 rounded-lg bg-red-100 px-3 py-2 text-sm text-red-800 dark:bg-red-500/20 dark:text-red-200">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-5 w-full rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:shadow-md active:scale-[0.99] disabled:opacity-50 disabled:shadow-none"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>

            <p className="mt-4 text-center text-sm">
              <Link
                href="/forgot-password"
                className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
              >
                Forgot password?
              </Link>
            </p>
          </form>

          <p className="mt-6 text-center text-xs text-neutral-400">
            Accounts are provisioned by your administrator.
          </p>
        </div>
      </section>
    </main>
  );
}
