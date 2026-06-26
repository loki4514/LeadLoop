# Lead Agent

Monorepo skeleton for an AI Lead Qualification app.

## Structure

```
.
├── backend/    FastAPI app (/health endpoint)
├── frontend/   Next.js + TypeScript landing page
├── worker/     RQ worker connected to Redis
└── docker-compose.yml   postgres, redis, backend, frontend, worker
```

## Run

```bash
cp .env.example .env   # fill in ANTHROPIC_API_KEY and JWT_SECRET as needed
docker-compose up      # use `docker compose up` on newer Docker
```

This starts all five services:

| Service  | URL / Port              |
|----------|-------------------------|
| backend  | http://localhost:8000   |
| frontend | http://localhost:3000   |
| postgres | localhost:5432          |
| redis    | localhost:6379          |
| worker   | (background process)    |

## Verify

- Backend health: `curl http://localhost:8000/health` → `{"status":"ok"}`
- Frontend: open http://localhost:3000 in a browser
- Worker: `docker-compose logs worker` shows `worker started`
