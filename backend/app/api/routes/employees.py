from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employee, require_admin
from app.crud import employee as employee_crud
from app.db.session import get_db
from app.models.employee import Employee
from app.models.enums import Role
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeUpdate

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


@router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: int,
    body: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    admin: Employee = Depends(require_admin),
):
    """Enable/disable an employee account. Admin only.

    Setting ``is_active=False`` is a soft delete (deactivate): the account can no
    longer log in and is skipped by auto-assignment, but its leads and history
    are preserved. An admin cannot deactivate their own account.
    """
    employee = await employee_crud.get_by_id(db, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
        )
    if employee.id == admin.id and not body.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    employee.is_active = body.is_active
    await db.commit()
    await db.refresh(employee)
    return employee


@router.delete("/{employee_id}", response_model=EmployeeRead)
async def deactivate_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    admin: Employee = Depends(require_admin),
):
    """Deactivate (soft delete) an employee. Admin only.

    Sets ``is_active=False`` rather than removing the row, so assigned leads and
    audit history survive. Reactivate via ``PATCH`` with ``is_active=True``. An
    admin cannot deactivate their own account.
    """
    employee = await employee_crud.get_by_id(db, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
        )
    if employee.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    employee.is_active = False
    await db.commit()
    await db.refresh(employee)
    return employee
