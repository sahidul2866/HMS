from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.encounter import Appointment
from app.models.user import User
from app.modules.patients.service import PatientsService
from app.modules.users.repository import UsersRepository
from app.schemas.portal import PatientAppointmentCreate, PatientAppointmentRead, PatientPortalOverviewRead
from app.schemas.user import UserRead


class PatientPortalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UsersRepository(db)
        self.patients = PatientsService(db)

    def get_overview(self, actor: User) -> PatientPortalOverviewRead:
        patient_id = self._require_patient_account(actor)
        history = self.patients.get_clinical_history(patient_id, actor)
        appointments = self.list_appointments(actor)
        doctors = [UserRead.model_validate(item, from_attributes=True) for item in self.users.list_doctors()]
        return PatientPortalOverviewRead(patient=history, appointments=appointments, doctors=doctors)

    def list_appointments(self, actor: User) -> list[PatientAppointmentRead]:
        patient_id = self._require_patient_account(actor)
        stmt = (
            select(Appointment)
            .join(Appointment.doctor)
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.appointment_at.desc())
        )
        appointments = list(self.db.scalars(stmt))
        return [
            PatientAppointmentRead(
                id=item.id,
                appointment_number=item.appointment_number,
                doctor_user_id=item.doctor_user_id,
                doctor_name=item.doctor.full_name,
                appointment_at=item.appointment_at,
                status=item.status,
                reason=item.reason,
                note=item.note,
            )
            for item in appointments
        ]

    def create_appointment(self, payload: PatientAppointmentCreate, actor: User) -> PatientAppointmentRead:
        patient_id = self._require_patient_account(actor)
        doctor = self.users.get_user(payload.doctor_user_id)
        if not doctor or not doctor.is_active or not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(404, "doctor_not_found", "Doctor not found")
        appointment = Appointment(
            branch_id=actor.branch_id or doctor.branch_id,
            patient_id=patient_id,
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
        return PatientAppointmentRead(
            id=appointment.id,
            appointment_number=appointment.appointment_number,
            doctor_user_id=appointment.doctor_user_id,
            doctor_name=doctor.full_name,
            appointment_at=appointment.appointment_at,
            status=appointment.status,
            reason=appointment.reason,
            note=appointment.note,
        )

    def _require_patient_account(self, actor: User):
        if not actor.patient_id:
            raise AppException(403, "patient_account_required", "This account is not linked to a patient")
        return actor.patient_id
