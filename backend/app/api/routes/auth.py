from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employee, oauth2_scheme, require_admin
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_session,
    delete_session,
    decode_access_token,
    verify_password,
)
from app.crud import employee as employee_crud
from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.auth import Token
from app.schemas.employee import EmployeeCreate, EmployeeRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Stateful login: verify credentials, open a server-side session, mint a JWT."""
    employee = await employee_crud.get_by_email(db, form_data.username)
    if employee is None or not verify_password(
        form_data.password, employee.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive account"
        )

    session_id = await create_session(redis, str(employee.id))
    token = create_access_token(
        subject=str(employee.id), session_id=session_id, role=employee.role.value
    )
    return Token(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: str = Depends(oauth2_scheme),
    redis: Redis = Depends(get_redis),
):
    """Revoke the current session so the JWT can no longer be used."""
    payload = decode_access_token(token)
    if payload and payload.get("sid"):
        await delete_session(redis, payload["sid"])


@router.get("/me", response_model=EmployeeRead)
async def read_me(current: Employee = Depends(get_current_employee)):
    return current


@router.post(
    "/register",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def register(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: create a new employee account."""
    if await employee_crud.get_by_email(db, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    return await employee_crud.create(db, data)
