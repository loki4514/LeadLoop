from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate


async def get_by_id(db: AsyncSession, employee_id: int) -> Employee | None:
    return await db.get(Employee, employee_id)


async def get_by_email(db: AsyncSession, email: str) -> Employee | None:
    result = await db.execute(select(Employee).where(Employee.email == email))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, data: EmployeeCreate) -> Employee:
    employee = Employee(
        name=data.name,
        email=data.email,
        role=data.role,
        hashed_password=hash_password(data.password),
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee
