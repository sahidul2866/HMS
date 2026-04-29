from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permissions
from app.modules.ot.service import OTService, serialize_booking, serialize_schedule
from app.schemas.ot import (
    AnesthesiaRecordUpdate,
    OTBillingItemCreate,
    OTBookingCreate,
    OTBookingRead,
    OTCaseSheetRead,
    OTConsumableUsageCreate,
    OTDashboardRead,
    OTDocumentCreate,
    OTEquipmentUsageCreate,
    OTRoomCreate,
    OTRoomRead,
    OTStatusUpdate,
    PostOpRecoveryUpdate,
    PreOpChecklistUpdate,
    SurgeryNoteUpdate,
    SurgeryScheduleCreate,
    SurgeryScheduleRead,
    TeamAssignmentCreate,
)

router = APIRouter(prefix="/ot", tags=["OT Management"])


@router.get("/dashboard", response_model=OTDashboardRead, dependencies=[Depends(require_permissions("ot.view"))])
def dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)) -> OTDashboardRead:
    return OTDashboardRead(**OTService(db).dashboard(user))


@router.get("/rooms", response_model=list[OTRoomRead], dependencies=[Depends(require_permissions("ot.view"))])
def list_rooms(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[OTRoomRead]:
    return [OTRoomRead.model_validate(item) for item in OTService(db).list_rooms(user)]


@router.post("/rooms", response_model=OTRoomRead, dependencies=[Depends(require_permissions("ot.room.manage"))])
def create_room(payload: OTRoomCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> OTRoomRead:
    return OTRoomRead.model_validate(OTService(db).create_room(payload, user))


@router.get("/bookings", response_model=list[OTBookingRead], dependencies=[Depends(require_permissions("ot.view"))])
def list_bookings(q: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[OTBookingRead]:
    return [OTBookingRead.model_validate(serialize_booking(item)) for item in OTService(db).list_bookings(user, q)]


@router.post("/bookings", response_model=OTBookingRead, dependencies=[Depends(require_permissions("ot.booking.manage"))])
def create_booking(payload: OTBookingCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> OTBookingRead:
    return OTBookingRead.model_validate(serialize_booking(OTService(db).create_booking(payload, user)))


@router.get("/schedules", response_model=list[SurgeryScheduleRead], dependencies=[Depends(require_permissions("ot.view"))])
def list_schedules(day: date | None = None, status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[SurgeryScheduleRead]:
    return [SurgeryScheduleRead.model_validate(serialize_schedule(item)) for item in OTService(db).list_schedules(user, day, status)]


@router.post("/schedules", response_model=SurgeryScheduleRead, dependencies=[Depends(require_permissions("ot.schedule.manage"))])
def create_schedule(payload: SurgeryScheduleCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> SurgeryScheduleRead:
    return SurgeryScheduleRead.model_validate(serialize_schedule(OTService(db).create_schedule(payload, user)))


@router.post("/schedules/{schedule_id}/status", response_model=SurgeryScheduleRead, dependencies=[Depends(require_permissions("ot.workflow.manage"))])
def update_status(schedule_id: UUID, payload: OTStatusUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> SurgeryScheduleRead:
    return SurgeryScheduleRead.model_validate(serialize_schedule(OTService(db).update_status(schedule_id, payload.status, user, payload.note)))


@router.post("/schedules/{schedule_id}/pre-op", dependencies=[Depends(require_permissions("ot.preop.manage"))])
def upsert_pre_op(schedule_id: UUID, payload: PreOpChecklistUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return OTService(db).upsert_pre_op(schedule_id, payload, user)


@router.post("/schedules/{schedule_id}/anesthesia", dependencies=[Depends(require_permissions("ot.anesthesia.manage"))])
def upsert_anesthesia(schedule_id: UUID, payload: AnesthesiaRecordUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return OTService(db).upsert_anesthesia(schedule_id, payload, user)


@router.post("/schedules/{schedule_id}/surgery-note", dependencies=[Depends(require_permissions("ot.surgery.signoff"))])
def upsert_surgery_note(schedule_id: UUID, payload: SurgeryNoteUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return OTService(db).upsert_surgery_note(schedule_id, payload, user)


@router.post("/schedules/{schedule_id}/recovery", dependencies=[Depends(require_permissions("ot.recovery.manage"))])
def upsert_recovery(schedule_id: UUID, payload: PostOpRecoveryUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return OTService(db).upsert_recovery(schedule_id, payload, user)


@router.post("/team-assignments", dependencies=[Depends(require_permissions("ot.schedule.manage"))])
def add_team_assignment(payload: TeamAssignmentCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return OTService(db).add_team_assignment(payload, user)


@router.post("/consumables", dependencies=[Depends(require_permissions("ot.inventory.manage"))])
def add_consumable(payload: OTConsumableUsageCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return OTService(db).add_consumable(payload, user)


@router.post("/equipment", dependencies=[Depends(require_permissions("ot.inventory.manage"))])
def add_equipment(payload: OTEquipmentUsageCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return OTService(db).add_equipment(payload, user)


@router.post("/billing-items", dependencies=[Depends(require_permissions("ot.billing.manage"))])
def add_billing_item(payload: OTBillingItemCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return OTService(db).add_billing_item(payload, user)


@router.post("/documents", dependencies=[Depends(require_permissions("ot.documents.manage"))])
def add_document(payload: OTDocumentCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return OTService(db).add_document(payload, user)


@router.get("/case-sheet/{schedule_id}", response_model=OTCaseSheetRead, dependencies=[Depends(require_permissions("ot.view"))])
def case_sheet(schedule_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> OTCaseSheetRead:
    return OTCaseSheetRead(**OTService(db).get_case_sheet(schedule_id, user))
