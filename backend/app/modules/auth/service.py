from datetime import UTC, datetime

from fastapi import status
from sqlalchemy.orm import Session

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
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.auth.repository import AuthRepository
from app.schemas.auth import LoginResponse, TokenPair
from app.schemas.user import CurrentUserRead
from app.utils.enums import AuditAction


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
        payload = CurrentUserRead.model_validate(user, from_attributes=True)
        return payload.model_copy(update={"effective_permissions": self.get_effective_permissions(user)})

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
