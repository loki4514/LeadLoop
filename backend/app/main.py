from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.api.routes import health
from app.core.config import settings
from app.core.ratelimit import limiter

app = FastAPI(title=settings.PROJECT_NAME)

# Rate limiting: attach the shared limiter and a 429 handler. Individual routes
# opt in via @limiter.limit(...); see widget + auth endpoints.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
