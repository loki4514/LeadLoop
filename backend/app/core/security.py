import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---- Password hashing -------------------------------------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---- JWT --------------------------------------------------------------------

def create_access_token(subject: str, session_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,      # employee id
        "sid": session_id,   # server-side session id (statefulness)
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None


# ---- Stateful session store (Redis) -----------------------------------------
#
# A login mints a JWT *and* records a session in Redis keyed by `sid`. The token
# is only honored while its session record exists, so logout / revocation works
# even though JWTs are otherwise stateless.

_SESSION_PREFIX = "session:"


def _session_key(session_id: str) -> str:
    return f"{_SESSION_PREFIX}{session_id}"


async def create_session(redis: Redis, employee_id: str) -> str:
    session_id = str(uuid.uuid4())
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    await redis.set(_session_key(session_id), employee_id, ex=ttl)
    return session_id


async def session_exists(redis: Redis, session_id: str) -> bool:
    return bool(await redis.exists(_session_key(session_id)))


async def delete_session(redis: Redis, session_id: str) -> None:
    await redis.delete(_session_key(session_id))
