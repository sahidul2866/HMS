from __future__ import annotations

import unittest
from uuid import uuid4

from app.core.exceptions import AppException
from app.models.encounter import IPDAdmission
from app.models.inventory import InventoryStore
from app.models.user import User
from app.modules.inventory.service import InventoryService
from app.modules.ipd.service import IPDService


class FakeScopeService:
    def __init__(self, *, values=None, refs=None, unrestricted=False):
        self.values = values or {}
        self.refs = refs or {}
        self.unrestricted = unrestricted

    def has_unrestricted_access(self, actor, *, module=None, scope_type=None):  # noqa: ARG002
        return self.unrestricted

    def has_scope_assignments(self, actor, *scope_types, module=None):  # noqa: ARG002
        return any(self.values.get(scope_type) or self.refs.get(scope_type) for scope_type in scope_types)

    def scope_values(self, actor, scope_type, *, module=None):  # noqa: ARG002
        return set(self.values.get(scope_type, set()))

    def scope_refs(self, actor, scope_type, *, module=None):  # noqa: ARG002
        return set(self.refs.get(scope_type, set()))

    def assert_in_scope(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise AppException(403, "scope_forbidden", "This record is outside your assigned operational scope")


class AssignmentScopeAccessTestCase(unittest.TestCase):
    def make_service(self, scope_service: FakeScopeService) -> IPDService:
        service = IPDService.__new__(IPDService)
        service.scopes = scope_service
        return service

    def make_admission(self, *, ward: str, doctor_id=None, nurse_id=None) -> IPDAdmission:
        return IPDAdmission(
            id=uuid4(),
            patient_id=uuid4(),
            admission_number="IPD-TEST",
            admitted_at="2026-05-13T10:00:00Z",
            ward_name=ward,
            bed_number="B1",
            attending_doctor_name="Dr Test",
            attending_doctor_user_id=doctor_id,
            assigned_nurse_user_id=nurse_id,
            admitted_by_user_id=uuid4(),
        )

    def test_nurse_assigned_to_one_ward_cannot_see_other_ward(self) -> None:
        actor = User(id=uuid4(), username="nurse", email="nurse@test.local", full_name="Nurse", hashed_password="x")
        service = self.make_service(FakeScopeService(values={"ward": {"ward a"}}))

        self.assertTrue(service._admission_in_scope(actor, self.make_admission(ward="Ward A")))
        self.assertFalse(service._admission_in_scope(actor, self.make_admission(ward="Ward B")))

    def test_assigned_doctor_can_see_own_patient_without_ward_scope_match(self) -> None:
        actor = User(id=uuid4(), username="doctor", email="doctor@test.local", full_name="Doctor", hashed_password="x")
        service = self.make_service(FakeScopeService(values={"ward": {"ward a"}}))

        self.assertTrue(service._admission_in_scope(actor, self.make_admission(ward="Ward B", doctor_id=actor.id)))

    def test_supervisor_unrestricted_scope_can_see_all_wards(self) -> None:
        actor = User(id=uuid4(), username="supervisor", email="supervisor@test.local", full_name="Supervisor", hashed_password="x")
        service = self.make_service(FakeScopeService(values={"ward": {"ward a"}}, unrestricted=True))

        self.assertTrue(service._admission_in_scope(actor, self.make_admission(ward="Ward B")))

    def test_inventory_user_scope_accepts_store_name(self) -> None:
        actor = User(id=uuid4(), username="store_user", email="store@test.local", full_name="Store User", hashed_password="x")
        service = InventoryService.__new__(InventoryService)
        service.scopes = FakeScopeService(values={"store": {"opd store"}})
        store = InventoryStore(id=uuid4(), code="OPD", name="OPD Store", store_type="sub_store", is_active=True)

        service._assert_store_in_scope(actor, store)

    def test_inventory_user_scope_rejects_other_store(self) -> None:
        actor = User(id=uuid4(), username="store_user", email="store@test.local", full_name="Store User", hashed_password="x")
        service = InventoryService.__new__(InventoryService)
        service.scopes = FakeScopeService(values={"store": {"opd store"}})
        store = InventoryStore(id=uuid4(), code="MAIN", name="Main Inventory", store_type="main", is_active=True)

        with self.assertRaises(AppException):
            service._assert_store_in_scope(actor, store)

    def test_inventory_supervisor_override_can_cross_store_scope(self) -> None:
        actor = User(id=uuid4(), username="inventory_manager", email="manager@test.local", full_name="Inventory Manager", hashed_password="x")
        service = InventoryService.__new__(InventoryService)
        service.scopes = FakeScopeService(values={"store": {"opd store"}}, unrestricted=True)
        store = InventoryStore(id=uuid4(), code="MAIN", name="Main Inventory", store_type="main", is_active=True)

        service._assert_store_in_scope(actor, store)


if __name__ == "__main__":
    unittest.main()
