#!/bin/sh
set -e

# Apply database migrations, then start the API.
alembic upgrade head

# WEB_CONCURRENCY controls the number of Uvicorn workers (prod sets >1 for
# concurrency; dev leaves it unset = single worker with fast reload-free boot).
WORKERS="${WEB_CONCURRENCY:-1}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "$WORKERS"
