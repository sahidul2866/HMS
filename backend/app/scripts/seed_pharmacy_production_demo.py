from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.billing import BillingService
from app.models.branch import Branch
from app.models.patient import Patient
from app.models.pharmacy import (
    PharmacyCompany,
    PharmacyCustomer,
    PharmacyGeneric,
    PharmacyInvestigationSetting,
    PharmacyMedicine,
    PharmacyMedicineType,
    PharmacyPurchase,
)
from app.models.user import User


MEDICINE_TYPES = [
    ("Tablet", "Solid oral dosage for routine pharmacy dispensing."),
    ("Capsule", "Encapsulated oral dosage."),
    ("Syrup", "Liquid oral dosage."),
    ("Injection", "Parenteral dosage handled by clinical staff."),
    ("Drop", "Eye, ear, and nasal drop dosage."),
    ("Inhaler", "Respiratory inhalation device."),
    ("Cream", "Topical semi-solid dosage."),
    ("Sachet", "Single dose powder sachet."),
]

GENERICS = [
    ("Paracetamol", "Analgesic and antipyretic."),
    ("Cefixime", "Third generation oral cephalosporin."),
    ("Amoxicillin + Clavulanic Acid", "Broad spectrum beta-lactam antibiotic."),
    ("Omeprazole", "Proton pump inhibitor."),
    ("Metformin", "Oral antidiabetic."),
    ("Salbutamol", "Short-acting bronchodilator."),
    ("Losartan", "Angiotensin receptor blocker."),
    ("Cetirizine", "Second generation antihistamine."),
    ("Oral Rehydration Salt", "Rehydration electrolyte mix."),
    ("Ciprofloxacin", "Fluoroquinolone antimicrobial."),
]

COMPANIES = [
    {
        "name": "Square Pharmaceuticals PLC",
        "contact_person": "Commercial Desk",
        "phone": "+8801711001001",
        "email": "square.supply@hms.local",
        "address": "Dhaka, Bangladesh",
        "note": "Primary fast-moving medicine supplier.",
    },
    {
        "name": "Beximco Pharmaceuticals Ltd.",
        "contact_person": "Key Account Desk",
        "phone": "+8801711001002",
        "email": "beximco.supply@hms.local",
        "address": "Dhaka, Bangladesh",
        "note": "Secondary branded medicine supplier.",
    },
    {
        "name": "Incepta Pharmaceuticals Ltd.",
        "contact_person": "Hospital Channel",
        "phone": "+8801711001003",
        "email": "incepta.supply@hms.local",
        "address": "Savar, Bangladesh",
        "note": "Injectable and specialty medicine supplier.",
    },
    {
        "name": "Renata PLC",
        "contact_person": "Distribution Desk",
        "phone": "+8801711001004",
        "email": "renata.supply@hms.local",
        "address": "Dhaka, Bangladesh",
        "note": "Chronic care medicine supplier.",
    },
]

MEDICINES = [
    {
        "name": "Napa 500mg",
        "strength": "500mg",
        "dosage_form": "Tablet",
        "sku": "MED-NAPA-500",
        "barcode": "894110000001",
        "type": "Tablet",
        "generic": "Paracetamol",
        "company": "Square Pharmaceuticals PLC",
        "purchase_price": "1.20",
        "sale_price": "2.00",
        "stock_quantity": "650",
        "reorder_level": "150",
        "description": "Common OPD analgesic and antipyretic.",
    },
    {
        "name": "Cef-3 200mg",
        "strength": "200mg",
        "dosage_form": "Capsule",
        "sku": "MED-CEF3-200",
        "barcode": "894110000002",
        "type": "Capsule",
        "generic": "Cefixime",
        "company": "Square Pharmaceuticals PLC",
        "purchase_price": "22.00",
        "sale_price": "35.00",
        "stock_quantity": "180",
        "reorder_level": "50",
        "description": "Antibiotic commonly prescribed from OPD.",
    },
    {
        "name": "DP 20mg",
        "strength": "20mg",
        "dosage_form": "Capsule",
        "sku": "MED-DP-20",
        "barcode": "894110000003",
        "type": "Capsule",
        "generic": "Omeprazole",
        "company": "Beximco Pharmaceuticals Ltd.",
        "purchase_price": "3.50",
        "sale_price": "6.00",
        "stock_quantity": "360",
        "reorder_level": "80",
        "description": "Gastric protection medicine.",
    },
    {
        "name": "Metfo 500mg",
        "strength": "500mg",
        "dosage_form": "Tablet",
        "sku": "MED-METFO-500",
        "barcode": "894110000004",
        "type": "Tablet",
        "generic": "Metformin",
        "company": "Renata PLC",
        "purchase_price": "2.80",
        "sale_price": "5.00",
        "stock_quantity": "240",
        "reorder_level": "70",
        "description": "Chronic diabetes medicine.",
    },
    {
        "name": "Salbutamol Inhaler",
        "strength": "100mcg/puff",
        "dosage_form": "Inhaler",
        "sku": "MED-SALB-INH",
        "barcode": "894110000005",
        "type": "Inhaler",
        "generic": "Salbutamol",
        "company": "Incepta Pharmaceuticals Ltd.",
        "purchase_price": "145.00",
        "sale_price": "190.00",
        "stock_quantity": "48",
        "reorder_level": "15",
        "description": "Asthma rescue inhaler.",
    },
    {
        "name": "Losar 50mg",
        "strength": "50mg",
        "dosage_form": "Tablet",
        "sku": "MED-LOSAR-50",
        "barcode": "894110000006",
        "type": "Tablet",
        "generic": "Losartan",
        "company": "Beximco Pharmaceuticals Ltd.",
        "purchase_price": "5.50",
        "sale_price": "8.00",
        "stock_quantity": "210",
        "reorder_level": "60",
        "description": "Hypertension medicine.",
    },
    {
        "name": "Cetrin 10mg",
        "strength": "10mg",
        "dosage_form": "Tablet",
        "sku": "MED-CETRIN-10",
        "barcode": "894110000007",
        "type": "Tablet",
        "generic": "Cetirizine",
        "company": "Square Pharmaceuticals PLC",
        "purchase_price": "1.10",
        "sale_price": "2.00",
        "stock_quantity": "320",
        "reorder_level": "80",
        "description": "Allergy medicine.",
    },
    {
        "name": "ORS Sachet",
        "strength": "13.95g",
        "dosage_form": "Sachet",
        "sku": "MED-ORS-SACHET",
        "barcode": "894110000008",
        "type": "Sachet",
        "generic": "Oral Rehydration Salt",
        "company": "Renata PLC",
        "purchase_price": "4.00",
        "sale_price": "6.00",
        "stock_quantity": "520",
        "reorder_level": "120",
        "description": "Dehydration support sachet.",
    },
    {
        "name": "Ciprocin Eye Drop",
        "strength": "0.3%",
        "dosage_form": "Drop",
        "sku": "MED-CIPRO-EYE",
        "barcode": "894110000009",
        "type": "Drop",
        "generic": "Ciprofloxacin",
        "company": "Incepta Pharmaceuticals Ltd.",
        "purchase_price": "42.00",
        "sale_price": "65.00",
        "stock_quantity": "34",
        "reorder_level": "12",
        "description": "Ophthalmic antimicrobial drop.",
    },
    {
        "name": "DP Aug 625mg",
        "strength": "625mg",
        "dosage_form": "Tablet",
        "sku": "MED-AUG-625",
        "barcode": "894110000010",
        "type": "Tablet",
        "generic": "Amoxicillin + Clavulanic Acid",
        "company": "Beximco Pharmaceuticals Ltd.",
        "purchase_price": "30.00",
        "sale_price": "45.00",
        "stock_quantity": "90",
        "reorder_level": "30",
        "description": "Broad spectrum antibiotic.",
    },
]

INVESTIGATION_SETTINGS = [
    {
        "category_name": "Hematology",
        "test_name": "Complete Blood Count",
        "code": "CBC",
        "service_area": "laboratory",
        "fee": "450.00",
        "room_number": "LAB-101",
        "normal_range": "See differential report",
        "unit": "Panel",
        "specimen_type": "Whole blood",
        "turnaround_time": "4 hours",
        "description": "Routine CBC panel with differential count.",
        "requires_report": True,
    },
    {
        "category_name": "Biochemistry",
        "test_name": "Random Blood Sugar",
        "code": "RBS",
        "service_area": "laboratory",
        "fee": "180.00",
        "room_number": "LAB-102",
        "normal_range": "70-140",
        "unit": "mg/dL",
        "specimen_type": "Blood",
        "turnaround_time": "1 hour",
        "description": "Random plasma glucose.",
        "requires_report": True,
    },
    {
        "category_name": "Biochemistry",
        "test_name": "Lipid Profile",
        "code": "LIPID",
        "service_area": "laboratory",
        "fee": "1200.00",
        "room_number": "LAB-103",
        "normal_range": "See component ranges",
        "unit": "Panel",
        "specimen_type": "Serum",
        "turnaround_time": "Same day",
        "description": "Cholesterol, triglyceride, HDL, LDL panel.",
        "requires_report": True,
    },
    {
        "category_name": "Cardiology",
        "test_name": "ECG",
        "code": "ECG",
        "service_area": "laboratory",
        "fee": "500.00",
        "room_number": "CARD-201",
        "normal_range": "Clinical interpretation",
        "unit": "Trace",
        "specimen_type": None,
        "turnaround_time": "30 minutes",
        "description": "12-lead ECG.",
        "requires_report": True,
    },
    {
        "category_name": "Radiology",
        "test_name": "Chest X-Ray PA View",
        "code": "XR-CHEST-PA",
        "service_area": "radiology",
        "fee": "900.00",
        "room_number": "RAD-301",
        "normal_range": "Radiologist interpretation",
        "unit": "Image",
        "specimen_type": None,
        "turnaround_time": "2 hours",
        "description": "Chest radiograph PA view.",
        "requires_report": True,
    },
    {
        "category_name": "Ultrasonography",
        "test_name": "USG Whole Abdomen",
        "code": "USG-WA",
        "service_area": "radiology",
        "fee": "1800.00",
        "room_number": "USG-302",
        "normal_range": "Radiologist interpretation",
        "unit": "Scan",
        "specimen_type": None,
        "turnaround_time": "Same day",
        "description": "Whole abdomen ultrasonography.",
        "requires_report": True,
    },
]

CUSTOMERS = [
    {
        "customer_number": "PHC-WALKIN",
        "name": "Walk-in Pharmacy Customer",
        "phone": "+8801700000000",
        "email": "walkin.pharmacy@hms.local",
        "address": "Pharmacy retail counter",
        "note": "Default customer for non-registered retail sale.",
    },
    {
        "customer_number": "PHC-CORP",
        "name": "Corporate Counter Account",
        "phone": "+8801700000001",
        "email": "corporate.pharmacy@hms.local",
        "address": "Accounts department",
        "note": "Demo customer for corporate medicine sale.",
    },
]


def decimal_value(value: str | int | float | Decimal) -> Decimal:
    return Decimal(str(value))


def get_actor(session: Session) -> User:
    actor = session.scalar(select(User).where(User.username == "admin"))
    if actor:
        return actor
    actor = session.scalar(select(User).order_by(User.created_at.asc()))
    if not actor:
        raise RuntimeError("No user found. Run access-control/user seed before pharmacy demo seed.")
    return actor


def get_branch(session: Session) -> Branch:
    branch = session.scalar(select(Branch).where(Branch.code == "HQ"))
    if branch:
        return branch
    branch = session.scalar(select(Branch).order_by(Branch.created_at.asc()))
    if not branch:
        raise RuntimeError("No branch found. Run branch/access-control seed before pharmacy demo seed.")
    return branch


def stamp(entity: Any, actor: User) -> None:
    entity.created_by = entity.created_by or actor.id
    entity.updated_by = actor.id
    entity.is_active = True


def sync_master_data(session: Session, branch: Branch, actor: User) -> tuple[dict[str, PharmacyMedicineType], dict[str, PharmacyGeneric], dict[str, PharmacyCompany]]:
    medicine_types: dict[str, PharmacyMedicineType] = {}
    generics: dict[str, PharmacyGeneric] = {}
    companies: dict[str, PharmacyCompany] = {}

    for name, description in MEDICINE_TYPES:
        entity = session.scalar(select(PharmacyMedicineType).where(PharmacyMedicineType.name == name))
        if not entity:
            entity = PharmacyMedicineType(name=name)
            session.add(entity)
        entity.branch_id = branch.id
        entity.description = description
        stamp(entity, actor)
        medicine_types[name] = entity

    for name, description in GENERICS:
        entity = session.scalar(select(PharmacyGeneric).where(PharmacyGeneric.name == name))
        if not entity:
            entity = PharmacyGeneric(name=name)
            session.add(entity)
        entity.branch_id = branch.id
        entity.description = description
        stamp(entity, actor)
        generics[name] = entity

    for payload in COMPANIES:
        entity = session.scalar(select(PharmacyCompany).where(PharmacyCompany.name == payload["name"]))
        if not entity:
            entity = PharmacyCompany(name=payload["name"])
            session.add(entity)
        entity.branch_id = branch.id
        entity.contact_person = payload["contact_person"]
        entity.phone = payload["phone"]
        entity.email = payload["email"]
        entity.address = payload["address"]
        entity.note = payload["note"]
        stamp(entity, actor)
        companies[payload["name"]] = entity

    session.flush()
    return medicine_types, generics, companies


def sync_medicines(
    session: Session,
    branch: Branch,
    actor: User,
    medicine_types: dict[str, PharmacyMedicineType],
    generics: dict[str, PharmacyGeneric],
    companies: dict[str, PharmacyCompany],
) -> dict[str, PharmacyMedicine]:
    medicines: dict[str, PharmacyMedicine] = {}
    purchase_date = date(2026, 4, 1)

    for index, payload in enumerate(MEDICINES, start=1):
        entity = session.scalar(select(PharmacyMedicine).where(PharmacyMedicine.sku == payload["sku"]))
        if not entity:
            entity = PharmacyMedicine(name=payload["name"])
            session.add(entity)
        entity.branch_id = branch.id
        entity.medicine_type_id = medicine_types[payload["type"]].id
        entity.generic_id = generics[payload["generic"]].id
        entity.company_id = companies[payload["company"]].id
        entity.name = payload["name"]
        entity.strength = payload["strength"]
        entity.dosage_form = payload["dosage_form"]
        entity.sku = payload["sku"]
        entity.barcode = payload["barcode"]
        entity.purchase_price = decimal_value(payload["purchase_price"])
        entity.sale_price = decimal_value(payload["sale_price"])
        entity.stock_quantity = decimal_value(payload["stock_quantity"])
        entity.reorder_level = decimal_value(payload["reorder_level"])
        entity.description = payload["description"]
        stamp(entity, actor)
        session.flush()

        purchase_number = f"PP-DEMO-{index:03d}"
        purchase = session.scalar(select(PharmacyPurchase).where(PharmacyPurchase.purchase_number == purchase_number))
        if not purchase:
            purchase = PharmacyPurchase(purchase_number=purchase_number, medicine_id=entity.id)
            session.add(purchase)
        purchase.branch_id = branch.id
        purchase.medicine_id = entity.id
        purchase.purchase_date = purchase_date
        purchase.supplier_name = payload["company"]
        purchase.invoice_number = f"SUP-DEMO-{index:03d}"
        purchase.batch_no = f"BATCH-{payload['sku'].replace('MED-', '')}"
        purchase.expiry_date = date(2027, 12, 31)
        purchase.quantity = decimal_value(payload["stock_quantity"])
        purchase.bonus_quantity = Decimal("0")
        purchase.unit_cost = decimal_value(payload["purchase_price"])
        purchase.sale_price = decimal_value(payload["sale_price"])
        purchase.total_amount = purchase.quantity * purchase.unit_cost
        purchase.note = "Seed opening stock for pharmacy demo and billing integration."
        purchase.purchased_by_user_id = actor.id
        stamp(purchase, actor)

        medicines[payload["sku"]] = entity

    session.flush()
    return medicines


def sync_customers(session: Session, branch: Branch, actor: User) -> None:
    patient = session.scalar(select(Patient).order_by(Patient.created_at.asc()))
    for payload in CUSTOMERS:
        entity = session.scalar(select(PharmacyCustomer).where(PharmacyCustomer.customer_number == payload["customer_number"]))
        if not entity:
            entity = PharmacyCustomer(customer_number=payload["customer_number"])
            session.add(entity)
        entity.branch_id = branch.id
        entity.patient_id = patient.id if payload["customer_number"] == "PHC-WALKIN" and patient else None
        entity.name = payload["name"]
        entity.phone = payload["phone"]
        entity.email = payload["email"]
        entity.address = payload["address"]
        entity.note = payload["note"]
        stamp(entity, actor)


def sync_investigations(session: Session, branch: Branch, actor: User) -> None:
    for payload in INVESTIGATION_SETTINGS:
        entity = session.scalar(select(PharmacyInvestigationSetting).where(PharmacyInvestigationSetting.code == payload["code"]))
        if not entity:
            entity = PharmacyInvestigationSetting(code=payload["code"])
            session.add(entity)
        entity.branch_id = branch.id
        entity.category_name = payload["category_name"]
        entity.test_name = payload["test_name"]
        entity.service_area = payload["service_area"]
        entity.fee = decimal_value(payload["fee"])
        entity.room_number = payload["room_number"]
        entity.normal_range = payload["normal_range"]
        entity.unit = payload["unit"]
        entity.description = payload["description"]
        entity.specimen_type = payload["specimen_type"]
        entity.turnaround_time = payload["turnaround_time"]
        entity.report_header = f"{payload['test_name']} Report"
        entity.report_template = "Result: {{ result_text }}\nReference: {{ normal_range }}"
        entity.report_note_template = "Please correlate clinically."
        entity.requires_report = payload["requires_report"]
        stamp(entity, actor)

        billing = session.scalar(select(BillingService).where(BillingService.service_code == payload["code"]))
        if not billing:
            billing = BillingService(service_code=payload["code"])
            session.add(billing)
        billing.branch_id = branch.id
        billing.name = payload["test_name"]
        billing.description = payload["description"]
        billing.unit_price = decimal_value(payload["fee"])
        billing.doctor_share_percentage = Decimal("10.00") if payload["service_area"] in {"laboratory", "radiology"} else Decimal("0.00")
        billing.max_discount_percentage = Decimal("20.00")
        billing.max_discount_amount = Decimal("300.00")
        billing.room_number = payload["room_number"]
        stamp(billing, actor)


def main() -> None:
    session = SessionLocal()
    try:
        branch = get_branch(session)
        actor = get_actor(session)
        medicine_types, generics, companies = sync_master_data(session, branch, actor)
        sync_medicines(session, branch, actor, medicine_types, generics, companies)
        sync_customers(session, branch, actor)
        sync_investigations(session, branch, actor)
        session.commit()
        print(
            "Pharmacy demo seed completed: "
            f"{len(MEDICINE_TYPES)} types, {len(GENERICS)} generics, {len(COMPANIES)} companies, "
            f"{len(MEDICINES)} medicines, {len(CUSTOMERS)} customers, {len(INVESTIGATION_SETTINGS)} investigations."
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
