// Base URL for the backend API. The browser runs on the host, so it reaches
// the backend via localhost (not the docker-internal "backend" hostname).
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const TOKEN_KEY = "leadagent_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export interface Employee {
  id: number;
  name: string;
  email: string;
  role: "employee" | "admin";
  is_active: boolean;
}

/** Log in with email + password. Returns the access token. */
export async function login(email: string, password: string): Promise<string> {
  // The backend uses an OAuth2 password form: fields are `username` + `password`.
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);

  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? "Login failed");
  }

  const data = await res.json();
  return data.access_token as string;
}

/** Fetch the currently authenticated employee. */
export async function fetchMe(token: string): Promise<Employee> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error("Not authenticated");
  }
  return (await res.json()) as Employee;
}

/** Revoke the current session on the backend. */
export async function logout(token: string): Promise<void> {
  await fetch(`${API_BASE}/api/v1/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => {
    /* best-effort; clear client token regardless */
  });
}
