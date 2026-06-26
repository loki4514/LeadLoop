from fastapi import FastAPI

from app.api.router import api_router
from app.api.routes import health
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# Unprefixed health check (docker-compose / load balancers hit /health).
app.include_router(health.router)

# Versioned API.
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
