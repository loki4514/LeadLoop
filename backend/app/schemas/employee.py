from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import Role


class EmployeeBase(BaseModel):
    name: str
    email: EmailStr
    role: Role = Role.EMPLOYEE


class EmployeeCreate(EmployeeBase):
    password: str


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
