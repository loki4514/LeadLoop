"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import Logo from "@/components/Logo";
import { CardSkeleton, Skeleton } from "@/components/Skeleton";
import {
  clearToken,
  fetchMe,
  getToken,
  logout,
  type Employee,
} from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Home" },
  { href: "/leads", label: "Leads" },
  { href: "/chat", label: "Chat" },
  { href: "/documents", label: "Documents" },
  { href: "/employees", label: "Employees" },
];

/**
 * Authenticated page wrapper: verifies the session, redirects to /login when
 * missing/invalid, and renders a shared nav. Children render only once the
 * employee is loaded, and receive it via the render prop.
 */
export default function AppShell({
  children,
}: {
  children: (employee: Employee) => React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    fetchMe(token)
      .then(setEmployee)
      .catch(() => {
        clearToken();
        router.replace("/login");
      })
      .finally(() => setLoading(false));
  }, [router]);

  async function handleLogout() {
    const token = getToken();
    if (token) await logout(token);
    clearToken();
    router.replace("/login");
  }

  // Render the shell (nav + chrome) immediately and shimmer only the content
  // area. Blanking the whole screen on every navigation is what made page
  // transitions feel like full reloads.
  if (loading || !employee) {
    return (
      <div className="min-h-screen">
        <Chrome pathname={pathname} employee={null} onLogout={handleLogout} />
        <main className="mx-auto max-w-4xl px-4 py-8">
          <Skeleton className="h-7 w-48" />
          <div className="mt-6 space-y-3">
            <CardSkeleton />
            <CardSkeleton />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Chrome pathname={pathname} employee={employee} onLogout={handleLogout} />
      <main className="mx-auto max-w-4xl px-4 py-8">{children(employee)}</main>
    </div>
  );
}


/**
 * Nav + header chrome. Rendered in both the loading and loaded states so the
 * frame stays put across navigations; `employee` is null while the session
 * is still resolving.
 */
function Chrome({
  pathname,
  employee,
  onLogout,
}: {
  pathname: string;
  employee: Employee | null;
  onLogout: () => void;
}) {
  return (
    <header className="border-b border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-6">
          <Logo href="/dashboard" size="sm" />
          <nav className="flex gap-1">
            {NAV.map((item) => {
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  prefetch
                  className={`rounded-md px-3 py-1.5 text-sm transition ${
                    active
                      ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                      : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm">
          {employee ? (
            <span className="hidden text-neutral-500 sm:inline">
              {employee.name} · {employee.role}
            </span>
          ) : (
            <Skeleton className="hidden h-4 w-32 sm:inline-block" />
          )}
          <button
            onClick={onLogout}
            disabled={!employee}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-neutral-700 transition hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-200 dark:hover:bg-neutral-800"
          >
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}
