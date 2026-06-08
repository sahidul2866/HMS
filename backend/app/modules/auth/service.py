from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.core.exceptions import AppException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token_safe,
    generate_session_id,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.patient import Patient
from app.models.role import Role
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.auth.repository import AuthRepository
from app.schemas.auth import LoginResponse, PasswordResetRequest, TokenPair
from app.schemas.auth import PatientRegisterRequest
from app.schemas.user import CurrentUserRead, UserRead
from app.utils.enums import AuditAction
from app.utils.phone import normalize_phone


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuthRepository(db)

    def get_effective_permissions(self, user: User) -> list[str]:
        permissions = {permission.code for permission in user.direct_permissions if permission.is_active}
        for role in user.roles:
            if role.is_active:
                permissions.update(permission.code for permission in role.permissions if permission.is_active)
        return sorted(permissions)

    def to_current_user(self, user: User) -> CurrentUserRead:
        base_payload = UserRead.model_validate(user, from_attributes=True)
        return CurrentUserRead(**base_payload.model_dump(), effective_permissions=self.get_effective_permissions(user))

    def _build_login_response(
        self,
        user: User,
        access_token: str,
        refresh_token: str,
        access_expires_at,
        refresh_expires_at,
    ) -> LoginResponse:
        return LoginResponse(
            user=self.to_current_user(user),
            tokens=TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                access_token_expires_at=access_expires_at,
                refresh_token_expires_at=refresh_expires_at,
            ),
        )

    def get_user_from_access_payload(self, payload: dict) -> User | None:
        subject = payload.get("sub")
        if not subject:
            return None
        return self.repository.get_user_by_id(subject)

    def login(self, username_or_email: str, password: str, context: dict[str, str | None]) -> LoginResponse:
        user = self.repository.find_user_for_login(username_or_email)
        if not user or not verify_password(password, user.hashed_password):
            raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials", "Invalid username/email or password")

        permissions = self.get_effective_permissions(user)
        access_token, access_expires_at = create_access_token(str(user.id), permissions)
        session_id = generate_session_id()
        refresh_token, refresh_expires_at, refresh_jti = create_refresh_token(str(user.id), session_id)

        self.repository.create_refresh_token(
            RefreshToken(
                user_id=user.id,
                session_id=session_id,
                token_hash=hash_token(refresh_token),
                token_jti=refresh_jti,
                expires_at=refresh_expires_at,
                user_agent=context.get("user_agent"),
                ip_address=context.get("ip_address"),
            )
        )
        user.last_login_at = datetime.now(UTC)
        AuditService(self.db).log(
            user_id=user.id,
            action=AuditAction.LOGIN,
            module="auth",
            entity_type="user",
            entity_id=str(user.id),
            detail={"username": user.username},
            context=context,
        )
        self.db.commit()
        self.db.refresh(user)
        return self._build_login_response(user, access_token, refresh_token, access_expires_at, refresh_expires_at)

    def reset_password(self, user: User, payload: PasswordResetRequest, context: dict[str, str | None]) -> None:
        if not verify_password(payload.current_password, user.hashed_password):
            raise AppException(status.HTTP_400_BAD_REQUEST, "invalid_current_password", "Current password is incorrect")
        user.hashed_password = get_password_hash(payload.new_password)
        user.must_reset_password = False
        user.updated_by = user.id
        AuditService(self.db).log(
            user_id=user.id,
            action="auth.password.reset",
            module="auth",
            entity_type="user",
            entity_id=str(user.id),
            detail={"username": user.username},
            context=context,
        )
        self.db.commit()

    def refresh(self, refresh_token: str, context: dict[str, str | None]) -> LoginResponse:
        payload = decode_token_safe(refresh_token)
        if not payload or payload.get("type") != "refresh" or not payload.get("sub") or not payload.get("sid") or not payload.get("jti"):
            raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_refresh_token", "Invalid refresh token")

        persisted = self.repository.find_valid_refresh_token(hash_token(refresh_token))
        if (
            not persisted
            or str(persisted.user_id) != payload.get("sub")
            or persisted.session_id != payload.get("sid")
            or persisted.token_jti != payload.get("jti")
        ):
            if payload.get("sid"):
                self.repository.revoke_session(payload["sid"])
                self.db.commit()
            raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_refresh_token", "Refresh token is invalid or revoked")

        self.repository.revoke_refresh_token(persisted)
        user = persisted.user
        if not user.is_active:
            self.repository.revoke_session(persisted.session_id)
            self.db.commit()
            raise AppException(status.HTTP_401_UNAUTHORIZED, "inactive_user", "User account is inactive")
        permissions = self.get_effective_permissions(user)
        access_token, access_expires_at = create_access_token(str(user.id), permissions)
        new_refresh_token, refresh_expires_at, refresh_jti = create_refresh_token(str(user.id), persisted.session_id)
        self.repository.create_refresh_token(
            RefreshToken(
                user_id=user.id,
                session_id=persisted.session_id,
                token_hash=hash_token(new_refresh_token),
                token_jti=refresh_jti,
                expires_at=refresh_expires_at,
                user_agent=context.get("user_agent"),
                ip_address=context.get("ip_address"),
            )
        )
        AuditService(self.db).log(
            user_id=user.id,
            action="auth.refresh",
            module="auth",
            entity_type="user",
            entity_id=str(user.id),
            detail={"session_id": persisted.session_id},
            context=context,
        )
        self.db.commit()
        return self._build_login_response(user, access_token, new_refresh_token, access_expires_at, refresh_expires_at)

    def logout(self, user: User | None, refresh_token: str | None, context: dict[str, str | None]) -> None:
        if refresh_token:
            persisted = self.repository.find_valid_refresh_token(hash_token(refresh_token))
            if persisted:
                self.repository.revoke_session(persisted.session_id)
        if user:
            AuditService(self.db).log(
                user_id=user.id,
                action=AuditAction.LOGOUT,
                module="auth",
                entity_type="user",
                entity_id=str(user.id),
                detail={"username": user.username},
                context=context,
            )
        self.db.commit()

    def register_patient(self, payload: PatientRegisterRequest, context: dict[str, str | None]) -> LoginResponse:
        existing = self.repository.find_user_for_login(payload.username) or self.repository.find_user_for_login(payload.email)
        if existing:
            raise AppException(status.HTTP_409_CONFLICT, "user_exists", "User with same username or email already exists")

        patient_role = self.db.scalar(select(Role).where(Role.code == "PATIENT"))
        if not patient_role:
            raise AppException(status.HTTP_500_INTERNAL_SERVER_ERROR, "patient_role_missing", "Patient role is not configured")

        branch = self.db.scalar(select(Branch).where(Branch.code == "HQ"))
        normalized_phone = normalize_phone(payload.phone)
        patient = Patient(
            branch_id=branch.id if branch else None,
            patient_number=f"PAT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            first_name=payload.full_name.split(" ", 1)[0],
            last_name=payload.full_name.split(" ", 1)[1] if " " in payload.full_name else "Patient",
            phone=normalized_phone,
            email=payload.email,
            gender=payload.gender,
            date_of_birth=payload.date_of_birth,
            address=payload.address,
            emergency_contact_name=payload.emergency_contact_name,
            emergency_contact_phone=payload.emergency_contact_phone,
        )
        self.db.add(patient)
        self.db.flush()
        user = User(
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=get_password_hash(payload.password),
            branch_id=patient.branch_id,
            patient_id=patient.id,
            is_active=True,
        )
        user.roles = [patient_role]
        self.db.add(user)
        self.db.flush()
        permissions = self.get_effective_permissions(user)
        access_token, access_expires_at = create_access_token(str(user.id), permissions)
        session_id = generate_session_id()
        refresh_token, refresh_expires_at, refresh_jti = create_refresh_token(str(user.id), session_id)
        self.repository.create_refresh_token(
            RefreshToken(
                user_id=user.id,
                session_id=session_id,
                token_hash=hash_token(refresh_token),
                token_jti=refresh_jti,
                expires_at=refresh_expires_at,
                user_agent=context.get("user_agent"),
                ip_address=context.get("ip_address"),
            )
        )
        user.last_login_at = datetime.now(UTC)
        AuditService(self.db).log(
            user_id=user.id,
            action=AuditAction.PATIENT_CREATE,
            module="portal",
            entity_type="patient_user",
            entity_id=str(user.id),
            detail={"username": user.username, "patient_number": patient.patient_number},
            context=context,
        )
        self.db.commit()
        self.db.refresh(user)
        return self._build_login_response(user, access_token, refresh_token, access_expires_at, refresh_expires_at)
