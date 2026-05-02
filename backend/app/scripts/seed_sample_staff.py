from collections.abc import Callable

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.branch import Branch
from app.models.department import Department
from app.models.patient import Patient
from app.models.patient_portal_account import PatientPortalAccount
from app.models.role import Role
from app.models.user import User
from app.scripts.script_checkpoints import run_checkpoint_step

SAMPLE_USERS = [
    {
        "username": "dr_rahman",
        "email": "dr.rahman@hms.local",
        "full_name": "Dr. Rahman",
        "password": "Doctor123!",
        "role_code": "DOCTOR",
        "department_code": "CLN",
    },
    {
        "username": "pharma_nadia",
        "email": "nadia.pharmacy@hms.local",
        "full_name": "Nadia Sultana",
        "password": "Pharma123!",
        "role_code": "PHARMACIST",
        "department_code": "PHR",
    },
    {
        "username": "acct_kamal",
        "email": "kamal.accounts@hms.local",
        "full_name": "Kamal Hossain",
        "password": "Account123!",
        "role_code": "ACCOUNTANT",
        "department_code": "ACC",
    },
    {
        "username": "ref_dr_sadia",
        "email": "sadia.referral@hms.local",
        "full_name": "Dr. Sadia Noor",
        "password": "Doctor123!",
        "role_code": "REFERRABLE_DOCTOR",
        "department_code": "CLN",
    },
]

DEMO_PATIENT_USERS = [
    {
        "username": "patient_fatema",
        "email": "fatema.patient@hms.local",
        "full_name": "Fatema Akter",
        "password": "Patient123!",
        "phone": "01700000001",
        "gender": "female",
    },
    {
        "username": "patient_rakib",
        "email": "rakib.patient@hms.local",
        "full_name": "Rakib Hasan",
        "password": "Patient123!",
        "phone": "01700000002",
        "gender": "male",
    },
    {
        "username": "patient_sumaiya",
        "email": "sumaiya.patient@hms.local",
        "full_name": "Sumaiya Jahan",
        "password": "Patient123!",
        "phone": "01700000003",
        "gender": "female",
    },
    {
        "username": "patient_arman",
        "email": "arman.patient@hms.local",
        "full_name": "Arman Kabir",
        "password": "Patient123!",
        "phone": "01700000004",
        "gender": "male",
    },
    {
        "username": "patient_nabila",
        "email": "nabila.patient@hms.local",
        "full_name": "Nabila Rahman",
        "password": "Patient123!",
        "phone": "01700000005",
        "gender": "female",
    },
    {
        "username": "patient_mahin",
        "email": "mahin.patient@hms.local",
        "full_name": "Mahin Chowdhury",
        "password": "Patient123!",
        "phone": "01700000006",
        "gender": "male",
    },
    {
        "username": "patient_tasnia",
        "email": "tasnia.patient@hms.local",
        "full_name": "Tasnia Karim",
        "password": "Patient123!",
        "phone": "01700000007",
        "gender": "female",
    },
    {
        "username": "patient_sabbir",
        "email": "sabbir.patient@hms.local",
        "full_name": "Sabbir Ahmed",
        "password": "Patient123!",
        "phone": "01700000008",
        "gender": "male",
    },
    {
        "username": "patient_ritu",
        "email": "ritu.patient@hms.local",
        "full_name": "Ritu Saha",
        "password": "Patient123!",
        "phone": "01700000009",
        "gender": "female",
    },
    {
        "username": "patient_farhan",
        "email": "farhan.patient@hms.local",
        "full_name": "Farhan Islam",
        "password": "Patient123!",
        "phone": "01700000010",
        "gender": "male",
    },
]


def get_required(session, model, field, value, label: str):
    item = session.scalar(select(model).where(field == value))
    if not item:
        raise RuntimeError(f"Missing required {label}: {value}. Run seed_access_control first.")
    return item


def create_or_update_staff_user(session, *, branch: Branch, role: Role, department: Department, payload: dict) -> None:
    user = session.scalar(select(User).where(User.username == payload["username"]))
    if not user:
        user = User(
            username=payload["username"],
            email=payload["email"],
            full_name=payload["full_name"],
            hashed_password=get_password_hash(payload["password"]),
            branch_id=branch.id,
            department_id=department.id,
            is_active=True,
        )
        session.add(user)
        session.flush()
    else:
        user.email = payload["email"]
        user.full_name = payload["full_name"]
        user.branch_id = branch.id
        user.department_id = department.id
        user.is_active = True
    user.roles = [role]


def create_or_update_demo_patient_user(session, *, branch: Branch, payload: dict) -> None:
    patient = session.scalar(select(Patient).where(Patient.email == payload["email"]))
    first_name, _, last_name = payload["full_name"].partition(" ")
    if not patient:
        patient = Patient(
            branch_id=branch.id,
            patient_number=f"PAT-DEMO-{payload['username'][-4:]}",
            first_name=first_name,
            last_name=last_name or "Patient",
            phone=payload["phone"],
            email=payload["email"],
            gender=payload["gender"],
        )
        session.add(patient)
        session.flush()
    else:
        patient.branch_id = branch.id
        patient.first_name = first_name
        patient.last_name = last_name or "Patient"
        patient.phone = payload["phone"]
        patient.email = payload["email"]
        patient.gender = payload["gender"]

    account = session.scalar(select(PatientPortalAccount).where(PatientPortalAccount.username == payload["username"]))
    if not account:
        account = PatientPortalAccount(
            username=payload["username"],
            email=payload["email"],
            full_name=payload["full_name"],
            hashed_password=get_password_hash(payload["password"]),
            branch_id=branch.id,
            patient_id=patient.id,
            phone=payload["phone"],
            is_active=True,
        )
        session.add(account)
        session.flush()
    else:
        account.email = payload["email"]
        account.full_name = payload["full_name"]
        account.branch_id = branch.id
        account.patient_id = patient.id
        account.phone = payload["phone"]
        account.is_active = True

    legacy_user = session.scalar(select(User).where(User.username == payload["username"]))
    if legacy_user and legacy_user.patient_id:
        legacy_user.is_active = False


def main() -> None:
    def make_staff_step(payload: dict) -> Callable[[], str]:
        def runner() -> str:
            session = SessionLocal()
            try:
                branch = get_required(session, Branch, Branch.code, "HQ", "branch")
                role = get_required(session, Role, Role.code, payload["role_code"], "role")
                department = get_required(session, Department, Department.code, payload["department_code"], "department")
                create_or_update_staff_user(session, branch=branch, role=role, department=department, payload=payload)
                session.commit()
                return f"{payload['username']} synchronized"
            finally:
                session.close()

        return runner

    for payload in SAMPLE_USERS:
        run_checkpoint_step("seed_sample_staff", payload["username"], make_staff_step(payload))

    def make_demo_patient_step(payload: dict) -> Callable[[], str]:
        def runner() -> str:
            session = SessionLocal()
            try:
                branch = get_required(session, Branch, Branch.code, "HQ", "branch")
                create_or_update_demo_patient_user(session, branch=branch, payload=payload)
                session.commit()
                return f"{payload['username']} synchronized"
            finally:
                session.close()

        return runner

    for payload in DEMO_PATIENT_USERS:
        run_checkpoint_step("seed_sample_staff", payload["username"], make_demo_patient_step(payload))

    print("Sample staff seed completed.")
    print("Doctor: dr_rahman / Doctor123!")
    print("Referral Doctor: ref_dr_sadia / Doctor123!")
    print("Pharmacist: pharma_nadia / Pharma123!")
    print("Accountant: acct_kamal / Account123!")
    print("Patient demo: patient_fatema / Patient123!")
    print("Patient demo: patient_rakib / Patient123!")
    print("Patient demo: patient_sumaiya / Patient123!")
    print("Patient demo: patient_arman / Patient123!")
    print("Patient demo: patient_nabila / Patient123!")
    print("Patient demo: patient_mahin / Patient123!")
    print("Patient demo: patient_tasnia / Patient123!")
    print("Patient demo: patient_sabbir / Patient123!")
    print("Patient demo: patient_ritu / Patient123!")
    print("Patient demo: patient_farhan / Patient123!")


if __name__ == "__main__":
    main()
