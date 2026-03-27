from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.encounter import Appointment
from app.models.user import User
from app.modules.opd.service import OPDService
from app.modules.patients.repository import PatientsRepository
from app.modules.users.repository import UsersRepository
from app.schemas.appointment import AppointmentCheckInRequest, AppointmentCreate, AppointmentRead
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
        patient = self.patients.get_patient(payload.patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")

        doctor = self.users.get_user(payload.doctor_user_id)
        if not doctor or not doctor.is_active or not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(404, "doctor_not_found", "Doctor not found")
        if actor.branch_id and doctor.branch_id and actor.branch_id != doctor.branch_id:
            raise AppException(403, "forbidden", "Doctor belongs to a different branch")

        appointment = Appointment(
            branch_id=actor.branch_id or patient.branch_id or doctor.branch_id,
            patient_id=patient.id,
            doctor_user_id=doctor.id,
            appointment_number=f"APT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            appointment_at=payload.appointment_at,
            status="scheduled",
            reason=payload.reason,
            note=payload.note,
            booked_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        appointment = self._get_accessible_appointment(appointment.id, actor)
        return self._serialize(appointment)

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
