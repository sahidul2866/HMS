from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.branch import Branch
from app.models.department import Department
from app.models.role import Role
from app.models.user import User

SAMPLE_USERS = [
    {
        "username": "dr_rahman",
        "email": "dr.rahman@hms.local",
        "full_name": "Dr. Rahman",
        "password": "Doctor123!",
        "role_code": "DOCTOR",
        "department_code": "CLN",
    },
    {
        "username": "pharma_nadia",
        "email": "nadia.pharmacy@hms.local",
        "full_name": "Nadia Sultana",
        "password": "Pharma123!",
        "role_code": "PHARMACIST",
        "department_code": "PHR",
    },
    {
        "username": "acct_kamal",
        "email": "kamal.accounts@hms.local",
        "full_name": "Kamal Hossain",
        "password": "Account123!",
        "role_code": "ACCOUNTANT",
        "department_code": "ACC",
    },
]


def get_required(session, model, field, value, label: str):
    item = session.scalar(select(model).where(field == value))
    if not item:
        raise RuntimeError(f"Missing required {label}: {value}. Run seed_access_control first.")
    return item


def create_or_update_staff_user(session, *, branch: Branch, role: Role, department: Department, payload: dict) -> None:
    user = session.scalar(select(User).where(User.username == payload["username"]))
    if not user:
        user = User(
            username=payload["username"],
            email=payload["email"],
            full_name=payload["full_name"],
            hashed_password=get_password_hash(payload["password"]),
            branch_id=branch.id,
            department_id=department.id,
            is_active=True,
        )
        session.add(user)
        session.flush()
    else:
        user.email = payload["email"]
        user.full_name = payload["full_name"]
        user.branch_id = branch.id
        user.department_id = department.id
        user.is_active = True
    user.roles = [role]


def main() -> None:
    session = SessionLocal()
    try:
        branch = get_required(session, Branch, Branch.code, "HQ", "branch")

        for payload in SAMPLE_USERS:
            role = get_required(session, Role, Role.code, payload["role_code"], "role")
            department = get_required(session, Department, Department.code, payload["department_code"], "department")
            create_or_update_staff_user(session, branch=branch, role=role, department=department, payload=payload)

        session.commit()
        print("Sample staff seed completed.")
        print("Doctor: dr_rahman / Doctor123!")
        print("Pharmacist: pharma_nadia / Pharma123!")
        print("Accountant: acct_kamal / Account123!")
    finally:
        session.close()


if __name__ == "__main__":
    main()
