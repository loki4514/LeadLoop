"""Property inventory management (what search_properties queries against)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employee, require_admin
from app.db.session import get_db
from app.models.employee import Employee
from app.models.property import Property
from app.schemas.lead import PropertyCreate, PropertyRead

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertyRead])
async def list_properties(
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
):
    result = await db.execute(select(Property).order_by(Property.id))
    return list(result.scalars().all())


@router.post("", response_model=PropertyRead, status_code=201)
async def create_property(
    body: PropertyCreate,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(require_admin),
):
    prop = Property(**body.model_dump())
    db.add(prop)
    await db.commit()
    await db.refresh(prop)
    return prop
