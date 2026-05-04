from collections.abc import Callable

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.billing import BillingItemConfig, ReferredDoctor
from app.models.branch import Branch
from app.scripts.script_checkpoints import run_checkpoint_step
from uuid import uuid4

BILLING_SERVICES = [
    {
        "service_code": "OPD-CONS-GEN",
        "name": "OPD General Consultation",
        "description": "OPD visit consultation fee (linked to OPD workflow)",
        "unit_price": 15.00,
        "doctor_share_percentage": 20.00,
    },
    {
        "service_code": "OPD-FOLLOWUP",
        "name": "OPD Follow-up Consultation",
        "description": "OPD follow-up visit fee (linked to OPD workflow)",
        "unit_price": 10.00,
        "doctor_share_percentage": 18.00,
    },
    {
        "service_code": "INV-LAB-CBC",
        "name": "Complete Blood Count",
        "description": "Laboratory panel billing item (linked to lab module)",
        "unit_price": 18.00,
        "doctor_share_percentage": 10.00,
    },
    {
        "service_code": "INV-LAB-BMP",
        "name": "Basic Metabolic Panel",
        "description": "Laboratory chemistry panel billing item (linked to lab module)",
        "unit_price": 25.00,
        "doctor_share_percentage": 10.00,
    },
    {
        "service_code": "INV-RAD-CXR",
        "name": "Chest X-Ray",
        "description": "Radiology PA view chest billing item (linked to radiology module)",
        "unit_price": 22.00,
        "doctor_share_percentage": 12.50,
    },
    {
        "service_code": "INV-RAD-US-ABDOMEN",
        "name": "Ultrasound Whole Abdomen",
        "description": "Radiology ultrasound billing item (linked to radiology module)",
        "unit_price": 30.00,
        "doctor_share_percentage": 12.50,
    },
    {
        "service_code": "ADMIN-REG-FEE",
        "name": "Registration Card Fee",
        "description": "Standalone administrative billing service (not linked to a clinical module)",
        "unit_price": 3.00,
        "doctor_share_percentage": 0.00,
    },
]

LEGACY_STANDALONE_CODES = ("CBC", "XR-CHEST", "CONS-GEN")

REFERRED_DOCTORS = [
    {
        "doctor_code": "REF-RAHMAN",
        "full_name": "Dr. Mahmudur Rahman",
        "specialty": "Internal Medicine",
        "phone": "+8801711000001",
        "email": "rahman.ref@hms.local",
    },
    {
        "doctor_code": "REF-FARIA",
        "full_name": "Dr. Faria Ahmed",
        "specialty": "Radiology",
        "phone": "+8801711000002",
        "email": "faria.ref@hms.local",
    },
]


def main() -> None:
    def make_service_step(payload: dict) -> Callable[[], str]:
        def runner() -> str:
            session = SessionLocal()
            try:
                branch = session.scalar(select(Branch).where(Branch.code == "HQ"))
                if not branch:
                    raise RuntimeError("Missing HQ branch. Run seed_access_control first.")

                service = session.scalar(select(BillingItemConfig).where(BillingItemConfig.service_code == payload["service_code"]))
                if not service:
                    service = BillingItemConfig(branch_id=branch.id, source_module="custom", source_entity_id=uuid4())
                    session.add(service)
                service.branch_id = branch.id
                service.service_code = payload["service_code"]
                service.service_name = payload["name"]
                service.billing_instruction = payload["description"]
                service.unit_price = payload["unit_price"]
                service.doctor_share_percentage = payload["doctor_share_percentage"]
                service.is_active = True
                session.commit()
                return f"{payload['service_code']} synchronized"
            finally:
                session.close()

        return runner

    def make_doctor_step(payload: dict) -> Callable[[], str]:
        def runner() -> str:
            session = SessionLocal()
            try:
                branch = session.scalar(select(Branch).where(Branch.code == "HQ"))
                if not branch:
                    raise RuntimeError("Missing HQ branch. Run seed_access_control first.")

                doctor = session.scalar(select(ReferredDoctor).where(ReferredDoctor.doctor_code == payload["doctor_code"]))
                if not doctor:
                    doctor = ReferredDoctor(branch_id=branch.id, **payload)
                    session.add(doctor)
                else:
                    doctor.branch_id = branch.id
                    doctor.full_name = payload["full_name"]
                    doctor.specialty = payload["specialty"]
                    doctor.phone = payload["phone"]
                    doctor.email = payload["email"]
                    doctor.is_active = True
                session.commit()
                return f"{payload['doctor_code']} synchronized"
            finally:
                session.close()

        return runner

    for payload in BILLING_SERVICES:
        run_checkpoint_step("seed_billing_catalog_v4.services", payload["service_code"], make_service_step(payload))

    for payload in REFERRED_DOCTORS:
        run_checkpoint_step("seed_billing_catalog_v4.referred_doctors", payload["doctor_code"], make_doctor_step(payload))

    def sync_services() -> str:
        session = SessionLocal()
        try:
            active_codes = {payload["service_code"] for payload in BILLING_SERVICES}
            for legacy_code in LEGACY_STANDALONE_CODES:
                if legacy_code in active_codes:
                    continue
                legacy = session.scalar(select(BillingItemConfig).where(BillingItemConfig.service_code == legacy_code))
                if legacy:
                    legacy.is_active = False
            session.commit()
            return f"{len(BILLING_SERVICES)} billing services synchronized, legacy standalone seeds disabled"
        finally:
            session.close()

    def sync_doctors() -> str:
        session = SessionLocal()
        try:
            session.commit()
            return f"{len(REFERRED_DOCTORS)} referred doctors synchronized"
        finally:
            session.close()

    run_checkpoint_step("seed_billing_catalog_v4", "services", sync_services)
    run_checkpoint_step("seed_billing_catalog_v4", "referred_doctors", sync_doctors)
    print("Billing catalog seed completed.")


if __name__ == "__main__":
    main()
