from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import SessionLocal
from app.models.billing import BillingInvoice, BillingInvoiceItem, BillingPayment, BillingService
from app.models.branch import Branch
from app.models.encounter import Appointment, IPDAdmission, IPDAdmissionMovement, IPDBed, OPDVisit, OPDVisitOrder
from app.models.pharmacy import PharmacyDispense
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
        code: get_required(session, BillingService, BillingService.service_code, code, "billing service")
        for code in ("CONS-GEN", "CBC", "XR-CHEST")
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
    items: list[tuple[BillingService, Decimal]],
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
            billing_service_id=service.id,
            service_name=service.name,
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
        services: dict[str, BillingService] = ctx["services"]  # type: ignore[assignment]

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
                (services["CONS-GEN"], Decimal("1")),
                (services["CBC"], Decimal("1")),
                (services["XR-CHEST"], Decimal("1")),
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
        services: dict[str, BillingService] = ctx["services"]  # type: ignore[assignment]
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
                (services["CONS-GEN"], Decimal("1")),
                (services["CBC"], Decimal("2")),
                (services["XR-CHEST"], Decimal("1")),
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


def main() -> None:
    workflows: list[tuple[str, Callable[[], str]]] = [
        ("fatema_complete_journey", seed_fatema_complete_journey),
        ("rakib_pending_diagnostics", seed_rakib_pending_diagnostics),
        ("sumaiya_ipd_journey", seed_sumaiya_ipd_journey),
        ("arman_upcoming_portal", seed_arman_upcoming_portal),
    ]

    for step_name, runner in workflows:
        run_checkpoint_step("seed_demo_workflows", step_name, runner)

    print("Demo workflow seed completed.")


if __name__ == "__main__":
    main()
