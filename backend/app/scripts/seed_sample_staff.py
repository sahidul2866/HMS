from collections.abc import Callable

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.branch import Branch
from app.models.department import Department
from app.models.inventory import InventoryStore
from app.models.patient import Patient
from app.models.patient_portal_account import PatientPortalAccount
from app.models.role import Role
from app.models.scope import UserScope
from app.models.user import User
from app.scripts.script_checkpoints import run_checkpoint_step

STAFF_DEMO_PASSWORD = "Demo12345!"

SAMPLE_USERS = [
    {
        "username": "admin_maya",
        "email": "maya.admin@hms.local",
        "full_name": "Maya Chowdhury",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "ADMIN",
        "department_code": "ADM",
    },
    {
        "username": "reception_isha",
        "email": "isha.reception@hms.local",
        "full_name": "Isha Karim",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "RECEPTIONIST",
        "department_code": "ADM",
    },
    {
        "username": "dr_rahman",
        "email": "dr.rahman@hms.local",
        "full_name": "Dr. Rahman",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "DOCTOR",
        "department_code": "CLN",
    },
    {
        "username": "nurse_lima",
        "email": "lima.nursing@hms.local",
        "full_name": "Lima Akter",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "NURSE",
        "department_code": "NUR",
    },
    {
        "username": "assistant_milon",
        "email": "milon.assistant@hms.local",
        "full_name": "Milon Ahmed",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "DOCTOR_ASSISTANT",
        "department_code": "CLN",
    },
    {
        "username": "lab_tanvir",
        "email": "tanvir.lab@hms.local",
        "full_name": "Tanvir Ahmed",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "LAB_TECHNICIAN",
        "department_code": "LAB",
    },
    {
        "username": "radio_mina",
        "email": "mina.radiology@hms.local",
        "full_name": "Mina Das",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "RADIOLOGY_TECHNICIAN",
        "department_code": "RAD",
    },
    {
        "username": "pharma_nadia",
        "email": "nadia.pharmacy@hms.local",
        "full_name": "Nadia Sultana",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "PHARMACIST",
        "department_code": "PHR",
    },
    {
        "username": "blood_rubel",
        "email": "rubel.bloodbank@hms.local",
        "full_name": "Rubel Hasan",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "BLOOD_BANK_OFFICER",
        "department_code": "BBK",
    },
    {
        "username": "inventory_shuvo",
        "email": "shuvo.inventory@hms.local",
        "full_name": "Shuvo Islam",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "INVENTORY_STAFF",
        "department_code": "INV",
    },
    {
        "username": "acct_kamal",
        "email": "kamal.accounts@hms.local",
        "full_name": "Kamal Hossain",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "ACCOUNTANT",
        "department_code": "ACC",
    },
    {
        "username": "billing_rashid",
        "email": "rashid.billing@hms.local",
        "full_name": "Rashid Khan",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "BILLING_STAFF",
        "department_code": "ACC",
    },
    {
        "username": "manager_farzana",
        "email": "farzana.management@hms.local",
        "full_name": "Farzana Hoque",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "MANAGEMENT",
        "department_code": "ADM",
    },
    {
        "username": "hr_sadia",
        "email": "sadia.hr@hms.local",
        "full_name": "Sadia Islam",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "HR_MANAGER",
        "department_code": "HR",
    },
    {
        "username": "payroll_jamal",
        "email": "jamal.payroll@hms.local",
        "full_name": "Jamal Uddin",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "PAYROLL_OFFICER",
        "department_code": "HR",
    },
    {
        "username": "dept_head_anika",
        "email": "anika.department@hms.local",
        "full_name": "Anika Rahman",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "DEPARTMENT_HEAD",
        "department_code": "CLN",
    },
    {
        "username": "employee_rina",
        "email": "rina.employee@hms.local",
        "full_name": "Rina Begum",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "EMPLOYEE",
        "department_code": "ADM",
    },
    {
        "username": "ot_manager_selim",
        "email": "selim.ot@hms.local",
        "full_name": "Selim Hossain",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "OT_MANAGER",
        "department_code": "OT",
    },
    {
        "username": "surgeon_arif",
        "email": "arif.surgeon@hms.local",
        "full_name": "Dr. Arif Khan",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "SURGEON",
        "department_code": "OT",
    },
    {
        "username": "anesthetist_faria",
        "email": "faria.anesthesia@hms.local",
        "full_name": "Dr. Faria Islam",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "ANESTHETIST",
        "department_code": "OT",
    },
    {
        "username": "ot_nurse_joya",
        "email": "joya.otnurse@hms.local",
        "full_name": "Joya Sultana",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "OT_NURSE",
        "department_code": "OT",
    },
    {
        "username": "ot_billing_tarek",
        "email": "tarek.otbilling@hms.local",
        "full_name": "Tarek Mahmud",
        "password": STAFF_DEMO_PASSWORD,
        "role_code": "OT_BILLING_OFFICER",
        "department_code": "OT",
    },
    {
        "username": "ref_dr_sadia",
        "email": "sadia.referral@hms.local",
        "full_name": "Dr. Sadia Noor",
        "password": STAFF_DEMO_PASSWORD,
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
        user.hashed_password = get_password_hash(payload["password"])
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


DEMO_USER_SCOPES = {
    "nurse_lima": [
        {"scope_type": "ward", "scope_value": "General Ward", "module": "ipd", "is_primary": True, "reason": "Demo ward nursing assignment"},
        {"scope_type": "shift", "scope_value": "morning", "module": "ipd", "reason": "Demo morning duty"},
    ],
    "assistant_milon": [
        {"scope_type": "queue_scope", "scope_value": "opd", "module": "queue", "is_primary": True, "reason": "Doctor assistant OPD queue support"},
        {"scope_type": "doctor_profile", "scope_value": "dr_rahman", "module": "opd", "reason": "Assigned to Dr. Rahman's consultation room"},
    ],
    "billing_rashid": [
        {"scope_type": "queue_scope", "scope_value": "billing", "module": "queue", "is_primary": True, "reason": "Billing counter demo assignment"},
    ],
    "inventory_shuvo": [
        {"scope_type": "store", "scope_value": "OPD Store", "module": "inventory", "is_primary": True, "reason": "OPD sub-store assignment"},
    ],
    "lab_tanvir": [
        {"scope_type": "lab_section", "scope_value": "hematology", "module": "laboratory", "is_primary": True, "reason": "Demo lab section assignment"},
    ],
    "radio_mina": [
        {"scope_type": "radiology_unit", "scope_value": "xray", "module": "radiology", "is_primary": True, "reason": "Demo imaging unit assignment"},
    ],
    "blood_rubel": [
        {"scope_type": "blood_bank_unit", "scope_value": "main", "module": "blood_bank", "is_primary": True, "reason": "Main blood bank unit assignment"},
    ],
}


def create_or_update_user_scopes(session, username: str) -> None:
    user = session.scalar(select(User).where(User.username == username))
    if not user:
        return
    for payload in DEMO_USER_SCOPES.get(username, []):
        data = dict(payload)
        if data["scope_type"] == "store" and data.get("scope_value"):
            store = session.scalar(
                select(InventoryStore).where(
                    InventoryStore.branch_id == user.branch_id,
                    InventoryStore.is_active.is_(True),
                    InventoryStore.name == data["scope_value"],
                )
            )
            if store:
                data["scope_ref_id"] = store.id
        existing = session.scalar(
            select(UserScope).where(
                UserScope.user_id == user.id,
                UserScope.scope_type == data["scope_type"],
                UserScope.scope_value == data["scope_value"],
                UserScope.module == data.get("module"),
            )
        )
        if existing:
            existing.is_active = True
            existing.status = "active"
            existing.is_primary = data.get("is_primary", False)
            existing.reason = data.get("reason")
            existing.branch_id = user.branch_id
            existing.scope_ref_id = data.get("scope_ref_id")
            continue
        session.add(
            UserScope(
                branch_id=user.branch_id,
                user_id=user.id,
                status="active",
                is_active=True,
                created_by=user.id,
                updated_by=user.id,
                **data,
            )
        )


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
        run_checkpoint_step("seed_sample_staff", f"staff:v2:{payload['username']}", make_staff_step(payload))

    def make_scope_step(username: str) -> Callable[[], str]:
        def runner() -> str:
            session = SessionLocal()
            try:
                create_or_update_user_scopes(session, username)
                session.commit()
                return f"{username} scopes synchronized"
            finally:
                session.close()

        return runner

    for username in DEMO_USER_SCOPES:
        run_checkpoint_step("seed_sample_staff", f"scopes:v1:{username}", make_scope_step(username))

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
        run_checkpoint_step("seed_sample_staff", f"patient:v2:{payload['username']}", make_demo_patient_step(payload))

    print("Sample staff seed completed.")
    print(f"Demo staff password: {STAFF_DEMO_PASSWORD}")
    print("Admin: admin_maya")
    print("Reception: reception_isha")
    print("Doctor: dr_rahman")
    print("Nurse: nurse_lima")
    print("Doctor Assistant: assistant_milon")
    print("Lab: lab_tanvir")
    print("Radiology: radio_mina")
    print("Pharmacist: pharma_nadia")
    print("Blood Bank: blood_rubel")
    print("Inventory: inventory_shuvo")
    print("Accountant: acct_kamal")
    print("Billing Staff: billing_rashid")
    print("Management: manager_farzana")
    print("HR Manager: hr_sadia")
    print("Payroll Officer: payroll_jamal")
    print("Department Head: dept_head_anika")
    print("Employee: employee_rina")
    print("OT Manager: ot_manager_selim")
    print("Surgeon: surgeon_arif")
    print("Anesthetist: anesthetist_faria")
    print("OT Nurse: ot_nurse_joya")
    print("OT Billing: ot_billing_tarek")
    print("Referral Doctor: ref_dr_sadia")
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
