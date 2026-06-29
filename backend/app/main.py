from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes import health
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# Allow the browser frontend (different origin/port) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unprefixed health check (docker-compose / load balancers hit /health).
app.include_router(health.router)

# Versioned API.
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
