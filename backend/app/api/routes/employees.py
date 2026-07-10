from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employee, require_admin
from app.crud import employee as employee_crud
from app.db.session import get_db
from app.models.employee import Employee
from app.models.enums import Role
from app.schemas.employee import EmployeeCreate, EmployeeRead

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeRead])
async def list_employees(
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
):
    """List all employees. Available to any authenticated employee."""
    return await employee_crud.list_all(db)


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_admin),
):
    """Create a new employee. Admin only.

    Only regular employees can be created through this endpoint — admins are
    provisioned out-of-band (seed script). The role is forced to ``employee``
    regardless of the request payload. Rejects a duplicate email with 409.
    """
    existing = await employee_crud.get_by_email(db, data.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An employee with this email already exists",
        )
    data = data.model_copy(update={"role": Role.EMPLOYEE})
    return await employee_crud.create(db, data)
