"use client";

import { useCallback, useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import {
  createEmployee,
  getToken,
  listEmployees,
  type Employee,
} from "@/lib/api";

function RoleBadge({ role }: { role: Employee["role"] }) {
  const admin = role === "admin";
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        admin
          ? "bg-indigo-200 text-indigo-900 dark:bg-indigo-500/30 dark:text-indigo-200"
          : "bg-neutral-200 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200"
      }`}
    >
      {role}
    </span>
  );
}

function AddEmployeeForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || busy) return;
    setError(null);
    setOk(null);
    setBusy(true);
    try {
      // Only regular employees can be created here; admins are provisioned
      // out-of-band (seed script).
      const created = await createEmployee(token, {
        name,
        email,
        role: "employee",
        password,
      });
      setOk(`Added ${created.name}.`);
      setName("");
      setEmail("");
      setPassword("");
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add employee");
    } finally {
      setBusy(false);
    }
  }

  const inputCls =
    "w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 dark:border-neutral-700 dark:bg-neutral-900";

  return (
    <form
      onSubmit={submit}
      className="mt-6 rounded-xl border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900"
    >
      <h2 className="text-sm font-semibold">Add employee</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Full name"
          required
          className={inputCls}
        />
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          required
          className={inputCls}
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Temporary password"
          required
          minLength={6}
          className={inputCls}
        />
      </div>
      {error && (
        <p className="mt-3 rounded-md bg-red-100 px-3 py-2 text-sm text-red-800 dark:bg-red-500/20 dark:text-red-200">
          {error}
        </p>
      )}
      {ok && (
        <p className="mt-3 rounded-md bg-green-100 px-3 py-2 text-sm text-green-800 dark:bg-green-500/20 dark:text-green-200">
          {ok}
        </p>
      )}
      <button
        type="submit"
        disabled={busy}
        className="mt-3 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
      >
        {busy ? "Adding…" : "Add employee"}
      </button>
    </form>
  );
}

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    try {
      setEmployees(await listEmployees(token));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load employees");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <AppShell>
      {(me) => (
        <div>
          <h1 className="text-2xl font-semibold">Employees</h1>
          <p className="mt-1 text-neutral-500">
            {me.role === "admin"
              ? "Manage your team. Add new employees and view everyone with access."
              : "Everyone on your team with access to LeadLoop."}
          </p>

          {me.role === "admin" && <AddEmployeeForm onCreated={refresh} />}

          {error && (
            <p className="mt-3 rounded-md bg-red-100 px-3 py-2 text-sm text-red-800 dark:bg-red-500/20 dark:text-red-200">
              {error}
            </p>
          )}

          <div className="mt-6 overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-800">
            {employees.length === 0 ? (
              <p className="p-6 text-center text-sm text-neutral-500">
                No employees yet.
              </p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="bg-neutral-100 text-neutral-500 dark:bg-neutral-800/50">
                  <tr>
                    <th className="px-4 py-2 font-medium">Name</th>
                    <th className="px-4 py-2 font-medium">Email</th>
                    <th className="px-4 py-2 font-medium">Role</th>
                    <th className="px-4 py-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((e) => (
                    <tr
                      key={e.id}
                      className="border-t border-neutral-200 dark:border-neutral-800"
                    >
                      <td className="px-4 py-2 font-medium">
                        {e.name}
                        {e.id === me.id && (
                          <span className="ml-2 text-xs text-neutral-400">
                            (you)
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-neutral-500">{e.email}</td>
                      <td className="px-4 py-2">
                        <RoleBadge role={e.role} />
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={
                            e.is_active
                              ? "text-green-600 dark:text-green-400"
                              : "text-neutral-400"
                          }
                        >
                          {e.is_active ? "active" : "inactive"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}
