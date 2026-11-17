"""Add visible, linked DEMO records for one explicitly selected local patient.

Usage: python -m app.scripts.seed_patient_portal_demo --patient-number PAT-...
Existing patient details, appointments and clinical records are preserved.
"""
from __future__ import annotations

import argparse
import json
from datetime import timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import engine

DEMO_NOTE = "DEMO data for testing the portal only. Not an actual clinical record or charge."


def seed_patient_records(f, patient_number: str) -> dict:
    patients = f.tables["patients"]
    patient = f.db.execute(select(patients).where(patients.c.patient_number == patient_number)).mappings().one()
    patient_id = patient["id"]
    f.branch = patient["branch_id"]
    prefix = f"DEMO-{patient_id.hex[:8].upper()}"
    now, today = f.now, f.today

    def put(table, key, **values):
        return f.put(table, key=f"portal:{patient_id}:{key}", **values)

    doctor = f.lookup("users", username="dr_rahman", email="dr.rahman@hms.local")
    nurse = f.lookup("users", username="nurse_lima", email="lima.nursing@hms.local")
    pharmacist = f.lookup("users", username="pharma_nadia", email="nadia.pharmacy@hms.local")
    cashier = f.lookup("users", username="billing_rashid", email="rashid.billing@hms.local")
    visits = []
    prescriptions = []
    for index, days_ago in enumerate([1, 8], 1):
        visit = put("opd_visits", f"visit-{index}", patient_id=patient_id,
                    visit_number=f"{prefix}-OPD-{index}", visit_date=today - timedelta(days=days_ago),
                    department_name="DEMO Medicine", consulting_doctor_name="Dr. Rahman",
                    consulting_doctor_user_id=doctor, registered_by_user_id=f.actor, status="completed",
                    chief_complaint="DEMO consultation example", final_diagnosis="DEMO follow-up example",
                    follow_up_date=today + timedelta(days=7), follow_up_note=DEMO_NOTE, note=DEMO_NOTE)
        visits.append(visit)
        prescription = put("opd_visit_orders", f"prescription-{index}", visit_id=visit,
                           order_type="prescription", service_area="pharmacy", item_name=f"DEMO sample prescription {index}",
                           quantity=1, status="completed", completed_at=now - timedelta(days=days_ago),
                           instructions="Display example only. Do not use this sample for treatment.")
        prescriptions.append(prescription)

    # The portal reads released OPD investigation orders, so link the lab/radiology
    # records to those orders as well as to the patient and visit.
    lab_text = "DEMO lab report: hemoglobin 13.5 g/dL; WBC 7.2 x10^9/L. Synthetic example values, not this patient's test results."
    lab = put("lab_orders", "lab", patient_id=patient_id, visit_id=visits[0], order_number=f"{prefix}-LAB",
              status="verified", completed_at=now, verified_at=now, verified_by_user_id=doctor, note=DEMO_NOTE)
    lab_item = put("lab_order_items", "lab-item", order_id=lab, test_name="DEMO complete blood count",
                  specimen_type="blood", quantity=1, unit_price=500, status="completed", note=DEMO_NOTE)
    lab_result = put("lab_results", "lab-result", order_id=lab, report_number=f"{prefix}-LAB-RPT", status="final",
                    approved_at=now, approved_by_user_id=doctor, overall_interpretation=DEMO_NOTE, note=DEMO_NOTE)
    for name, value, unit in [("Hemoglobin", "13.5", "g/dL"), ("WBC", "7.2", "x10^9/L")]:
        put("lab_result_items", f"lab-result-{name}", result_id=lab_result, order_item_id=lab_item,
            analyte_name=f"DEMO {name}", value=value, unit=unit, note=DEMO_NOTE)
    put("opd_visit_orders", "lab-order", visit_id=visits[0], order_type="investigation", service_area="laboratory",
        item_name="DEMO complete blood count", quantity=1, status="verified", result_text=lab_text,
        completed_at=now, verified_at=now, verified_by_user_id=doctor, lab_order_id=lab)
    rad_text = "DEMO radiology report: sample findings and impression for previewing the report layout. No real imaging study was performed."
    rad = put("radiology_orders", "radiology", patient_id=patient_id, visit_id=visits[0],
              order_number=f"{prefix}-RAD", modality="X-ray", study_description="DEMO chest X-ray",
              status="verified", completed_at=now, verified_at=now, verified_by_user_id=doctor, note=DEMO_NOTE)
    rad_report = put("radiology_reports", "radiology-report", order_id=rad, report_number=f"{prefix}-RAD-RPT",
                     status="final", overall_findings=rad_text, impression=DEMO_NOTE,
                     approved_at=now, approved_by_user_id=doctor, note=DEMO_NOTE)
    put("radiology_report_sections", "radiology-section", report_id=rad_report, section_name="DEMO findings", content=rad_text)
    put("opd_visit_orders", "radiology-order", visit_id=visits[0], order_type="investigation", service_area="radiology",
        item_name="DEMO chest X-ray", quantity=1, status="verified", result_text=rad_text,
        completed_at=now, verified_at=now, verified_by_user_id=doctor, radiology_order_id=rad)

    for index, (total, paid) in enumerate([(1500, 1000), (800, 800)], 1):
        invoice = put("billing_invoices", f"invoice-{index}", patient_id=patient_id,
                      invoice_number=f"{prefix}-INV-{index}", sub_total=total, discount_percentage=0,
                      discount_amount=0, total_amount=total, referred_doctor_amount=0, billed_by_user_id=cashier,
                      paid_amount=paid, due_amount=total-paid, payment_status="paid" if total == paid else "partial",
                      status="issued", source_opd_visit_id=visits[index-1], source_module="opd", note=DEMO_NOTE)
        put("billing_invoice_items", f"invoice-item-{index}", invoice_id=invoice, service_name="DEMO consultation and diagnostics",
            quantity=1, unit_price=total, line_total=total, doctor_share_percentage=0, doctor_share_amount=0,
            source_label="DEMO portal example")
        put("billing_payments", f"payment-{index}", invoice_id=invoice, patient_id=patient_id,
            receipt_number=f"{prefix}-RCPT-{index}", payment_method="cash", amount=paid,
            received_at=now - timedelta(hours=index), collected_by_user_id=cashier, note=DEMO_NOTE)
        put("pharmacy_dispenses", f"dispense-{index}", patient_id=patient_id, source_visit_id=visits[index-1],
            source_visit_order_id=prescriptions[index-1], prescription_ref=f"{prefix}-OPD-{index}",
            medicine_name=f"DEMO sample medicine {index}", requested_quantity=1, quantity=1,
            unit_price=0, total_price=0, dispensed_by_user_id=pharmacist, note=DEMO_NOTE)

    admissions = f.tables["ipd_admissions"]
    active = f.db.scalar(select(admissions.c.id).where(admissions.c.patient_id == patient_id,
        admissions.c.discharged_at.is_(None), admissions.c.status.not_in(["discharged", "cancelled"])))
    # Never create a second active admission if this patient already has one.
    for kind, days_ago in [("current", 1), ("past", 20)]:
        if kind == "current" and active:
            continue
        current = kind == "current"
        bed_number = f"{prefix}-{kind.upper()}"
        bed = put("ipd_beds", f"bed-{kind}", ward_name="DEMO Ward", bed_number=bed_number,
                  status="occupied" if current else "available", daily_rate=500, note=DEMO_NOTE)
        admission = put("ipd_admissions", f"admission-{kind}", patient_id=patient_id, bed_id=bed,
                        admission_number=f"{prefix}-IPD-{kind.upper()}", admitted_at=now - timedelta(days=days_ago),
                        ward_name="DEMO Ward", bed_number=bed_number, attending_doctor_name="Dr. Rahman",
                        attending_doctor_user_id=doctor, assigned_nurse_user_id=nurse, admitted_by_user_id=f.actor,
                        diagnosis="DEMO observation stay - not a real admission", daily_charge=500,
                        status="admitted" if current else "discharged", department_name="DEMO Medicine",
                        discharged_at=None if current else now - timedelta(days=18),
                        discharge_summary=None if current else DEMO_NOTE,
                        discharge_note=None if current else "DEMO discharge summary: sample follow-up document.")
        put("ipd_bed_stays", f"bed-stay-{kind}", admission_id=admission, bed_id=bed, ward_name="DEMO Ward",
            bed_number=bed_number, daily_rate=500, started_at=now - timedelta(days=days_ago),
            ended_at=None if current else now - timedelta(days=18), estimated=False)
        put("ipd_timeline_events", f"admission-event-{kind}", admission_id=admission,
            event_type="demo_preview", title="DEMO admission" if current else "DEMO discharge",
            detail=DEMO_NOTE, occurred_at=now - timedelta(days=days_ago), actor_user_id=f.actor)
        if current:
            for role, user, name in [("doctor", doctor, "Dr. Rahman"), ("nurse", nurse, "Lima Akter")]:
                put("ipd_staff_assignments", f"assignment-{role}", admission_id=admission, staff_user_id=user,
                    staff_name=name, role_type=role, assigned_at=now, assigned_by_user_id=f.actor, reason=DEMO_NOTE)

    put("appointments", "completed-appointment", patient_id=patient_id, doctor_user_id=doctor,
        appointment_number=f"{prefix}-APT-PAST", appointment_at=now - timedelta(days=8),
        status="completed", reason="DEMO past consultation", booked_by_user_id=f.actor, note=DEMO_NOTE)
    return {"patient_number": patient_number, "inserted": f.added, "demo_prefix": prefix}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patient-number", required=True)
    args = parser.parse_args()
    if get_settings().app_env != "development" or engine.url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Patient demo records can only be added to a local development database.")
    from app.scripts.seed_complete_demo import Fixtures
    with engine.begin() as connection:
        report = seed_patient_records(Fixtures(connection), args.patient_number)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
