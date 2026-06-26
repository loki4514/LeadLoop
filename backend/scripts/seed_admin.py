"""Bootstrap an initial admin account so you can log in and create employees.

Usage (inside the backend container):
    docker compose exec backend python -m scripts.seed_admin \
        --email admin@example.com --password secret --name "Admin"
"""
import argparse
import asyncio

from app.db.session import AsyncSessionLocal
from app.crud import employee as employee_crud
from app.models.enums import Role
from app.schemas.employee import EmployeeCreate


async def main(name: str, email: str, password: str) -> None:
    async with AsyncSessionLocal() as db:
        if await employee_crud.get_by_email(db, email):
            print(f"Employee {email} already exists; nothing to do.")
            return
        data = EmployeeCreate(
            name=name, email=email, password=password, role=Role.ADMIN
        )
        employee = await employee_crud.create(db, data)
        print(f"Created admin #{employee.id}: {employee.email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Admin")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.name, args.email, args.password))
