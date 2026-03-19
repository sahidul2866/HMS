from collections.abc import Iterable

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.branch import Branch
from app.models.department import Department
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

PERMISSION_CATALOG = [
    ("dashboard.view", "dashboard", "view", "View operational dashboard"),
    ("patient.view", "patient", "view", "View patient records"),
    ("patient.create", "patient", "create", "Create patient records"),
    ("patient.edit", "patient", "edit", "Edit patient records"),
    ("patient.delete", "patient", "delete", "Delete patient records"),
    ("pharmacy.view", "pharmacy", "view", "View pharmacy module"),
    ("pharmacy.dispense", "pharmacy", "dispense", "Dispense medicines"),
    ("pharmacy.stock.adjust", "pharmacy", "stock.adjust", "Adjust pharmacy stock"),
    ("accounting.view", "accounting", "view", "View accounting module"),
    ("accounting.journal.create", "accounting", "journal.create", "Create accounting journals"),
    ("accounting.journal.post", "accounting", "journal.post", "Post accounting journals"),
    ("settings.user.manage", "settings", "user.manage", "Manage users"),
    ("settings.role.manage", "settings", "role.manage", "Manage roles"),
    ("settings.permission.manage", "settings", "permission.manage", "Manage permissions"),
    ("settings.branch.manage", "settings", "branch.manage", "Manage branches"),
    ("settings.department.manage", "settings", "department.manage", "Manage departments"),
    ("audit.view", "audit", "view", "View audit logs"),
]

ROLE_CATALOG: dict[str, list[str]] = {
    "SUPER_ADMIN": [code for code, *_ in PERMISSION_CATALOG],
    "ADMIN": [
        "dashboard.view",
        "patient.view",
        "patient.create",
        "patient.edit",
        "pharmacy.view",
        "accounting.view",
        "settings.user.manage",
        "settings.role.manage",
        "settings.permission.manage",
        "settings.branch.manage",
        "settings.department.manage",
        "audit.view",
    ],
    "DOCTOR": [
        "dashboard.view",
        "patient.view",
        "patient.create",
        "patient.edit",
    ],
    "PHARMACIST": [
        "dashboard.view",
        "patient.view",
        "pharmacy.view",
        "pharmacy.dispense",
        "pharmacy.stock.adjust",
    ],
    "ACCOUNTANT": [
        "dashboard.view",
        "accounting.view",
        "accounting.journal.create",
        "accounting.journal.post",
    ],
}


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
        clinical = get_or_create_department(session, hq.id, "CLN", "Clinical", "General clinical services")
        pharmacy = get_or_create_department(session, hq.id, "PHR", "Pharmacy", "Pharmacy operations")
        finance = get_or_create_department(session, hq.id, "ACC", "Accounting", "Finance and accounting")
        admin = get_or_create_department(session, hq.id, "ADM", "Administration", "Administrative services")

        permission_map = sync_permissions(session)
        role_map = sync_roles(session, permission_map)

        create_or_update_user(
            session,
            username="superadmin",
            email="superadmin@hms.local",
            full_name="System Super Admin",
            password="Admin123!",
            branch_id=hq.id,
            department_id=admin.id,
            roles=[role_map["SUPER_ADMIN"]],
        )

        session.commit()
        print("Access-control seed completed.")
        print("Super admin: superadmin / Admin123!")
    finally:
        session.close()


if __name__ == "__main__":
    main()

