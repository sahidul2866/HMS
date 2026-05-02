from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import decode_token
from app.modules.auth.service import AuthService
from app.modules.patient_auth.service import PatientAuthService

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
    if payload.get("principal_type", "user") != "user":
        raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Token is not a staff access token")

    user = AuthService(db).get_user_from_access_payload(payload)
    if not user:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "user_not_found", "Authenticated user does not exist")
    return user


def get_current_patient_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Authentication credentials were not provided")
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid access token") from exc
    if payload.get("type") != "access" or payload.get("principal_type") != "patient":
        raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Token is not a patient portal access token")
    account = PatientAuthService(db).get_account_from_access_payload(payload)
    if not account:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "patient_account_not_found", "Patient portal account does not exist")
    return account


def get_current_patient_account_or_superadmin_demo(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Authentication credentials were not provided")
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid access token") from exc
    if payload.get("type") != "access":
        raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Token is not an access token")
    if payload.get("principal_type") == "patient":
        account = PatientAuthService(db).get_account_from_access_payload(payload)
        if not account:
            raise AppException(status.HTTP_401_UNAUTHORIZED, "patient_account_not_found", "Patient portal account does not exist")
        return account
    if payload.get("principal_type", "user") == "user":
        user = AuthService(db).get_user_from_access_payload(payload)
        if not user:
            raise AppException(status.HTTP_401_UNAUTHORIZED, "user_not_found", "Authenticated user does not exist")
        is_super_admin = any(role.code == "SUPER_ADMIN" for role in user.roles)
        if not is_super_admin:
            raise AppException(status.HTTP_403_FORBIDDEN, "patient_account_required", "Patient portal access requires a patient account")
        account = PatientAuthService(db).first_active_demo_account()
        if not account:
            raise AppException(status.HTTP_404_NOT_FOUND, "patient_demo_account_missing", "No patient portal account is available for Super Admin preview")
        return account
    raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Unsupported token principal")


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
