from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.encounter import Appointment
from app.models.user import User
from app.modules.opd.service import OPDService
from app.schemas.appointment import AppointmentCheckInRequest, AppointmentRead
from app.schemas.encounter import OPDVisitCreate


class AppointmentsService:
    def __init__(self, db: Session) -> None:
        self.db = db

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

    def update_status(self, appointment_id, status: str, actor: User) -> AppointmentRead:
        appointment = self._get_accessible_appointment(appointment_id, actor)
        appointment.status = status
        appointment.updated_by = actor.id
        self.db.commit()
        self.db.refresh(appointment)
        return self._serialize(appointment)

    def check_in_to_opd(self, appointment_id, payload: AppointmentCheckInRequest, actor: User, context: dict[str, str | None]):
        appointment = self._get_accessible_appointment(appointment_id, actor)
        if appointment.status == "checked_in":
            raise AppException(409, "appointment_already_checked_in", "Appointment already checked in")
        existing_visit = self.db.scalar(select(Appointment).join(Appointment.opd_visits).where(Appointment.id == appointment.id))
        if existing_visit:
            raise AppException(409, "appointment_already_linked", "Appointment already linked to an OPD visit")
        visit = OPDService(self.db).create_visit(
            OPDVisitCreate(
                patient_id=appointment.patient_id,
                visit_date=appointment.appointment_at.date(),
                department_name=payload.department_name,
                doctor_user_id=appointment.doctor_user_id,
                consulting_doctor_name=appointment.doctor.full_name,
                chief_complaint=payload.chief_complaint or appointment.reason,
                consultation_fee=payload.consultation_fee,
                note=payload.note or appointment.note,
            ),
            actor,
            context,
        )
        visit.source_appointment_id = appointment.id
        visit.updated_by = actor.id
        appointment.status = "checked_in"
        appointment.updated_by = actor.id
        self.db.commit()
        self.db.refresh(appointment)
        return visit

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

    def _serialize(self, appointment: Appointment) -> AppointmentRead:
        return AppointmentRead(
            id=appointment.id,
            appointment_number=appointment.appointment_number,
            patient_id=appointment.patient_id,
            patient_name=f"{appointment.patient.first_name} {appointment.patient.last_name}",
            doctor_user_id=appointment.doctor_user_id,
            doctor_name=appointment.doctor.full_name,
            appointment_at=appointment.appointment_at,
            status=appointment.status,
            reason=appointment.reason,
            note=appointment.note,
        )
