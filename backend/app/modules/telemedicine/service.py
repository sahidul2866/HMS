from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.encounter import DoctorOPDSchedule, DoctorSlotBooking, OPDVisit
from app.models.laboratory import LabOrder, LabOrderItem
from app.models.patient import Patient
from app.models.radiology import RadiologyOrder
from app.models.telemedicine import (
    TelemedicineAppointment,
    TelemedicineChatMessage,
    TelemedicineConsultation,
    TelemedicineFile,
    TelemedicineInvestigationOrder,
    TelemedicineSetting,
)
from app.models.queue import QueueToken
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.opd.service import OPDService
from app.modules.queue.service import QueueService, patient_label
from app.schemas.encounter import OPDVisitCreate
from app.schemas.queue import QueueTokenCreate
from app.schemas.telemedicine import (
    TelemedicineAppointmentCreate,
    TelemedicineChatCreate,
    TelemedicineConsentUpdate,
    TelemedicineConsultationUpdate,
    TelemedicineDashboardRead,
    TelemedicineFileCreate,
    TelemedicineInvestigationCreate,
    TelemedicinePaymentUpdate,
    TelemedicineReportRead,
    TelemedicineSettingCreate,
)


ALLOWED_FILE_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE = 15 * 1024 * 1024


class TelemedicineService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def dashboard(self, actor: User, filters: dict) -> TelemedicineDashboardRead:
        rows = self.list_appointments(actor, filters)
        consultations = self.list_consultations(actor, filters)
        today = date.today()
        by_status: dict[str, int] = {}
        by_payment: dict[str, int] = {}
        for item in rows:
            by_status[item.status] = by_status.get(item.status, 0) + 1
            by_payment[item.payment_status] = by_payment.get(item.payment_status, 0) + 1
        return TelemedicineDashboardRead(
            todays_online_appointments=len([a for a in rows if a.appointment_at.date() == today]),
            waiting_patients=len([a for a in rows if a.status in {"waiting", "ready_to_join"}]),
            active_consultations=len([c for c in consultations if c.status == "in_consultation"]),
            completed_consultations=len([c for c in consultations if c.status == "completed" and c.completed_at and c.completed_at.date() == today]),
            missed_no_show=len([a for a in rows if a.status == "no_show"]),
            pending_payments=len([a for a in rows if a.payment_status in {"pending", "unpaid", "partial"}]),
            pending_prescriptions=len([c for c in consultations if c.prescription_status == "pending"]),
            follow_up_requests=len([c for c in consultations if c.follow_up_date]),
            doctors_available=len({a.doctor_user_id for a in rows if a.status in {"scheduled", "waiting", "ready_to_join"}}),
            by_status=by_status,
            by_payment_status=by_payment,
        )

    def list_appointments(self, actor: User, filters: dict | None = None) -> list[TelemedicineAppointment]:
        filters = filters or {}
        stmt = (
            select(TelemedicineAppointment)
            .options(joinedload(TelemedicineAppointment.patient), joinedload(TelemedicineAppointment.doctor), joinedload(TelemedicineAppointment.department))
            .where(TelemedicineAppointment.is_active.is_(True))
        )
        if actor.branch_id:
            stmt = stmt.where(or_(TelemedicineAppointment.branch_id == actor.branch_id, TelemedicineAppointment.branch_id.is_(None)))
        if any(role.is_doctor_role for role in actor.roles):
            stmt = stmt.where(TelemedicineAppointment.doctor_user_id == actor.id)
        if filters.get("doctor_id"):
            stmt = stmt.where(TelemedicineAppointment.doctor_user_id == filters["doctor_id"])
        if filters.get("department"):
            stmt = stmt.where(TelemedicineAppointment.department_name == filters["department"])
        if filters.get("status"):
            stmt = stmt.where(TelemedicineAppointment.status == filters["status"])
        if filters.get("payment_status"):
            stmt = stmt.where(TelemedicineAppointment.payment_status == filters["payment_status"])
        if filters.get("appointment_type"):
            stmt = stmt.where(TelemedicineAppointment.appointment_type == filters["appointment_type"])
        if filters.get("date"):
            target = filters["date"]
            if isinstance(target, str):
                target = date.fromisoformat(target)
            start = datetime(target.year, target.month, target.day, tzinfo=UTC)
            stmt = stmt.where(TelemedicineAppointment.appointment_at >= start, TelemedicineAppointment.appointment_at < start + timedelta(days=1))
        return list(self.db.scalars(stmt.order_by(TelemedicineAppointment.appointment_at.asc())).unique())

    def create_appointment(self, payload: TelemedicineAppointmentCreate, actor: User, context: dict[str, str | None]) -> TelemedicineAppointment:
        patient = self.db.get(Patient, payload.patient_id)
        doctor = self.db.get(User, payload.doctor_user_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if not doctor:
            raise AppException(404, "doctor_not_found", "Doctor not found")
        appointment_at = self._normalize_dt(payload.appointment_at)
        if appointment_at <= datetime.now(UTC):
            raise AppException(400, "appointment_in_past", "Appointment must be in the future")
        payload_data = payload.model_dump(exclude={"uploaded_files", "appointment_at"})
        item = TelemedicineAppointment(
            branch_id=actor.branch_id or patient.branch_id or doctor.branch_id,
            telemedicine_number=self._next_number("TEL", TelemedicineAppointment.telemedicine_number),
            queue_number=self._next_queue(appointment_at.date(), payload.doctor_user_id),
            estimated_wait_minutes=0,
            status="payment_pending" if payload.payment_status in {"pending", "unpaid"} and payload.consultation_fee > 0 else "scheduled",
            video_provider="placeholder",
            meeting_id=self._next_number("ROOM", TelemedicineAppointment.meeting_id),
            join_url="",
            doctor_join_url="",
            booked_by_user_id=actor.id,
            **payload_data,
            appointment_at=appointment_at,
            uploaded_files=payload.uploaded_files or [],
            created_by=actor.id,
            updated_by=actor.id,
        )
        item.join_url = f"/telemedicine/consultation/{item.meeting_id}/patient"
        item.doctor_join_url = f"/telemedicine/consultation/{item.meeting_id}/doctor"
        self.db.add(item)
        self.db.flush()
        self._create_slot_booking(item, appointment_at, actor)
        if item.status in {"scheduled", "waiting", "ready_to_join"}:
            QueueService(self.db).ensure_token(
                QueueTokenCreate(
                    queue_scope="telemedicine",
                    module="telemedicine",
                    service_area="virtual_consultation",
                    department_name=item.department_name or "Telemedicine",
                    doctor_user_id=item.doctor_user_id,
                    patient_id=item.patient_id,
                    patient_label=patient_label(patient),
                    priority="follow_up" if item.visit_type == "follow_up" else "normal",
                    source_type="telemedicine_appointment",
                    source_id=item.id,
                    due_at=item.appointment_at,
                    meta={"visit_type": item.visit_type, "telemedicine_number": item.telemedicine_number, "join_url": item.join_url},
                ),
                actor,
                commit=False,
            )
        audit_detail = payload.model_dump(mode="json")
        audit_detail["appointment_at"] = appointment_at.isoformat()
        self._audit(actor, "telemedicine.appointment.create", "telemedicine_appointment", item, audit_detail, context)
        return item

    def update_status(self, appointment_id: UUID, payload, actor: User, context: dict[str, str | None]) -> TelemedicineAppointment:
        item = self._get_appointment(appointment_id)
        previous = item.status
        item.status = payload.status
        item.remarks = payload.remarks or item.remarks
        item.updated_by = actor.id
        if payload.status == "cancelled":
            self._release_slot_booking(item)
        if payload.status in {"waiting", "ready_to_join"}:
            QueueService(self.db).ensure_token(
                QueueTokenCreate(
                    queue_scope="telemedicine",
                    module="telemedicine",
                    service_area="virtual_consultation",
                    department_name=item.department_name or "Telemedicine",
                    doctor_user_id=item.doctor_user_id,
                    patient_id=item.patient_id,
                    patient_label=patient_label(item.patient),
                    priority="follow_up" if item.visit_type == "follow_up" else "normal",
                    source_type="telemedicine_appointment",
                    source_id=item.id,
                    due_at=item.appointment_at,
                    meta={"visit_type": item.visit_type, "telemedicine_number": item.telemedicine_number, "join_url": item.join_url},
                ),
                actor,
                commit=False,
            )
        self._audit(actor, f"telemedicine.appointment.{payload.status}", "telemedicine_appointment", item, {"from": previous, "to": payload.status}, context)
        return item

    def accept_consent(self, appointment_id: UUID, payload: TelemedicineConsentUpdate, actor: User, context: dict[str, str | None]) -> TelemedicineAppointment:
        item = self._get_appointment(appointment_id)
        item.consent_accepted = payload.consent_accepted
        item.consent_by = payload.consent_by
        item.consent_terms_version = payload.consent_terms_version
        item.consent_at = datetime.now(UTC)
        item.updated_by = actor.id
        self._audit(actor, "telemedicine.consent.accept", "telemedicine_appointment", item, payload.model_dump(), context)
        return item

    def start_consultation(self, appointment_id: UUID, actor: User, context: dict[str, str | None]) -> TelemedicineConsultation:
        appointment = self._get_appointment(appointment_id)
        if appointment.consent_required and not appointment.consent_accepted:
            raise AppException(409, "telemedicine_consent_required", "Telemedicine consent is required before consultation")
        if appointment.payment_status in {"pending", "unpaid"} and appointment.consultation_fee > 0:
            raise AppException(409, "telemedicine_payment_pending", "Payment is pending for this online consultation")
        existing = self.db.scalar(select(TelemedicineConsultation).where(TelemedicineConsultation.telemedicine_appointment_id == appointment.id))
        if existing:
            existing.status = "in_consultation"
            existing.started_at = existing.started_at or datetime.now(UTC)
            appointment.status = "in_consultation"
            self._sync_queue_status(appointment, "in_progress", actor, f"Telemedicine consultation started for {appointment.telemedicine_number}")
            return existing
        visit = OPDService(self.db).create_visit(
            OPDVisitCreate(
                patient_id=appointment.patient_id,
                visit_date=appointment.appointment_at.date(),
                slot_start_at=appointment.appointment_at,
                department_name=appointment.department_name or "Telemedicine",
                doctor_user_id=appointment.doctor_user_id,
                consulting_doctor_name=appointment.doctor.full_name if appointment.doctor else "Telemedicine Doctor",
                consultation_fee=appointment.consultation_fee,
                visit_type=appointment.visit_type,
                chief_complaint=appointment.consultation_reason,
                note=f"Telemedicine reference {appointment.telemedicine_number}",
            ),
            actor,
            context,
            source_appointment_id=appointment.appointment_id,
        )
        consultation = TelemedicineConsultation(
            branch_id=appointment.branch_id,
            telemedicine_appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            doctor_user_id=appointment.doctor_user_id,
            opd_visit_id=visit.id,
            started_at=datetime.now(UTC),
            doctor_joined_at=datetime.now(UTC),
            connection_status="connected",
            status="in_consultation",
            current_complaint=appointment.consultation_reason,
            created_by=actor.id,
            updated_by=actor.id,
        )
        appointment.status = "in_consultation"
        self.db.add(consultation)
        self.db.flush()
        self._sync_queue_status(appointment, "in_progress", actor, f"Telemedicine consultation started for {appointment.telemedicine_number}")
        self._audit(actor, "telemedicine.consultation.start", "telemedicine_consultation", consultation, {"appointment": appointment.telemedicine_number}, context)
        return consultation

    def join_consultation(self, consultation_id: UUID, role: str, actor: User, context: dict[str, str | None]) -> TelemedicineConsultation:
        item = self._get_consultation(consultation_id)
        now = datetime.now(UTC)
        if role == "patient":
            item.patient_joined_at = item.patient_joined_at or now
        else:
            item.doctor_joined_at = item.doctor_joined_at or now
        item.connection_status = "connected"
        item.updated_by = actor.id
        self._audit(actor, f"telemedicine.{role}.join", "telemedicine_consultation", item, {}, context)
        return item

    def update_consultation(self, consultation_id: UUID, payload: TelemedicineConsultationUpdate, actor: User, context: dict[str, str | None]) -> TelemedicineConsultation:
        item = self._get_consultation(consultation_id)
        for key, value in payload.model_dump().items():
            if value is not None:
                setattr(item, key, value)
        if payload.prescription_text:
            item.prescription_status = "finalized"
        item.updated_by = actor.id
        self._audit(actor, "telemedicine.consultation.update", "telemedicine_consultation", item, payload.model_dump(mode="json"), context)
        return item

    def complete_consultation(self, consultation_id: UUID, payload: TelemedicineConsultationUpdate, actor: User, context: dict[str, str | None]) -> TelemedicineConsultation:
        item = self.update_consultation(consultation_id, payload, actor, context)
        now = datetime.now(UTC)
        item.status = "completed"
        item.ended_at = now
        item.completed_at = now
        item.completed_by_user_id = actor.id
        if item.telemedicine_appointment:
            item.telemedicine_appointment.status = "completed" if not item.follow_up_date else "follow_up_scheduled"
            self._sync_queue_status(item.telemedicine_appointment, "completed", actor, f"Telemedicine consultation completed for {item.telemedicine_appointment.telemedicine_number}")
        if item.opd_visit:
            item.opd_visit.final_diagnosis = item.diagnosis
            item.opd_visit.follow_up_date = item.follow_up_date
            item.opd_visit.follow_up_note = item.follow_up_plan
            item.opd_visit.status = "completed"
        self._audit(actor, "telemedicine.consultation.complete", "telemedicine_consultation", item, {}, context)
        return item

    def list_consultations(self, actor: User, filters: dict | None = None) -> list[TelemedicineConsultation]:
        filters = filters or {}
        stmt = select(TelemedicineConsultation).options(joinedload(TelemedicineConsultation.telemedicine_appointment), joinedload(TelemedicineConsultation.patient), joinedload(TelemedicineConsultation.doctor), joinedload(TelemedicineConsultation.completed_by)).where(TelemedicineConsultation.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(TelemedicineConsultation.branch_id == actor.branch_id, TelemedicineConsultation.branch_id.is_(None)))
        if any(role.is_doctor_role for role in actor.roles):
            stmt = stmt.where(TelemedicineConsultation.doctor_user_id == actor.id)
        if filters.get("status"):
            stmt = stmt.where(TelemedicineConsultation.status == filters["status"])
        if filters.get("doctor_id"):
            stmt = stmt.where(TelemedicineConsultation.doctor_user_id == filters["doctor_id"])
        return list(self.db.scalars(stmt.order_by(TelemedicineConsultation.created_at.desc())).unique())

    def list_chat(self, consultation_id: UUID, actor: User) -> list[TelemedicineChatMessage]:
        self._get_consultation(consultation_id)
        return list(self.db.scalars(select(TelemedicineChatMessage).options(joinedload(TelemedicineChatMessage.sender_user), joinedload(TelemedicineChatMessage.sender_patient)).where(TelemedicineChatMessage.consultation_id == consultation_id).order_by(TelemedicineChatMessage.created_at.asc())).unique())

    def add_chat(self, consultation_id: UUID, payload: TelemedicineChatCreate, actor: User, context: dict[str, str | None]) -> TelemedicineChatMessage:
        consultation = self._get_consultation(consultation_id)
        item = TelemedicineChatMessage(consultation_id=consultation.id, sender_user_id=actor.id, sender_role="doctor" if any(role.is_doctor_role for role in actor.roles) else "staff", **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self._audit(actor, "telemedicine.chat.create", "telemedicine_chat_message", item, {"consultation": str(consultation.id)}, context)
        return item

    def add_file(self, payload: TelemedicineFileCreate, actor: User, context: dict[str, str | None]) -> TelemedicineFile:
        if payload.mime_type not in ALLOWED_FILE_TYPES:
            raise AppException(400, "telemedicine_file_type_blocked", "File type is not allowed")
        if payload.file_size_bytes > MAX_FILE_SIZE:
            raise AppException(400, "telemedicine_file_too_large", "File exceeds telemedicine upload size limit")
        item = TelemedicineFile(branch_id=actor.branch_id, uploaded_by_user_id=actor.id, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self._audit(actor, "telemedicine.file.upload", "telemedicine_file", item, payload.model_dump(mode="json"), context)
        return item

    def list_files(self, consultation_id: UUID | None, appointment_id: UUID | None, actor: User) -> list[TelemedicineFile]:
        stmt = select(TelemedicineFile).options(joinedload(TelemedicineFile.uploaded_by)).where(TelemedicineFile.is_active.is_(True))
        if consultation_id:
            stmt = stmt.where(TelemedicineFile.consultation_id == consultation_id)
        if appointment_id:
            stmt = stmt.where(TelemedicineFile.telemedicine_appointment_id == appointment_id)
        return list(self.db.scalars(stmt.order_by(TelemedicineFile.created_at.desc())).unique())

    def create_investigation(self, consultation_id: UUID, payload: TelemedicineInvestigationCreate, actor: User, context: dict[str, str | None]) -> TelemedicineInvestigationOrder:
        consultation = self._get_consultation(consultation_id)
        lab_order = radiology_order = None
        if payload.service_area == "laboratory":
            lab_order = LabOrder(branch_id=consultation.branch_id, patient_id=consultation.patient_id, visit_id=consultation.opd_visit_id, order_number=self._next_number("LAB-TM", LabOrder.order_number), status="pending", priority="routine", note=payload.instructions, created_by=actor.id, updated_by=actor.id)
            self.db.add(lab_order)
            self.db.flush()
            self.db.add(LabOrderItem(order_id=lab_order.id, test_name=payload.item_name, note=payload.instructions, created_by=actor.id, updated_by=actor.id))
        else:
            radiology_order = RadiologyOrder(branch_id=consultation.branch_id, patient_id=consultation.patient_id, visit_id=consultation.opd_visit_id, order_number=self._next_number("RAD-TM", RadiologyOrder.order_number), study_description=payload.item_name, status="pending", priority="routine", note=payload.instructions, created_by=actor.id, updated_by=actor.id)
            self.db.add(radiology_order)
            self.db.flush()
        item = TelemedicineInvestigationOrder(consultation_id=consultation.id, patient_id=consultation.patient_id, lab_order_id=lab_order.id if lab_order else None, radiology_order_id=radiology_order.id if radiology_order else None, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self._audit(actor, "telemedicine.investigation.create", "telemedicine_investigation_order", item, payload.model_dump(mode="json"), context)
        return item

    def update_payment(self, appointment_id: UUID, payload: TelemedicinePaymentUpdate, actor: User, context: dict[str, str | None]) -> TelemedicineAppointment:
        item = self._get_appointment(appointment_id)
        item.payment_status = payload.payment_status
        item.billing_invoice_id = payload.billing_invoice_id or item.billing_invoice_id
        if item.status == "payment_pending" and payload.payment_status in {"paid", "partial", "not_required"}:
            item.status = "scheduled"
        self._audit(actor, "telemedicine.payment.update", "telemedicine_appointment", item, payload.model_dump(mode="json"), context)
        return item

    def list_settings(self, actor: User) -> list[TelemedicineSetting]:
        stmt = select(TelemedicineSetting).where(TelemedicineSetting.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(TelemedicineSetting.branch_id == actor.branch_id, TelemedicineSetting.branch_id.is_(None)))
        return list(self.db.scalars(stmt.order_by(TelemedicineSetting.setting_key.asc())))

    def upsert_setting(self, payload: TelemedicineSettingCreate, actor: User, context: dict[str, str | None]) -> TelemedicineSetting:
        key = payload.setting_key.strip().lower().replace(" ", "_")
        item = self.db.scalar(select(TelemedicineSetting).where(TelemedicineSetting.setting_key == key, or_(TelemedicineSetting.branch_id == actor.branch_id, TelemedicineSetting.branch_id.is_(None))))
        if not item:
            item = TelemedicineSetting(branch_id=actor.branch_id, setting_key=key, created_by=actor.id)
            self.db.add(item)
        item.setting_value = payload.setting_value
        item.description = payload.description
        item.meta = payload.meta
        item.updated_by = actor.id
        self._audit(actor, "telemedicine.setting.upsert", "telemedicine_setting", item, payload.model_dump(mode="json"), context)
        return item

    def reports(self, actor: User, report_type: str, filters: dict) -> TelemedicineReportRead:
        if report_type in {"online_appointments", "payment_pending", "revenue"}:
            appointments = self.list_appointments(actor, filters)
            rows = [{"number": a.telemedicine_number, "patient": self._patient_name(a.patient), "doctor": a.doctor.full_name if a.doctor else None, "appointment_at": a.appointment_at.isoformat(), "status": a.status, "payment_status": a.payment_status, "fee": float(a.consultation_fee)} for a in appointments]
            totals = {"appointments": len(rows), "revenue": sum(r["fee"] for r in rows if r["payment_status"] in {"paid", "partial"})}
        else:
            consultations = self.list_consultations(actor, filters)
            rows = [{"number": c.telemedicine_appointment.telemedicine_number if c.telemedicine_appointment else None, "patient": self._patient_name(c.patient), "doctor": c.doctor.full_name if c.doctor else None, "status": c.status, "prescription_status": c.prescription_status, "follow_up_date": c.follow_up_date.isoformat() if c.follow_up_date else None} for c in consultations]
            totals = {"consultations": len(rows), "completed": len([r for r in rows if r["status"] == "completed"]), "follow_ups": len([r for r in rows if r["follow_up_date"]])}
        return TelemedicineReportRead(report_type=report_type, filters=filters, rows=rows, totals=totals)

    def _get_appointment(self, appointment_id: UUID) -> TelemedicineAppointment:
        item = self.db.scalar(select(TelemedicineAppointment).options(joinedload(TelemedicineAppointment.patient), joinedload(TelemedicineAppointment.doctor)).where(TelemedicineAppointment.id == appointment_id))
        if not item:
            raise AppException(404, "telemedicine_appointment_not_found", "Telemedicine appointment not found")
        return item

    def _get_consultation(self, consultation_id: UUID) -> TelemedicineConsultation:
        item = self.db.scalar(select(TelemedicineConsultation).options(joinedload(TelemedicineConsultation.telemedicine_appointment), joinedload(TelemedicineConsultation.patient), joinedload(TelemedicineConsultation.doctor), joinedload(TelemedicineConsultation.opd_visit), joinedload(TelemedicineConsultation.completed_by)).where(TelemedicineConsultation.id == consultation_id))
        if not item:
            raise AppException(404, "telemedicine_consultation_not_found", "Telemedicine consultation not found")
        return item

    def _next_number(self, prefix: str, column) -> str:
        stamp = datetime.now(UTC).strftime("%Y%m%d")
        count = self.db.scalar(select(func.count()).select_from(column.class_).where(column.ilike(f"{prefix}-{stamp}-%"))) or 0
        return f"{prefix}-{stamp}-{int(count) + 1:04d}"

    def _next_queue(self, queue_date: date, doctor_id: UUID) -> str:
        start = datetime(queue_date.year, queue_date.month, queue_date.day, tzinfo=UTC)
        count = self.db.scalar(select(func.count(TelemedicineAppointment.id)).where(TelemedicineAppointment.doctor_user_id == doctor_id, TelemedicineAppointment.appointment_at >= start, TelemedicineAppointment.appointment_at < start + timedelta(days=1))) or 0
        return f"TQ-{int(count) + 1:03d}"

    def _normalize_dt(self, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    def _create_slot_booking(self, appointment: TelemedicineAppointment, appointment_at: datetime, actor: User) -> None:
        schedule = self._schedule_for_slot(appointment.doctor_user_id, appointment_at)
        slot_end_at = appointment_at + timedelta(minutes=schedule.slot_duration_minutes)
        booking = DoctorSlotBooking(
            branch_id=appointment.branch_id,
            doctor_user_id=appointment.doctor_user_id,
            patient_id=appointment.patient_id,
            slot_start_at=appointment_at,
            slot_end_at=slot_end_at,
            source_type="telemedicine",
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(booking)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(409, "slot_conflict", "Selected slot is already booked") from exc

    def _release_slot_booking(self, appointment: TelemedicineAppointment) -> None:
        booking = self.db.scalar(
            select(DoctorSlotBooking).where(
                DoctorSlotBooking.doctor_user_id == appointment.doctor_user_id,
                DoctorSlotBooking.patient_id == appointment.patient_id,
                DoctorSlotBooking.slot_start_at == appointment.appointment_at,
                DoctorSlotBooking.source_type == "telemedicine",
            )
        )
        if booking:
            self.db.delete(booking)

    def _schedule_for_slot(self, doctor_user_id: UUID, slot_start_at: datetime) -> DoctorOPDSchedule:
        schedule = self.db.scalar(
            select(DoctorOPDSchedule).where(
                DoctorOPDSchedule.doctor_user_id == doctor_user_id,
                DoctorOPDSchedule.weekday == slot_start_at.date().weekday(),
            )
        )
        if not schedule:
            raise AppException(400, "schedule_not_configured", "Doctor schedule is not configured for this day")

        start_hour, start_minute = [int(part) for part in schedule.start_time.split(":")]
        end_hour, end_minute = [int(part) for part in schedule.end_time.split(":")]
        start_dt = datetime.combine(slot_start_at.date(), time(start_hour, start_minute), tzinfo=UTC)
        end_dt = datetime.combine(slot_start_at.date(), time(end_hour, end_minute), tzinfo=UTC)
        step = timedelta(minutes=schedule.slot_duration_minutes + schedule.buffer_minutes)
        slot_size = timedelta(minutes=schedule.slot_duration_minutes)
        current = start_dt
        while current + slot_size <= end_dt:
            if current == slot_start_at:
                return schedule
            current += step
        raise AppException(400, "slot_not_in_schedule", "Selected slot is outside configured schedule")

    def _patient_name(self, patient: Patient | None) -> str | None:
        return f"{patient.first_name} {patient.last_name}".strip() if patient else None

    def _sync_queue_status(self, appointment: TelemedicineAppointment, status: str, actor: User, notes: str | None = None) -> None:
        token = self.db.scalar(
            select(QueueToken).where(
                QueueToken.queue_scope == "telemedicine",
                QueueToken.source_type == "telemedicine_appointment",
                QueueToken.source_id == appointment.id,
                QueueToken.is_active.is_(True),
            )
        )
        if not token:
            return
        now = datetime.now(UTC)
        token.status = status
        token.notes = notes or token.notes
        token.updated_by = actor.id
        if status in {"called", "recalled"}:
            token.called_at = token.called_at or now
        elif status == "in_progress":
            token.started_at = token.started_at or now
        elif status == "completed":
            token.completed_at = now
        appointment.queue_number = token.token_number
        appointment.estimated_wait_minutes = max(int((now - (token.created_at or now)).total_seconds() // 60), 0)

    def _audit(self, actor: User, action: str, entity_type: str, entity, detail: dict | None, context: dict[str, str | None]) -> None:
        AuditService(self.db).log(actor.id, action, "telemedicine", entity_type, str(getattr(entity, "id", "")), detail or {}, context)
