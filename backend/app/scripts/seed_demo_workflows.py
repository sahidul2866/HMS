from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import SessionLocal
from app.models.billing import BillingInvoice, BillingInvoiceItem, BillingItemConfig, BillingPayment
from app.models.branch import Branch
from app.models.encounter import Appointment, IPDAdmission, IPDAdmissionMovement, IPDBed, OPDVisit, OPDVisitOrder
from app.models.pharmacy import (
    PharmacyCompany,
    PharmacyCustomer,
    PharmacyDispense,
    PharmacyGeneric,
    PharmacyInvestigation,
    PharmacyInvestigationSetting,
    PharmacyMedicine,
    PharmacyMedicineType,
    PharmacyPurchase,
    PharmacySale,
    PharmacySaleItem,
    PharmacySaleReturn,
)
from app.models.user import User
from app.scripts.script_checkpoints import run_checkpoint_step


def get_required(session, model, field, value, label: str):
    item = session.scalar(select(model).where(field == value))
    if not item:
        raise RuntimeError(f"Missing required {label}: {value}. Run the core seeds first.")
    return item


def get_demo_context(session) -> dict[str, object]:
    branch = get_required(session, Branch, Branch.code, "HQ", "branch")
    doctor = get_required(session, User, User.username, "dr_rahman", "doctor user")
    accountant = get_required(session, User, User.username, "acct_kamal", "accountant user")
    pharmacist = get_required(session, User, User.username, "pharma_nadia", "pharmacist user")
    patient_users = {
        username: get_required(session, User, User.username, username, "patient portal user")
        for username in ("patient_fatema", "patient_rakib", "patient_sumaiya", "patient_arman")
    }
    services = {
        code: get_required(session, BillingItemConfig, BillingItemConfig.service_code, code, "billing item config")
        for code in ("OPD-CONS-GEN", "INV-LAB-CBC", "INV-RAD-CXR")
    }
    return {
        "branch": branch,
        "doctor": doctor,
        "accountant": accountant,
        "pharmacist": pharmacist,
        "patient_users": patient_users,
        "services": services,
    }


def ensure_bed(session, *, branch_id, actor_id, ward_name: str, bed_number: str, bed_type: str, daily_rate: Decimal) -> IPDBed:
    bed = session.scalar(select(IPDBed).where(IPDBed.branch_id == branch_id, IPDBed.ward_name == ward_name, IPDBed.bed_number == bed_number))
    if bed:
        return bed
    bed = IPDBed(
        branch_id=branch_id,
        ward_name=ward_name,
        bed_number=bed_number,
        bed_type=bed_type,
        daily_rate=daily_rate,
        status="available",
        note="Demo workflow bed",
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(bed)
    session.flush()
    return bed


def build_invoice(
    *,
    branch_id,
    patient_id,
    accountant_id,
    invoice_number: str,
    note: str,
    items: list[tuple[BillingItemConfig, Decimal]],
    paid_amount: Decimal,
) -> BillingInvoice:
    sub_total = sum(service.unit_price * quantity for service, quantity in items)
    total_amount = Decimal(sub_total)
    due_amount = total_amount - paid_amount
    payment_status = "paid" if due_amount <= 0 else ("partial" if paid_amount > 0 else "unpaid")
    invoice = BillingInvoice(
        branch_id=branch_id,
        patient_id=patient_id,
        invoice_number=invoice_number,
        sub_total=sub_total,
        discount_percentage=Decimal("0"),
        discount_amount=Decimal("0"),
        total_amount=total_amount,
        paid_amount=paid_amount,
        refunded_amount=Decimal("0"),
        due_amount=due_amount,
        payment_status=payment_status,
        referred_doctor_amount=Decimal("0"),
        status="posted",
        note=note,
        billed_by_user_id=accountant_id,
        created_by=accountant_id,
        updated_by=accountant_id,
    )
    invoice.items = [
        BillingInvoiceItem(
            source_entity_id=service.source_entity_id,
            source_module=service.source_module,
            service_name=service.service_name,
            quantity=quantity,
            unit_price=service.unit_price,
            line_total=service.unit_price * quantity,
            doctor_share_percentage=service.doctor_share_percentage,
            doctor_share_amount=(service.unit_price * quantity * service.doctor_share_percentage) / Decimal("100"),
            created_by=accountant_id,
            updated_by=accountant_id,
        )
        for service, quantity in items
    ]
    return invoice


def seed_fatema_complete_journey() -> str:
    session = SessionLocal()
    try:
        ctx = get_demo_context(session)
        branch: Branch = ctx["branch"]  # type: ignore[assignment]
        doctor: User = ctx["doctor"]  # type: ignore[assignment]
        accountant: User = ctx["accountant"]  # type: ignore[assignment]
        pharmacist: User = ctx["pharmacist"]  # type: ignore[assignment]
        patient_user: User = ctx["patient_users"]["patient_fatema"]  # type: ignore[index]
        services: dict[str, BillingItemConfig] = ctx["services"]  # type: ignore[assignment]

        patient = patient_user.patient
        if patient is None:
            raise RuntimeError("patient_fatema is not linked to a patient")

        appointment = Appointment(
            branch_id=branch.id,
            patient_id=patient.id,
            doctor_user_id=doctor.id,
            appointment_number="APT-DEMO-FATEMA-001",
            appointment_at=datetime.now(UTC) - timedelta(days=8),
            status="completed",
            reason="Persistent cough and fever",
            note="Demo completed appointment",
            booked_by_user_id=patient_user.id,
            created_by=patient_user.id,
            updated_by=patient_user.id,
        )
        session.add(appointment)
        session.flush()

        visit = OPDVisit(
            branch_id=branch.id,
            patient_id=patient.id,
            source_appointment_id=appointment.id,
            consulting_doctor_user_id=doctor.id,
            visit_number="OPD-DEMO-FATEMA-001",
            visit_date=date.today() - timedelta(days=8),
            department_name="General Medicine",
            consulting_doctor_name=doctor.full_name,
            chief_complaint="Persistent cough and fever for five days",
            history_of_present_illness="Low-grade fever, dry cough, and fatigue after viral exposure.",
            past_history="No diabetes or hypertension. Seasonal allergy history.",
            vital_signs="BP 110/70, Pulse 86, Temp 99.4F, SpO2 97%",
            examination_note="Mild pharyngeal congestion, scattered basal crepitations.",
            provisional_diagnosis="Acute lower respiratory tract infection",
            final_diagnosis="Community acquired respiratory infection",
            follow_up_date=date.today() + timedelta(days=7),
            follow_up_note="Continue medication and repeat CBC if symptoms persist.",
            status="completed",
            consultation_fee=Decimal("15.00"),
            note="Demo OPD consultation with complete downstream workflow.",
            registered_by_user_id=doctor.id,
            created_by=doctor.id,
            updated_by=doctor.id,
        )
        session.add(visit)
        session.flush()

        prescription = OPDVisitOrder(
            visit_id=visit.id,
            order_type="prescription",
            item_name="Azithromycin 500mg",
            instructions="1 tablet once daily after meal for 5 days",
            quantity=Decimal("5"),
            status="completed",
            created_by=doctor.id,
            updated_by=pharmacist.id,
        )
        lab = OPDVisitOrder(
            visit_id=visit.id,
            order_type="investigation",
            service_area="laboratory",
            item_name="Complete Blood Count",
            instructions="Sample to be collected fasting not required",
            quantity=Decimal("1"),
            status="verified",
            sample_note="EDTA sample collected in green tube",
            sample_collected_at=datetime.now(UTC) - timedelta(days=8, hours=-1),
            sample_collected_by_user_id=doctor.id,
            result_text="Hemoglobin 11.8 g/dL, WBC 12.4 x10^9/L, Neutrophils 78%",
            completed_at=datetime.now(UTC) - timedelta(days=8, hours=-2),
            completed_by_user_id=doctor.id,
            verified_at=datetime.now(UTC) - timedelta(days=8, hours=-3),
            verified_by_user_id=doctor.id,
            created_by=doctor.id,
            updated_by=doctor.id,
        )
        radiology = OPDVisitOrder(
            visit_id=visit.id,
            order_type="investigation",
            service_area="radiology",
            item_name="Chest X-Ray",
            instructions="PA view",
            quantity=Decimal("1"),
            status="verified",
            sample_note="PA chest completed without contrast",
            sample_collected_at=datetime.now(UTC) - timedelta(days=8, hours=-1),
            sample_collected_by_user_id=doctor.id,
            result_text="Mild peribronchial thickening. No focal consolidation or pleural effusion.",
            completed_at=datetime.now(UTC) - timedelta(days=8, hours=-2),
            completed_by_user_id=doctor.id,
            verified_at=datetime.now(UTC) - timedelta(days=8, hours=-3),
            verified_by_user_id=doctor.id,
            created_by=doctor.id,
            updated_by=doctor.id,
        )
        session.add_all([prescription, lab, radiology])
        session.flush()

        invoice = build_invoice(
            branch_id=branch.id,
            patient_id=patient.id,
            accountant_id=accountant.id,
            invoice_number="INV-DEMO-FATEMA-001",
            note="Demo invoice linked to completed OPD visit",
            items=[
                (services["OPD-CONS-GEN"], Decimal("1")),
                (services["INV-LAB-CBC"], Decimal("1")),
                (services["INV-RAD-CXR"], Decimal("1")),
            ],
            paid_amount=Decimal("55.00"),
        )
        session.add(invoice)
        session.flush()

        payment = BillingPayment(
            invoice_id=invoice.id,
            patient_id=patient.id,
            branch_id=branch.id,
            receipt_number="RCT-DEMO-FATEMA-001",
            payment_method="cash",
            amount=Decimal("55.00"),
            note="Paid in full at front desk",
            received_at=datetime.now(UTC) - timedelta(days=8, hours=-4),
            collected_by_user_id=accountant.id,
            created_by=accountant.id,
            updated_by=accountant.id,
        )
        session.add(payment)

        dispense = PharmacyDispense(
            patient_id=patient.id,
            branch_id=branch.id,
            source_visit_id=visit.id,
            source_visit_order_id=prescription.id,
            prescription_ref=visit.visit_number,
            medicine_name=prescription.item_name,
            quantity=Decimal("5"),
            unit_price=Decimal("2.40"),
            total_price=Decimal("12.00"),
            note="Full dispense against completed prescription",
            dispensed_by_user_id=pharmacist.id,
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        session.add(dispense)

        session.commit()
        return "Fatema complete OPD journey created"
    finally:
        session.close()


def seed_rakib_pending_diagnostics() -> str:
    session = SessionLocal()
    try:
        ctx = get_demo_context(session)
        branch: Branch = ctx["branch"]  # type: ignore[assignment]
        doctor: User = ctx["doctor"]  # type: ignore[assignment]
        patient_user: User = ctx["patient_users"]["patient_rakib"]  # type: ignore[index]
        patient = patient_user.patient
        if patient is None:
            raise RuntimeError("patient_rakib is not linked to a patient")

        visit = OPDVisit(
            branch_id=branch.id,
            patient_id=patient.id,
            consulting_doctor_user_id=doctor.id,
            visit_number="OPD-DEMO-RAKIB-001",
            visit_date=date.today() - timedelta(days=1),
            department_name="General Medicine",
            consulting_doctor_name=doctor.full_name,
            chief_complaint="Shortness of breath and fatigue",
            history_of_present_illness="Symptoms worse with exertion for last three days.",
            past_history="Smoker for 5 years. No known asthma history.",
            vital_signs="BP 118/76, Pulse 94, Temp 98.8F, SpO2 95%",
            examination_note="Mild wheeze bilaterally.",
            provisional_diagnosis="Acute bronchospasm under evaluation",
            follow_up_note="Await diagnostics before medication escalation.",
            status="prescribed",
            consultation_fee=Decimal("15.00"),
            note="Pending diagnostics demo case",
            registered_by_user_id=doctor.id,
            created_by=doctor.id,
            updated_by=doctor.id,
        )
        session.add(visit)
        session.flush()

        session.add_all(
            [
                OPDVisitOrder(
                    visit_id=visit.id,
                    order_type="prescription",
                    item_name="Salbutamol Inhaler",
                    instructions="2 puffs when needed for wheeze",
                    quantity=Decimal("1"),
                    status="pending",
                    created_by=doctor.id,
                    updated_by=doctor.id,
                ),
                OPDVisitOrder(
                    visit_id=visit.id,
                    order_type="investigation",
                    service_area="laboratory",
                    item_name="Complete Blood Count",
                    instructions="Routine urgent processing",
                    quantity=Decimal("1"),
                    status="collected",
                    sample_note="Sample received at counter",
                    sample_collected_at=datetime.now(UTC) - timedelta(hours=5),
                    sample_collected_by_user_id=doctor.id,
                    created_by=doctor.id,
                    updated_by=doctor.id,
                ),
                OPDVisitOrder(
                    visit_id=visit.id,
                    order_type="investigation",
                    service_area="radiology",
                    item_name="Chest X-Ray",
                    instructions="Portable AP if patient unstable",
                    quantity=Decimal("1"),
                    status="in_progress",
                    sample_note="Patient sent to imaging room",
                    sample_collected_at=datetime.now(UTC) - timedelta(hours=3),
                    sample_collected_by_user_id=doctor.id,
                    created_by=doctor.id,
                    updated_by=doctor.id,
                ),
            ]
        )
        session.commit()
        return "Rakib pending diagnostics journey created"
    finally:
        session.close()


def seed_sumaiya_ipd_journey() -> str:
    session = SessionLocal()
    try:
        ctx = get_demo_context(session)
        branch: Branch = ctx["branch"]  # type: ignore[assignment]
        doctor: User = ctx["doctor"]  # type: ignore[assignment]
        accountant: User = ctx["accountant"]  # type: ignore[assignment]
        patient_user: User = ctx["patient_users"]["patient_sumaiya"]  # type: ignore[index]
        services: dict[str, BillingItemConfig] = ctx["services"]  # type: ignore[assignment]
        patient = patient_user.patient
        if patient is None:
            raise RuntimeError("patient_sumaiya is not linked to a patient")

        bed = ensure_bed(
            session,
            branch_id=branch.id,
            actor_id=doctor.id,
            ward_name="Ward B",
            bed_number="B-12",
            bed_type="General",
            daily_rate=Decimal("35.00"),
        )

        admitted_at = datetime.now(UTC) - timedelta(days=4)
        discharged_at = datetime.now(UTC) - timedelta(days=1)
        admission = IPDAdmission(
            branch_id=branch.id,
            patient_id=patient.id,
            bed_id=bed.id,
            attending_doctor_user_id=doctor.id,
            admission_number="IPD-DEMO-SUMAIYA-001",
            admitted_at=admitted_at,
            admission_type="Emergency",
            ward_name=bed.ward_name,
            bed_number=bed.bed_number,
            attending_doctor_name=doctor.full_name,
            diagnosis="Dengue fever with dehydration",
            daily_charge=bed.daily_rate,
            advance_amount=Decimal("100.00"),
            status="discharged",
            expected_discharge_date=(date.today() - timedelta(days=1)),
            discharged_at=discharged_at,
            discharge_condition="Improved",
            discharge_diagnosis="Resolved dehydration, dengue under recovery",
            discharge_summary="Received IV fluid, monitoring, and supportive therapy. Stable for discharge.",
            discharge_note="Follow up in 3 days with repeat CBC.",
            discharged_by_user_id=doctor.id,
            admitted_by_user_id=doctor.id,
            created_by=doctor.id,
            updated_by=doctor.id,
        )
        session.add(admission)
        session.flush()

        session.add_all(
            [
                IPDAdmissionMovement(
                    admission_id=admission.id,
                    movement_type="admission",
                    moved_at=admitted_at,
                    to_ward_name=admission.ward_name,
                    to_bed_number=admission.bed_number,
                    note="Admitted through emergency",
                    moved_by_user_id=doctor.id,
                    created_by=doctor.id,
                    updated_by=doctor.id,
                ),
                IPDAdmissionMovement(
                    admission_id=admission.id,
                    movement_type="discharge",
                    moved_at=discharged_at,
                    from_ward_name=admission.ward_name,
                    from_bed_number=admission.bed_number,
                    note=admission.discharge_note,
                    moved_by_user_id=doctor.id,
                    created_by=doctor.id,
                    updated_by=doctor.id,
                ),
            ]
        )

        invoice = build_invoice(
            branch_id=branch.id,
            patient_id=patient.id,
            accountant_id=accountant.id,
            invoice_number="INV-DEMO-SUMAIYA-001",
            note="Final IPD discharge invoice",
            items=[
                (services["OPD-CONS-GEN"], Decimal("1")),
                (services["INV-LAB-CBC"], Decimal("2")),
                (services["INV-RAD-CXR"], Decimal("1")),
            ],
            paid_amount=Decimal("30.00"),
        )
        session.add(invoice)
        session.flush()

        session.add(
            BillingPayment(
                invoice_id=invoice.id,
                patient_id=patient.id,
                branch_id=branch.id,
                receipt_number="RCT-DEMO-SUMAIYA-001",
                payment_method="mobile_banking",
                amount=Decimal("30.00"),
                note="Advance adjusted against final bill",
                received_at=datetime.now(UTC) - timedelta(days=1),
                collected_by_user_id=accountant.id,
                created_by=accountant.id,
                updated_by=accountant.id,
            )
        )

        bed.status = "available"
        bed.updated_by = doctor.id
        session.commit()
        return "Sumaiya discharged IPD journey created"
    finally:
        session.close()


def seed_arman_upcoming_portal() -> str:
    session = SessionLocal()
    try:
        ctx = get_demo_context(session)
        branch: Branch = ctx["branch"]  # type: ignore[assignment]
        doctor: User = ctx["doctor"]  # type: ignore[assignment]
        patient_user: User = ctx["patient_users"]["patient_arman"]  # type: ignore[index]
        patient = patient_user.patient
        if patient is None:
            raise RuntimeError("patient_arman is not linked to a patient")

        appointment = Appointment(
            branch_id=branch.id,
            patient_id=patient.id,
            doctor_user_id=doctor.id,
            appointment_number="APT-DEMO-ARMAN-001",
            appointment_at=datetime.now(UTC) + timedelta(days=2),
            status="scheduled",
            reason="Follow-up consultation for migraine",
            note="Booked from demo patient portal",
            booked_by_user_id=patient_user.id,
            created_by=patient_user.id,
            updated_by=patient_user.id,
        )
        session.add(appointment)
        session.commit()
        return "Arman upcoming portal appointment created"
    finally:
        session.close()


def seed_pharmacy_inventory_demo() -> str:
    session = SessionLocal()
    try:
        existing_sale = session.scalar(select(PharmacySale).where(PharmacySale.sale_number == "SALE-DEMO-001"))
        if existing_sale:
            return "Pharmacy inventory demo already exists"

        ctx = get_demo_context(session)
        branch: Branch = ctx["branch"]  # type: ignore[assignment]
        pharmacist: User = ctx["pharmacist"]  # type: ignore[assignment]
        patient_fatema: User = ctx["patient_users"]["patient_fatema"]  # type: ignore[index]
        patient_rakib: User = ctx["patient_users"]["patient_rakib"]  # type: ignore[index]

        fatema = patient_fatema.patient
        rakib = patient_rakib.patient
        if fatema is None or rakib is None:
            raise RuntimeError("Demo patients are not linked correctly")

        tablet_type = PharmacyMedicineType(
            branch_id=branch.id,
            name="Tablet",
            description="Oral solid medicines",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        syrup_type = PharmacyMedicineType(
            branch_id=branch.id,
            name="Syrup",
            description="Liquid oral medicines",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        paracetamol_generic = PharmacyGeneric(
            branch_id=branch.id,
            name="Paracetamol",
            description="Analgesic and antipyretic",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        cefixime_generic = PharmacyGeneric(
            branch_id=branch.id,
            name="Cefixime",
            description="Third-generation cephalosporin antibiotic",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        acme_company = PharmacyCompany(
            branch_id=branch.id,
            name="ACME Pharma",
            contact_person="Ahsan Karim",
            phone="01710000001",
            email="supply@acme.demo",
            address="Dhaka trade depot",
            note="Demo pharmaceutical supplier",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        beacon_company = PharmacyCompany(
            branch_id=branch.id,
            name="Beacon Healthcare",
            contact_person="Nusrat Jahan",
            phone="01710000002",
            email="orders@beacon.demo",
            address="Chattogram regional warehouse",
            note="Secondary demo supplier",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        session.add_all([tablet_type, syrup_type, paracetamol_generic, cefixime_generic, acme_company, beacon_company])
        session.flush()

        napa = PharmacyMedicine(
            branch_id=branch.id,
            medicine_type_id=tablet_type.id,
            generic_id=paracetamol_generic.id,
            company_id=acme_company.id,
            name="Napa 500",
            strength="500 mg",
            dosage_form="Tablet",
            sku="MED-DEMO-NAPA-500",
            barcode="890100000001",
            purchase_price=Decimal("1.80"),
            sale_price=Decimal("2.50"),
            stock_quantity=Decimal("93"),
            reorder_level=Decimal("20"),
            description="Demo pain and fever relief tablet",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        cef3 = PharmacyMedicine(
            branch_id=branch.id,
            medicine_type_id=tablet_type.id,
            generic_id=cefixime_generic.id,
            company_id=beacon_company.id,
            name="Cef-3 200",
            strength="200 mg",
            dosage_form="Tablet",
            sku="MED-DEMO-CEF3-200",
            barcode="890100000002",
            purchase_price=Decimal("18.00"),
            sale_price=Decimal("24.00"),
            stock_quantity=Decimal("38"),
            reorder_level=Decimal("10"),
            description="Demo antibiotic tablet",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        ace = PharmacyMedicine(
            branch_id=branch.id,
            medicine_type_id=syrup_type.id,
            generic_id=paracetamol_generic.id,
            company_id=acme_company.id,
            name="Ace Syrup",
            strength="120 mg/5 ml",
            dosage_form="Syrup",
            sku="MED-DEMO-ACE-SYRUP",
            barcode="890100000003",
            purchase_price=Decimal("28.00"),
            sale_price=Decimal("36.00"),
            stock_quantity=Decimal("24"),
            reorder_level=Decimal("6"),
            description="Demo pediatric syrup",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        session.add_all([napa, cef3, ace])
        session.flush()

        retail_customer = PharmacyCustomer(
            branch_id=branch.id,
            patient_id=fatema.id,
            customer_number="PHC-DEMO-001",
            name=f"{fatema.first_name} {fatema.last_name}",
            phone=fatema.phone,
            email=fatema.email,
            address=fatema.address,
            note="Linked to demo patient Fatema",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        walk_in_customer = PharmacyCustomer(
            branch_id=branch.id,
            patient_id=None,
            customer_number="PHC-DEMO-002",
            name="Walk-in Customer",
            phone="01810000000",
            email=None,
            address="Demo retail counter",
            note="Standalone retail customer",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        session.add_all([retail_customer, walk_in_customer])
        session.flush()

        purchases = [
            PharmacyPurchase(
                branch_id=branch.id,
                medicine_id=napa.id,
                purchase_number="PUR-DEMO-001",
                purchase_date=date.today() - timedelta(days=10),
                supplier_name=acme_company.name,
                invoice_number="ACME-INV-001",
                batch_no="NAPA-B01",
                expiry_date=date.today() + timedelta(days=365),
                quantity=Decimal("100"),
                bonus_quantity=Decimal("0"),
                unit_cost=Decimal("1.80"),
                sale_price=Decimal("2.50"),
                total_amount=Decimal("180.00"),
                note="Initial demo stock load",
                purchased_by_user_id=pharmacist.id,
                created_by=pharmacist.id,
                updated_by=pharmacist.id,
            ),
            PharmacyPurchase(
                branch_id=branch.id,
                medicine_id=cef3.id,
                purchase_number="PUR-DEMO-002",
                purchase_date=date.today() - timedelta(days=9),
                supplier_name=beacon_company.name,
                invoice_number="BHC-INV-002",
                batch_no="CEF3-B09",
                expiry_date=date.today() + timedelta(days=300),
                quantity=Decimal("40"),
                bonus_quantity=Decimal("0"),
                unit_cost=Decimal("18.00"),
                sale_price=Decimal("24.00"),
                total_amount=Decimal("720.00"),
                note="Demo antibiotic stock load",
                purchased_by_user_id=pharmacist.id,
                created_by=pharmacist.id,
                updated_by=pharmacist.id,
            ),
            PharmacyPurchase(
                branch_id=branch.id,
                medicine_id=ace.id,
                purchase_number="PUR-DEMO-003",
                purchase_date=date.today() - timedelta(days=8),
                supplier_name=acme_company.name,
                invoice_number="ACME-INV-003",
                batch_no="ACE-B03",
                expiry_date=date.today() + timedelta(days=240),
                quantity=Decimal("24"),
                bonus_quantity=Decimal("0"),
                unit_cost=Decimal("28.00"),
                sale_price=Decimal("36.00"),
                total_amount=Decimal("672.00"),
                note="Demo syrup stock load",
                purchased_by_user_id=pharmacist.id,
                created_by=pharmacist.id,
                updated_by=pharmacist.id,
            ),
        ]
        session.add_all(purchases)
        session.flush()

        sale = PharmacySale(
            branch_id=branch.id,
            customer_id=retail_customer.id,
            patient_id=fatema.id,
            sale_number="SALE-DEMO-001",
            sale_date=date.today() - timedelta(days=2),
            subtotal=Decimal("58.00"),
            discount_amount=Decimal("4.00"),
            return_amount=Decimal("2.50"),
            net_payable=Decimal("51.50"),
            status="partially_returned",
            note="Demo retail sale with a partial return",
            sold_by_user_id=pharmacist.id,
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        session.add(sale)
        session.flush()

        sale_item_napa = PharmacySaleItem(
            sale_id=sale.id,
            medicine_id=napa.id,
            quantity=Decimal("8"),
            returned_quantity=Decimal("1"),
            unit_price=Decimal("2.50"),
            line_total=Decimal("20.00"),
            note="Sold against fever complaint",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        sale_item_cef3 = PharmacySaleItem(
            sale_id=sale.id,
            medicine_id=cef3.id,
            quantity=Decimal("1"),
            returned_quantity=Decimal("0"),
            unit_price=Decimal("24.00"),
            line_total=Decimal("24.00"),
            note="One strip-equivalent demo line",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        sale_item_ace = PharmacySaleItem(
            sale_id=sale.id,
            medicine_id=ace.id,
            quantity=Decimal("1"),
            returned_quantity=Decimal("0"),
            unit_price=Decimal("14.00"),
            line_total=Decimal("14.00"),
            note="Single bottle",
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        session.add_all([sale_item_napa, sale_item_cef3, sale_item_ace])
        session.flush()

        sale_return = PharmacySaleReturn(
            branch_id=branch.id,
            sale_id=sale.id,
            sale_item_id=sale_item_napa.id,
            customer_id=retail_customer.id,
            medicine_id=napa.id,
            return_number="RET-DEMO-001",
            returned_at=date.today() - timedelta(days=1),
            quantity=Decimal("1"),
            unit_price=Decimal("2.50"),
            total_amount=Decimal("2.50"),
            note="One tablet returned due to duplicate purchase",
            returned_by_user_id=pharmacist.id,
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        session.add(sale_return)

        cbc_setting = PharmacyInvestigationSetting(
            branch_id=branch.id,
            category_name="Hematology",
            test_name="Complete Blood Count",
            code="LAB-CBC-DEMO",
            service_area="laboratory",
            fee=Decimal("18.00"),
            specimen_type="Whole blood",
            turnaround_time="4 hours",
            report_header="Complete Blood Count Report",
            report_template="Hemoglobin / WBC / Platelet summary",
            report_note_template="Correlate clinically if abnormal.",
            requires_report=True,
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        xray_setting = PharmacyInvestigationSetting(
            branch_id=branch.id,
            category_name="Radiology",
            test_name="Chest X-Ray",
            code="RAD-CXR-DEMO",
            service_area="radiology",
            fee=Decimal("25.00"),
            specimen_type=None,
            turnaround_time="Same day",
            report_header="Chest X-Ray Report",
            report_template="Technique / Findings / Impression",
            report_note_template="Review by duty radiologist.",
            requires_report=True,
            created_by=pharmacist.id,
            updated_by=pharmacist.id,
        )
        session.add_all([cbc_setting, xray_setting])
        session.flush()

        investigations = [
            PharmacyInvestigation(
                branch_id=branch.id,
                setting_id=cbc_setting.id,
                customer_id=retail_customer.id,
                patient_id=fatema.id,
                investigation_number="INVEST-DEMO-001",
                ordered_at=date.today() - timedelta(days=2),
                status="reported",
                fee=Decimal("18.00"),
                discount_amount=Decimal("3.00"),
                total_amount=Decimal("15.00"),
                result_text="Hemoglobin 11.8 g/dL, WBC mildly elevated.",
                report_note="Suggest repeat CBC in 72 hours if fever persists.",
                note="Linked with pharmacy customer and patient",
                created_by=pharmacist.id,
                updated_by=pharmacist.id,
            ),
            PharmacyInvestigation(
                branch_id=branch.id,
                setting_id=xray_setting.id,
                customer_id=None,
                patient_id=rakib.id,
                investigation_number="INVEST-DEMO-002",
                ordered_at=date.today() - timedelta(days=1),
                status="ordered",
                fee=Decimal("25.00"),
                discount_amount=Decimal("0.00"),
                total_amount=Decimal("25.00"),
                result_text=None,
                report_note=None,
                note="Patient-linked radiology order awaiting report",
                created_by=pharmacist.id,
                updated_by=pharmacist.id,
            ),
        ]
        session.add_all(investigations)

        session.commit()
        return "Pharmacy inventory demo created"
    finally:
        session.close()


def main() -> None:
    workflows: list[tuple[str, Callable[[], str]]] = [
        ("fatema_complete_journey", seed_fatema_complete_journey),
        ("rakib_pending_diagnostics", seed_rakib_pending_diagnostics),
        ("sumaiya_ipd_journey", seed_sumaiya_ipd_journey),
        ("arman_upcoming_portal", seed_arman_upcoming_portal),
        ("pharmacy_inventory_demo", seed_pharmacy_inventory_demo),
    ]

    for step_name, runner in workflows:
        run_checkpoint_step("seed_demo_workflows", step_name, runner)

    print("Demo workflow seed completed.")


if __name__ == "__main__":
    main()
