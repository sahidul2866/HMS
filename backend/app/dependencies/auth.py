from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import decode_token
from app.modules.auth.service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def _resolve_user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    db: Session,
):
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid access token") from exc

    if payload.get("type") != "access":
        raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Token is not an access token")

    user = AuthService(db).get_user_from_access_payload(payload)
    if not user:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "user_not_found", "Authenticated user does not exist")
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    user = _resolve_user_from_credentials(credentials, db)
    if not user:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Authentication credentials were not provided")
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    return _resolve_user_from_credentials(credentials, db)


def get_request_context(request: Request) -> dict[str, str | None]:
    return {"ip_address": request.client.host if request.client else None, "user_agent": request.headers.get("user-agent")}
