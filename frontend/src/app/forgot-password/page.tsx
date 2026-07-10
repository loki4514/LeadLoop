"use client";

import Link from "next/link";
import { useState } from "react";

import { forgotPassword } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
        <h1 className="text-xl font-semibold">Reset your password</h1>
        {sent ? (
          <>
            <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-300">
              If that email is registered, we&apos;ve sent a reset link. Check
              your inbox and follow the link to choose a new password.
            </p>
            <Link
              href="/login"
              className="mt-6 inline-block text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
            >
              ← Back to sign in
            </Link>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            <p className="mt-1 text-sm text-neutral-500">
              Enter your account email and we&apos;ll send you a reset link.
            </p>
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-6 w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 dark:border-neutral-700 dark:bg-neutral-800"
            />
            {error && (
              <p className="mt-3 rounded-md bg-red-100 px-3 py-2 text-sm text-red-800 dark:bg-red-500/20 dark:text-red-200">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="mt-5 w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
            >
              {loading ? "Sending…" : "Send reset link"}
            </button>
            <Link
              href="/login"
              className="mt-4 block text-center text-sm text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
            >
              Back to sign in
            </Link>
          </form>
        )}
      </div>
    </main>
  );
}
