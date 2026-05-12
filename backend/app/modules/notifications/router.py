from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permissions
from app.modules.notifications.service import NotificationsService
from app.schemas.notification import (
    NotificationListResponse,
    NotificationRead,
    NotificationSettingRead,
    NotificationSettingUpsert,
    NotificationStatusUpdate,
    NotificationSummary,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/summary", response_model=NotificationSummary, dependencies=[Depends(require_permissions("notification.view"))])
def notification_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> NotificationSummary:
    return NotificationsService(db).summary(user)


@router.get("", response_model=NotificationListResponse, dependencies=[Depends(require_permissions("notification.view"))])
def list_notifications(
    status: str | None = None,
    priority: str | None = None,
    module: str | None = None,
    category: str | None = None,
    assigned_to_me: bool = False,
    due_today: bool = False,
    overdue: bool = False,
    search: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    items, total, unread, action_required, critical = NotificationsService(db).list_notifications(
        user,
        status=status,
        priority=priority,
        module=module,
        category=category,
        assigned_to_me=assigned_to_me,
        due_today=due_today,
        overdue=overdue,
        search=search,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(
        items=items,
        latest=items[:8],
        total=total,
        unread_count=unread,
        action_required_count=action_required,
        critical_count=critical,
    )


@router.post("/{notification_id}/status", response_model=NotificationRead, dependencies=[Depends(require_permissions("notification.view"))])
def update_notification_status(
    notification_id: UUID,
    payload: NotificationStatusUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationRead:
    return NotificationsService(db).update_status(notification_id, payload.status, user)


@router.post("/mark-all-read", dependencies=[Depends(require_permissions("notification.view"))])
def mark_all_read(user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, int]:
    return {"updated": NotificationsService(db).mark_all_read(user)}


@router.get("/settings", response_model=list[NotificationSettingRead], dependencies=[Depends(require_permissions("notification.configure"))])
def list_settings(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[NotificationSettingRead]:
    return NotificationsService(db).list_settings(user)


@router.post("/settings", response_model=NotificationSettingRead, dependencies=[Depends(require_permissions("notification.configure"))])
def save_setting(
    payload: NotificationSettingUpsert,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationSettingRead:
    return NotificationsService(db).save_setting(payload, user)
