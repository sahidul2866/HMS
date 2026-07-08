from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.encounter import OPDVisit
from app.models.queue import QueueToken
from app.models.telemedicine import TelemedicineAppointment, TelemedicineConsultation
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.opd.service import OPDService
from app.modules.queue.service import QueueService
from app.modules.telemedicine.service import TelemedicineService
from app.schemas.telemedicine import TelemedicineConsultationUpdate
from app.schemas.outpatient import OutpatientDashboardRead, OutpatientQueueAction, OutpatientReportRead, UnifiedOutpatientQueueItem


ACTION_TO_QUEUE_STATUS = {
    "call": "called",
    "skip": "skipped",
    "recall": "recalled",
    "start": "in_progress",
    "complete": "completed",
    "no_show": "no_show",
    "cancel": "cancelled",
}


class OutpatientService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.queue = QueueService(db)

    def dashboard(self, actor: User, filters: dict) -> OutpatientDashboardRead:
        items = self.queue_items(actor, filters)
        by_visit_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for item in items:
            by_visit_type[item.visit_mode] = by_visit_type.get(item.visit_mode, 0) + 1
            by_status[item.status] = by_status.get(item.status, 0) + 1
        return OutpatientDashboardRead(
            opd_waiting=len([i for i in items if i.visit_mode == "opd" and i.queue_status in {"waiting", "registered", "recalled"}]),
            telemedicine_waiting=len([i for i in items if i.visit_mode == "telemedicine" and i.queue_status in {"waiting", "registered", "recalled"}]),
            called=len([i for i in items if i.queue_status == "called"]),
            in_consultation=len([i for i in items if i.status in {"in_consultation", "in_progress"}]),
            completed_today=len([i for i in items if i.status == "completed"]),
            no_show=len([i for i in items if i.status == "no_show"]),
            pending_payments=len([i for i in items if i.payment_status and i.payment_status not in {"paid", "not_required"}]),
            pending_prescriptions=self._pending_prescriptions(actor),
            by_visit_type=by_visit_type,
            by_status=by_status,
        )

    def queue_items(self, actor: User, filters: dict | None = None) -> list[UnifiedOutpatientQueueItem]:
        filters = filters or {}
        visit_mode = filters.get("visit_mode")
        doctor_id = filters.get("doctor_id")
        status = filters.get("status")
        items: list[UnifiedOutpatientQueueItem] = []
        if visit_mode in {None, "", "opd"}:
            for token in self.queue.list_tokens(actor, queue_scope="opd", doctor_user_id=doctor_id, status=None, token_date=date.today()):
                visit = self.db.scalar(select(OPDVisit).options(joinedload(OPDVisit.patient), joinedload(OPDVisit.consulting_doctor)).where(OPDVisit.id == token.visit_id))
                if not visit or (status and visit.status != status):
                    continue
                items.append(self._opd_item(token, visit))
        if visit_mode in {None, "", "telemedicine"}:
            for token in self.queue.list_tokens(actor, queue_scope="telemedicine", doctor_user_id=doctor_id, status=None, token_date=date.today()):
                appointment = self.db.scalar(select(TelemedicineAppointment).options(joinedload(TelemedicineAppointment.patient), joinedload(TelemedicineAppointment.doctor)).where(TelemedicineAppointment.id == token.source_id))
                if not appointment or (status and appointment.status != status):
                    continue
                items.append(self._telemedicine_item(token, appointment))
        return sorted(items, key=lambda item: (item.priority != "urgent", item.appointment_at or datetime.now(UTC), item.waiting_minutes))

    def action(self, token_id: UUID, payload: OutpatientQueueAction, actor: User, context: dict[str, str | None]) -> UnifiedOutpatientQueueItem:
        token = self.db.get(QueueToken, token_id)
        if not token:
            raise AppException(404, "outpatient_token_not_found", "Queue token not found")
        if payload.action not in ACTION_TO_QUEUE_STATUS:
            raise AppException(400, "outpatient_action_invalid", "Unsupported outpatient queue action")
        queue_status = ACTION_TO_QUEUE_STATUS[payload.action]
        if token.queue_scope == "telemedicine" and payload.action == "start":
            appointment = self.db.get(TelemedicineAppointment, token.source_id)
            if not appointment:
                raise AppException(404, "telemedicine_appointment_not_found", "Telemedicine appointment not found")
            consultation = TelemedicineService(self.db).start_consultation(appointment.id, actor, context)
            self.db.commit()
            self.db.refresh(consultation)
        elif token.queue_scope == "telemedicine" and payload.action == "complete":
            consultation = self.db.scalar(select(TelemedicineConsultation).where(TelemedicineConsultation.telemedicine_appointment_id == token.source_id))
            if consultation:
                TelemedicineService(self.db).complete_consultation(consultation.id, TelemedicineConsultationUpdate(remarks=payload.notes), actor, context)
                self.db.commit()
            else:
                self.queue.update_status(token.id, queue_status, actor, notes=payload.notes)
        else:
            self.queue.update_status(token.id, queue_status, actor, notes=payload.notes)
            if token.queue_scope == "opd" and token.visit_id:
                visit_status = {"called": "waiting", "skipped": "waiting", "recalled": "waiting", "in_progress": "in_consultation", "completed": "completed", "no_show": "no_show", "cancelled": "cancelled"}.get(queue_status)
                if visit_status:
                    visit = self.db.get(OPDVisit, token.visit_id)
                    if visit:
                        visit.status = visit_status
                        visit.updated_by = actor.id
                        self.db.commit()
        token = self.db.get(QueueToken, token_id)
        AuditService(self.db).log(actor.id, f"outpatient.queue.{payload.action}", "outpatient", "queue_token", str(token_id), {"queue_scope": token.queue_scope if token else None}, context)
        if token and token.queue_scope == "telemedicine":
            appointment = self.db.scalar(select(TelemedicineAppointment).options(joinedload(TelemedicineAppointment.patient), joinedload(TelemedicineAppointment.doctor)).where(TelemedicineAppointment.id == token.source_id))
            return self._telemedicine_item(self.queue._read(token), appointment)
        visit = self.db.scalar(select(OPDVisit).options(joinedload(OPDVisit.patient), joinedload(OPDVisit.consulting_doctor)).where(OPDVisit.id == token.visit_id))
        return self._opd_item(self.queue._read(token), visit)

    def reports(self, actor: User, report_type: str, filters: dict) -> OutpatientReportRead:
        rows = [item.model_dump(mode="json") for item in self.queue_items(actor, filters)]
        totals = {
            "total": len(rows),
            "opd": len([r for r in rows if r["visit_mode"] == "opd"]),
            "telemedicine": len([r for r in rows if r["visit_mode"] == "telemedicine"]),
            "completed": len([r for r in rows if r["status"] == "completed"]),
            "no_show": len([r for r in rows if r["status"] == "no_show"]),
        }
        return OutpatientReportRead(report_type=report_type, filters=filters, rows=rows, totals=totals)

    def _opd_item(self, token, visit: OPDVisit) -> UnifiedOutpatientQueueItem:
        return UnifiedOutpatientQueueItem(
            token_id=token.id,
            source_id=visit.id,
            source_type="opd_visit",
            visit_mode="opd",
            visit_type=visit.visit_type,
            number=visit.visit_number,
            queue_number=token.token_number,
            patient_id=visit.patient_id,
            patient_name=self._patient_name(visit.patient),
            doctor_user_id=visit.consulting_doctor_user_id,
            doctor_name=visit.consulting_doctor_name,
            department_name=visit.department_name,
            appointment_at=visit.slot_start_at,
            status=visit.status,
            queue_status=token.status,
            payment_status=visit.consultation_payment_status,
            waiting_minutes=token.waiting_minutes,
            priority=token.priority,
            current_complaint=visit.chief_complaint,
            has_video_panel=False,
            meta=token.meta or {},
        )

    def _telemedicine_item(self, token, appointment: TelemedicineAppointment) -> UnifiedOutpatientQueueItem:
        return UnifiedOutpatientQueueItem(
            token_id=token.id,
            source_id=appointment.id,
            source_type="telemedicine_appointment",
            visit_mode="telemedicine",
            visit_type=appointment.visit_type,
            number=appointment.telemedicine_number,
            queue_number=token.token_number,
            patient_id=appointment.patient_id,
            patient_name=self._patient_name(appointment.patient),
            doctor_user_id=appointment.doctor_user_id,
            doctor_name=appointment.doctor.full_name if appointment.doctor else None,
            department_name=appointment.department_name,
            appointment_at=appointment.appointment_at,
            status=appointment.status,
            queue_status=token.status,
            payment_status=appointment.payment_status,
            waiting_minutes=token.waiting_minutes,
            priority=token.priority,
            join_url=appointment.join_url,
            current_complaint=appointment.consultation_reason,
            has_video_panel=True,
            meta=token.meta or {},
        )

    def _pending_prescriptions(self, actor: User) -> int:
        stmt = select(func.count(TelemedicineConsultation.id)).where(TelemedicineConsultation.prescription_status == "pending")
        if actor.branch_id:
            stmt = stmt.where(or_(TelemedicineConsultation.branch_id == actor.branch_id, TelemedicineConsultation.branch_id.is_(None)))
        return int(self.db.scalar(stmt) or 0)

    def _patient_name(self, patient) -> str | None:
        return f"{patient.first_name} {patient.last_name}".strip() if patient else None
