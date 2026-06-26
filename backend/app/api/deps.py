from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import decode_access_token, session_exists
from app.crud import employee as employee_crud
from app.db.session import get_db
from app.models.employee import Employee
from app.models.enums import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_employee(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Employee:
    payload = decode_access_token(token)
    if payload is None:
        raise _credentials_error

    employee_id = payload.get("sub")
    session_id = payload.get("sid")
    if employee_id is None or session_id is None:
        raise _credentials_error

    # Statefulness: the token is only valid while its session record lives.
    if not await session_exists(redis, session_id):
        raise _credentials_error

    employee = await employee_crud.get_by_id(db, int(employee_id))
    if employee is None or not employee.is_active:
        raise _credentials_error

    return employee


def require_roles(*roles: Role) -> Callable:
    """Dependency factory enforcing role-based access control."""

    async def _checker(
        employee: Employee = Depends(get_current_employee),
    ) -> Employee:
        if employee.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return employee

    return _checker


# Convenience guard for admin-only endpoints.
require_admin = require_roles(Role.ADMIN)
