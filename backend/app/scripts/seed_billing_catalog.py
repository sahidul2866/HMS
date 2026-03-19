from collections.abc import Callable

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.billing import BillingService, ReferredDoctor
from app.models.branch import Branch
from app.scripts.script_checkpoints import run_checkpoint_step

BILLING_SERVICES = [
    {
        "service_code": "CBC",
        "name": "Complete Blood Count",
        "description": "Routine hematology panel",
        "unit_price": 18.00,
        "doctor_share_percentage": 10.00,
    },
    {
        "service_code": "XR-CHEST",
        "name": "Chest X-Ray",
        "description": "PA view chest radiology",
        "unit_price": 22.00,
        "doctor_share_percentage": 12.50,
    },
    {
        "service_code": "CONS-GEN",
        "name": "General Consultation",
        "description": "Outpatient consultation fee",
        "unit_price": 15.00,
        "doctor_share_percentage": 20.00,
    },
]

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

                service = session.scalar(select(BillingService).where(BillingService.service_code == payload["service_code"]))
                if not service:
                    service = BillingService(branch_id=branch.id, **payload)
                    session.add(service)
                else:
                    service.branch_id = branch.id
                    service.name = payload["name"]
                    service.description = payload["description"]
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
        run_checkpoint_step("seed_billing_catalog.services", payload["service_code"], make_service_step(payload))

    for payload in REFERRED_DOCTORS:
        run_checkpoint_step("seed_billing_catalog.referred_doctors", payload["doctor_code"], make_doctor_step(payload))

    def sync_services() -> str:
        session = SessionLocal()
        try:
            session.commit()
            return f"{len(BILLING_SERVICES)} billing services synchronized"
        finally:
            session.close()

    def sync_doctors() -> str:
        session = SessionLocal()
        try:
            session.commit()
            return f"{len(REFERRED_DOCTORS)} referred doctors synchronized"
        finally:
            session.close()

    run_checkpoint_step("seed_billing_catalog", "services", sync_services)
    run_checkpoint_step("seed_billing_catalog", "referred_doctors", sync_doctors)
    print("Billing catalog seed completed.")


if __name__ == "__main__":
    main()
