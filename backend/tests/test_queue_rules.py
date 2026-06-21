from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import app.main  # noqa: F401 - register all SQLAlchemy models

from app.modules.queue.service import QueueService, TOKEN_TRANSITIONS


class QueueRuleTestCase(unittest.TestCase):
    def test_opd_token_uses_doctor_code_and_serial(self) -> None:
        doctor_id = uuid4()
        service = QueueService.__new__(QueueService)
        service.db = SimpleNamespace(get=lambda model, entity_id: SimpleNamespace(username="dr_rahman", full_name="Dr. Rahman") if entity_id == doctor_id else None)
        service._setting_value = lambda *args: {}  # type: ignore[method-assign]

        token = service._format_token("opd", "Medicine", "consultation", 7, doctor_id, uuid4())

        self.assertEqual(token, "RAHMAN-007")

    def test_completed_is_only_allowed_after_consultation_started(self) -> None:
        self.assertNotIn("completed", TOKEN_TRANSITIONS["waiting"])
        self.assertIn("completed", TOKEN_TRANSITIONS["in_progress"])

    def test_late_arrival_sorts_by_check_in_instead_of_old_slot(self) -> None:
        service = QueueService.__new__(QueueService)
        now = datetime.now(UTC)
        late = SimpleNamespace(priority="normal", due_at=now - timedelta(hours=2), created_at=now, token_sequence=1, meta={"late_arrival": True})
        on_time = SimpleNamespace(priority="normal", due_at=now - timedelta(minutes=5), created_at=now - timedelta(minutes=1), token_sequence=2, meta={})

        self.assertGreater(service._sort_key(late), service._sort_key(on_time))


if __name__ == "__main__":
    unittest.main()
