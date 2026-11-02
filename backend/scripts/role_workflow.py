"""Connected OPD -> IPD -> billing -> discharge journey where each step is done by the role that owns it.

Local dev backend only. Creates synthetic 'RoleFlow' records. For every step, unrelated roles are tried first
and must be refused (403) without changing state. If the owning role is refused, the step is reported and
completed as superadmin so the rest of the chain can still be exercised.
Run: PYTHONPATH=. .venv/bin/python scripts/role_workflow.py (HMS_API_BASE overrides http://127.0.0.1:8000)
"""
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select

import app.main  # noqa: F401
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.user import User
from app.modules.auth.service import AuthService

BASE = os.environ.get("HMS_API_BASE", "http://127.0.0.1:8000") + "/api/v1"
if not BASE.startswith(("http://127.0.0.1", "http://localhost")):
    raise SystemExit("local only")
db = SessionLocal()
client = httpx.Client(timeout=60)
tokens: dict[str, str] = {}
report: list[tuple[str, str, str, int, str]] = []  # (step, kind, role, status, note)


def token_for(username: str | None = None, user_id=None) -> str:
    key = username or str(user_id)
    if key not in tokens:
        user = db.scalar(select(User).where(User.username == username)) if username else db.get(User, user_id)
        perms = sorted(AuthService(db).get_effective_permissions(user))
        tokens[key] = create_access_token(str(user.id), perms)[0]
    return tokens[key]


def call(who: str, method: str, route: str, body=None, uid=None):
    return client.request(method, BASE + route, json=body, headers={"Authorization": "Bearer " + token_for(None if uid else who, uid)})


OUTSIDERS = ["pharma_nadia", "employee_rina", "lab_tanvir", "payroll_jamal", "radio_mina", "hr_sadia", "inventory_shuvo", "blood_rubel"]


def step(name, owner, method, route, body=None, deny=(), uid=None, expect=(200, 201)):
    for outsider in deny:
        r = call(outsider, method, route, body)
        ok = r.status_code in (401, 403)
        report.append((name, "deny", outsider, r.status_code, "" if ok else "NOT REFUSED: " + r.text[:120]))
    r = call(owner, method, route, body, uid=uid)
    if r.status_code not in expect:
        report.append((name, "owner", owner, r.status_code, "OWNER REFUSED/FAILED: " + r.text[:200]))
        r = call("superadmin", method, route, body)
        report.append((name, "fallback", "superadmin", r.status_code, r.text[:120] if r.status_code not in expect else ""))
    else:
        report.append((name, "owner", owner, r.status_code, ""))
    if r.status_code not in expect:
        raise SystemExit(f"cannot continue after {name}: {r.status_code} {r.text[:300]}")
    return r.json() if r.content else None


def summary():
    bad = [r for r in report if r[4]]
    print(f"steps recorded: {len(report)}; problems: {len(bad)}")
    for r in report:
        print(("!! " if r[4] else "   ") + f"{r[0]:40} {r[1]:8} {r[2]:16} {r[3]} {r[4]}")
    return bad


import atexit
atexit.register(summary)
suffix = uuid.uuid4().hex[:6]
phone = "019" + "".join(str(int(c, 16) % 10) for c in uuid.uuid4().hex[:8])
patient = step("register patient", "reception_isha", "POST", "/patients", {"first_name": "RoleFlow", "last_name": "Synthetic" + suffix, "phone": phone}, deny=OUTSIDERS[:5])

DOCTOR = os.environ.get("ROLEFLOW_DOCTOR", "dr_rahman")
doctor_user = db.scalar(select(User).where(User.username == DOCTOR))
doctors = [d for d in call("reception_isha", "GET", "/users/doctors?referral_only=true").json() if d["id"] == str(doctor_user.id)]
chosen = None
for day in range(1, 29):
    slot_date = (datetime.now(UTC) + timedelta(days=day)).date().isoformat()
    for doctor in doctors:
        slots = call("reception_isha", "GET", f"/appointments/doctor-slots?doctor_user_id={doctor['id']}&slot_date={slot_date}").json()
        free = [s for s in slots.get("slots", []) if s["status"] == "available"]
        if free:
            chosen = (doctor, free[0])
            break
    if chosen:
        break
if not chosen:
    day = datetime.now(UTC) + timedelta(days=1)
    r = call("superadmin", "POST", "/appointments/doctor-schedules", {"doctor_user_id": str(doctor_user.id), "weekday": day.weekday(), "start_time": "09:00", "end_time": "10:00", "slot_duration_minutes": 15, "buffer_minutes": 0})
    slots = call("reception_isha", "GET", f"/appointments/doctor-slots?doctor_user_id={doctor_user.id}&slot_date={day.date().isoformat()}").json()
    free = [s for s in slots.get("slots", []) if s["status"] == "available"]
    if not free:
        raise SystemExit(f"no free slot for {DOCTOR}: schedule create {r.status_code} {r.text[:150]}")
    chosen = (doctors[0], free[0])
doctor, slot = chosen
doctor_uid = doctor["id"]
# A previous aborted run leaves its synthetic patients on the doctor's counter; call-next would pick them before ours.
for token in call("superadmin", "GET", f"/queue/tokens?queue_scope=opd&doctor_user_id={doctor_uid}&limit=200").json():
    if token["status"] in ("registered", "waiting", "called", "recalled", "in_progress", "skipped") and "RoleFlow" in (token.get("patient_label") or ""):
        call("superadmin", "POST", f"/queue/tokens/{token['id']}/status", {"status": "cancelled", "notes": "RoleFlow cleanup"})
appointment = step("book appointment", "reception_isha", "POST", "/appointments", {"patient_id": patient["id"], "doctor_user_id": doctor_uid, "slot_start_at": slot.get("slot_start_at") or slot.get("start_at"), "reason": "RoleFlow synthetic"}, deny=OUTSIDERS[:4])
visit = step("check in to OPD", "reception_isha", "POST", f"/appointments/{appointment['id']}/check-in", {"department_name": "Medicine"}, deny=OUTSIDERS[:4])

call("billing_rashid", "GET", "/billing/services")
draft = step("billing draft", "billing_rashid", "GET", f"/billing/drafts/opd-visit/{visit['id']}", deny=["employee_rina", "lab_tanvir", "payroll_jamal"])


def invoice_body(d):
    return {"patient_id": d["patient_id"], "source_opd_visit_id": d.get("source_opd_visit_id"), "source_ipd_admission_id": d.get("source_ipd_admission_id"), "source_module": d["source_module"], "billing_stage": d["billing_stage"],
            "items": [{"billing_service_id": i["billing_service_id"], "quantity": i["quantity"], "source_module": i.get("source_module"), "source_opd_visit_order_id": i.get("source_opd_visit_order_id"), "source_record_type": i.get("source_record_type"), "source_record_id": i.get("source_record_id"), "bed_charge_date": i.get("bed_charge_date"), "source_label": i.get("source_label")} for i in d["items"]]}


invoice = step("post consultation invoice", "billing_rashid", "POST", "/billing/invoices", invoice_body(draft), deny=["employee_rina", "nurse_lima", "pharma_nadia", "lab_tanvir"])
step("collect consultation payment", "billing_rashid", "POST", f"/billing/invoices/{invoice['id']}/payments", {"amount": invoice["total_amount"], "payment_method": "cash"}, deny=["employee_rina", "nurse_lima", "pharma_nadia", "dr_rahman"])
step("refund needs refund right (receptionist)", "reception_isha", "POST", f"/billing/invoices/{invoice['id']}/refunds", {"amount": "1", "refund_method": "cash", "reason": "RoleFlow probe"}, expect=(401, 403, 422))

step("doctor calls next patient", "doctor", "POST", f"/queue/call-next?queue_scope=opd&doctor_user_id={doctor_uid}", uid=doctor_uid, deny=["employee_rina", "pharma_nadia", "payroll_jamal"])
step("start consultation", "doctor", "PUT", f"/opd/visits/{visit['id']}/status", {"status": "in_consultation"}, uid=doctor_uid, deny=["employee_rina", "pharma_nadia", "payroll_jamal", "reception_isha"])
step("prescribe", "doctor", "POST", f"/opd/visits/{visit['id']}/orders", {"order_type": "prescription", "item_name": "RoleFlow prescription", "instructions": "Synthetic"}, uid=doctor_uid, deny=["employee_rina", "pharma_nadia", "reception_isha", "nurse_lima"])
step("finalize prescription", "doctor", "POST", f"/opd/visits/{visit['id']}/finalize", {"final_diagnosis": "RoleFlow synthetic diagnosis"}, uid=doctor_uid, deny=["employee_rina", "reception_isha", "nurse_lima"])

bed = step("create synthetic bed", "admin_maya", "POST", "/ipd/beds", {"ward_name": "RoleFlow Ward", "bed_number": "RF-" + suffix, "bed_type": "General", "daily_rate": 300, "status": "available"}, deny=["nurse_lima", "reception_isha", "employee_rina"])
admission = step("admit to IPD", "doctor", "POST", f"/opd/visits/{visit['id']}/convert-to-ipd", {"bed_id": bed["id"], "admitted_at": datetime.now(UTC).isoformat(), "admission_type": "General", "ward_name": bed["ward_name"], "bed_number": bed["bed_number"], "attending_doctor_name": doctor["full_name"]}, uid=doctor_uid, deny=["employee_rina", "pharma_nadia", "payroll_jamal", "billing_rashid"])
aid = admission["id"]
step("doctor note", "doctor", "POST", f"/ipd/admissions/{aid}/clinical-notes", {"note": "RoleFlow assessment", "diagnosis": "Synthetic"}, uid=doctor_uid, deny=["employee_rina", "pharma_nadia", "billing_rashid"])
step("nursing vitals", "nurse_lima", "POST", f"/ipd/admissions/{aid}/nursing-notes", {"note": "RoleFlow round", "pulse": 80, "spo2": 98, "systolic_bp": 120, "diastolic_bp": 80}, deny=["employee_rina", "pharma_nadia", "billing_rashid", "payroll_jamal"])
order = step("doctor orders monitoring", "doctor", "POST", f"/ipd/admissions/{aid}/orders", {"order_type": "monitoring", "item_name": "RoleFlow monitoring"}, uid=doctor_uid, deny=["employee_rina", "pharma_nadia", "billing_rashid", "reception_isha"])
step("nurse task list", "nurse_lima", "GET", "/ipd/nursing-tasks", deny=["employee_rina", "payroll_jamal"])
step("discharge plan requested", "doctor", "POST", f"/ipd/admissions/{aid}/discharge-plan?status=requested", uid=doctor_uid, deny=["employee_rina", "reception_isha"])
final_draft = step("final billing draft", "billing_rashid", "GET", f"/billing/drafts/ipd-admission/{aid}?stage=final", deny=["employee_rina", "nurse_lima"])
final_invoice = step("post final invoice", "billing_rashid", "POST", "/billing/invoices", invoice_body(final_draft), deny=["employee_rina", "nurse_lima"])
step("collect final payment", "billing_rashid", "POST", f"/billing/invoices/{final_invoice['id']}/payments", {"amount": final_invoice["total_amount"], "payment_method": "cash"}, deny=["employee_rina", "nurse_lima"])
step("cash handover by cashier", "billing_rashid", "GET", "/billing/cash/balance")
step("discharge plan approved", "doctor", "POST", f"/ipd/admissions/{aid}/discharge-plan?status=approved", uid=doctor_uid, deny=["employee_rina", "nurse_lima", "billing_rashid"])
step("discharge", "doctor", "PUT", f"/ipd/admissions/{aid}/discharge", {"discharge_condition": "Stable", "discharge_diagnosis": "Synthetic", "discharge_summary": "RoleFlow synthetic"}, uid=doctor_uid, deny=["employee_rina", "nurse_lima", "billing_rashid", "reception_isha"])

sys.exit(1 if [r for r in report if r[4]] else 0)
