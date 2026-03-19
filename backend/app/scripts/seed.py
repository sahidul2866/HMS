from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.branch import Branch
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.utils.seed_data import PERMISSION_CATALOG, ROLE_CATALOG


def seed() -> None:
    db = SessionLocal()
    try:
        branch = db.scalar(select(Branch).where(Branch.code == "HQ"))
        if not branch:
            branch = Branch(code="HQ", name="Headquarters", description="Default branch", address="Dhaka")
            db.add(branch)
            db.flush()

        permission_map: dict[str, Permission] = {}
        for code, module, action, description in PERMISSION_CATALOG:
            permission = db.scalar(select(Permission).where(Permission.code == code))
            if not permission:
                permission = Permission(code=code, module=module, action=action, description=description)
                db.add(permission)
                db.flush()
            permission_map[code] = permission

        role_map: dict[str, Role] = {}
        for code, permission_codes in ROLE_CATALOG.items():
            role = db.scalar(select(Role).where(Role.code == code))
            if not role:
                role = Role(code=code, name=code.replace("_", " ").title(), description=f"{code.title()} role")
                db.add(role)
                db.flush()
            role.permissions = [permission_map[item] for item in permission_codes]
            role_map[code] = role

        admin = db.scalar(select(User).where(User.username == "superadmin"))
        if not admin:
            admin = User(
                username="superadmin",
                email="superadmin@hms.local",
                full_name="System Super Admin",
                hashed_password=get_password_hash("Admin123!"),
                branch_id=branch.id,
            )
            admin.roles = [role_map["SUPER_ADMIN"]]
            db.add(admin)

        db.commit()
        print("Seed completed. Default user: superadmin / Admin123!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

