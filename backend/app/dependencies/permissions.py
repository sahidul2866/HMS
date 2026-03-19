from collections.abc import Callable

from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppException
from app.dependencies.auth import get_current_user
from app.modules.auth.service import AuthService


def require_permissions(*permission_codes: str) -> Callable:
    def dependency(user=Depends(get_current_user), db: Session = Depends(get_db)):
        effective_permissions = AuthService(db).get_effective_permissions(user)
        missing = [code for code in permission_codes if code not in effective_permissions]
        if missing:
            raise AppException(status.HTTP_403_FORBIDDEN, "forbidden", f"Missing permissions: {', '.join(missing)}")
        return user

    return dependency


def require_any_permissions(*permission_codes: str) -> Callable:
    def dependency(user=Depends(get_current_user), db: Session = Depends(get_db)):
        effective_permissions = set(AuthService(db).get_effective_permissions(user))
        if not any(code in effective_permissions for code in permission_codes):
            raise AppException(
                status.HTTP_403_FORBIDDEN,
                "forbidden",
                f"Requires any of: {', '.join(permission_codes)}",
            )
        return user

    return dependency
