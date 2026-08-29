# Deploying LeadLoop to Railway

Railway runs **individual services**, not `docker-compose`. This project becomes
**5 services in one Railway project**:

| Service    | Source            | Notes |
|------------|-------------------|-------|
| Postgres   | pgvector image    | Must have the `vector` extension (see step 2). |
| Redis      | Railway plugin    | Celery broker + sessions. |
| backend    | `backend/` Docker | FastAPI API; runs migrations on boot. |
| worker     | `backend/` Docker | Same image, Celery start command. |
| frontend   | `frontend/` Docker| Next.js; needs the backend's public URL at build time. |

Caddy is **not used** on Railway — Railway terminates TLS and gives each public
service a free `*.up.railway.app` HTTPS URL.

---

## Prerequisites

```bash
npm i -g @railway/cli     # install the CLI
railway login             # opens the browser
```

Code is already on GitHub (`loki4514/LeadLoop`). You can deploy from GitHub
(auto-deploy on push) or with `railway up` from local — this guide uses the CLI.

---

## Step 1 — Create the project

```bash
cd LeadLoop
railway init            # create a new project (give it a name, e.g. leadloop)
```

## Step 2 — Postgres WITH pgvector (important)

Railway's default Postgres does **not** include the `vector` extension, which the
RAG migration requires. Use the **pgvector template** instead:

- In the Railway dashboard: **New → Database → "Postgres" → search templates for
  "pgvector"** (the `pgvector/pgvector` image), **or** deploy a service from the
  Docker image `pgvector/pgvector:pg16` and set `POSTGRES_USER/PASSWORD/DB`.
- Railway exposes `DATABASE_URL` on that service (format
  `postgresql://user:pass@host:port/db`) — the backend normalizes it to the async
  driver automatically (`config.py: sqlalchemy_url`), and migration `0002` runs
  `CREATE EXTENSION IF NOT EXISTS vector`.

## Step 3 — Redis

Dashboard: **New → Database → Redis.** Railway exposes `REDIS_URL`.

## Step 4 — Backend service

```bash
# From the repo root, create a service rooted at backend/
railway add           # or use the dashboard: New -> GitHub repo -> root: backend
```

Set the backend service's **root directory to `backend`** (dashboard → service →
Settings → Root Directory). Railway picks up `backend/railway.json` (Dockerfile
build, `/health` healthcheck, `sh entrypoint.sh` start — which runs migrations
then uvicorn).

**Environment variables** (dashboard → backend → Variables). Use Railway's
reference syntax to wire the databases:

```
ENVIRONMENT=production
WEB_CONCURRENCY=2
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
JWT_SECRET=<run: openssl rand -hex 32>
CORS_ORIGINS=https://<your-frontend-domain>.up.railway.app
FRONTEND_BASE_URL=https://<your-frontend-domain>.up.railway.app
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=<your key>
OPENAI_API_KEY=<your key>
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
EMBEDDING_API_KEY=<your key>
RESEND_API_KEY=            # optional; blank = reset links logged
EMAIL_FROM=LeadLoop <onboarding@resend.dev>
```

> `ENVIRONMENT=production` makes the backend refuse to boot with an insecure
> JWT_SECRET or the default DB password — so set a strong `JWT_SECRET`.

Generate a public domain for the backend: **Settings → Networking → Generate
Domain.** Note the URL (e.g. `https://leadloop-backend.up.railway.app`).

## Step 5 — Worker service

Add a **second service from the same `backend` directory**. Override its start
command (Settings → Deploy → Custom Start Command) so it runs Celery instead of
the API:

```
celery -A app.core.celery_app.celery_app worker -B --loglevel=info --concurrency=2
```

Give it the **same environment variables** as the backend (DATABASE_URL,
REDIS_URL, JWT_SECRET, the LLM/EMBEDDING keys, STALL_HOURS, etc.). It has no HTTP
port and needs no public domain or healthcheck.

## Step 6 — Frontend service

Add a service rooted at **`frontend`** (picks up `frontend/railway.json`).

The frontend calls the backend directly (no Caddy), and `NEXT_PUBLIC_API_BASE` is
**baked in at build time**. Set it as a **build variable** so the Dockerfile
`ARG` receives it:

```
NEXT_PUBLIC_API_BASE=https://leadloop-backend.up.railway.app
```

(Use the backend URL from step 4 — no trailing slash.) Then **Generate Domain**
for the frontend; that URL is what you share. Put it back into the backend's
`CORS_ORIGINS` and `FRONTEND_BASE_URL` (step 4) and redeploy the backend so CORS
allows it.

## Step 7 — Deploy & seed

```bash
railway up            # or push to GitHub if you connected the repo
```

Migrations run automatically on the backend's first boot (`entrypoint.sh`). Then
seed an admin (Railway shell or `railway run`):

```bash
railway run --service backend \
  python -m scripts.seed_admin --email admin@example.com --password 'STRONG_PW' --name Admin

# optional: sample properties for the widget demo
railway run --service backend python -m scripts.seed_properties
```

## Step 8 — Verify

- Frontend: `https://<frontend>.up.railway.app` — landing page loads.
- Log in with the seeded admin.
- Widget: `https://<frontend>.up.railway.app/widget` — the agent replies (needs
  the LLM key set and properties seeded).

---

## Gotchas

- **pgvector:** if migration `0002` fails with `type "vector" does not exist`, the
  Postgres service doesn't have the extension — use the pgvector image (step 2).
- **CORS errors in the browser:** the backend's `CORS_ORIGINS` must exactly match
  the frontend's Railway URL (https, no trailing slash). Redeploy backend after
  setting it.
- **Frontend calls localhost:** means `NEXT_PUBLIC_API_BASE` wasn't set at build
  time — it's a build var, not a runtime var. Set it and redeploy the frontend.
- **Cost:** Railway's trial credit covers a demo; beyond that it's usage-based
  (~$5/mo range for small services). Redis + Postgres each count as a service.
