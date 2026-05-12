from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.queue.service import QueueService
from app.schemas.queue import (
    QueueCounterCreate,
    QueueCounterRead,
    QueueDisplayRead,
    QueueSettingRead,
    QueueSettingUpsert,
    QueueSummary,
    QueueTokenCreate,
    QueueTokenRead,
    QueueTokenStatusUpdate,
    QueueTransferRequest,
)

router = APIRouter(prefix="/queue", tags=["Queue Management"])


@router.get("/tokens", response_model=list[QueueTokenRead], dependencies=[Depends(require_permissions("queue.view"))])
def list_tokens(
    queue_scope: str | None = None,
    status: str | None = None,
    counter_id: UUID | None = None,
    department_name: str | None = None,
    doctor_user_id: UUID | None = None,
    token_date: date | None = None,
    search: str | None = None,
    limit: int = Query(default=80, ge=1, le=200),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QueueTokenRead]:
    return QueueService(db).list_tokens(
        user,
        queue_scope=queue_scope,
        status=status,
        counter_id=counter_id,
        department_name=department_name,
        doctor_user_id=doctor_user_id,
        token_date=token_date,
        search=search,
        limit=limit,
    )


@router.post("/tokens", response_model=QueueTokenRead, dependencies=[Depends(require_permissions("queue.counter.manage"))])
def create_token(payload: QueueTokenCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> QueueTokenRead:
    return QueueService(db)._read(QueueService(db).ensure_token(payload, user))


QUEUE_ACTION_PERMISSIONS = (
    "queue.call_next",
    "opd.queue.call",
    "billing.queue.manage",
    "pharmacy.queue.manage",
    "lab.queue.manage",
    "radiology.queue.manage",
    "blood_bank.queue.manage",
)


@router.post("/call-next", response_model=QueueTokenRead, dependencies=[Depends(require_any_permissions(*QUEUE_ACTION_PERMISSIONS))])
def call_next(
    queue_scope: str,
    counter_id: UUID | None = None,
    doctor_user_id: UUID | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueTokenRead:
    return QueueService(db).call_next(user, queue_scope=queue_scope, counter_id=counter_id, doctor_user_id=doctor_user_id)


@router.post("/tokens/{token_id}/status", response_model=QueueTokenRead, dependencies=[Depends(require_any_permissions(*QUEUE_ACTION_PERMISSIONS))])
def update_status(
    token_id: UUID,
    payload: QueueTokenStatusUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueTokenRead:
    return QueueService(db).update_status(token_id, payload.status, user, counter_id=payload.counter_id, notes=payload.notes)


@router.post("/tokens/{token_id}/transfer", response_model=QueueTokenRead, dependencies=[Depends(require_permissions("queue.transfer"))])
def transfer_token(
    token_id: UUID,
    payload: QueueTransferRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueTokenRead:
    return QueueService(db).transfer(token_id, payload, user)


@router.get("/counters", response_model=list[QueueCounterRead], dependencies=[Depends(require_permissions("queue.view"))])
def list_counters(module: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[QueueCounterRead]:
    return QueueService(db).list_counters(user, module)


@router.post("/counters", response_model=QueueCounterRead, dependencies=[Depends(require_permissions("queue.counter.manage"))])
def create_counter(payload: QueueCounterCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> QueueCounterRead:
    return QueueService(db).create_counter(payload, user)


@router.get("/summary", response_model=QueueSummary, dependencies=[Depends(require_permissions("queue.view"))])
def queue_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> QueueSummary:
    return QueueService(db).summary(user)


@router.get("/display/{scope}", response_model=QueueDisplayRead, dependencies=[Depends(require_permissions("queue.display.manage"))])
def queue_display(scope: str, user=Depends(get_current_user), db: Session = Depends(get_db)) -> QueueDisplayRead:
    return QueueService(db).display(user, scope)


@router.get("/settings", response_model=list[QueueSettingRead], dependencies=[Depends(require_permissions("queue.counter.manage"))])
def list_settings(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[QueueSettingRead]:
    return QueueService(db).list_settings(user)


@router.post("/settings", response_model=QueueSettingRead, dependencies=[Depends(require_permissions("queue.counter.manage"))])
def save_setting(payload: QueueSettingUpsert, user=Depends(get_current_user), db: Session = Depends(get_db)) -> QueueSettingRead:
    return QueueService(db).save_setting(payload, user)
