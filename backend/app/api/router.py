from fastapi import APIRouter

from app.api.routes import auth, chat, documents, health

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)

# /health stays unprefixed at the app root (see main.py).
__all__ = ["api_router", "health"]
