from __future__ import annotations

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from app.models.encounter import Appointment
from app.models.user import User
from app.modules.appointments.service import AppointmentsService
from app.schemas.appointment import AppointmentCheckInRequest


class FakeDB:
    def scalar(self, stmt):  # noqa: ANN001, ARG002
        return None

    def commit(self) -> None:
        pass

    def refresh(self, entity) -> None:  # noqa: ANN001
        pass


class AppointmentCheckInTestCase(unittest.TestCase):
    def test_check_in_passes_source_appointment_before_opd_slot_booking(self) -> None:
        appointment = Appointment(
            id=uuid4(),
            branch_id=uuid4(),
            patient_id=uuid4(),
            doctor_user_id=uuid4(),
            appointment_number="APT-TEST-001",
            appointment_at=datetime(2026, 6, 18, 10, 0, tzinfo=UTC),
            slot_start_at=datetime(2026, 6, 18, 10, 0, tzinfo=UTC),
            status="scheduled",
            reason="Fever",
        )
        appointment.doctor = User(
            id=appointment.doctor_user_id,
            username="doctor",
            email="doctor@test.local",
            full_name="Dr Test",
            hashed_password="x",
        )
        actor = User(id=uuid4(), username="frontdesk", email="frontdesk@test.local", full_name="Front Desk", hashed_password="x")
        visit = SimpleNamespace(id=uuid4(), updated_by=None)

        service = AppointmentsService(FakeDB())  # type: ignore[arg-type]
        service._get_accessible_appointment = lambda appointment_id, actor: appointment  # type: ignore[method-assign, arg-type]

        with patch("app.modules.appointments.service.OPDService") as opd_service_class:
            opd_service_class.return_value.create_visit.return_value = visit

            service.check_in_to_opd(
                appointment.id,
                AppointmentCheckInRequest(department_name="General OPD", consultation_fee=0),
                actor,
                {},
            )

        self.assertEqual(opd_service_class.return_value.create_visit.call_args.kwargs["source_appointment_id"], appointment.id)
        self.assertEqual(appointment.status, "checked_in")


if __name__ == "__main__":
    unittest.main()
