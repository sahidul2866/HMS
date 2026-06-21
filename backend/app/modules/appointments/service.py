from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.encounter import Appointment, DoctorOPDSchedule, DoctorSlotBooking, OPDVisit
from app.models.user import User
from app.modules.opd.service import OPDService
from app.modules.patients.repository import PatientsRepository
from app.modules.users.repository import UsersRepository
from app.schemas.appointment import (
    AppointmentCheckInRequest,
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    DoctorOPDScheduleRead,
    DoctorOPDScheduleUpsert,
    DoctorSlotAvailability,
    DoctorSlotsResponse,
)
from app.schemas.encounter import OPDVisitCreate


class AppointmentsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UsersRepository(db)
        self.patients = PatientsRepository(db)

    def list_appointments(self, actor: User) -> list[AppointmentRead]:
        stmt = (
            select(Appointment)
            .options(joinedload(Appointment.patient), joinedload(Appointment.doctor))
            .order_by(Appointment.appointment_at.desc())
        )
        if actor.branch_id:
            stmt = stmt.where(Appointment.branch_id == actor.branch_id)
        if any(role.is_doctor_role for role in actor.roles):
            stmt = stmt.where(or_(Appointment.doctor_user_id == actor.id, Appointment.booked_by_user_id == actor.id))
        appointments = list(self.db.scalars(stmt).unique())
        return [self._serialize(item) for item in appointments]

    def create_appointment(self, payload: AppointmentCreate, actor: User) -> AppointmentRead:
        patient, doctor = self._validate_patient_doctor(payload.patient_id, payload.doctor_user_id, actor)
        slot_start = payload.slot_start_at or payload.appointment_at
        if not slot_start:
            raise AppException(400, "slot_required", "Slot time is required")
        slot_start = self._normalize_dt(slot_start)
        if slot_start <= datetime.now(UTC):
            raise AppException(400, "slot_in_past", "Selected slot must be in the future")

        slot_end = self._slot_end_for_doctor(doctor.id, slot_start, actor)
        self._assert_slot_within_schedule(doctor.id, slot_start, actor)

        appointment = Appointment(
            branch_id=actor.branch_id or patient.branch_id or doctor.branch_id,
            patient_id=patient.id,
            doctor_user_id=doctor.id,
            appointment_number=f"APT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            appointment_at=slot_start,
            slot_start_at=slot_start,
            status="scheduled",
            reason=payload.reason,
            note=payload.note,
            booked_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(appointment)
        self.db.flush()

        self._create_slot_booking(
            branch_id=appointment.branch_id,
            doctor_user_id=doctor.id,
            patient_id=patient.id,
            slot_start_at=slot_start,
            slot_end_at=slot_end,
            source_type="appointment",
            appointment_id=appointment.id,
            actor=actor,
        )

        self.db.commit()
        self.db.refresh(appointment)
        appointment = self._get_accessible_appointment(appointment.id, actor)
        return self._serialize(appointment)

    def create_portal_appointment(self, patient_id, payload, actor) -> AppointmentRead:
        patient, doctor = self._validate_patient_doctor(patient_id, payload.doctor_user_id, actor)
        slot_start = self._normalize_dt(payload.appointment_at)
        if slot_start <= datetime.now(UTC):
            raise AppException(400, "slot_in_past", "Selected slot must be in the future")
        slot_end = self._slot_end_for_doctor(doctor.id, slot_start, actor)
        self._assert_slot_within_schedule(doctor.id, slot_start, actor)

        appointment = Appointment(
            branch_id=actor.branch_id or patient.branch_id or doctor.branch_id,
            patient_id=patient.id,
            doctor_user_id=doctor.id,
            appointment_number=f"APT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            appointment_at=slot_start,
            slot_start_at=slot_start,
            status="scheduled",
            reason=payload.reason,
            note=payload.note,
            booked_by_user_id=actor.id if isinstance(actor, User) else None,
            booked_by_patient_account_id=None if isinstance(actor, User) else actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(appointment)
        self.db.flush()
        self._create_slot_booking(
            branch_id=appointment.branch_id,
            doctor_user_id=doctor.id,
            patient_id=patient.id,
            slot_start_at=slot_start,
            slot_end_at=slot_end,
            source_type="appointment",
            appointment_id=appointment.id,
            actor=actor,
        )
        self.db.commit()
        appointment = self.db.scalar(
            select(Appointment)
            .options(joinedload(Appointment.patient), joinedload(Appointment.doctor))
            .where(Appointment.id == appointment.id)
        )
        return self._serialize(appointment)

    def update_appointment(self, appointment_id, payload: AppointmentUpdate, actor: User) -> AppointmentRead:
        appointment = self._get_accessible_appointment(appointment_id, actor)
        patient, doctor = self._validate_patient_doctor(appointment.patient_id, payload.doctor_user_id, actor)
        new_start = self._normalize_dt(payload.slot_start_at)
        new_end = self._slot_end_for_doctor(doctor.id, new_start, actor)
        self._assert_slot_within_schedule(doctor.id, new_start, actor)

        booking = self.db.scalar(select(DoctorSlotBooking).where(DoctorSlotBooking.appointment_id == appointment.id))
        if booking:
            if booking.slot_start_at != new_start or booking.doctor_user_id != doctor.id:
                self.db.delete(booking)
                self.db.flush()
                self._create_slot_booking(
                    branch_id=appointment.branch_id,
                    doctor_user_id=doctor.id,
                    patient_id=patient.id,
                    slot_start_at=new_start,
                    slot_end_at=new_end,
                    source_type="appointment",
                    appointment_id=appointment.id,
                    actor=actor,
                )
        else:
            self._create_slot_booking(
                branch_id=appointment.branch_id,
                doctor_user_id=doctor.id,
                patient_id=patient.id,
                slot_start_at=new_start,
                slot_end_at=new_end,
                source_type="appointment",
                appointment_id=appointment.id,
                actor=actor,
            )

        appointment.doctor_user_id = doctor.id
        appointment.doctor = doctor
        appointment.slot_start_at = new_start
        appointment.appointment_at = new_start
        appointment.reason = payload.reason
        appointment.note = payload.note
        appointment.updated_by = actor.id

        self.db.commit()
        self.db.refresh(appointment)
        return self._serialize(appointment)

    def update_status(self, appointment_id, status: str, actor: User) -> AppointmentRead:
        appointment = self._get_accessible_appointment(appointment_id, actor)
        appointment.status = status
        appointment.updated_by = actor.id
        if status == "cancelled":
            self._release_slot(appointment.id)
        self.db.commit()
        self.db.refresh(appointment)
        return self._serialize(appointment)

    def check_in_to_opd(self, appointment_id, payload: AppointmentCheckInRequest, actor: User, context: dict[str, str | None]):
        appointment = self._get_accessible_appointment(appointment_id, actor)
        if appointment.status == "checked_in":
            raise AppException(409, "appointment_already_checked_in", "Appointment already checked in")
        existing_visit = self.db.scalar(select(OPDVisit.id).where(OPDVisit.source_appointment_id == appointment.id))
        if existing_visit:
            raise AppException(409, "appointment_already_linked", "Appointment already linked to an OPD visit")

        visit = OPDService(self.db).create_visit(
            OPDVisitCreate(
                patient_id=appointment.patient_id,
                visit_date=appointment.appointment_at.date(),
                slot_start_at=appointment.slot_start_at or appointment.appointment_at,
                department_name=payload.department_name,
                doctor_user_id=appointment.doctor_user_id,
                consulting_doctor_name=appointment.doctor.full_name,
                chief_complaint=payload.chief_complaint or appointment.reason,
                consultation_fee=payload.consultation_fee,
                note=payload.note or appointment.note,
            ),
            actor,
            context,
            source_appointment_id=appointment.id,
        )
        visit.updated_by = actor.id
        appointment.status = "checked_in"
        appointment.updated_by = actor.id

        booking = self.db.scalar(select(DoctorSlotBooking).where(DoctorSlotBooking.appointment_id == appointment.id))
        if booking:
            booking.opd_visit_id = visit.id
            booking.source_type = "visit"
            booking.updated_by = actor.id

        self.db.commit()
        self.db.refresh(appointment)
        return visit

    def list_doctor_schedules(self, actor: User, doctor_user_id=None) -> list[DoctorOPDScheduleRead]:
        stmt = select(DoctorOPDSchedule).order_by(DoctorOPDSchedule.doctor_user_id, DoctorOPDSchedule.weekday)
        if actor.branch_id:
            stmt = stmt.where(or_(DoctorOPDSchedule.branch_id == actor.branch_id, DoctorOPDSchedule.branch_id.is_(None)))
        if doctor_user_id:
            stmt = stmt.where(DoctorOPDSchedule.doctor_user_id == doctor_user_id)
        return [DoctorOPDScheduleRead.model_validate(item, from_attributes=True) for item in self.db.scalars(stmt)]

    def upsert_doctor_schedule(self, payload: DoctorOPDScheduleUpsert, actor: User) -> DoctorOPDScheduleRead:
        doctor = self.users.get_user(payload.doctor_user_id)
        if not doctor or not doctor.is_active or not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(404, "doctor_not_found", "Doctor not found")
        if payload.end_time <= payload.start_time:
            raise AppException(400, "invalid_time_range", "End time must be after start time")

        existing = self.db.scalar(
            select(DoctorOPDSchedule).where(
                DoctorOPDSchedule.doctor_user_id == payload.doctor_user_id,
                DoctorOPDSchedule.weekday == payload.weekday,
            )
        )
        if existing:
            existing.start_time = payload.start_time
            existing.end_time = payload.end_time
            existing.slot_duration_minutes = payload.slot_duration_minutes
            existing.buffer_minutes = payload.buffer_minutes
            existing.updated_by = actor.id
            schedule = existing
        else:
            schedule = DoctorOPDSchedule(
                branch_id=actor.branch_id or doctor.branch_id,
                doctor_user_id=payload.doctor_user_id,
                weekday=payload.weekday,
                start_time=payload.start_time,
                end_time=payload.end_time,
                slot_duration_minutes=payload.slot_duration_minutes,
                buffer_minutes=payload.buffer_minutes,
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.db.add(schedule)

        self.db.commit()
        self.db.refresh(schedule)
        return DoctorOPDScheduleRead.model_validate(schedule, from_attributes=True)

    def get_doctor_slots(self, doctor_user_id, slot_date: date, actor: User) -> DoctorSlotsResponse:
        doctor = self.users.get_user(doctor_user_id)
        if not doctor or not doctor.is_active or not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(404, "doctor_not_found", "Doctor not found")

        schedule = self.db.scalar(
            select(DoctorOPDSchedule).where(
                DoctorOPDSchedule.doctor_user_id == doctor_user_id,
                DoctorOPDSchedule.weekday == slot_date.weekday(),
            )
        )
        if not schedule:
            return DoctorSlotsResponse(
                doctor_user_id=doctor_user_id,
                date=slot_date,
                slot_duration_minutes=15,
                buffer_minutes=0,
                slots=[],
            )

        slots = self._generate_slots(slot_date, schedule.start_time, schedule.end_time, schedule.slot_duration_minutes, schedule.buffer_minutes)
        day_start = datetime.combine(slot_date, time(0, 0), tzinfo=UTC)
        day_end = datetime.combine(slot_date, time(23, 59), tzinfo=UTC)
        query_start = slots[0][0] if slots else day_start
        query_end = slots[-1][1] if slots else day_end
        booked = {
            row.slot_start_at: row
            for row in self.db.scalars(
                select(DoctorSlotBooking).where(
                    DoctorSlotBooking.doctor_user_id == doctor_user_id,
                    DoctorSlotBooking.slot_start_at >= query_start,
                    DoctorSlotBooking.slot_start_at < query_end,
                )
            )
        }

        slot_rows: list[DoctorSlotAvailability] = []
        now = datetime.now(UTC)
        for start_at, end_at in slots:
            booking = booked.get(start_at)
            status_value = "booked" if booking else ("unavailable" if start_at <= now else "available")
            slot_rows.append(
                DoctorSlotAvailability(
                    slot_start_at=start_at,
                    slot_end_at=end_at,
                    status=status_value,
                    source_type=booking.source_type if booking else None,
                )
            )

        return DoctorSlotsResponse(
            doctor_user_id=doctor_user_id,
            date=slot_date,
            slot_duration_minutes=schedule.slot_duration_minutes,
            buffer_minutes=schedule.buffer_minutes,
            slots=slot_rows,
        )

    def _get_accessible_appointment(self, appointment_id, actor: User) -> Appointment:
        stmt = select(Appointment).options(joinedload(Appointment.patient), joinedload(Appointment.doctor)).where(Appointment.id == appointment_id)
        appointment = self.db.scalar(stmt)
        if not appointment:
            raise AppException(404, "appointment_not_found", "Appointment not found")
        if actor.branch_id and appointment.branch_id and actor.branch_id != appointment.branch_id:
            raise AppException(403, "forbidden", "Appointment belongs to a different branch")
        if any(role.is_doctor_role for role in actor.roles) and appointment.doctor_user_id != actor.id:
            raise AppException(403, "forbidden", "Appointment does not belong to this doctor")
        return appointment

    def _validate_patient_doctor(self, patient_id, doctor_user_id, actor: User):
        patient = self.patients.get_patient(patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")

        doctor = self.users.get_user(doctor_user_id)
        if not doctor or not doctor.is_active or not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(404, "doctor_not_found", "Doctor not found")
        if actor.branch_id and doctor.branch_id and actor.branch_id != doctor.branch_id:
            raise AppException(403, "forbidden", "Doctor belongs to a different branch")
        return patient, doctor

    def _normalize_dt(self, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    def _release_slot(self, appointment_id) -> None:
        booking = self.db.scalar(select(DoctorSlotBooking).where(DoctorSlotBooking.appointment_id == appointment_id))
        if booking:
            self.db.delete(booking)

    def _assert_slot_within_schedule(self, doctor_user_id, slot_start: datetime, actor: User) -> None:
        schedule = self.db.scalar(
            select(DoctorOPDSchedule).where(
                DoctorOPDSchedule.doctor_user_id == doctor_user_id,
                DoctorOPDSchedule.weekday == slot_start.date().weekday(),
            )
        )
        if not schedule:
            raise AppException(400, "schedule_not_configured", "Doctor schedule is not configured for this day")

        slots = self._generate_slots(slot_start.date(), schedule.start_time, schedule.end_time, schedule.slot_duration_minutes, schedule.buffer_minutes)
        if not any(start == slot_start for start, _ in slots):
            raise AppException(400, "slot_not_in_schedule", "Selected slot is outside configured schedule")

    def _slot_end_for_doctor(self, doctor_user_id, slot_start: datetime, actor: User) -> datetime:
        schedule = self.db.scalar(
            select(DoctorOPDSchedule).where(
                DoctorOPDSchedule.doctor_user_id == doctor_user_id,
                DoctorOPDSchedule.weekday == slot_start.date().weekday(),
            )
        )
        if not schedule:
            raise AppException(400, "schedule_not_configured", "Doctor schedule is not configured for this day")
        return slot_start + timedelta(minutes=schedule.slot_duration_minutes)

    def _create_slot_booking(
        self,
        *,
        branch_id,
        doctor_user_id,
        patient_id,
        slot_start_at: datetime,
        slot_end_at: datetime,
        source_type: str,
        appointment_id,
        actor: User,
    ) -> DoctorSlotBooking:
        booking = DoctorSlotBooking(
            branch_id=branch_id,
            doctor_user_id=doctor_user_id,
            patient_id=patient_id,
            slot_start_at=slot_start_at,
            slot_end_at=slot_end_at,
            source_type=source_type,
            appointment_id=appointment_id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(booking)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(409, "slot_conflict", "Selected slot is already booked") from exc
        return booking

    def _generate_slots(self, slot_date: date, start_hhmm: str, end_hhmm: str, duration: int, buffer: int) -> list[tuple[datetime, datetime]]:
        start_hour, start_min = [int(part) for part in start_hhmm.split(":")]
        end_hour, end_min = [int(part) for part in end_hhmm.split(":")]
        current = datetime.combine(slot_date, time(start_hour, start_min), tzinfo=UTC)
        end_dt = datetime.combine(slot_date, time(end_hour, end_min), tzinfo=UTC)
        step = timedelta(minutes=duration + buffer)
        length = timedelta(minutes=duration)
        slots: list[tuple[datetime, datetime]] = []
        while current + length <= end_dt:
            slots.append((current, current + length))
            current = current + step
        return slots

    def _serialize(self, appointment: Appointment) -> AppointmentRead:
        return AppointmentRead(
            id=appointment.id,
            appointment_number=appointment.appointment_number,
            patient_id=appointment.patient_id,
            patient_name=f"{appointment.patient.first_name} {appointment.patient.last_name}",
            doctor_user_id=appointment.doctor_user_id,
            doctor_name=appointment.doctor.full_name,
            appointment_at=appointment.appointment_at,
            slot_start_at=appointment.slot_start_at,
            status=appointment.status,
            reason=appointment.reason,
            note=appointment.note,
        )
