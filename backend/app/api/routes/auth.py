from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employee, oauth2_scheme, require_admin
from app.core.config import settings
from app.core.email import reset_email_html, send_email
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    create_session,
    delete_session,
    decode_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.crud import employee as employee_crud
from app.crud import password_reset as reset_crud
from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.auth import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
)
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
    # is_active is the admin enable/disable switch — a deactivated account
    # cannot log in (and cannot un-deactivate itself by logging in).
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
        )

    # Presence: mark online for the new session.
    employee.is_online = True

    session_id = await create_session(redis, str(employee.id))
    token = create_access_token(
        subject=str(employee.id), session_id=session_id, role=employee.role.value
    )
    await db.commit()
    return Token(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Revoke the current session and mark the employee offline.

    Sets `is_online=False` (presence) — NOT `is_active`, which is the admin
    enable/disable switch. The session is revoked so the JWT can no longer be
    used regardless.
    """
    payload = decode_access_token(token)
    if payload is None:
        return
    if payload.get("sid"):
        await delete_session(redis, payload["sid"])
    sub = payload.get("sub")
    if sub is not None:
        employee = await employee_crud.get_by_id(db, int(sub))
        if employee is not None and employee.is_online:
            employee.is_online = False
            await db.commit()


@router.get("/me", response_model=EmployeeRead)
async def read_me(current: Employee = Depends(get_current_employee)):
    return current


# A fixed response for /forgot-password regardless of whether the email exists,
# so the endpoint can't be used to discover which emails have accounts.
_FORGOT_OK = {"message": "If that email is registered, a reset link has been sent."}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Begin a password reset: email a single-use reset link if the account exists.

    Works for both employees and admins. Always returns the same message to
    avoid leaking which emails are registered.
    """
    employee = await employee_crud.get_by_email(db, body.email)
    if employee is not None and employee.is_active:
        raw = generate_reset_token()
        await reset_crud.create(
            db,
            employee_id=employee.id,
            token_hash=hash_reset_token(raw),
            ttl_minutes=settings.RESET_TOKEN_EXPIRE_MINUTES,
        )
        await db.commit()
        reset_url = f"{settings.FRONTEND_BASE_URL}/reset?token={raw}"
        await send_email(
            to=employee.email,
            subject="Reset your LeadLoop password",
            html=reset_email_html(
                employee.name, reset_url, settings.RESET_TOKEN_EXPIRE_MINUTES
            ),
        )
    return _FORGOT_OK


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Complete a password reset with a valid token; sets the new password.

    Consumes the token (single use) and, for safety, does not affect existing
    sessions here — the user simply logs in with the new password.
    """
    row = await reset_crud.get_valid(db, hash_reset_token(body.token))
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired.",
        )
    employee = await employee_crud.get_by_id(db, row.employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired.",
        )
    employee.hashed_password = hash_password(body.new_password)
    row.used = True
    await db.commit()
    return {"message": "Your password has been reset. You can now log in."}


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
