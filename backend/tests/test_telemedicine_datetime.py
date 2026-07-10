from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import app.main  # noqa: F401 - register all SQLAlchemy models

from app.models.patient import Patient
from app.models.encounter import DoctorOPDSchedule, DoctorSlotBooking
from app.models.telemedicine import TelemedicineAppointment
from app.models.user import User
from app.modules.telemedicine.service import TelemedicineService
from app.schemas.telemedicine import TelemedicineAppointmentCreate


class FakeDB:
    def __init__(self, patient: Patient, doctor: User) -> None:
        self.patient = patient
        self.doctor = doctor
        self.added = None
        self.bookings = []

    def get(self, model, entity_id):  # noqa: ANN001
        if model is Patient and entity_id == self.patient.id:
            return self.patient
        if model is User and entity_id == self.doctor.id:
            return self.doctor
        return None

    def scalar(self, stmt):  # noqa: ANN001, ARG002
        stmt_text = str(stmt)
        if "doctor_opd_schedules" in stmt_text:
            return DoctorOPDSchedule(
                id=uuid4(),
                doctor_user_id=self.doctor.id,
                weekday=(datetime.now(UTC) + timedelta(days=1)).weekday(),
                start_time="09:00",
                end_time="17:00",
                slot_duration_minutes=15,
                buffer_minutes=0,
            )
        return 0

    def add(self, entity) -> None:  # noqa: ANN001
        self.added = entity
        if isinstance(entity, DoctorSlotBooking):
            self.bookings.append(entity)

    def flush(self) -> None:
        if isinstance(self.added, TelemedicineAppointment) and self.added.id is None:
            self.added.id = uuid4()


class TelemedicineDatetimeTestCase(unittest.TestCase):
    def test_create_appointment_accepts_naive_future_datetime(self) -> None:
        patient = Patient(id=uuid4(), patient_number="PAT-TEST", first_name="Test", last_name="Patient")
        doctor = User(id=uuid4(), username="doctor", email="doctor@test.local", full_name="Dr Test", hashed_password="x")
        actor = User(id=uuid4(), username="frontdesk", email="frontdesk@test.local", full_name="Front Desk", hashed_password="x")
        appointment_at = (datetime.now(UTC) + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0, tzinfo=None)
        payload = TelemedicineAppointmentCreate(
            patient_id=patient.id,
            doctor_user_id=doctor.id,
            appointment_at=appointment_at,
            consultation_fee=Decimal("0"),
        )

        with patch("app.modules.telemedicine.service.QueueService") as queue_service_class, patch("app.modules.telemedicine.service.AuditService") as audit_service_class:
            db = FakeDB(patient, doctor)
            service = TelemedicineService(db)
            original_next_number = service._next_number
            number_calls = []

            def record_next_number(prefix, column):  # noqa: ANN001
                number_calls.append((prefix, column.key))
                return original_next_number(prefix, column)

            service._next_number = record_next_number  # type: ignore[method-assign]
            item = service.create_appointment(payload, actor, {})

        self.assertIs(item.appointment_at.tzinfo, UTC)
        self.assertIn(("ROOM", "meeting_id"), number_calls)
        self.assertEqual(len(db.bookings), 1)
        self.assertEqual(db.bookings[0].source_type, "telemedicine")
        self.assertEqual(db.bookings[0].slot_start_at, item.appointment_at)
        queue_service_class.return_value.ensure_token.assert_called_once()
        audit_service_class.return_value.log.assert_called_once()


if __name__ == "__main__":
    unittest.main()
