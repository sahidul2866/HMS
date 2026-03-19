from collections.abc import Iterable

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.branch import Branch
from app.models.department import Department
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.utils.seed_data import PERMISSION_CATALOG, ROLE_CATALOG


def get_or_create_branch(session, code: str, name: str, description: str | None = None) -> Branch:
    branch = session.scalar(select(Branch).where(Branch.code == code))
    if branch:
        return branch
    branch = Branch(code=code, name=name, description=description)
    session.add(branch)
    session.flush()
    return branch


def get_or_create_department(session, branch_id, code: str, name: str, description: str | None = None) -> Department:
    department = session.scalar(select(Department).where(Department.code == code))
    if department:
        return department
    department = Department(branch_id=branch_id, code=code, name=name, description=description)
    session.add(department)
    session.flush()
    return department


def sync_permissions(session) -> dict[str, Permission]:
    permission_map: dict[str, Permission] = {}
    for code, module, action, description in PERMISSION_CATALOG:
        permission = session.scalar(select(Permission).where(Permission.code == code))
        if not permission:
            permission = Permission(code=code, module=module, action=action, description=description)
            session.add(permission)
            session.flush()
        else:
            permission.module = module
            permission.action = action
            permission.description = description
            permission.is_active = True
        permission_map[code] = permission
    return permission_map


def sync_roles(session, permission_map: dict[str, Permission]) -> dict[str, Role]:
    role_map: dict[str, Role] = {}
    for code, permission_codes in ROLE_CATALOG.items():
        role = session.scalar(select(Role).where(Role.code == code))
        if not role:
            role = Role(code=code, name=code.replace("_", " ").title(), description=f"{code.title()} role")
            session.add(role)
            session.flush()
        role.permissions = [permission_map[item] for item in permission_codes]
        role.is_active = True
        role_map[code] = role
    return role_map


def create_or_update_user(
    session,
    *,
    username: str,
    email: str,
    full_name: str,
    password: str,
    branch_id,
    department_id,
    roles: Iterable[Role],
) -> User:
    user = session.scalar(select(User).where(User.username == username))
    if not user:
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            branch_id=branch_id,
            department_id=department_id,
            is_active=True,
        )
        session.add(user)
        session.flush()
    else:
        user.email = email
        user.full_name = full_name
        user.branch_id = branch_id
        user.department_id = department_id
        user.is_active = True
    user.roles = list(roles)
    return user


def main() -> None:
    session = SessionLocal()
    try:
        hq = get_or_create_branch(session, "HQ", "Headquarters", "Primary operating branch")
        get_or_create_department(session, hq.id, "CLN", "Clinical", "General clinical services")
        get_or_create_department(session, hq.id, "PHR", "Pharmacy", "Pharmacy operations")
        get_or_create_department(session, hq.id, "ACC", "Accounting", "Finance and accounting")
        get_or_create_department(session, hq.id, "ADM", "Administration", "Administrative services")

        permission_map = sync_permissions(session)
        role_map = sync_roles(session, permission_map)

        admin_department = session.scalar(select(Department).where(Department.code == "ADM"))
        create_or_update_user(
            session,
            username="superadmin",
            email="superadmin@hms.local",
            full_name="System Super Admin",
            password="Admin123!",
            branch_id=hq.id,
            department_id=admin_department.id if admin_department else None,
            roles=[role_map["SUPER_ADMIN"]],
        )

        session.commit()
        print("Access-control seed completed.")
        print("Super admin: superadmin / Admin123!")
    finally:
        session.close()


if __name__ == "__main__":
    main()
