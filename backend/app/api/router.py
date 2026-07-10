from fastapi import APIRouter

from app.api.routes import (
    auth,
    chat,
    documents,
    employees,
    health,
    leads,
    properties,
    widget,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(employees.router)
api_router.include_router(leads.router)
api_router.include_router(leads.followups_router)
api_router.include_router(properties.router)
api_router.include_router(widget.router)

# /health stays unprefixed at the app root (see main.py).
__all__ = ["api_router", "health"]
