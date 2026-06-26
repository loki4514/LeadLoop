from fastapi import APIRouter

from app.api.routes import auth, health

api_router = APIRouter()
api_router.include_router(auth.router)

# /health stays unprefixed at the app root (see main.py).
__all__ = ["api_router", "health"]
