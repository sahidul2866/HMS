from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions
from app.modules.pharmacy.service import PharmacyService
from app.schemas.pharmacy import (
    PaginatedResponse,
    PharmacyInvestigationCreate,
    PharmacyInvestigationDraftRead,
    PharmacyInvestigationRead,
    PharmacyInvestigationSettingCreate,
    PharmacyInvestigationSettingRead,
    PharmacyInvestigationSettingUpdate,
    PharmacyInvestigationUpdate,
)

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


@router.get(
    "/settings",
    response_model=PaginatedResponse[PharmacyInvestigationSettingRead],
    dependencies=[Depends(require_any_permissions("laboratory.view", "radiology.view", "billing.invoice.create", "opd.view"))],
)
def list_diagnostic_settings(
    page: int = 1,
    page_size: int = 10,
    q: str | None = None,
    service_area: str | None = None,
    is_active: bool | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).list_investigation_settings(user, page=page, page_size=page_size, q=q, service_area=service_area, is_active=is_active)


@router.post(
    "/settings",
    response_model=PharmacyInvestigationSettingRead,
    dependencies=[Depends(require_any_permissions("laboratory.manage", "radiology.manage"))],
)
def create_diagnostic_setting(
    payload: PharmacyInvestigationSettingCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).create_investigation_setting(payload, user, context)


@router.get(
    "/settings/{entity_id}",
    response_model=PharmacyInvestigationSettingRead,
    dependencies=[Depends(require_any_permissions("laboratory.view", "radiology.view"))],
)
def get_diagnostic_setting(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_investigation_setting(entity_id, user)


@router.put(
    "/settings/{entity_id}",
    response_model=PharmacyInvestigationSettingRead,
    dependencies=[Depends(require_any_permissions("laboratory.manage", "radiology.manage"))],
)
def update_diagnostic_setting(
    entity_id: UUID,
    payload: PharmacyInvestigationSettingUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).update_investigation_setting(entity_id, payload, user, context)


@router.delete(
    "/settings/{entity_id}",
    dependencies=[Depends(require_any_permissions("laboratory.manage", "radiology.manage"))],
)
def delete_diagnostic_setting(
    entity_id: UUID,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    PharmacyService(db).delete_investigation_setting(entity_id, user, context)
    return {"success": True}


@router.get(
    "/orders",
    response_model=PaginatedResponse[PharmacyInvestigationRead],
    dependencies=[Depends(require_any_permissions("laboratory.view", "radiology.view"))],
)
def list_diagnostic_orders(
    page: int = 1,
    page_size: int = 10,
    q: str | None = None,
    status: str | None = None,
    service_area: str | None = None,
    customer_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).list_investigations(
        user,
        page=page,
        page_size=page_size,
        q=q,
        status=status,
        service_area=service_area,
        customer_id=customer_id,
        date_from=date.fromisoformat(date_from) if date_from else None,
        date_to=date.fromisoformat(date_to) if date_to else None,
    )


@router.post(
    "/orders",
    response_model=PharmacyInvestigationRead,
    dependencies=[Depends(require_any_permissions("laboratory.manage", "radiology.manage"))],
)
def create_diagnostic_order(
    payload: PharmacyInvestigationCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).create_investigation(payload, user, context)


@router.get(
    "/orders/{entity_id}",
    response_model=PharmacyInvestigationRead,
    dependencies=[Depends(require_any_permissions("laboratory.view", "radiology.view"))],
)
def get_diagnostic_order(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_investigation(entity_id, user)


@router.put(
    "/orders/{entity_id}",
    response_model=PharmacyInvestigationRead,
    dependencies=[Depends(require_any_permissions("laboratory.manage", "radiology.manage"))],
)
def update_diagnostic_order(
    entity_id: UUID,
    payload: PharmacyInvestigationUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).update_investigation(entity_id, payload, user, context)


@router.delete(
    "/orders/{entity_id}",
    dependencies=[Depends(require_any_permissions("laboratory.manage", "radiology.manage"))],
)
def delete_diagnostic_order(
    entity_id: UUID,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    PharmacyService(db).delete_investigation(entity_id, user, context)
    return {"success": True}


@router.get(
    "/drafts/opd-visit/{visit_id}",
    response_model=PharmacyInvestigationDraftRead,
    dependencies=[Depends(require_any_permissions("laboratory.view", "radiology.view"))],
)
def get_diagnostic_draft_for_visit(visit_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).build_investigation_draft_from_visit(visit_id, user)
