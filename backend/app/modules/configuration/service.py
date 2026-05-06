from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.configuration import ConfigurationProfile
from app.models.user import User
from app.modules.auth.service import AuthService
from app.schemas.configuration import ConfigurationProfileCreate, ConfigurationProfileRead, ConfigurationProfileUpdate, ConfigurationWorkspaceRead

OPD_PROFILE_TYPES = {"doctor_share", "prescription_suggestion", "prescription_layout"}


class ConfigurationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def workspace(self, actor: User) -> ConfigurationWorkspaceRead:
        profiles = self.list_profiles(actor)
        counts = Counter(item.profile_type for item in profiles)
        return ConfigurationWorkspaceRead(
            profiles=profiles,
            counts=dict(counts),
            demo_points=[
                "OPD consultation share can be configured from the OPD module by doctor, department, visit type, corporate, and follow-up rules.",
                "Prescription templates help doctors add favorites, advice, investigations, dosage, and follow-up instructions faster.",
                "Print builders keep prescription and invoice branding configurable without code changes.",
            ],
        )

    def list_profiles(self, actor: User, profile_type: str | None = None) -> list[ConfigurationProfileRead]:
        allowed_types = self._allowed_profile_types(actor)
        if profile_type and allowed_types is not None and profile_type not in allowed_types:
            raise AppException(403, "forbidden", "This configuration area is not available for your role")
        stmt = select(ConfigurationProfile).where(ConfigurationProfile.is_active.is_(True)).order_by(
            ConfigurationProfile.profile_type.asc(),
            ConfigurationProfile.is_default.desc(),
            ConfigurationProfile.name.asc(),
        )
        if allowed_types is not None:
            stmt = stmt.where(ConfigurationProfile.profile_type.in_(allowed_types))
        if actor.branch_id:
            stmt = stmt.where((ConfigurationProfile.branch_id == actor.branch_id) | (ConfigurationProfile.branch_id.is_(None)))
        if profile_type:
            stmt = stmt.where(ConfigurationProfile.profile_type == profile_type)
        return [ConfigurationProfileRead.model_validate(item) for item in self.db.scalars(stmt)]

    def create_profile(self, payload: ConfigurationProfileCreate, actor: User) -> ConfigurationProfileRead:
        self._assert_profile_type_allowed(actor, payload.profile_type)
        existing = self.db.scalar(
            select(ConfigurationProfile).where(
                ConfigurationProfile.branch_id == actor.branch_id,
                ConfigurationProfile.profile_type == payload.profile_type,
                ConfigurationProfile.code == payload.code,
            )
        )
        if existing:
            raise AppException(409, "configuration_duplicate", "A configuration profile with this code already exists")
        item = ConfigurationProfile(branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id, **payload.model_dump())
        if item.is_default:
            self._clear_default(actor, item.profile_type)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return ConfigurationProfileRead.model_validate(item)

    def update_profile(self, profile_id, payload: ConfigurationProfileUpdate, actor: User) -> ConfigurationProfileRead:
        item = self.db.get(ConfigurationProfile, profile_id)
        if not item or not item.is_active:
            raise AppException(404, "configuration_not_found", "Configuration profile not found")
        self._assert_profile_type_allowed(actor, item.profile_type)
        if actor.branch_id and item.branch_id and actor.branch_id != item.branch_id:
            raise AppException(403, "forbidden", "Configuration profile belongs to a different branch")
        if payload.is_default:
            self._clear_default(actor, item.profile_type, exclude_id=item.id)
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        item.updated_by = actor.id
        self.db.commit()
        self.db.refresh(item)
        return ConfigurationProfileRead.model_validate(item)

    def delete_profile(self, profile_id, actor: User) -> None:
        item = self.db.get(ConfigurationProfile, profile_id)
        if not item or not item.is_active:
            raise AppException(404, "configuration_not_found", "Configuration profile not found")
        self._assert_profile_type_allowed(actor, item.profile_type)
        if actor.branch_id and item.branch_id and actor.branch_id != item.branch_id:
            raise AppException(403, "forbidden", "Configuration profile belongs to a different branch")
        item.is_active = False
        item.updated_by = actor.id
        self.db.commit()

    def _clear_default(self, actor: User, profile_type: str, exclude_id=None) -> None:
        stmt = select(ConfigurationProfile).where(ConfigurationProfile.profile_type == profile_type, ConfigurationProfile.is_default.is_(True))
        if actor.branch_id:
            stmt = stmt.where(ConfigurationProfile.branch_id == actor.branch_id)
        for item in self.db.scalars(stmt):
            if exclude_id and item.id == exclude_id:
                continue
            item.is_default = False
            item.updated_by = actor.id

    def _allowed_profile_types(self, actor: User) -> set[str] | None:
        permissions = set(AuthService(self.db).get_effective_permissions(actor))
        if "settings.configuration.manage" in permissions:
            return None
        if "opd.settings.manage" in permissions:
            return OPD_PROFILE_TYPES
        return set()

    def _assert_profile_type_allowed(self, actor: User, profile_type: str) -> None:
        allowed_types = self._allowed_profile_types(actor)
        if allowed_types is not None and profile_type not in allowed_types:
            raise AppException(403, "forbidden", "This configuration area is not available for your role")
