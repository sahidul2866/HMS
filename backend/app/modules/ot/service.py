from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppException
from app.models.ot import (
    AnesthesiaRecord,
    OTAuditLog,
    OTBillingItem,
    OTBooking,
    OTConsumableUsage,
    OTDocument,
    OTEquipmentUsage,
    OTRoom,
    PostOpRecovery,
    PreOpChecklist,
    SurgeryNote,
    SurgerySchedule,
    SurgeryTeamAssignment,
)
from app.models.patient import Patient
from app.models.user import User
from app.schemas.ot import (
    AnesthesiaRecordUpdate,
    OTBillingItemCreate,
    OTBookingCreate,
    OTConsumableUsageCreate,
    OTDocumentCreate,
    OTEquipmentUsageCreate,
    OTRoomCreate,
    PostOpRecoveryUpdate,
    PreOpChecklistUpdate,
    SurgeryNoteUpdate,
    SurgeryScheduleCreate,
    TeamAssignmentCreate,
)


class OTService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def dashboard(self, actor: User) -> dict:
        today = date.today()
        schedules = self.list_schedules(actor, day=today)
        upcoming = self.db.scalar(select(func.count(SurgerySchedule.id)).where(SurgerySchedule.branch_id == actor.branch_id, SurgerySchedule.scheduled_start_at > datetime.now(UTC), SurgerySchedule.status.in_(["scheduled", "ready_for_ot"]))) or 0
        available_rooms = self.db.scalar(select(func.count(OTRoom.id)).where(OTRoom.branch_id == actor.branch_id, OTRoom.status == "available")) or 0
        occupied_rooms = self.db.scalar(select(func.count(OTRoom.id)).where(OTRoom.branch_id == actor.branch_id, OTRoom.status.in_(["booked", "in_use", "cleaning"]))) or 0
        pending_pre_op = self.db.scalar(select(func.count(SurgerySchedule.id)).outerjoin(PreOpChecklist).where(SurgerySchedule.branch_id == actor.branch_id, SurgerySchedule.status.in_(["scheduled", "approved"]), or_(PreOpChecklist.id.is_(None), PreOpChecklist.ready_for_ot.is_(False)))) or 0
        pending_anesthesia = self.db.scalar(select(func.count(SurgerySchedule.id)).outerjoin(AnesthesiaRecord).where(SurgerySchedule.branch_id == actor.branch_id, SurgerySchedule.status.in_(["scheduled", "approved", "ready_for_ot"]), or_(AnesthesiaRecord.id.is_(None), AnesthesiaRecord.clearance_status != "cleared"))) or 0
        surgeon_schedule: dict[str, int] = {}
        department_schedule: dict[str, int] = {}
        alerts: list[str] = []
        for schedule in schedules:
            surgeon = schedule.primary_surgeon.full_name if schedule.primary_surgeon else "Unassigned"
            department = schedule.booking.department_name if schedule.booking else "Unassigned"
            surgeon_schedule[surgeon] = surgeon_schedule.get(surgeon, 0) + 1
            department_schedule[department] = department_schedule.get(department, 0) + 1
            if schedule.booking and schedule.booking.priority_level in {"critical", "high"}:
                alerts.append(f"{schedule.booking.priority_level.title()} priority: {schedule.booking.procedure_name}")
            if schedule.status == "scheduled" and schedule.scheduled_start_at < datetime.now(UTC):
                alerts.append(f"Delayed surgery: {schedule.booking.procedure_name if schedule.booking else schedule.id}")
        return {
            "today_surgeries": len(schedules),
            "upcoming_surgeries": upcoming,
            "ongoing_surgeries": len([item for item in schedules if item.status == "in_progress"]),
            "completed_surgeries": len([item for item in schedules if item.status == "completed"]),
            "cancelled_surgeries": len([item for item in schedules if item.status == "cancelled"]),
            "emergency_surgeries": len([item for item in schedules if item.booking and item.booking.surgery_type == "emergency"]),
            "available_rooms": available_rooms,
            "occupied_rooms": occupied_rooms,
            "pending_pre_op": pending_pre_op,
            "pending_anesthesia": pending_anesthesia,
            "surgeon_schedule": surgeon_schedule,
            "department_schedule": department_schedule,
            "room_utilization": [{"room": item.room.name if item.room else "OT", "status": item.status, "procedure": item.booking.procedure_name if item.booking else ""} for item in schedules],
            "alerts": alerts[:8],
        }

    def list_rooms(self, actor: User) -> list[OTRoom]:
        return list(self.db.scalars(select(OTRoom).where(OTRoom.branch_id == actor.branch_id).order_by(OTRoom.room_number)))

    def create_room(self, payload: OTRoomCreate, actor: User) -> OTRoom:
        room = OTRoom(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
        self.db.add(room)
        self._audit(actor, "room.create", "ot_room", None, room.name)
        self.db.commit()
        self.db.refresh(room)
        return room

    def list_bookings(self, actor: User, q: str | None = None) -> list[OTBooking]:
        stmt = select(OTBooking).options(selectinload(OTBooking.patient), selectinload(OTBooking.schedule)).where(OTBooking.branch_id == actor.branch_id).order_by(OTBooking.preferred_start_at.desc())
        if q:
            pattern = f"%{q}%"
            stmt = stmt.join(OTBooking.patient).where(or_(OTBooking.booking_number.ilike(pattern), OTBooking.procedure_name.ilike(pattern), Patient.patient_number.ilike(pattern), Patient.first_name.ilike(pattern), Patient.last_name.ilike(pattern)))
        return list(self.db.scalars(stmt))

    def create_booking(self, payload: OTBookingCreate, actor: User) -> OTBooking:
        booking = OTBooking(
            **payload.model_dump(),
            branch_id=actor.branch_id,
            booking_number=self._next_number(actor, "OTB", OTBooking),
            requested_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(booking)
        self._audit(actor, "booking.create", "ot_booking", None, booking.procedure_name)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def list_schedules(self, actor: User, day: date | None = None, status: str | None = None) -> list[SurgerySchedule]:
        stmt = (
            select(SurgerySchedule)
            .options(
                selectinload(SurgerySchedule.booking).selectinload(OTBooking.patient),
                selectinload(SurgerySchedule.room),
                selectinload(SurgerySchedule.primary_surgeon),
                selectinload(SurgerySchedule.anesthetist),
                selectinload(SurgerySchedule.pre_op_checklist),
                selectinload(SurgerySchedule.anesthesia_record),
                selectinload(SurgerySchedule.surgery_notes),
                selectinload(SurgerySchedule.recovery),
            )
            .where(SurgerySchedule.branch_id == actor.branch_id)
            .order_by(SurgerySchedule.scheduled_start_at)
        )
        if day:
            stmt = stmt.where(func.date(SurgerySchedule.scheduled_start_at) == day)
        if status:
            stmt = stmt.where(SurgerySchedule.status == status)
        return list(self.db.scalars(stmt))

    def create_schedule(self, payload: SurgeryScheduleCreate, actor: User) -> SurgerySchedule:
        self._validate_schedule_conflict(payload, actor)
        schedule = SurgerySchedule(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
        booking = self.db.get(OTBooking, payload.booking_id)
        if not booking or booking.branch_id != actor.branch_id:
            raise AppException(404, "ot_booking_not_found", "OT booking not found")
        booking.status = payload.status if payload.status != "scheduled" else "scheduled"
        room = self.db.get(OTRoom, payload.room_id)
        if room:
            room.status = "booked"
        self.db.add(schedule)
        self.db.flush()
        self._ensure_case_children(schedule, actor)
        self._audit(actor, "schedule.create", "surgery_schedule", str(schedule.id), booking.procedure_name)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def update_status(self, schedule_id: UUID, status: str, actor: User, note: str | None = None) -> SurgerySchedule:
        schedule = self._get_schedule(schedule_id, actor)
        now = datetime.now(UTC)
        schedule.status = status
        if status == "ready_for_ot" and schedule.booking:
            schedule.booking.status = "ready_for_ot"
        if status == "in_progress":
            schedule.surgery_start_at = schedule.surgery_start_at or now
            schedule.room_entry_at = schedule.room_entry_at or now
            if schedule.room:
                schedule.room.status = "in_use"
        if status == "completed":
            schedule.surgery_end_at = schedule.surgery_end_at or now
            schedule.room_exit_at = schedule.room_exit_at or now
            if schedule.booking:
                schedule.booking.status = "completed"
            if schedule.room:
                schedule.room.status = "cleaning"
        if status == "cancelled" and schedule.booking:
            schedule.booking.status = "cancelled"
            schedule.booking.cancellation_reason = note
        schedule.updated_by = actor.id
        self._audit(actor, f"schedule.{status}", "surgery_schedule", str(schedule.id), note)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def upsert_pre_op(self, schedule_id: UUID, payload: PreOpChecklistUpdate, actor: User) -> PreOpChecklist:
        schedule = self._get_schedule(schedule_id, actor)
        item = schedule.pre_op_checklist or PreOpChecklist(schedule_id=schedule.id, created_by=actor.id)
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        item.checked_by_user_id = actor.id
        item.updated_by = actor.id
        self.db.add(item)
        if item.ready_for_ot:
            schedule.status = "ready_for_ot"
            if schedule.booking:
                schedule.booking.status = "ready_for_ot"
        self._audit(actor, "preop.update", "pre_op_checklist", str(schedule.id), str(item.ready_for_ot))
        self.db.commit()
        self.db.refresh(item)
        return item

    def upsert_anesthesia(self, schedule_id: UUID, payload: AnesthesiaRecordUpdate, actor: User) -> AnesthesiaRecord:
        schedule = self._get_schedule(schedule_id, actor)
        item = schedule.anesthesia_record or AnesthesiaRecord(schedule_id=schedule.id, created_by=actor.id)
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        if item.clearance_status == "cleared":
            item.signed_off_by_user_id = actor.id
            item.signed_off_at = datetime.now(UTC)
        item.updated_by = actor.id
        self.db.add(item)
        self._audit(actor, "anesthesia.update", "anesthesia_record", str(schedule.id), item.clearance_status)
        self.db.commit()
        self.db.refresh(item)
        return item

    def upsert_surgery_note(self, schedule_id: UUID, payload: SurgeryNoteUpdate, actor: User) -> SurgeryNote:
        schedule = self._get_schedule(schedule_id, actor)
        item = schedule.surgery_notes or SurgeryNote(schedule_id=schedule.id, created_by=actor.id)
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        if item.instrument_count_confirmed and item.sponge_count_confirmed:
            item.surgeon_signed_by_user_id = actor.id
            item.signed_off_at = datetime.now(UTC)
        item.updated_by = actor.id
        self.db.add(item)
        self._audit(actor, "surgery_note.update", "surgery_note", str(schedule.id), item.surgery_outcome)
        self.db.commit()
        self.db.refresh(item)
        return item

    def upsert_recovery(self, schedule_id: UUID, payload: PostOpRecoveryUpdate, actor: User) -> PostOpRecovery:
        schedule = self._get_schedule(schedule_id, actor)
        item = schedule.recovery or PostOpRecovery(schedule_id=schedule.id, created_by=actor.id)
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        item.updated_by = actor.id
        self.db.add(item)
        self._audit(actor, "recovery.update", "post_op_recovery", str(schedule.id), item.transfer_to)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_team_assignment(self, payload: TeamAssignmentCreate, actor: User) -> SurgeryTeamAssignment:
        schedule = self._get_schedule(payload.schedule_id, actor)
        if payload.user_id:
            self._validate_staff_conflict(payload.user_id, schedule.scheduled_start_at, schedule.scheduled_end_at, actor, exclude_schedule_id=schedule.id)
        item = SurgeryTeamAssignment(**payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self._audit(actor, "team.assign", "surgery_team_assignment", str(schedule.id), payload.role)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_consumable(self, payload: OTConsumableUsageCreate, actor: User) -> OTConsumableUsage:
        self._get_schedule(payload.schedule_id, actor)
        item = OTConsumableUsage(**payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self._audit(actor, "consumable.add", "ot_consumable_usage", str(payload.schedule_id), payload.item_name)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_equipment(self, payload: OTEquipmentUsageCreate, actor: User) -> OTEquipmentUsage:
        self._get_schedule(payload.schedule_id, actor)
        item = OTEquipmentUsage(**payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_billing_item(self, payload: OTBillingItemCreate, actor: User) -> OTBillingItem:
        self._get_schedule(payload.schedule_id, actor)
        item = OTBillingItem(**payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self._audit(actor, "billing.add", "ot_billing_item", str(payload.schedule_id), payload.charge_type)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_document(self, payload: OTDocumentCreate, actor: User) -> OTDocument:
        self._get_schedule(payload.schedule_id, actor)
        item = OTDocument(**payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_case_sheet(self, schedule_id: UUID, actor: User) -> dict:
        schedule = self._get_schedule(schedule_id, actor)
        return {
            "schedule": serialize_schedule(schedule),
            "pre_op": self._row_dict(schedule.pre_op_checklist),
            "anesthesia": self._row_dict(schedule.anesthesia_record),
            "surgery_note": self._row_dict(schedule.surgery_notes),
            "recovery": self._row_dict(schedule.recovery),
            "consumables": [self._row_dict(item) for item in self.db.scalars(select(OTConsumableUsage).where(OTConsumableUsage.schedule_id == schedule.id))],
            "equipment": [self._row_dict(item) for item in self.db.scalars(select(OTEquipmentUsage).where(OTEquipmentUsage.schedule_id == schedule.id))],
            "billing": [self._row_dict(item) for item in self.db.scalars(select(OTBillingItem).where(OTBillingItem.schedule_id == schedule.id))],
            "documents": [self._row_dict(item) for item in self.db.scalars(select(OTDocument).where(OTDocument.schedule_id == schedule.id))],
        }

    def _validate_schedule_conflict(self, payload: SurgeryScheduleCreate, actor: User) -> None:
        if payload.scheduled_end_at <= payload.scheduled_start_at:
            raise AppException(422, "ot_invalid_time", "Schedule end time must be after start time")
        overlap = and_(SurgerySchedule.scheduled_start_at < payload.scheduled_end_at, SurgerySchedule.scheduled_end_at > payload.scheduled_start_at, SurgerySchedule.status.not_in(["cancelled", "completed"]))
        room_conflict = self.db.scalar(select(SurgerySchedule).where(SurgerySchedule.branch_id == actor.branch_id, SurgerySchedule.room_id == payload.room_id, overlap))
        if room_conflict:
            raise AppException(409, "ot_room_conflict", "OT room is already booked in this time slot")
        for user_id in [payload.primary_surgeon_user_id, payload.assistant_surgeon_user_id, payload.anesthetist_user_id, payload.scrub_nurse_user_id, payload.circulating_nurse_user_id, payload.technician_user_id]:
            if user_id:
                self._validate_staff_conflict(user_id, payload.scheduled_start_at, payload.scheduled_end_at, actor)

    def _validate_staff_conflict(self, user_id: UUID, start: datetime, end: datetime, actor: User, exclude_schedule_id: UUID | None = None) -> None:
        overlap = and_(SurgerySchedule.scheduled_start_at < end, SurgerySchedule.scheduled_end_at > start, SurgerySchedule.status.not_in(["cancelled", "completed"]))
        stmt = select(SurgerySchedule).where(
            SurgerySchedule.branch_id == actor.branch_id,
            overlap,
            or_(
                SurgerySchedule.primary_surgeon_user_id == user_id,
                SurgerySchedule.assistant_surgeon_user_id == user_id,
                SurgerySchedule.anesthetist_user_id == user_id,
                SurgerySchedule.scrub_nurse_user_id == user_id,
                SurgerySchedule.circulating_nurse_user_id == user_id,
                SurgerySchedule.technician_user_id == user_id,
            ),
        )
        if exclude_schedule_id:
            stmt = stmt.where(SurgerySchedule.id != exclude_schedule_id)
        if self.db.scalar(stmt):
            raise AppException(409, "ot_staff_conflict", "Assigned staff already has another OT schedule in this time slot")

    def _get_schedule(self, schedule_id: UUID, actor: User) -> SurgerySchedule:
        schedule = self.db.scalar(
            select(SurgerySchedule)
            .options(
                selectinload(SurgerySchedule.booking).selectinload(OTBooking.patient),
                selectinload(SurgerySchedule.room),
                selectinload(SurgerySchedule.primary_surgeon),
                selectinload(SurgerySchedule.anesthetist),
                selectinload(SurgerySchedule.pre_op_checklist),
                selectinload(SurgerySchedule.anesthesia_record),
                selectinload(SurgerySchedule.surgery_notes),
                selectinload(SurgerySchedule.recovery),
            )
            .where(SurgerySchedule.id == schedule_id)
        )
        if not schedule or schedule.branch_id != actor.branch_id:
            raise AppException(404, "ot_schedule_not_found", "Surgery schedule not found")
        return schedule

    def _ensure_case_children(self, schedule: SurgerySchedule, actor: User) -> None:
        self.db.add(PreOpChecklist(schedule_id=schedule.id, created_by=actor.id, updated_by=actor.id))
        self.db.add(AnesthesiaRecord(schedule_id=schedule.id, created_by=actor.id, updated_by=actor.id))
        self.db.add(SurgeryNote(schedule_id=schedule.id, created_by=actor.id, updated_by=actor.id))
        self.db.add(PostOpRecovery(schedule_id=schedule.id, created_by=actor.id, updated_by=actor.id))

    def _next_number(self, actor: User, prefix: str, model) -> str:
        count = self.db.scalar(select(func.count(model.id)).where(model.branch_id == actor.branch_id)) or 0
        return f"{prefix}-{datetime.now().strftime('%y%m')}-{int(count) + 1001}"

    def _audit(self, actor: User, action: str, entity_type: str, entity_id: str | None, detail: str | None = None) -> None:
        self.db.add(OTAuditLog(branch_id=actor.branch_id, actor_user_id=actor.id, action=action, entity_type=entity_type, entity_id=entity_id, detail=detail, created_by=actor.id, updated_by=actor.id))

    def _row_dict(self, row) -> dict | None:
        if not row:
            return None
        return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def serialize_booking(item: OTBooking) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["patient_name"] = f"{item.patient.first_name} {item.patient.last_name}" if item.patient else None
    data["patient_number"] = item.patient.patient_number if item.patient else None
    return data


def serialize_schedule(item: SurgerySchedule) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    booking = item.booking
    patient = booking.patient if booking else None
    data["booking_number"] = booking.booking_number if booking else None
    data["patient_name"] = f"{patient.first_name} {patient.last_name}" if patient else None
    data["patient_number"] = patient.patient_number if patient else None
    data["procedure_name"] = booking.procedure_name if booking else None
    data["surgery_type"] = booking.surgery_type if booking else None
    data["priority_level"] = booking.priority_level if booking else None
    data["department_name"] = booking.department_name if booking else None
    data["room_name"] = item.room.name if item.room else None
    data["room_number"] = item.room.room_number if item.room else None
    data["primary_surgeon_name"] = item.primary_surgeon.full_name if item.primary_surgeon else None
    data["anesthetist_name"] = item.anesthetist.full_name if item.anesthetist else None
    return data
