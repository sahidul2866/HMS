from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permissions
from app.modules.configuration.service import ConfigurationService
from app.schemas.configuration import ConfigurationProfileCreate, ConfigurationProfileRead, ConfigurationProfileUpdate, ConfigurationWorkspaceRead

router = APIRouter(prefix="/configuration", tags=["configuration"])


@router.get("/workspace", response_model=ConfigurationWorkspaceRead, dependencies=[Depends(require_permissions("settings.configuration.manage"))])
def get_workspace(user=Depends(get_current_user), db: Session = Depends(get_db)) -> ConfigurationWorkspaceRead:
    return ConfigurationService(db).workspace(user)


@router.get("/profiles", response_model=list[ConfigurationProfileRead], dependencies=[Depends(require_permissions("settings.configuration.manage"))])
def list_profiles(
    profile_type: str | None = Query(default=None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConfigurationProfileRead]:
    return ConfigurationService(db).list_profiles(user, profile_type=profile_type)


@router.post("/profiles", response_model=ConfigurationProfileRead, dependencies=[Depends(require_permissions("settings.configuration.manage"))])
def create_profile(payload: ConfigurationProfileCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> ConfigurationProfileRead:
    return ConfigurationService(db).create_profile(payload, user)


@router.put("/profiles/{profile_id}", response_model=ConfigurationProfileRead, dependencies=[Depends(require_permissions("settings.configuration.manage"))])
def update_profile(profile_id: str, payload: ConfigurationProfileUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> ConfigurationProfileRead:
    return ConfigurationService(db).update_profile(profile_id, payload, user)


@router.delete("/profiles/{profile_id}", dependencies=[Depends(require_permissions("settings.configuration.manage"))])
def delete_profile(profile_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, bool]:
    ConfigurationService(db).delete_profile(profile_id, user)
    return {"success": True}
