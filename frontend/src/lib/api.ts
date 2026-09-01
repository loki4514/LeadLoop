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
  is_online?: boolean;
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

/**
 * Request a password reset link. Always resolves (the backend returns the same
 * response whether or not the email exists) unless the network fails.
 */
export async function forgotPassword(email: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? "Request failed");
  }
}

/** Complete a password reset with the emailed token. */
export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? "Reset failed");
  }
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

// ---------------------------------------------------------------------------
// Shared authed-JSON helper
// ---------------------------------------------------------------------------

async function authedJson<T>(
  token: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  return (await res.json()) as T;
}

// ---------------------------------------------------------------------------
// Documents (RAG knowledge base)
// ---------------------------------------------------------------------------

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface DocumentRead {
  id: number;
  filename: string;
  content_type: string | null;
  status: DocumentStatus;
  error: string | null;
  embedding_provider: string | null;
  embedding_model: string | null;
  created_at: string;
}

/** List uploaded documents, newest first. */
export function listDocuments(token: string): Promise<DocumentRead[]> {
  return authedJson<DocumentRead[]>(token, "/api/v1/documents");
}

/** Upload a file; it is queued for ingestion into the vector store. */
export function uploadDocument(
  token: string,
  file: File,
): Promise<DocumentRead> {
  const form = new FormData();
  form.set("file", file);
  return authedJson<DocumentRead>(token, "/api/v1/documents", {
    method: "POST",
    body: form,
  });
}

// ---------------------------------------------------------------------------
// RAG chat
// ---------------------------------------------------------------------------

export interface SearchHit {
  document_id: number;
  filename: string;
  chunk_index: number;
  content: string;
  score: number;
}

export interface ChatResponse {
  question: string;
  answer: string;
  sources: SearchHit[];
  conversation_id: number;
}

/**
 * Ask a question over the ingested knowledge base (RAG + LLM).
 * Pass `conversationId` to continue a thread; omit to start a new one.
 */
export function askChat(
  token: string,
  question: string,
  conversationId?: number,
  k?: number,
): Promise<ChatResponse> {
  return authedJson<ChatResponse>(token, "/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, k, conversation_id: conversationId ?? null }),
  });
}

export interface ConversationSummary {
  id: number;
  title: string | null;
  created_at: string;
}

export interface ChatMessage {
  id: number;
  sender: "lead" | "agent" | "employee";
  body: string;
  sources: SearchHit[] | null;
  created_at: string;
}

export interface ConversationDetail {
  id: number;
  title: string | null;
  created_at: string;
  messages: ChatMessage[];
}

/** List the current employee's chat threads, newest first. */
export function listConversations(
  token: string,
): Promise<ConversationSummary[]> {
  return authedJson<ConversationSummary[]>(token, "/api/v1/chat/conversations");
}

/** Load a chat thread with its full message history. */
export function getConversation(
  token: string,
  id: number,
): Promise<ConversationDetail> {
  return authedJson<ConversationDetail>(
    token,
    `/api/v1/chat/conversations/${id}`,
  );
}

// ---------------------------------------------------------------------------
// Public demo chat (no auth — the try-it-out surface)
// ---------------------------------------------------------------------------

export interface DemoTurn {
  role: "user" | "assistant";
  content: string;
}

export interface DemoChatResponse {
  answer: string;
  /** False when nothing relevant was found and the answer is the refusal. */
  grounded: boolean;
}

/**
 * Ask the public demo a question. Answers come only from documents in the
 * knowledge base; the response deliberately carries no sources, filenames or
 * scores. The demo is stateless, so recent turns are passed back for context.
 */
export async function askDemo(
  question: string,
  history: DemoTurn[] = [],
): Promise<DemoChatResponse> {
  const res = await fetch(`${API_BASE}/api/v1/demo/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // The API caps history at 10 turns; trim here so a long chat doesn't 422.
    body: JSON.stringify({ question, history: history.slice(-10) }),
  });
  if (!res.ok) {
    if (res.status === 429) {
      throw new Error("Too many questions just now — give it a minute.");
    }
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  return (await res.json()) as DemoChatResponse;
}

/** Starter questions for the demo's empty state. */
export async function getDemoSuggestions(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/v1/demo/suggestions`);
  if (!res.ok) return [];
  return (await res.json()) as string[];
}

// ---------------------------------------------------------------------------
// Employees
// ---------------------------------------------------------------------------

export interface NewEmployee {
  name: string;
  email: string;
  role: "employee" | "admin";
  password: string;
}

/** List all employees (any authenticated user). */
export function listEmployees(token: string): Promise<Employee[]> {
  return authedJson<Employee[]>(token, "/api/v1/employees");
}

/** Create a new employee (admin only). */
export function createEmployee(
  token: string,
  data: NewEmployee,
): Promise<Employee> {
  return authedJson<Employee>(token, "/api/v1/employees", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

/** Deactivate (soft delete) an employee — admin only. Preserves their leads/history. */
export function deactivateEmployee(
  token: string,
  id: number,
): Promise<Employee> {
  return authedJson<Employee>(token, `/api/v1/employees/${id}`, {
    method: "DELETE",
  });
}

/** Enable/disable an employee (admin only). Pass is_active=true to reactivate. */
export function setEmployeeActive(
  token: string,
  id: number,
  isActive: boolean,
): Promise<Employee> {
  return authedJson<Employee>(token, `/api/v1/employees/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
  });
}

// ---------------------------------------------------------------------------
// Leads dashboard
// ---------------------------------------------------------------------------

export type LeadTier = "hot" | "warm" | "cold";
export type LeadStatus = "new" | "qualifying" | "qualified" | "assigned" | "closed";

export interface EmployeeBrief {
  id: number;
  name: string;
  email: string;
}

export interface LeadSummary {
  id: number;
  name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  bhk: number | null;
  budget_min: number | null;
  budget_max: number | null;
  timeline: string | null;
  purpose: string | null;
  financing: string | null;
  score: number | null;
  tier: LeadTier | null;
  status: LeadStatus;
  ad_source: string | null;
  assigned_employee: EmployeeBrief | null;
  is_bot_active: boolean;
  last_activity_at: string;
  created_at: string;
}

export interface FollowupRead {
  id: number;
  lead_id: number;
  draft_body: string;
  status: string;
  created_at: string;
}

export interface LeadMessage {
  id: number;
  sender: "lead" | "agent" | "employee";
  body: string;
  created_at: string;
}

export type AuditAction =
  | "edited"
  | "tier_changed"
  | "reassigned"
  | "deleted";

export interface AuditLogRead {
  id: number;
  action: AuditAction;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
  actor: EmployeeBrief | null;
  created_at: string;
}

export interface LeadDetail extends LeadSummary {
  messages: LeadMessage[];
  followups: FollowupRead[];
  audit: AuditLogRead[];
  // False when the viewer is a non-owner employee: metadata is visible but the
  // chat transcript, follow-ups, audit and reply box are withheld by the API.
  can_edit: boolean;
}

/** Editable lead fields. Only include the ones being changed. */
export interface LeadUpdate {
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  bhk?: number | null;
  budget_min?: number | null;
  budget_max?: number | null;
  timeline?: string | null;
  purpose?: string | null;
  financing?: string | null;
  tier?: LeadTier | null;
  status?: LeadStatus | null;
  assigned_employee_id?: number | null; // admin only
}

export function listLeads(
  token: string,
  filters: { tier?: LeadTier; status?: LeadStatus; mine?: boolean } = {},
): Promise<LeadSummary[]> {
  const params = new URLSearchParams();
  if (filters.tier) params.set("tier", filters.tier);
  if (filters.status) params.set("status", filters.status);
  if (filters.mine) params.set("mine", "true");
  const qs = params.toString();
  return authedJson<LeadSummary[]>(token, `/api/v1/leads${qs ? `?${qs}` : ""}`);
}

export function getLead(token: string, id: number): Promise<LeadDetail> {
  return authedJson<LeadDetail>(token, `/api/v1/leads/${id}`);
}

/**
 * Activity/audit trail for a lead, optionally filtered by the acting employee.
 * Owner or admin only (mirrors the detail boundary).
 */
export function getLeadActivity(
  token: string,
  leadId: number,
  opts?: { actorId?: number; limit?: number },
): Promise<AuditLogRead[]> {
  const q = new URLSearchParams();
  if (opts?.actorId != null) q.set("actor_id", String(opts.actorId));
  if (opts?.limit != null) q.set("limit", String(opts.limit));
  const qs = q.toString();
  return authedJson<AuditLogRead[]>(
    token,
    `/api/v1/leads/${leadId}/activity${qs ? `?${qs}` : ""}`,
  );
}

/** Edit a lead (owner or admin; reassignment is admin-only). Returns the fresh detail. */
export function updateLead(
  token: string,
  id: number,
  changes: LeadUpdate,
): Promise<LeadDetail> {
  return authedJson<LeadDetail>(token, `/api/v1/leads/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
}

/** Delete a lead (admin only). */
export async function deleteLead(token: string, id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/leads/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok && res.status !== 204) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Delete failed (${res.status})`);
  }
}

/** Send an employee reply into a lead's widget chat (also takes over from the bot). */
export function replyToLead(
  token: string,
  leadId: number,
  body: string,
): Promise<LeadMessage> {
  return authedJson<LeadMessage>(token, `/api/v1/leads/${leadId}/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
}

/** SSE stream URL for a lead's chat. EventSource can't set headers, so the
 *  token and resume point ride in the query string. */
export function leadStreamUrl(
  token: string,
  leadId: number,
  afterMessageId: number,
): string {
  const params = new URLSearchParams({
    token,
    after: String(afterMessageId),
  });
  return `${API_BASE}/api/v1/leads/${leadId}/stream?${params.toString()}`;
}

// ---------------------------------------------------------------------------
// Follow-up drafts
// ---------------------------------------------------------------------------

export function listFollowups(token: string): Promise<FollowupRead[]> {
  return authedJson<FollowupRead[]>(token, "/api/v1/followups?status=draft");
}

export function editFollowup(
  token: string,
  id: number,
  draftBody: string,
): Promise<FollowupRead> {
  return authedJson<FollowupRead>(token, `/api/v1/followups/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft_body: draftBody }),
  });
}

export function sendFollowup(token: string, id: number): Promise<FollowupRead> {
  return authedJson<FollowupRead>(token, `/api/v1/followups/${id}/send`, {
    method: "POST",
  });
}

export function dismissFollowup(
  token: string,
  id: number,
): Promise<FollowupRead> {
  return authedJson<FollowupRead>(token, `/api/v1/followups/${id}/dismiss`, {
    method: "POST",
  });
}

// ---------------------------------------------------------------------------
// Public chat widget (no auth — the lead-facing surface)
// ---------------------------------------------------------------------------

export interface WidgetSession {
  lead_id: number;
  conversation_id: number;
  greeting: string;
}

export async function createWidgetSession(
  adSource?: string | null,
): Promise<WidgetSession> {
  const res = await fetch(`${API_BASE}/api/v1/widget/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ad_source: adSource ?? null }),
  });
  if (!res.ok) throw new Error("Could not start the chat");
  return (await res.json()) as WidgetSession;
}

/** Public SSE stream URL for a widget conversation — lets the lead see human
 *  (employee) replies live. No auth: the conversation id is the session handle. */
export function widgetStreamUrl(
  conversationId: number,
  afterMessageId: number,
): string {
  const params = new URLSearchParams({
    conversation_id: String(conversationId),
    after: String(afterMessageId),
  });
  return `${API_BASE}/api/v1/widget/stream?${params.toString()}`;
}

export async function sendWidgetMessage(
  conversationId: number,
  message: string,
): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/widget/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? "Message failed");
  }
  const data = await res.json();
  return data.reply as string;
}
