"""Persistence for single-use password reset tokens."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset import PasswordResetToken


async def create(
    db: AsyncSession, employee_id: int, token_hash: str, ttl_minutes: int
) -> PasswordResetToken:
    # Invalidate any outstanding tokens for this user so only the newest works.
    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.employee_id == employee_id,
            PasswordResetToken.used.is_(False),
        )
        .values(used=True)
    )
    row = PasswordResetToken(
        employee_id=employee_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
    )
    db.add(row)
    await db.flush()
    return row


async def get_valid(db: AsyncSession, token_hash: str) -> PasswordResetToken | None:
    """Return the token row if it exists, is unused, and hasn't expired."""
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
    )
    row = result.scalar_one_or_none()
    if row is None or row.used:
        return None
    if row.expires_at <= datetime.now(timezone.utc):
        return None
    return row
