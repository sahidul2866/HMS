from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.er.service import ERService
from app.schemas.encounter import (
    ERVisitAmbulanceCreate,
    ERVisitAmbulanceRead,
    ERVisitAssignmentUpdate,
    ERVisitConvertToIPD,
    ERVisitCreate,
    ERVisitRead,
    ERVisitStatusUpdate,
    ERVisitTriageUpdate,
    ERVisitTreatmentUpdate,
    ERSummary,
)

router = APIRouter(prefix="/er", tags=["ER"])


@router.get("/visits", response_model=list[ERVisitRead], dependencies=[Depends(require_any_permissions("er.view", "emergency.view"))])
def list_er_visits(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[ERVisitRead]:
    return [ERVisitRead.model_validate(item, from_attributes=True) for item in ERService(db).list_visits(user)]


@router.get("/visits/{visit_id}", response_model=ERVisitRead, dependencies=[Depends(require_any_permissions("er.view", "emergency.view"))])
def get_er_visit(visit_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> ERVisitRead:
    visit = ERService(db).get_visit(visit_id, user)
    return ERVisitRead.model_validate(visit, from_attributes=True)


@router.get("/summary", response_model=ERSummary, dependencies=[Depends(require_any_permissions("er.view", "emergency.view"))])
def get_er_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> ERSummary:
    return ERService(db).get_summary(user)


@router.post("/visits", response_model=ERVisitRead, dependencies=[Depends(require_any_permissions("er.visit.manage", "emergency.register"))])
def create_er_visit(
    payload: ERVisitCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ERVisitRead:
    visit = ERService(db).create_visit(payload, user, context)
    return ERVisitRead.model_validate(visit, from_attributes=True)


@router.put("/visits/{visit_id}/triage", response_model=ERVisitRead, dependencies=[Depends(require_any_permissions("er.triage.manage", "emergency.triage", "emergency.retriage"))])
def triage_er_visit(
    visit_id: UUID,
    payload: ERVisitTriageUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ERVisitRead:
    visit = ERService(db).update_triage(visit_id, payload, user, context)
    return ERVisitRead.model_validate(visit, from_attributes=True)


@router.put("/visits/{visit_id}/assign", response_model=ERVisitRead, dependencies=[Depends(require_any_permissions("er.assignment.manage", "emergency.bed.assign"))])
def assign_er_visit(
    visit_id: UUID,
    payload: ERVisitAssignmentUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ERVisitRead:
    visit = ERService(db).assign_team(visit_id, payload, user, context)
    return ERVisitRead.model_validate(visit, from_attributes=True)


@router.put("/visits/{visit_id}/treatment", response_model=ERVisitRead, dependencies=[Depends(require_any_permissions("er.visit.manage", "emergency.assess", "emergency.order.create", "emergency.medication.administer"))])
def treat_er_visit(
    visit_id: UUID,
    payload: ERVisitTreatmentUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ERVisitRead:
    visit = ERService(db).update_treatment(visit_id, payload, user, context)
    return ERVisitRead.model_validate(visit, from_attributes=True)


@router.put("/visits/{visit_id}/status", response_model=ERVisitRead, dependencies=[Depends(require_any_permissions("er.visit.manage", "emergency.status.update", "emergency.disposition"))])
def update_er_visit_status(
    visit_id: UUID,
    payload: ERVisitStatusUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ERVisitRead:
    visit = ERService(db).update_status(visit_id, payload, user, context)
    return ERVisitRead.model_validate(visit, from_attributes=True)


@router.post("/visits/{visit_id}/ambulance", response_model=ERVisitAmbulanceRead, dependencies=[Depends(require_any_permissions("er.ambulance.manage", "emergency.transfer"))])
def create_er_ambulance(
    visit_id: UUID,
    payload: ERVisitAmbulanceCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ERVisitAmbulanceRead:
    record = ERService(db).create_ambulance_record(visit_id, payload, user, context)
    return ERVisitAmbulanceRead.model_validate(record, from_attributes=True)


@router.post("/visits/{visit_id}/convert-to-ipd", response_model=ERVisitRead, dependencies=[Depends(require_permissions("ipd.admit"))])
def convert_er_to_ipd(
    visit_id: UUID,
    payload: ERVisitConvertToIPD,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ERVisitRead:
    visit = ERService(db).convert_to_ipd(visit_id, payload, user, context)
    return ERVisitRead.model_validate(visit, from_attributes=True)
