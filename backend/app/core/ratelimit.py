"""Shared rate limiter (slowapi) — protects the public widget and auth endpoints
from cost-abuse and brute force. Keyed by client IP; limits are applied per-route
via the @limiter.limit(...) decorator."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Default has no global limit; specific routes opt in with their own limits.
limiter = Limiter(key_func=get_remote_address)
