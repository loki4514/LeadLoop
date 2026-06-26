# Lead Agent

Monorepo skeleton for an AI Lead Qualification app.

## Structure

```
.
├── backend/    FastAPI app: data models, migrations, JWT auth
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

###### Verify

- Backend health: `curl http://localhost:8000/health` → `{"status":"ok"}`
- Frontend: open http://localhost:3000 in a browser
- Worker: `docker-compose logs worker` shows `worker started`

## Auth

The backend uses stateful JWT auth (tokens are bound to a Redis-backed session,
so logout revokes them) with role-based access control (`employee`, `admin`).

Bootstrap the first admin, then log in:

```bash
# Create an admin (runs migrations on backend startup automatically)
docker compose exec backend python -m scripts.seed_admin \
  --email admin@example.com --password secret123 --name "Admin"

# Log in to get a token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@example.com&password=secret123"
```

Endpoints (under `/api/v1`): `POST /auth/login`, `POST /auth/logout`,
`GET /auth/me`, `POST /auth/register` (admin only).



