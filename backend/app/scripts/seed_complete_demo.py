"""Add an isolated, repeatable demo dataset to a local development database.

Run after seed_all. Every clinical reference below belongs to PAT-DEMO-FULL;
existing records are never updated or deleted. These are UI preview fixtures,
not records of actual care, stock handling, payments or external API calls.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import MetaData, and_, func, select

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.security import get_password_hash
from app.scripts.seed_portal_booking_demo import main as seed_portal_booking

DEMO = "DEMO preview only; synthetic data, not an actual hospital transaction."
DOCUMENT_URL = "assets/demo/sample-record.txt"


class Fixtures:
    def __init__(self, connection):
        self.db = connection
        self.metadata = MetaData()
        self.metadata.reflect(bind=connection)
        self.tables = self.metadata.tables
        self.now = datetime.now(UTC).replace(microsecond=0)
        self.today = self.now.date()
        self.actor = self.lookup("users", username="admin_maya", email="maya.admin@hms.local")
        self.branch = self.lookup("branches", code="HQ")
        self.added = 0

    def lookup(self, table, **where):
        t = self.tables[table]
        value = self.db.scalar(select(t.c.id).where(and_(*(t.c[k] == v for k, v in where.items()))))
        if value is None:
            raise RuntimeError(f"Missing demo prerequisite {table} {list(where)}; run seed_all first.")
        return value

    def put(self, table, key="preview", **values):
        t = self.tables[table]
        row_id = uuid5(NAMESPACE_URL, f"mediprofit:demo:v1:{table}:{key}")
        if self.db.scalar(select(t.c.id).where(t.c.id == row_id)):
            return row_id
        defaults = {
            "id": row_id, "is_active": True, "created_at": self.now,
            "updated_at": self.now, "created_by": self.actor,
            "updated_by": self.actor, "branch_id": self.branch,
        }
        data = {k: v for k, v in defaults.items() if k in t.c}
        data.update(values)
        unknown = set(data) - set(t.c.keys())
        missing = [c.name for c in t.c if not c.nullable and c.server_default is None and c.name not in data]
        if unknown or missing:
            raise RuntimeError(f"{table}: unknown fields {sorted(unknown)}; missing required fields {missing}")
        self.db.execute(t.insert().values(**data))
        self.added += 1
        return row_id


def seed_records(f: Fixtures):
    p, now, today, actor, branch = f.put, f.now, f.today, f.actor, f.branch
    doctor = f.lookup("users", username="dr_rahman", email="dr.rahman@hms.local")
    nurse = f.lookup("users", username="nurse_lima", email="lima.nursing@hms.local")
    cashier = f.lookup("users", username="billing_rashid", email="rashid.billing@hms.local")
    accountant = f.lookup("users", username="acct_kamal", email="kamal.accounts@hms.local")
    patient = p("patients", patient_number="PAT-DEMO-FULL", first_name="Demo", last_name="Preview",
                gender="female", date_of_birth=date(1996, 1, 1),
                phone="01700000999", email="demo.preview@example.test")
    p("patient_portal_accounts", patient_id=patient, username="patient_demo",
      email="demo.preview@example.test", full_name="Demo Preview", phone="01700000999",
      hashed_password=get_password_hash("Patient123!"))
    visit = p("opd_visits", patient_id=patient, visit_number="OPD-DEMO-FULL", visit_date=today,
              department_name="Demo Medicine", consulting_doctor_name="Dr. Rahman",
              consulting_doctor_user_id=doctor, registered_by_user_id=actor,
              chief_complaint="DEMO consultation preview", note=DEMO)
    bed = p("ipd_beds", ward_name="Demo Ward", bed_number="DEMO-01", daily_rate=500,
            status="occupied", note=DEMO)
    admission = p("ipd_admissions", patient_id=patient, admission_number="IPD-DEMO-FULL", bed_id=bed,
                  admitted_at=now - timedelta(days=1), ward_name="Demo Ward", bed_number="DEMO-01",
                  attending_doctor_name="Dr. Rahman", attending_doctor_user_id=doctor,
                  assigned_nurse_user_id=nurse, admitted_by_user_id=actor, daily_charge=500,
                  diagnosis="DEMO observation record", department_name="Demo Medicine")
    p("ipd_bed_stays", admission_id=admission, bed_id=bed, ward_name="Demo Ward", bed_number="DEMO-01",
      daily_rate=500, started_at=now - timedelta(days=1), estimated=False)
    er = p("er_visits", patient_id=patient, visit_number="ER-DEMO-FULL", arrival_time=now,
           arrival_mode="ambulance", assigned_doctor_user_id=doctor, assigned_nurse_user_id=nurse,
           chief_complaint="DEMO triage screen preview", assigned_location="Demo triage bay",
           triage_category="green", triage_level=4, treatment_notes=DEMO)
    p("er_ambulance_records", er_visit_id=er, ambulance_service="Demo transport service",
      driver_name="Demo Driver", received_at=now, pickup_location="Demo clinic",
      drop_off_location="Demo triage bay", note=DEMO)
    p("ipd_clinical_notes", admission_id=admission, title="DEMO progress note", note=DEMO,
      authored_by_user_id=doctor, authored_at=now)
    p("ipd_timeline_events", admission_id=admission, event_type="demo_preview", title="DEMO record created",
      detail=DEMO, occurred_at=now, actor_user_id=actor)
    p("ipd_staff_assignments", admission_id=admission, staff_user_id=nurse, staff_name="Lima Akter",
      role_type="nurse", assigned_at=now, assigned_by_user_id=actor, ward_name="Demo Ward", bed_number="DEMO-01", reason=DEMO)
    p("ipd_handovers", admission_id=admission, summary="DEMO nursing handover", pending_items="Review demo chart",
      sender_user_id=nurse, receiver_user_id=doctor, handed_over_at=now)
    p("ipd_nursing_notes", admission_id=admission, note=DEMO, temperature=36.8, pulse=76,
      systolic_bp=120, diastolic_bp=80, spo2=98, recorded_by_user_id=nurse, recorded_at=now)
    med_order = p("ipd_orders", admission_id=admission, order_type="medication", service_area="pharmacy",
                  item_name="DEMO medicine placeholder", instructions="Preview only; do not administer",
                  ordered_by_user_id=doctor, ordered_at=now, status="discontinued", discontinued_at=now)
    p("ipd_medication_administrations", admission_id=admission, order_id=med_order,
      medicine_name="DEMO medicine placeholder", status="held", reason=DEMO, scheduled_at=now)
    p("ipd_nursing_tasks", admission_id=admission, assigned_nurse_user_id=nurse,
      task_type="observation", title="DEMO chart review", instructions=DEMO, due_at=now + timedelta(hours=2))

    lab = p("lab_orders", patient_id=patient, visit_id=visit, order_number="LAB-DEMO-FULL",
            status="verified", collected_at=now - timedelta(hours=2), completed_at=now - timedelta(hours=1),
            verified_at=now, verified_by_user_id=doctor, note=DEMO)
    lab_item = p("lab_order_items", order_id=lab, test_name="DEMO CBC", specimen_type="blood",
                 status="completed", unit_price=100, note=DEMO)
    lab_result = p("lab_results", order_id=lab, report_number="LR-DEMO-FULL", status="final",
                   reviewed_at=now, approved_at=now, approved_by_user_id=doctor, note=DEMO)
    p("lab_result_items", result_id=lab_result, order_item_id=lab_item, analyte_name="DEMO Hemoglobin",
      value="13.5", unit="g/dL", reference_range_low=12, reference_range_high=16, flag="normal", note=DEMO)
    p("lab_attachments", order_id=lab, file_name="sample-record.txt", mime_type="text/plain", url=DOCUMENT_URL,
      created_by_user_id=actor)
    rad = p("radiology_orders", patient_id=patient, visit_id=visit, order_number="RAD-DEMO-FULL",
            modality="X-ray", study_description="DEMO chest study", body_part="chest", note=DEMO)
    rad_report = p("radiology_reports", order_id=rad, report_number="RR-DEMO-FULL", overall_findings=DEMO, note=DEMO)
    p("radiology_report_sections", report_id=rad_report, section_name="DEMO findings", content=DEMO)
    p("radiology_attachments", order_id=rad, report_id=rad_report, file_name="sample-record.txt",
      mime_type="text/plain", url=DOCUMENT_URL, created_by_user_id=actor)
    p("pacs_links", order_id=rad, study_uid=f"2.25.{rad.int}", status="pending",
      pacs_provider="DEMO metadata only")
    order = p("opd_visit_orders", visit_id=visit, order_type="investigation", service_area="laboratory",
              item_name="DEMO CBC", status="verified", result_text=DEMO, lab_order_id=lab)

    billing_type = p("billing_types", code="DEMO", name="Demo services", department="Demo Medicine")
    invoice = p("billing_invoices", patient_id=patient, invoice_number="INV-DEMO-FULL",
                sub_total=100, discount_percentage=0, discount_amount=0, total_amount=100,
                referred_doctor_amount=0, billed_by_user_id=cashier, note=DEMO, status="issued",
                paid_amount=100, due_amount=0, payment_status="paid", refunded_amount=25,
                source_opd_visit_id=visit, billing_type_id=billing_type, billing_type_name="Demo services")
    invoice_item = p("billing_invoice_items", invoice_id=invoice, service_name="DEMO CBC", quantity=1,
                     unit_price=100, line_total=100, doctor_share_percentage=0, doctor_share_amount=0,
                     source_opd_visit_order_id=order, source_module="laboratory")
    p("billing_item_links", invoice_item_id=invoice_item, source_module="laboratory",
      source_entity_type="lab_order_item", source_entity_id=lab_item, meta={"demo": True})
    payment = p("billing_payments", invoice_id=invoice, patient_id=patient, receipt_number="RCPT-DEMO-FULL",
                payment_method="cash", amount=100, received_at=now, collected_by_user_id=cashier, note=DEMO)
    refund = p("billing_refunds", invoice_id=invoice, payment_id=payment, patient_id=patient,
               refund_number="REF-DEMO-FULL", amount=25, reason=DEMO, refunded_at=now,
               refunded_by_user_id=cashier, refund_type="payment_refund", payment_method="cash")
    p("billing_settings", max_item_discount_percentage=100, max_invoice_discount_percentage=100)
    p("billing_events", invoice_id=invoice, actor_id=actor, kind="demo_seed", reason=DEMO,
      snapshot={"demo": True, "total": 100, "paid": 100, "refunded": 25})
    handover = p("billing_cash_handovers", number="HANDOVER-DEMO-FULL", collector_id=cashier, receiver_id=accountant,
                 expected_amount=75, declared_amount=75, variance=0, status="pending", note=DEMO)
    p("billing_cash_handover_entries", "payment", handover_id=handover, payment_id=payment, amount=100)
    p("billing_cash_handover_entries", "refund", handover_id=handover, refund_id=refund, amount=-25)
    p("billing_report_snapshots", actor_id=actor, filters={"demo": True}, statistics={"demo": True, "invoices": 1, "net_collection": 75})
    p("accounting_journals", journal_number="JRN-DEMO-FULL", reference="DEMO", description=DEMO,
      debit_amount=100, credit_amount=100, status="draft", posted_by_user_id=accountant)
    bank = p("bank_accounts", account_name="DEMO bank account", bank_name="Demo bank",
             account_number="DEMO-NOT-A-REAL-ACCOUNT", current_balance=0)
    p("bank_reconciliations", bank_account_id=bank, statement_date=today, system_balance=0,
      bank_balance=0, difference_amount=0, status="draft")
    p("accounting_audit_logs", actor_user_id=actor, action="demo_seed", entity_type="demo_fixture", new_value=DEMO)
    p("ot_audit_logs", actor_user_id=actor, action="demo_seed", entity_type="demo_fixture", detail=DEMO)
    p("operational_postings", source_type="demo_fixture", source_id=invoice, event="preview",
      amount=0, invoice_id=invoice, details={"demo": True, "note": DEMO})

    seed_inventory(f, patient, visit)
    seed_staff(f)
    seed_support(f, patient, visit, admission, doctor, nurse, lab, rad)
    seed_blood(f, patient, doctor)
    seed_system(f, patient, visit, doctor)


def seed_inventory(f: Fixtures, patient, visit):
    p, now, today = f.put, f.now, f.today
    store = p("inventory_stores", "main", code="DEMO-MAIN", name="Demo Main Store", store_type="main_store", description=DEMO)
    ward_store = p("inventory_stores", "ward", code="DEMO-WARD", name="Demo Ward Store", description=DEMO)
    item = p("inventory_items", name="DEMO rice", item_code="DEMO-RICE", item_type="general",
             unit_of_measurement="kg", stock_quantity=92, stock_value=5520, reorder_level=20,
             minimum_stock_level=10, maximum_stock_level=200, is_batch_tracked=True, description=DEMO)
    batch = p("stock_batches", item_id=item, batch_no="DEMO-RICE-01", quantity=92,
              expiry_date=today + timedelta(days=180), unit_cost=60, total_cost=5520, store_id=store, notes=DEMO)
    p("inventory_store_items", store_id=store, item_id=item, quantity_on_hand=92, reorder_level=20)
    p("inventory_requisitions", item_id=item, source_store_id=store, destination_store_id=ward_store,
      requested_quantity=10, requested_by=f.actor, reason=DEMO, required_date=today + timedelta(days=1))
    issue = p("stock_issues", item_id=item, batch_id=batch, store_id=store, department="Demo kitchen",
              requestor="Demo staff", purpose=DEMO, quantity=5, issue_date=today, note=DEMO)
    p("stock_transfers", item_id=item, batch_id=batch, source_store_id=store, destination_store_id=ward_store,
      source_location="Demo Main Store", destination_location="Demo Ward Store", quantity=10,
      requested_quantity=10, transfer_date=today, status="requested", note=DEMO, requested_by=f.actor)
    adjustment = p("stock_adjustments", item_id=item, batch_id=batch, store_id=store,
                   adjustment_type="damage", quantity_change=2, reason=DEMO, note=DEMO, status="posted")
    p("inventory_stock_transactions", "opening", item_id=item, batch_id=batch, store_id=store,
      transaction_type="opening", quantity_change=100, stock_before=0, stock_after=100, note=DEMO)
    p("inventory_stock_transactions", "issue", item_id=item, batch_id=batch, store_id=store,
      transaction_type="issue", reference_type="stock_issue", reference_id=issue,
      quantity_change=-5, stock_before=100, stock_after=95, note=DEMO)
    p("inventory_stock_transactions", "adjustment", item_id=item, batch_id=batch, store_id=store,
      transaction_type="adjustment", reference_type="stock_adjustment", reference_id=adjustment,
      quantity_change=-2, stock_before=95, stock_after=93, note=DEMO)
    meal_tx = p("inventory_stock_transactions", "meal", item_id=item, batch_id=batch, store_id=store,
                transaction_type="consumption", reference_type="demo_meal", quantity_change=-1,
                stock_before=93, stock_after=92, note=DEMO)
    f.inventory = {"item": item, "store": store, "meal_tx": meal_tx}
    reagent = p("reagents", reagent_code="DEMO-REAGENT", name="DEMO reagent", category="hematology", opening_balance=100,
                opened_balance=98, status="active", note=DEMO)
    p("reagent_wastage", reagent_id=reagent, wasted_quantity=2, reason="DEMO spillage", status="recorded", recorded_at=today, note=DEMO)
    p("reagent_test_mappings", reagent_id=reagent, test_name="DEMO CBC", volume_used_per_test=1, remark=DEMO)
    generic = p("pharmacy_generics", name="DEMO generic")
    company = p("pharmacy_companies", name="DEMO manufacturer")
    medicine_type = p("pharmacy_medicine_types", name="DEMO tablet")
    medicine = p("pharmacy_medicines", name="DEMO medicine - preview only", sku="DEMO-MEDICINE",
                 medicine_type_id=medicine_type, generic_id=generic, company_id=company,
                 stock_quantity=100, purchase_price=5, sale_price=6, description=DEMO)
    p("pharmacy_stock_movements", medicine_id=medicine, movement_type="opening", reference_type="demo_seed",
      quantity_change=100, stock_before=0, stock_after=100, note=DEMO)
    p("pharmacy_stock_reviews", kind="adjustment", status="pending", submitted_by_id=f.actor,
      details={"demo": True, "medicine_id": str(medicine), "quantity_change": -1, "reason": DEMO})
    setting = p("pharmacy_investigation_settings", category_name="DEMO diagnostics", test_name="DEMO screening",
                code="DEMO-SCREEN", fee=100, description=DEMO)
    investigation = p("pharmacy_investigations", setting_id=setting, patient_id=patient,
                      investigation_number="PH-INV-DEMO-FULL", ordered_at=today, fee=100, total_amount=100,
                      note=DEMO, source_visit_id=visit)
    p("pharmacy_investigation_items", investigation_id=investigation, setting_id=setting, fee=100, note=DEMO)


def seed_staff(f: Fixtures):
    p, today = f.put, f.today
    employee = p("hr_employees", staff_code="HR-DEMO-FULL", full_name="Demo Preview Staff",
                 joining_date=today - timedelta(days=90), email="staff.preview@example.test")
    f.employee = employee
    p("hr_employee_documents", employee_id=employee, document_type="demo_document", file_name="sample-record.txt",
      file_url=DOCUMENT_URL, note=DEMO)
    p("hr_resignations", employee_id=employee, resignation_date=today,
      last_working_date=today + timedelta(days=30), status="applied", reason=DEMO)
    p("hr_letters", employee_id=employee, letter_type="employment", title="DEMO employment letter", body=DEMO)
    p("hr_salary_revisions", employee_id=employee, effective_from=today,
      components={"basic_salary": 30000, "house_rent": 10000, "medical_allowance": 1000})
    p("hr_payroll_adjustments", employee_id=employee, target_month=today.strftime("%Y-%m"),
      kind="bonus", amount=500, reason=DEMO, status="pending")


def seed_support(f: Fixtures, patient, visit, admission, doctor, nurse, lab, rad):
    p, now, today = f.put, f.now, f.today
    diet = p("catering_diet_types", code="DEMO-REGULAR", name="DEMO regular diet", description=DEMO,
             is_npo=False, requires_approval=False)
    p("catering_meal_schedules", meal_type="lunch", display_name="Demo lunch", serving_time=time(13, 0),
      cutoff_minutes=60, sort_order=3)
    plan = p("catering_meal_plans", diet_type_id=diet, name="DEMO rice and vegetables", meal_type="lunch",
             description=DEMO, ingredients="Rice and vegetables", billable_amount=0, inventory_quantity=1,
             inventory_item_id=f.inventory["item"], inventory_store_id=f.inventory["store"])
    diet_order = p("catering_diet_orders", patient_id=patient, ipd_admission_id=admission, diet_type_id=diet,
                   meal_plan_id=plan, admission_number="IPD-DEMO-FULL", ward_name="Demo Ward", bed_number="DEMO-01",
                   start_at=now, status="active", requires_approval=False, special_instructions=DEMO,
                   ordered_by_user_id=doctor)
    meal = p("catering_meal_tasks", diet_order_id=diet_order, patient_id=patient, meal_plan_id=plan,
             meal_number="MEAL-DEMO-FULL", meal_date=today, meal_type="lunch", due_at=now,
             diet_type_name="DEMO regular diet", preparation_status="prepared", delivery_status="pending",
             safety_status="clear", billable_amount=0, ward_name="Demo Ward", bed_number="DEMO-01",
             inventory_status="consumed", posting_policy="manual_review", remarks=DEMO)
    p("catering_inventory_usage", meal_task_id=meal, inventory_item_id=f.inventory["item"], item_name="DEMO rice",
      quantity_used=1, unit="kg", stock_status="consumed", inventory_store_id=f.inventory["store"],
      stock_transaction_id=f.inventory["meal_tx"], remarks=DEMO)
    p("catering_staff_meal_orders", employee_id=f.employee, staff_name="Demo Preview Staff", staff_code="HR-DEMO-FULL",
      meal_date=today, meal_type="lunch", eligibility_type="paid", amount=50, status="requested",
      payroll_deductible=False, deduction_state="manual_review", remarks=DEMO)
    vehicle = p("transport_vehicles", vehicle_number="DEMO-AMB-01", vehicle_type="ambulance",
                current_status="available", readiness_status="ready", capacity=2,
                equipment_available=["Demo stretcher"], remarks=DEMO)
    driver = p("transport_drivers", driver_name="Demo Driver", license_number="DEMO-LICENSE-NOT-VALID",
               availability_status="available", assigned_vehicle_id=vehicle, remarks=DEMO)
    request = p("transport_requests", request_number="TR-REQ-DEMO-FULL", request_type="patient_transport",
                patient_id=patient, pickup_location="Demo clinic", dropoff_location="Demo hospital",
                required_at=now + timedelta(days=1), urgency="routine", priority="normal",
                attendant_required=False, status="vehicle_assigned", billing_required=False,
                billing_status="not_required", override_used=False, assigned_vehicle_id=vehicle,
                assigned_driver_id=driver, reason=DEMO, remarks=DEMO)
    p("transport_trips", request_id=request, trip_number="TRIP-DEMO-FULL", vehicle_id=vehicle, driver_id=driver,
      patient_id=patient, pickup_location="Demo clinic", dropoff_location="Demo hospital", scheduled_at=now + timedelta(days=1),
      distance_km=0, waiting_minutes=0, priority="normal", status="vehicle_assigned", billing_status="not_required",
      posting_policy="manual_review", remarks=DEMO)
    p("transport_schedules", vehicle_id=vehicle, driver_id=driver, schedule_type="booking",
      start_at=now + timedelta(days=1), end_at=now + timedelta(days=1, hours=1), status="scheduled", purpose="DEMO pickup", remarks=DEMO)
    p("transport_maintenance", vehicle_id=vehicle, maintenance_type="DEMO routine inspection", service_date=today,
      cost=0, status="scheduled", next_service_date=today + timedelta(days=30), remarks=DEMO)
    p("transport_fuel_logs", vehicle_id=vehicle, fuel_date=today, quantity=10, fuel_cost=1000,
      expense_category="fuel", filled_by="Demo Driver", remarks=DEMO)
    tele = p("telemedicine_appointments", patient_id=patient, doctor_user_id=doctor,
             telemedicine_number="TELE-DEMO-FULL", appointment_at=now + timedelta(days=2),
             consultation_reason="DEMO video consultation", visit_type="new", appointment_type="video",
             status="scheduled", payment_status="pending", consultation_fee=0,
             consent_required=True, consent_accepted=False, remarks=DEMO)
    consult = p("telemedicine_consultations", telemedicine_appointment_id=tele, patient_id=patient,
                doctor_user_id=doctor, connection_status="not_connected", status="ready_to_join",
                prescription_status="pending", notes=DEMO, remarks=DEMO)
    p("telemedicine_files", telemedicine_appointment_id=tele, consultation_id=consult, patient_id=patient,
      file_category="medical_document", file_name="sample-record.txt", mime_type="text/plain",
      file_size_bytes=len((Path(__file__).resolve().parents[3] / "frontend/src/assets/demo/sample-record.txt").read_bytes()),
      file_url=DOCUMENT_URL, validation_status="accepted", remarks=DEMO)
    p("telemedicine_chat_messages", consultation_id=consult, sender_user_id=doctor, sender_role="doctor",
      message="DEMO: Welcome to the consultation preview. No live call is connected.", message_type="text")
    p("telemedicine_investigation_orders", consultation_id=consult, patient_id=patient, service_area="laboratory",
      item_name="DEMO investigation placeholder", instructions=DEMO, billing_status="pending", status="cancelled")


def seed_blood(f: Fixtures, patient, doctor):
    p, now, today = f.put, f.now, f.today
    storage = p("blood_storage_locations", code="DEMO-FRIDGE", name="DEMO blood storage",
                temperature_min=2, temperature_max=6, current_temperature=4, remarks=DEMO)
    request = p("blood_requests", request_number="BLD-REQ-DEMO-FULL", patient_id=patient,
                requesting_doctor_id=doctor, blood_group="O+", component_type="whole_blood",
                quantity_units=2, status="issued", indication=DEMO, remarks=DEMO)
    for index, state in enumerate(["transfused", "discarded", "available"], 1):
        key = str(index)
        donor = p("blood_donors", key, donor_number=f"DONOR-DEMO-{index}", name=f"DEMO Donor {index}",
                  age=30 + index, blood_group="O+", eligibility_status="eligible",
                  medical_screening_status="passed", remarks=DEMO)
        screening = p("blood_donor_screenings", key, donor_id=donor, weight=70, hemoglobin_level=14,
                      blood_pressure="120/80", eligibility_result="eligible", screened_at=now - timedelta(days=1),
                      screening_staff_id=doctor, remarks=DEMO)
        collection = p("blood_collections", key, donor_id=donor, screening_id=screening,
                       collection_number=f"COL-DEMO-{index}", unit_number=f"UNIT-DEMO-{index}", blood_group="O+",
                       collection_volume_ml=450, collected_at=now - timedelta(days=1), collection_staff_id=doctor, remarks=DEMO)
        unit = p("blood_units", key, collection_id=collection, donor_id=donor, unit_number=f"UNIT-DEMO-{index}",
                 blood_group="O+", rh_factor="positive", component_type="whole_blood", collection_date=today - timedelta(days=1),
                 expiry_date=today + timedelta(days=30), volume_ml=450, storage_location_id=storage,
                 status=state, testing_status="passed", remarks=DEMO)
        for code in ["HIV", "HBsAg", "HCV", "Syphilis", "Malaria"]:
            p("blood_test_results", f"{key}-{code}", unit_id=unit, test_name=f"DEMO {code}", test_code=code,
              status="verified", result="negative", performed_by=doctor, verified_by=doctor,
              performed_at=now, verified_at=now, remarks=DEMO)
        if state == "available":
            continue
        crossmatch = p("blood_crossmatches", key, request_id=request, unit_id=unit, patient_blood_group="O+",
                       unit_blood_group="O+", component_type="whole_blood", result="compatible",
                       compatibility_status="compatible", tested_by=doctor, verified_by=doctor, tested_at=now, remarks=DEMO)
        issue = p("blood_issues", key, issue_number=f"BLD-ISSUE-DEMO-{index}", request_id=request,
                  patient_id=patient, unit_id=unit, crossmatch_id=crossmatch, issued_by=doctor,
                  received_by="Demo ward staff", issued_at=now, destination="Demo Ward", remarks=DEMO)
        if state == "transfused":
            p("blood_transfusions", issue_id=issue, unit_id=unit, patient_id=patient, status="completed",
              started_by=doctor, started_at=now, completed_by=doctor, completed_at=now + timedelta(hours=1),
              vitals={"demo": True, "pulse": 76}, reaction_observed=False, remarks=DEMO)
        else:
            p("blood_returns", issue_id=issue, unit_id=unit, returned_by="Demo ward staff", returned_at=now,
              minutes_outside_bank=60, reason="DEMO temperature exception", decision="discard", checked_by=doctor, remarks=DEMO)
            p("blood_discards", unit_id=unit, reason="DEMO temperature exception", details=DEMO,
              discarded_by=doctor, discarded_at=now, approved_by=doctor)


def seed_system(f: Fixtures, patient, visit, doctor):
    p, now, today = f.put, f.now, f.today
    counter = p("queue_counters", code="DEMO-OPD", name="Demo OPD counter", module="opd",
                doctor_user_id=doctor, room_number="Demo 101", audio_enabled=False, settings={"demo": True})
    token = p("queue_tokens", token_number="DEMO-001", token_date=today, queue_scope="demo",
              module="opd", patient_id=patient, patient_label="Demo Preview", counter_id=counter,
              doctor_user_id=doctor, source_type="opd_visit", source_id=visit, visit_id=visit,
              notes=DEMO, meta={"demo": True})
    p("queue_audit_logs", token_id=token, counter_id=counter, user_id=f.actor, action="demo_seed",
      module="opd", detail={"demo": True, "note": DEMO})
    p("scan_codes", code_value="DEMO-PATIENT-FULL", purpose="patient_identity", record_type="patient",
      record_id=patient, display_value="PAT-DEMO-FULL", meta={"demo": True})
    p("scan_events", user_id=f.actor, scanned_code="DEMO-PATIENT-FULL", normalized_code="DEMO-PATIENT-FULL",
      module="patients", action="demo_preview", record_type="patient", record_id=patient,
      success="true", message=DEMO, meta={"demo": True})
    for table in ["blood_bank_settings", "scan_settings", "staff_bot_settings", "notification_settings", "queue_settings"]:
        p(table, setting_key="demo_preview", setting_value={"enabled": True, "note": DEMO})
    for table in ["catering_settings", "transport_settings", "telemedicine_settings"]:
        p(table, setting_key="demo_preview", setting_value="true", description=DEMO, meta={"demo": True})
    role = p("roles", code="DEMO_PREVIEW_UNASSIGNED", name="Demo unassigned role", description=DEMO,
             is_doctor_role=False, is_referral_role=False)
    p("role_scopes", role_id=role, scope_type="branch", scope_value="HQ", scope_ref_id=f.branch,
      reason=DEMO, meta={"demo": True})
    # Only duplicate a permission already inherited by the bundled demo admin.
    user_roles, role_permissions, direct = [f.tables[n] for n in ["user_roles", "role_permissions", "user_permissions"]]
    permission = f.db.scalar(select(role_permissions.c.permission_id).join(user_roles,
        user_roles.c.role_id == role_permissions.c.role_id).where(user_roles.c.user_id == f.actor)
        .order_by(role_permissions.c.permission_id).limit(1))
    if permission is not None and not f.db.scalar(select(direct.c.permission_id).where(
            direct.c.user_id == f.actor, direct.c.permission_id == permission)):
        f.db.execute(direct.insert().values(user_id=f.actor, permission_id=permission))
        f.added += 1
    conversation = p("patient_bot_conversations", patient_id=patient, title="DEMO appointment help",
                     state="collecting", intake={}, safety_level="normal", gemini_calls_today=0)
    p("patient_bot_messages", conversation_id=conversation, patient_id=patient, sender="bot",
      message_type="text", content="DEMO: Choose Book Appointment to view doctor availability.",
      payload={"demo": True}, gemini_used=False)
    p("patient_bot_audit_logs", conversation_id=conversation, patient_id=patient, action="demo_seed", payload={"demo": True})
    p("patient_bot_intake_answers", conversation_id=conversation, patient_id=patient,
      field_name="request", answer="DEMO appointment help")
    p("patient_bot_intents", conversation_id=conversation, patient_id=patient,
      intent="appointment", confidence=100, source="local")
    p("patient_bot_recommendations", conversation_id=conversation, patient_id=patient, intent="appointment",
      department="Demo Medicine", reason="DEMO booking navigation example", safety_level="normal", payload={"demo": True})
    p("gemini_api_logs", patient_id=patient, conversation_id=conversation, model_name="demo-no-model-called",
      prompt_context={"demo": True}, response_summary="No external API request was made.", status="demo_not_called")
    staff_chat = p("staff_bot_conversations", user_id=f.actor, title="DEMO navigation help", context={"demo": True})
    p("staff_bot_messages", conversation_id=staff_chat, sender="bot", message="DEMO: Open Patients to find a patient record.", meta={"demo": True})
    p("staff_bot_audit_logs", user_id=f.actor, conversation_id=staff_chat, question="DEMO navigation preview",
      intent="demo_preview", source_module="patients", used_database=False, used_gemini=False, response_summary=DEMO)
    notification = p("notifications", recipient_user_id=f.actor, title="DEMO records ready", message=DEMO,
                     category="info", module="patients", source_key="demo-preview-ready", route="/patients",
                     related_record_type="patient", related_record_id=patient, meta={"demo": True})
    p("notification_audit_logs", notification_id=notification, user_id=f.actor, action="demo_seed",
      module="patients", detail={"demo": True})
    p("audit_logs", user_id=f.actor, action="demo_seed", module="demo", entity_type="demo_dataset",
      entity_id="mediprofit-demo-v1", detail={"demo": True, "note": DEMO})


def seed_demo_appointment() -> int:
    from app.models.encounter import Appointment
    from app.models.patient_portal_account import PatientPortalAccount
    from app.models.user import User
    from app.modules.patient_portal.service import PatientPortalService
    from app.schemas.portal import PatientAppointmentCreate

    with SessionLocal() as db:
        account = db.scalar(select(PatientPortalAccount).where(PatientPortalAccount.username == "patient_demo"))
        doctor = db.scalar(select(User).where(User.username == "dr_rahman"))
        note = "DEMO-FULL-BOOKING: synthetic portal appointment"
        if db.scalar(select(Appointment.id).where(Appointment.patient_id == account.patient_id, Appointment.note == note)):
            return 0
        service = PatientPortalService(db)
        # Use the actual booking service so the appointment and slot reservation agree.
        for offset in range(1, 8):
            day = (datetime.now(UTC) + timedelta(days=offset)).date()
            slots = service.get_doctor_slots(doctor.id, day, account).slots
            slot = next((slot for slot in slots if slot.status == "available"), None)
            if slot:
                service.create_appointment(PatientAppointmentCreate(
                    doctor_user_id=doctor.id, appointment_at=slot.slot_start_at,
                    reason="DEMO consultation preview", note=note,
                ), account)
                return 2  # appointment + slot reservation
        raise RuntimeError("No free demo doctor slots in the next week; existing bookings were preserved.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-core", action="store_true", help="Run bundled core demo seeds first")
    parser.add_argument("--report", type=Path, help="Write per-table row counts to this local JSON file")
    args = parser.parse_args()
    settings = get_settings()
    if settings.app_env != "development" or engine.url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("This sample-data command only runs against a local development database.")
    if args.include_core:
        from app.scripts.seed_all import main as seed_core
        seed_core()
    seed_portal_booking()
    with engine.begin() as connection:
        f = Fixtures(connection)
        seed_records(f)
        from app.scripts.seed_patient_portal_demo import seed_patient_records
        seed_patient_records(f, "PAT-DEMO-FULL")
    booking_rows = seed_demo_appointment()
    with engine.connect() as connection:
        counts = {name: connection.scalar(select(func.count()).select_from(table)) for name, table in sorted(f.tables.items())}
        report = {"dataset": "mediprofit-demo-v1", "created_at": f.now.isoformat(), "inserted": f.added + booking_rows,
                  "tables": len(counts), "populated": sum(n > 0 for n in counts.values()),
                  "empty": [name for name, n in counts.items() if not n], "row_counts": counts}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "row_counts"}, indent=2))


if __name__ == "__main__":
    main()
