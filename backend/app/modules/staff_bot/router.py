from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permissions
from app.modules.staff_bot.service import StaffBotService
from app.schemas.staff_bot import StaffBotMessageCreate, StaffBotResetCreate, StaffBotResponse, StaffBotSettingsRead

router = APIRouter(prefix="/staff-bot", tags=["Staff Assistant"])


@router.get("/settings", response_model=StaffBotSettingsRead, dependencies=[Depends(require_permissions("dashboard.view"))])
def staff_bot_settings(user=Depends(get_current_user), db: Session = Depends(get_db)) -> StaffBotSettingsRead:
    return StaffBotService(db).settings(user)


@router.post("/message", response_model=StaffBotResponse, dependencies=[Depends(require_permissions("dashboard.view"))])
def staff_bot_message(payload: StaffBotMessageCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> StaffBotResponse:
    return StaffBotService(db).handle_message(payload, user)


@router.post("/reset", response_model=StaffBotResponse, dependencies=[Depends(require_permissions("dashboard.view"))])
def staff_bot_reset(payload: StaffBotResetCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> StaffBotResponse:
    return StaffBotService(db).reset(payload, user)

