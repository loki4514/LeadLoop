"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  clearToken,
  fetchMe,
  getToken,
  logout,
  type Employee,
} from "@/lib/api";

export default function Home() {
  const router = useRouter();
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

  if (loading) {
    return (
      <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
        <p>Loading…</p>
      </main>
    );
  }

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>Lead Agent</h1>
      <p>AI Lead Qualification dashboard.</p>
      {employee && (
        <div style={{ marginTop: "1.5rem" }}>
          <p>
            Signed in as <strong>{employee.name}</strong> ({employee.email}) —
            role: <strong>{employee.role}</strong>
          </p>
          <button
            onClick={handleLogout}
            style={{ padding: "0.5rem 1rem", cursor: "pointer" }}
          >
            Log out
          </button>
        </div>
      )}
    </main>
  );
}
