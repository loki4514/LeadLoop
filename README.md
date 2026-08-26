# LeadLoop

An **AI Lead Qualification & Follow-up Agent** for real estate (positioned for
any high-ticket sales). Inbound leads land in a web chat widget; an AI agent
qualifies them, shows matching properties, captures contact details, scores them
**Hot / Warm / Cold**, and auto-assigns them to an employee. Any employee can
**take over the live chat** at any moment — the AI steps back and a human
continues the conversation. If a lead goes quiet for two days, a background
worker drafts a follow-up email and pings the assigned employee, who approves,
edits, or sends it from the dashboard.

A public **landing page** presents the product; the **dashboard** (behind login)
is where the team works leads, and the embeddable **widget** is what a lead sees.

## The agent flow

```
Ad click (web widget)                          [ad source tagged for attribution]
   ↓
AI asks: location? BHK? budget?
   ↓
AI shows matching properties (parameterized Postgres query)
   ↓
AI asks for a callback → captures email + phone
   ↓
score_lead()  → Hot / Warm / Cold             (deterministic, rules-based)
   ↓
assign_employee()  → an employee              (round-robin, tier-weighted load)
   ↓
Employee follows up: chat (AI hands over) / email / call
   ↓
2 days, no activity? → worker drafts a follow-up email → pings employee → approve & send
   ↓
Dashboard: leads, scores, owners, ad source, status, full activity/audit trail
```

**Design principles**
- **One** conversational AI agent. It uses **tools** — it is not several agents.
- `score_lead()` and `assign_employee()` are **deterministic Python functions**,
  never LLM calls, so scoring and routing are auditable and reproducible.
- The agent **never writes SQL**. It extracts structured filters (location, bhk,
  min/max price) and calls a fixed tool signature; Python runs the prepared query.
- **Property search is a parameterized, indexed Postgres query — not a vector DB.**
  pgvector is used only for the separate document **knowledge-base RAG** that
  answers free-text questions.

## How it works (in depth)

### 1. The conversational agent — a native tool-calling loop

The agent is a single loop in `app/agent/service.py`, written directly against
the LLM's native tool-use API (no LangChain). One inbound widget message runs
`run_agent_turn`, which:

1. Loads the conversation and the lead, then builds the message list: a **system
   prompt** (persona + conversation-flow rules + the lead's already-known answers
   injected as JSON so the agent never re-asks) followed by the full transcript
   and the new message.
2. Enters `_agent_loop`: **call the model → if it returned tool calls, run them
   in Python and feed the results back → repeat** (bounded by `MAX_TOOL_ROUNDS`).
   When the model returns plain text instead of tool calls, that text is the
   reply. Every tool result is appended to the message list so the model reasons
   over real data (e.g. the actual properties returned), never guesses.
3. Persists both turns and bumps `last_activity_at` (which the stall checker
   later reads).

The agent's job is to **normalize** the free-text conversation into structured
fields and call fixed tool signatures — it does not compute scores, choose
employees, or write SQL itself.

### 2. Human takeover

The lead has an `is_bot_active` flag. Two paths flip it off:

- **Deterministic:** if the lead's message matches a "talk to a human" intent,
  `run_agent_turn` hands over immediately (rather than hoping the LLM calls the
  tool that turn), acknowledges once, and goes silent.
- **Employee-initiated:** an employee posting via `POST /leads/{id}/reply` sets
  `is_bot_active=false`.

Once handed over, the AI stays silent — it persists the lead's messages (so the
employee sees them) but sends no reply. Live messages flow to both the widget
and the dashboard over **Server-Sent Events** (`/leads/{id}/stream`,
`/widget/stream`), which poll the DB and push new rows; SSE (not WebSockets)
keeps it simple and reconnect-friendly.

### 3. Scoring — deterministic rules (`app/agent/scoring.py`)

`score_lead(lead)` is a pure function over the stored answers, 0–100:

| Signal | Points |
|--------|--------|
| Budget given (serious-vs-browsing) | 30 |
| Timeline | 25 / 15 / 8 / 3 (0–3mo → 12mo+) |
| Purpose | own use 15, investment 10, exploring 0 |
| Financing | ready cash 10, approved 8, needed 5, unsure 2 |
| Search criteria known (location, BHK) | 5 + 5 |
| Reachable (email or phone) | 10 |

Tier: **Hot ≥ 70, Warm ≥ 40, else Cold.** Same answers always produce the same
score — auditable and unit-tested at the threshold boundaries.

### 4. Assignment — load-balanced, tier-weighted round-robin (`app/agent/assignment.py`)

`assign_employee(lead)` picks the **least-loaded active employee**:

- Each employee's open (non-closed) leads are summed with a **tier weight** —
  Hot = 3, Warm = 2, Cold = 1 — so a rep holding hot leads is considered busier
  than one holding the same count of cold ones.
- **Ties break** to whoever was assigned a lead least recently (the round-robin
  part), then by id.
- Only `is_active` employees are eligible; deactivated accounts are skipped. If
  no plain employees exist it falls back to admins, so a one-person shop still
  gets leads routed.

### 5. Property search vs. knowledge-base RAG

Two different retrieval paths, on purpose:

- **`search_properties`** — a parameterized, **indexed relational query** on
  `location / bhk / listing_type / price`. If nothing matches the budget, it
  falls back to the closest listings by price and flags the result
  (`fallback: true`) so the agent presents them honestly and pivots to a human
  handoff instead of dead-ending.
- **`search_knowledge_base`** — **pgvector** cosine-similarity over embedded
  document chunks, for free-text factual questions (loans, legal, amenities).

### 6. The stall checker & follow-up drafts (`app/tasks/followups.py`)

A Celery **beat** schedule runs `check_stalled_leads` periodically. It selects
leads that are qualified/assigned, reachable (have an email), quiet past
`STALL_HOURS` (default 48h), and **don't already have a pending draft**. For each,
it drafts a follow-up email from the recent transcript, stores it as a
`Followup(status="draft")`, and emails the assigned employee that a draft is
waiting. The employee then edits / sends / dismisses it from the dashboard —
sending refreshes the lead's `last_activity_at` so it isn't immediately
re-drafted.

## Structure

```
.
├── backend/          FastAPI (async): agent, tools, scoring, RAG, auth, follow-ups
│   ├── app/agent/    the AI agent loop, tools, scoring, assignment
│   ├── app/api/      routes: auth, widget, leads, properties, employees, chat, documents
│   ├── app/tasks/    Celery tasks (stall checker + follow-up drafting)
│   └── tests/        pytest suite (scoring + assignment)
├── frontend/         Next.js + TypeScript: landing page, dashboard, chat widget
│   └── src/app/      routes: / (landing), /login, /dashboard, /leads, /leads/[id],
│                     /employees, /chat, /documents, /widget
├── knowledge_base/   sample FAQ docs for the RAG knowledge base
└── docker-compose.yml
```

> **Note:** the frontend runs as a compiled production image (no dev source
> mount). Frontend code changes require a rebuild to take effect:
> `docker compose build frontend && docker compose up -d frontend`.

## Tech stack

| Layer | Choice |
|-------|--------|
| Backend | Python + FastAPI (async) |
| LLM | Pluggable via `app/llm/factory.py` — OpenAI or Google Gemini (`LLM_PROVIDER`) |
| Embeddings | Pluggable (`EMBEDDING_PROVIDER`); OpenAI `text-embedding-3-small` by default |
| DB | PostgreSQL (source of truth) + pgvector for the RAG knowledge base |
| Property search | Parameterized, indexed SQL query (no vector DB) |
| Background jobs | Celery + Redis (worker runs the stall checker + follow-up drafting) |
| Frontend | Next.js (React + TypeScript) |
| Email | Resend (drafts logged to console when `RESEND_API_KEY` is unset) |
| Auth | Stateful JWT + role-based access control (`employee`, `admin`) |
| Infra | Docker + docker-compose |

## Run

```bash
cp .env.example .env   # set JWT_SECRET and an LLM/embedding API key
docker compose up      # use `docker-compose up` on older Docker
```

This starts all services:

| Service  | URL / Port            | Role                                    |
|----------|-----------------------|-----------------------------------------|
| backend  | http://localhost:8000 | FastAPI API (migrations run on startup) |
| frontend | http://localhost:3000 | Dashboard + chat widget                 |
| postgres | localhost:5432        | Primary DB (pgvector image)             |
| redis    | localhost:6379        | Celery broker + result backend          |
| worker   | (background)          | Celery worker + beat (stall checker)    |

### Verify

- Backend health: `curl http://localhost:8000/health` → `{"status":"ok"}`
- API docs: open http://localhost:8000/docs
- Frontend: open http://localhost:3000
- Worker: `docker compose logs worker` shows the Celery worker + beat starting

## Seed data

```bash
# Create the first admin (migrations run automatically on backend startup)
docker compose exec backend python -m scripts.seed_admin \
  --email admin@example.com --password secret123 --name "Admin"

# Load sample properties so the agent has inventory to show
docker compose exec backend python -m scripts.seed_properties
```

## Auth

Stateful JWT auth (tokens are bound to a Redis-backed session, so logout revokes
them) with role-based access control (`employee`, `admin`).

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@example.com&password=secret123"
```

Auth endpoints (under `/api/v1`): `POST /auth/login`, `POST /auth/logout`,
`GET /auth/me`, `POST /auth/register` (admin only), plus the email-based
forgot-password / reset flow.

Two independent employee flags:
- **`is_active`** — the admin enable/disable switch. A deactivated account cannot
  log in (login returns 403) and is skipped by auto-assignment. Reversible.
- **`is_online`** — session presence. Set on login, cleared on logout. Kept
  separate from `is_active` so logging in can never silently re-enable a
  deactivated account.

## Access model & lifecycle

- **Lead ownership.** Employees see all leads in the list (so they know *who* is
  working what), but the **conversation transcript, follow-ups, and controls of a
  lead assigned to someone else are withheld** — the detail response returns
  metadata only with `can_edit: false`. Owners and admins get the full detail.
- **Editing.** The lead owner (or an admin) can edit qualification fields, tier,
  and status. **Reassignment and deletion are admin-only.** Every change is
  written to an **audit trail** surfaced as an Activity timeline on the lead, and
  queryable via `GET /leads/{id}/activity?actor_id=`.
- **Human takeover.** An employee replying into a lead's chat flips it out of bot
  mode (`is_bot_active=false`) — the AI goes silent and the human takes over.
  Live messages stream to both the widget and the dashboard over SSE.
- **Employee lifecycle.** Admins add employees, and **deactivate/reactivate**
  them (soft delete via `is_active`, preserving their leads and history — no hard
  delete). An admin cannot deactivate their own account.

## API surface (`/api/v1`)

| Area | Endpoints |
|------|-----------|
| Widget (public lead chat) | `POST /widget/sessions`, `POST /widget/messages`, `GET /widget/stream` (SSE) |
| Leads | `GET /leads`, `GET /leads/{id}`, `PATCH /leads/{id}` (edit/reassign), `DELETE /leads/{id}` (admin), `GET /leads/{id}/activity` |
| Human takeover | `POST /leads/{id}/reply` (employee replies into the chat), `GET /leads/{id}/stream` (SSE live messages) |
| Follow-ups | `GET /followups`, `PATCH /followups/{id}` (edit), `POST /followups/{id}/send`, `POST /followups/{id}/dismiss` |
| Properties | `GET /properties`, `POST /properties` |
| Employees | `GET /employees`, `POST /employees` (admin), `PATCH /employees/{id}` (activate/deactivate, admin), `DELETE /employees/{id}` (deactivate, admin) |
| RAG chat (internal) | under `/chat` |
| Documents (knowledge base) | under `/documents` |

## Agent tools

Defined in `app/agent/tools.py`, executed by the loop in `app/agent/service.py`:

- `search_properties(location, bhk, min_price, max_price, limit)` → matching listings
- `save_lead_answers(...)` → normalize the conversation's answers into stored fields
- `capture_contact(email, phone)` → record contact details
- `score_lead()` → `{score, tier}` (deterministic; see `app/agent/scoring.py`)
- `assign_employee()` → chosen employee (deterministic; see `app/agent/assignment.py`)
- `search_knowledge_base(query)` → relevant chunks from the RAG knowledge base
- `handover_to_human()` → flag the conversation for employee takeover

## Tests

```bash
docker compose run --rm backend pytest      # in Docker
cd backend && pytest                        # or locally, with backend deps installed
```

Covers the deterministic core: lead **scoring** (all tiers + threshold boundaries)
and **assignment** (load balancing, tier weighting, round-robin tiebreak).
