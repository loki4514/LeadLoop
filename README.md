# LeadLoop

An **AI Lead Qualification & Follow-up Agent** for real estate (positioned for
any high-ticket sales). Inbound leads land in a web chat widget; an AI agent
qualifies them, shows matching properties, captures contact details, scores them
**Hot / Warm / Cold**, and auto-assigns them to an employee. If a lead goes quiet
for two days, a background worker drafts a follow-up email and pings the assigned
employee, who approves, edits, or sends it from a dashboard.

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
Employee follows up: chat / email / call
   ↓
2 days, no activity? → worker drafts a follow-up email → pings employee → approve & send
   ↓
Dashboard: leads, scores, owners, ad source, status
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

## Structure

```
.
├── backend/          FastAPI (async): agent, tools, scoring, RAG, auth, follow-ups
│   ├── app/agent/    the AI agent loop, tools, scoring, assignment
│   ├── app/api/      routes: auth, widget, leads, properties, employees, chat, documents
│   ├── app/tasks/    Celery tasks (stall checker + follow-up drafting)
│   └── tests/        pytest suite (scoring + assignment)
├── frontend/         Next.js + TypeScript: dashboard + embeddable chat widget
├── knowledge_base/   sample FAQ docs for the RAG knowledge base
└── docker-compose.yml
```

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

## API surface (`/api/v1`)

| Area | Endpoints |
|------|-----------|
| Widget (public lead chat) | `POST /widget/sessions`, `POST /widget/messages` |
| Leads | `GET /leads`, `GET /leads/{id}` |
| Follow-ups | under `/followups` (approve / edit / send drafts) |
| Properties | `GET /properties`, `POST /properties` |
| Employees | `GET /employees`, `POST /employees` |
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
