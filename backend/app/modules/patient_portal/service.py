from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.encounter import Appointment, DoctorSlotBooking
from app.models.user import User
from app.modules.patients.service import PatientsService
from app.modules.appointments.service import AppointmentsService
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
        appointment = AppointmentsService(self.db).create_portal_appointment(patient_id, payload, actor)
        return PatientAppointmentRead(
            id=appointment.id,
            appointment_number=appointment.appointment_number,
            doctor_user_id=appointment.doctor_user_id,
            doctor_name=appointment.doctor_name,
            appointment_at=appointment.appointment_at,
            status=appointment.status,
            reason=appointment.reason,
            note=appointment.note,
        )

    def get_doctor_slots(self, doctor_user_id, slot_date, actor):
        self._require_patient_account(actor)
        return AppointmentsService(self.db).get_doctor_slots(doctor_user_id, slot_date, actor)

    def update_appointment_status(self, appointment_id, status: str, actor: User) -> PatientAppointmentRead:
        patient_id = self._require_patient_account(actor)
        stmt = (
            select(Appointment)
            .join(Appointment.doctor)
            .where(Appointment.id == appointment_id, Appointment.patient_id == patient_id)
        )
        appointment = self.db.scalar(stmt)
        if not appointment:
            raise AppException(404, "appointment_not_found", "Appointment not found")
        if appointment.status not in {"scheduled", "confirmed"}:
            raise AppException(409, "appointment_status_locked", "Only scheduled appointments can be cancelled from the portal")

        appointment.status = status
        appointment.updated_by = actor.id
        booking = self.db.scalar(select(DoctorSlotBooking).where(DoctorSlotBooking.appointment_id == appointment.id))
        if booking:
            self.db.delete(booking)
        self.db.commit()
        self.db.refresh(appointment)
        return PatientAppointmentRead(
            id=appointment.id,
            appointment_number=appointment.appointment_number,
            doctor_user_id=appointment.doctor_user_id,
            doctor_name=appointment.doctor.full_name,
            appointment_at=appointment.appointment_at,
            status=appointment.status,
            reason=appointment.reason,
            note=appointment.note,
        )

    def _require_patient_account(self, actor: User):
        if not actor.patient_id:
            raise AppException(403, "patient_account_required", "This account is not linked to a patient")
        return actor.patient_id
