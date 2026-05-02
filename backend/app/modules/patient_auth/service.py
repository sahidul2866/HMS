from __future__ import annotations

from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token_safe,
    generate_session_id,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.models.branch import Branch
from app.models.patient import Patient
from app.models.patient_portal_account import PatientPortalAccount, PatientPortalRefreshToken
from app.schemas.auth import PatientLoginResponse, PatientPortalAccountRead, PatientRegisterRequest, TokenPair
from app.utils.phone import normalize_phone

PATIENT_PORTAL_PERMISSIONS = ["patient.portal.view", "appointment.view", "appointment.book"]


class PatientAuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def login(self, username_or_email: str, password: str, context: dict[str, str | None]) -> PatientLoginResponse:
        account = self.find_account_for_login(username_or_email)
        if not account or not verify_password(password, account.hashed_password):
            raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials", "Invalid patient username/email or password")
        account.last_login_at = datetime.now(UTC)
        response = self._issue_tokens(account, context)
        self.db.commit()
        return response

    def register(self, payload: PatientRegisterRequest, context: dict[str, str | None]) -> PatientLoginResponse:
        if self.find_account_for_login(payload.username) or self.find_account_for_login(payload.email):
            raise AppException(status.HTTP_409_CONFLICT, "patient_account_exists", "Patient portal account already exists")
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
        account = PatientPortalAccount(
            branch_id=patient.branch_id,
            patient_id=patient.id,
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            phone=normalized_phone,
            hashed_password=get_password_hash(payload.password),
            is_active=True,
            created_by=None,
            updated_by=None,
        )
        self.db.add(account)
        self.db.flush()
        response = self._issue_tokens(account, context)
        self.db.commit()
        return response

    def refresh(self, refresh_token: str, context: dict[str, str | None]) -> PatientLoginResponse:
        payload = decode_token_safe(refresh_token)
        if not payload or payload.get("type") != "refresh" or payload.get("principal_type") != "patient":
            raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_refresh_token", "Invalid patient refresh token")
        persisted = self.find_valid_refresh_token(hash_token(refresh_token))
        if (
            not persisted
            or str(persisted.account_id) != payload.get("sub")
            or persisted.session_id != payload.get("sid")
            or persisted.token_jti != payload.get("jti")
        ):
            if payload.get("sid"):
                self.revoke_session(payload["sid"])
                self.db.commit()
            raise AppException(status.HTTP_401_UNAUTHORIZED, "invalid_refresh_token", "Patient refresh token is invalid or revoked")
        persisted.revoked_at = datetime.now(UTC)
        account = persisted.account
        if not account.is_active:
            self.revoke_session(persisted.session_id)
            self.db.commit()
            raise AppException(status.HTTP_401_UNAUTHORIZED, "inactive_patient_account", "Patient portal account is inactive")
        response = self._issue_tokens(account, context, session_id=persisted.session_id)
        self.db.commit()
        return response

    def logout(self, refresh_token: str | None) -> None:
        if refresh_token:
            persisted = self.find_valid_refresh_token(hash_token(refresh_token))
            if persisted:
                self.revoke_session(persisted.session_id)
        self.db.commit()

    def find_account_for_login(self, username_or_email: str) -> PatientPortalAccount | None:
        stmt = (
            select(PatientPortalAccount)
            .options(joinedload(PatientPortalAccount.patient))
            .where(
                or_(PatientPortalAccount.username == username_or_email, PatientPortalAccount.email == username_or_email),
                PatientPortalAccount.is_active.is_(True),
            )
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def first_active_demo_account(self) -> PatientPortalAccount | None:
        stmt = (
            select(PatientPortalAccount)
            .options(joinedload(PatientPortalAccount.patient))
            .where(PatientPortalAccount.is_active.is_(True))
            .order_by(PatientPortalAccount.created_at.asc())
        )
        return self.db.execute(stmt).unique().scalars().first()

    def get_account_from_access_payload(self, payload: dict) -> PatientPortalAccount | None:
        subject = payload.get("sub")
        if not subject:
            return None
        return self.db.scalar(
            select(PatientPortalAccount)
            .options(joinedload(PatientPortalAccount.patient))
            .where(PatientPortalAccount.id == subject, PatientPortalAccount.is_active.is_(True))
        )

    def find_valid_refresh_token(self, token_hash: str) -> PatientPortalRefreshToken | None:
        stmt = (
            select(PatientPortalRefreshToken)
            .options(joinedload(PatientPortalRefreshToken.account).joinedload(PatientPortalAccount.patient))
            .where(
                PatientPortalRefreshToken.token_hash == token_hash,
                PatientPortalRefreshToken.revoked_at.is_(None),
                PatientPortalRefreshToken.expires_at > datetime.now(UTC),
                PatientPortalRefreshToken.is_active.is_(True),
            )
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def revoke_session(self, session_id: str) -> None:
        stmt = select(PatientPortalRefreshToken).where(PatientPortalRefreshToken.session_id == session_id, PatientPortalRefreshToken.revoked_at.is_(None))
        for token in self.db.scalars(stmt):
            token.revoked_at = datetime.now(UTC)
        self.db.flush()

    def _issue_tokens(self, account: PatientPortalAccount, context: dict[str, str | None], session_id: str | None = None) -> PatientLoginResponse:
        session_id = session_id or generate_session_id()
        access_token, access_expires_at = create_access_token(str(account.id), PATIENT_PORTAL_PERMISSIONS, principal_type="patient")
        refresh_token, refresh_expires_at, refresh_jti = create_refresh_token(str(account.id), session_id, principal_type="patient")
        self.db.add(
            PatientPortalRefreshToken(
                account_id=account.id,
                session_id=session_id,
                token_hash=hash_token(refresh_token),
                token_jti=refresh_jti,
                expires_at=refresh_expires_at,
                user_agent=context.get("user_agent"),
                ip_address=context.get("ip_address"),
            )
        )
        self.db.flush()
        return PatientLoginResponse(
            user=self.to_current_patient(account),
            tokens=TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                access_token_expires_at=access_expires_at,
                refresh_token_expires_at=refresh_expires_at,
            ),
        )

    def to_current_patient(self, account: PatientPortalAccount) -> PatientPortalAccountRead:
        return PatientPortalAccountRead(
            id=str(account.id),
            username=account.username,
            email=account.email,
            full_name=account.full_name,
            branch_id=str(account.branch_id) if account.branch_id else None,
            patient_id=str(account.patient_id),
            is_active=account.is_active,
            last_login_at=account.last_login_at,
            effective_permissions=PATIENT_PORTAL_PERMISSIONS,
        )
