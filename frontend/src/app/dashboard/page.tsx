"use client";

import Link from "next/link";

import AppShell from "@/components/AppShell";

const CARDS = [
  {
    href: "/leads",
    title: "Leads",
    body: "Review qualified leads, their scores, owners, and follow-up drafts.",
  },
  {
    href: "/chat",
    title: "Chat",
    body: "Ask questions and get answers grounded in your uploaded documents, with source citations.",
  },
  {
    href: "/documents",
    title: "Documents",
    body: "Upload files to the knowledge base and track their ingestion status.",
  },
  {
    href: "/employees",
    title: "Employees",
    body: "Manage your team, add members, and control account access.",
  },
];

export default function DashboardPage() {
  return (
    <AppShell>
      {(employee) => (
        <div>
          <h1 className="text-2xl font-semibold">
            Welcome, {employee.name.split(" ")[0]}
          </h1>
          <p className="mt-1 text-neutral-500">
            AI Lead Qualification — knowledge base &amp; chat.
          </p>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {CARDS.map((c) => (
              <Link
                key={c.href}
                href={c.href}
                className="rounded-xl border border-neutral-200 bg-white p-5 transition hover:border-neutral-400 hover:shadow-sm dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-neutral-600"
              >
                <h2 className="font-medium">{c.title}</h2>
                <p className="mt-1 text-sm text-neutral-500">{c.body}</p>
              </Link>
            ))}
          </div>
        </div>
      )}
    </AppShell>
  );
}
