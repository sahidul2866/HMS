from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import get_password_hash
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.users.repository import UsersRepository
from app.schemas.user import UserCreate, UserOPDSettingsUpdate
from app.utils.enums import AuditAction


class UsersService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = UsersRepository(db)

    def list_users(self) -> list[User]:
        return self.repository.list_users()

    def list_doctors(self, *, referral_only: bool = False) -> list[User]:
        return self.repository.list_doctors(referral_only=referral_only)

    def create_user(self, payload: UserCreate, actor_id, context: dict[str, str | None]) -> User:
        existing = [user for user in self.repository.list_users() if user.username == payload.username or user.email == payload.email]
        if existing:
            raise AppException(409, "user_exists", "User with same username or email already exists")

        roles = self.repository.get_roles(payload.role_codes)
        if payload.patient_id or any(role.code == "PATIENT" for role in roles):
            raise AppException(400, "patient_accounts_separated", "Patient portal accounts must be created from patient registration, not staff user management")
        permissions = self.repository.get_permissions(payload.direct_permission_codes)
        user = User(
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=get_password_hash(payload.password),
            branch_id=payload.branch_id,
            department_id=payload.department_id,
            patient_id=payload.patient_id,
            is_active=payload.is_active,
            opd_consultation_fee=payload.opd_consultation_fee,
            opd_follow_up_fee=payload.opd_follow_up_fee,
            opd_follow_up_days=payload.opd_follow_up_days,
            opd_prescription_header_name=payload.opd_prescription_header_name,
            opd_prescription_header_degrees=payload.opd_prescription_header_degrees,
            opd_prescription_header_specialty=payload.opd_prescription_header_specialty,
            opd_prescription_header_workplace=payload.opd_prescription_header_workplace,
            opd_prescription_header_chamber=payload.opd_prescription_header_chamber,
            opd_prescription_header_phone=payload.opd_prescription_header_phone,
            opd_prescription_header_address=payload.opd_prescription_header_address,
            created_by=actor_id,
            updated_by=actor_id,
        )
        user.roles = roles
        user.direct_permissions = permissions
        self.repository.create_user(user)
        AuditService(self.db).log(
            user_id=actor_id,
            action=AuditAction.USER_CREATE,
            module="admin",
            entity_type="user",
            entity_id=str(user.id),
            detail={"username": user.username, "roles": [role.code for role in roles]},
            context=context,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_opd_settings(self, user_id, payload: UserOPDSettingsUpdate, actor_id, context: dict[str, str | None]) -> User:
        user = self.repository.get_user(user_id)
        if not user:
            raise AppException(404, "user_not_found", "User not found")

        user.opd_consultation_fee = payload.opd_consultation_fee
        user.opd_follow_up_fee = payload.opd_follow_up_fee
        user.opd_follow_up_days = payload.opd_follow_up_days
        user.opd_prescription_header_name = payload.opd_prescription_header_name
        user.opd_prescription_header_degrees = payload.opd_prescription_header_degrees
        user.opd_prescription_header_specialty = payload.opd_prescription_header_specialty
        user.opd_prescription_header_workplace = payload.opd_prescription_header_workplace
        user.opd_prescription_header_chamber = payload.opd_prescription_header_chamber
        user.opd_prescription_header_phone = payload.opd_prescription_header_phone
        user.opd_prescription_header_address = payload.opd_prescription_header_address
        user.updated_by = actor_id
        AuditService(self.db).log(
            user_id=actor_id,
            action=AuditAction.USER_UPDATE,
            module="admin",
            entity_type="user",
            entity_id=str(user.id),
            detail={
                "username": user.username,
                "opd_consultation_fee": str(payload.opd_consultation_fee),
                "opd_follow_up_fee": str(payload.opd_follow_up_fee),
                "opd_follow_up_days": payload.opd_follow_up_days,
                "opd_prescription_header_name": payload.opd_prescription_header_name,
                "opd_prescription_header_chamber": payload.opd_prescription_header_chamber,
            },
            context=context,
        )
        self.db.commit()
        self.db.refresh(user)
        return user
