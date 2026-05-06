from __future__ import annotations

import re
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models.billing import BillingInvoice, BillingPayment
from app.models.encounter import IPDBed, IPDAdmission, OPDVisit, Appointment
from app.models.inventory import InventoryItem
from app.models.laboratory import LabOrder
from app.models.patient import Patient
from app.models.pharmacy import PharmacyMedicine, PharmacyPurchase
from app.models.radiology import RadiologyOrder
from app.models.staff_bot import StaffBotAuditLog, StaffBotConversation, StaffBotMessage
from app.models.user import User
from app.modules.appointments.service import AppointmentsService
from app.modules.auth.service import AuthService
from app.schemas.appointment import AppointmentCreate
from app.schemas.staff_bot import StaffBotContext, StaffBotDetailRow, StaffBotMessageCreate, StaffBotResetCreate, StaffBotResponse, StaffBotSettingsRead


SYSTEM_PROMPT = (
    "You are a hospital-aware staff assistant inside a hospital management system (HMS). "
    "Always follow access control: never reveal restricted patient or financial data unless the logged-in user has permission. "
    "Prefer answering from the HMS database/module data. Only use Gemini for general explanation, natural-language guidance, "
    "or fallback if system data is insufficient. Do not diagnose disease or prescribe medication. "
    "If asked for health guidance, provide educational guidance only and include: "
    "'This is not a medical diagnosis. Please consult a qualified doctor for proper evaluation.'"
)


DEFAULT_GREETING = "Hi! I’m your Staff Assistant. Ask about OPD, IPD beds, pharmacy stock, billing dues, appointments, or patients."


INTENT_PERMISSIONS: dict[str, list[str]] = {
    "patient_info": ["patient.view"],
    "opd_today_summary": ["opd.view"],
    "ipd_bed_occupancy": ["ipd.view"],
    "ipd_admitted_under_me": ["ipd.view"],
    "pharmacy_stock": ["pharmacy.view"],
    "billing_due": ["billing.view"],
    "pending_payments": ["billing.view", "reporting.financial.view"],
    "appointment_status": ["appointment.view"],
    "opd_booking": ["appointment.book", "appointment.manage"],
    "hospital_summary": ["dashboard.view"],
    "revenue_analysis": ["reporting.financial.view"],
    "permission_check": ["settings.user.manage", "settings.role.manage", "settings.permission.manage"],
    "low_stock": ["pharmacy.view", "inventory.view"],
    "lab_pending": ["laboratory.view"],
    "radiology_pending": ["radiology.view"],
    "payroll_exceptions": ["payroll.view"],
}


ROLE_QUICK_ACTIONS: list[tuple[str, list[str], list[str]]] = [
    ("Admin", ["dashboard.view"], ["Show today's hospital summary", "Show total OPD patients today", "Show IPD occupancy", "Show pharmacy low stock", "Show pending bills"]),
    ("Doctor", ["opd.view"], ["Show my appointments today", "Show waiting OPD patients", "Show admitted patients under me", "Show previous prescriptions"]),
    ("Pharmacist", ["pharmacy.view"], ["Check medicine stock", "Show low-stock medicines", "Show near-expiry medicines", "Search prescription"]),
    ("Billing", ["billing.invoice.create"], ["Search invoice", "Show pending payments", "Show today’s collection", "Show patient due"]),
    ("Reception", ["appointment.view"], ["Show today's appointments", "Show today's OPD patients", "Find a doctor by department", "Register OPD visit", "Book OPD appointment"]),
]


class StaffBotService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.app_settings = get_settings()
        self.auth = AuthService(db)

    def settings(self, actor: User) -> StaffBotSettingsRead:
        try:
            permissions = set(self.auth.get_effective_permissions(actor))
            quick_actions: list[str] = []
            for _, required, actions in ROLE_QUICK_ACTIONS:
                if any(code in permissions for code in required):
                    quick_actions.extend(actions)
            if not quick_actions:
                fallback_actions = [
                    ("Show today’s OPD patients", "opd.view"),
                    ("Show IPD bed occupancy", "ipd.view"),
                    ("Check medicine stock", "pharmacy.view"),
                    ("Show pending bills", "billing.view"),
                    ("Show my appointments", "appointment.view"),
                ]
                quick_actions = [label for label, permission in fallback_actions if permission in permissions]
            return StaffBotSettingsRead(
                greeting_message=DEFAULT_GREETING,
                quick_actions=sorted(set(quick_actions)),
                gemini_enabled=bool(self.app_settings.gemini_api_key),
            )
        except SQLAlchemyError as exc:
            raise AppException(
                503,
                "staff_bot_unavailable",
                "Staff assistant is not ready. Database connection/migrations may be missing. Ensure Postgres is running and restart backend (AUTO_DB_BOOTSTRAP=true).",
            ) from exc

    def _contextual_suggestions(self, actor: User, assistant_context: StaffBotContext | None) -> list[str]:
        permissions = set(self.auth.get_effective_permissions(actor))

        def can_any(*codes: str) -> bool:
            return any(code in permissions for code in codes)

        module = (assistant_context.module if assistant_context else None) or ""
        path = (assistant_context.path if assistant_context else None) or ""
        suggestions: list[tuple[str, tuple[str, ...]]] = []

        if module == "opd" or path.startswith("/opd"):
            suggestions = [
                ("Summarize today's OPD visits", ("opd.view",)),
                ("Show waiting OPD patients", ("opd.view",)),
                ("Compare previous visit for selected patient", ("patient.view", "opd.view")),
                ("Help draft prescription notes", ("opd.prescribe",)),
                ("List pending lab/radiology orders", ("diagnostics.view", "opd.view")),
            ]
        elif module == "billing" or path.startswith("/billing"):
            suggestions = [
                ("Explain this bill", ("billing.view",)),
                ("Show pending payments", ("billing.view",)),
                ("Check refund eligibility", ("billing.payment.refund",)),
                ("Find billing discrepancies", ("billing.view",)),
                ("Summarize patient balance", ("billing.view",)),
            ]
        elif module == "pharmacy" or path.startswith("/pharmacy"):
            suggestions = [
                ("Check medicine stock", ("pharmacy.view",)),
                ("Show low-stock medicines", ("pharmacy.view",)),
                ("Explain dispense status", ("pharmacy.dispense",)),
                ("Find medicine alternatives", ("pharmacy.view",)),
                ("Review return eligibility", ("pharmacy.return",)),
            ]
        elif module in {"laboratory", "diagnostics"} or path.startswith("/laboratory") or path.startswith("/diagnostics"):
            suggestions = [
                ("Show pending lab tests", ("laboratory.view",)),
                ("Highlight abnormal results", ("laboratory.view",)),
                ("Explain selected result", ("laboratory.view",)),
                ("Review verification checklist", ("laboratory.verify_result",)),
            ]
        elif module == "radiology" or path.startswith("/radiology"):
            suggestions = [
                ("Summarize imaging order status", ("radiology.view",)),
                ("Summarize selected report", ("radiology.view",)),
                ("Check pending PACS uploads", ("radiology.upload_image", "radiology.view")),
                ("Review verification checklist", ("radiology.verify_result",)),
            ]
        elif module == "ipd" or path.startswith("/ipd"):
            suggestions = [
                ("Show IPD occupancy", ("ipd.view",)),
                ("Draft discharge summary", ("ipd.discharge",)),
                ("Check transfer readiness", ("ipd.transfer",)),
                ("Explain interim bill", ("billing.view",)),
            ]
        elif module == "hr" or path.startswith("/hr"):
            if "payroll" in path:
                suggestions = [
                    ("Review payroll exceptions", ("payroll.view",)),
                    ("Summarize deduction issues", ("payroll.view",)),
                    ("Check payroll approval checklist", ("hr.payroll.approve",)),
                    ("Show salary processing status", ("payroll.process_salary",)),
                ]
            else:
                suggestions = [
                    ("Summarize employee profile", ("hr.view",)),
                    ("Show attendance issues", ("hr.attendance.manage",)),
                    ("Check leave balance", ("hr.leave.manage",)),
                    ("Review document checklist", ("hr.documents.manage",)),
                ]
        elif module == "inventory" or path.startswith("/inventory"):
            suggestions = [
                ("Find low-stock items", ("inventory.view",)),
                ("Review purchase requests", ("inventory.purchase",)),
                ("Summarize stock movements", ("inventory.view",)),
                ("Export inventory exceptions", ("inventory.export",)),
            ]
        elif module == "dashboard" or path.startswith("/dashboard"):
            suggestions = [
                ("Show today's hospital summary", ("dashboard.view",)),
                ("Show operational alerts", ("dashboard.view",)),
                ("Show pending payments", ("billing.view",)),
                ("Show low-stock medicines", ("pharmacy.view",)),
                ("Show IPD occupancy", ("ipd.view",)),
            ]
        else:
            suggestions = [
                ("Show today's hospital summary", ("dashboard.view",)),
                ("Find pending tasks", ("dashboard.view",)),
                ("Search patient", ("patient.view",)),
                ("Show pending payments", ("billing.view",)),
                ("Check medicine stock", ("pharmacy.view",)),
            ]

        return [label for label, required in suggestions if can_any(*required)][:5]

    def reset(self, payload: StaffBotResetCreate, actor: User) -> StaffBotResponse:
        try:
            assistant_context = self._coerce_context(payload.context)
            conversation = self._create_conversation(actor, assistant_context=assistant_context)
            self._save_message(conversation, "bot", DEFAULT_GREETING, meta={"intent": "greeting", "source_module": "assistant"})
            suggestions = self._contextual_suggestions(actor, assistant_context)
            return StaffBotResponse(
                conversation_id=conversation.id,
                message=DEFAULT_GREETING,
                intent="greeting",
                source_module="assistant",
                used_database=False,
                used_gemini=False,
                quick_replies=suggestions or self.settings(actor).quick_actions[:6],
                context_suggestions=suggestions,
            )
        except SQLAlchemyError as exc:
            raise AppException(
                503,
                "staff_bot_unavailable",
                "Staff assistant is not ready. Database connection/migrations may be missing. Ensure Postgres is running and restart backend (AUTO_DB_BOOTSTRAP=true).",
            ) from exc

    def handle_message(self, payload: StaffBotMessageCreate, actor: User) -> StaffBotResponse:
        try:
            message = payload.message.strip()
            if not message:
                raise AppException(400, "empty_message", "Message cannot be empty")

            assistant_context = self._coerce_context(payload.context)
            conversation = self._get_or_create_conversation(payload.conversation_id, actor, assistant_context=assistant_context)
            self._merge_context(conversation, assistant_context)
            self._save_message(conversation, "user", message, meta={})

            normalized = self._normalize(message)
            intent = self._detect_intent(normalized)

            permissions = set(self.auth.get_effective_permissions(actor))
            required_perms = INTENT_PERMISSIONS.get(intent, [])
            if required_perms and not any(code in permissions for code in required_perms):
                reply = "Access denied for this request. Please ask an authorized staff member or switch to an allowed module."
                self._audit(actor, conversation, message, intent=intent, source_module="permissions", used_db=False, used_gemini=False, response_summary="denied")
                self._save_message(conversation, "bot", reply, meta={"intent": intent, "source_module": "permissions", "denied": True})
                return StaffBotResponse(
                    conversation_id=conversation.id,
                    message=reply,
                    intent=intent,
                    source_module="Permission Module",
                    used_database=False,
                    used_gemini=False,
                    details=[],
                    next_action="Open your role/permission settings or contact admin.",
                    permission_denied=True,
                    context_suggestions=self._contextual_suggestions(actor, assistant_context),
                )

            answer = self._database_first_answer(intent, normalized, actor, conversation)
            if answer is not None:
                self._audit(
                    actor,
                    conversation,
                    message,
                    intent=intent,
                    source_module=answer.source_module,
                    used_db=answer.used_database,
                    used_gemini=answer.used_gemini,
                    response_summary=answer.message[:220],
                )
                self._save_message(
                    conversation,
                    "bot",
                    answer.message,
                    meta={"intent": answer.intent, "source_module": answer.source_module, "used_database": answer.used_database, "used_gemini": answer.used_gemini},
                )
                return answer

            # Fallback: Gemini (only when configured)
            if not self.app_settings.gemini_api_key:
                reply = "I couldn’t find enough system data to answer that. Please rephrase or provide more details (patient/invoice/medicine/visit)."
                self._audit(actor, conversation, message, intent=intent, source_module="assistant", used_db=False, used_gemini=False, response_summary="no_gemini")
                self._save_message(conversation, "bot", reply, meta={"intent": "unknown", "source_module": "assistant"})
                return StaffBotResponse(conversation_id=conversation.id, message=reply, intent="unknown", source_module="assistant", quick_replies=self.settings(actor).quick_actions[:6])

            gemini_message = self._gemini_fallback(actor, question=message, conversation=conversation)
            used_gemini = True
            reply = gemini_message
            self._audit(actor, conversation, message, intent="unknown", source_module="Gemini", used_db=False, used_gemini=used_gemini, response_summary=reply[:220])
            self._save_message(conversation, "bot", reply, meta={"intent": "unknown", "source_module": "Gemini", "used_gemini": True})
            return StaffBotResponse(
                conversation_id=conversation.id,
                message=reply,
                intent="unknown",
                source_module="Gemini Fallback",
                used_database=False,
                used_gemini=True,
                quick_replies=self.settings(actor).quick_actions[:6],
            )
        except SQLAlchemyError as exc:
            raise AppException(
                503,
                "staff_bot_unavailable",
                "Staff assistant is not ready. Database connection/migrations may be missing. Ensure Postgres is running and restart backend (AUTO_DB_BOOTSTRAP=true).",
            ) from exc

    def _database_first_answer(self, intent: str, normalized: str, actor: User, conversation: StaffBotConversation) -> StaffBotResponse | None:
        if intent == "hospital_summary":
            return self._hospital_summary(actor, conversation)
        if intent == "revenue_analysis":
            return self._revenue_analysis(actor, conversation, normalized)
        if intent == "opd_today_summary":
            return self._opd_today_summary(actor, conversation)
        if intent == "ipd_bed_occupancy":
            return self._ipd_bed_occupancy(actor, conversation)
        if intent == "ipd_admitted_under_me":
            return self._ipd_admitted_under_me(actor, conversation)
        if intent == "pharmacy_stock":
            return self._pharmacy_stock(actor, conversation, normalized)
        if intent == "billing_due":
            return self._billing_due(actor, conversation, normalized)
        if intent == "pending_payments":
            return self._pending_payments(actor, conversation, normalized)
        if intent == "appointment_status":
            return self._appointments_today(actor, conversation)
        if intent == "opd_booking":
            return self._book_opd_appointment(actor, conversation, normalized)
        if intent == "patient_info":
            return self._patient_lookup(actor, conversation, normalized)
        if intent == "low_stock":
            return self._low_stock_summary(actor, conversation, normalized)
        if intent == "lab_pending":
            return self._lab_pending_summary(actor, conversation)
        if intent == "radiology_pending":
            return self._radiology_pending_summary(actor, conversation)
        if intent == "payroll_exceptions":
            return self._payroll_exception_stub(actor, conversation)
        if intent == "general_health_guidance":
            # Intentionally no DB lookup; prefer Gemini for explanation.
            return None
        return None

    def _low_stock_summary(self, actor: User, conversation: StaffBotConversation, normalized: str) -> StaffBotResponse:
        details: list[StaffBotDetailRow] = []
        permissions = set(self.auth.get_effective_permissions(actor))
        if "pharmacy.view" in permissions and ("medicine" in normalized or "pharmacy" in normalized or "stock" in normalized):
            stmt = select(PharmacyMedicine).where(PharmacyMedicine.stock_quantity <= PharmacyMedicine.reorder_level)
            if actor.branch_id:
                stmt = stmt.where(PharmacyMedicine.branch_id == actor.branch_id)
            medicines = list(self.db.scalars(stmt.order_by(PharmacyMedicine.stock_quantity.asc()).limit(5)))
            for item in medicines:
                details.append(StaffBotDetailRow(label=item.name, value=f"{float(item.stock_quantity):,.0f} left"))
            message = f"Pharmacy low-stock medicines: {len(medicines)} item(s) shown."
            source = "Pharmacy Module"
        elif "inventory.view" in permissions:
            stmt = select(InventoryItem).where(InventoryItem.is_active.is_(True), InventoryItem.stock_quantity <= InventoryItem.reorder_level)
            if actor.branch_id:
                stmt = stmt.where(InventoryItem.branch_id == actor.branch_id)
            items = list(self.db.scalars(stmt.order_by(InventoryItem.stock_quantity.asc()).limit(5)))
            for item in items:
                details.append(StaffBotDetailRow(label=item.name, value=f"{float(item.stock_quantity):,.0f} {item.unit_of_measurement}"))
            message = f"Inventory low-stock items: {len(items)} item(s) shown."
            source = "Inventory Module"
        else:
            message = "Access denied for low-stock data."
            source = "Permissions"
        return StaffBotResponse(
            conversation_id=conversation.id,
            message=message,
            intent="low_stock",
            source_module=source,
            used_database=True,
            used_gemini=False,
            details=details,
            next_action="Open the stock module to reorder, adjust, or review batches.",
            quick_replies=["Check medicine stock", "Review purchase requests"],
        )

    def _lab_pending_summary(self, actor: User, conversation: StaffBotConversation) -> StaffBotResponse:
        stmt = select(LabOrder.status, func.count(LabOrder.id)).group_by(LabOrder.status)
        if actor.branch_id:
            stmt = stmt.where(LabOrder.branch_id == actor.branch_id)
        rows = {str(status or "unknown"): int(count or 0) for status, count in self.db.execute(stmt)}
        pending = rows.get("pending", 0) + rows.get("collected", 0) + rows.get("in_progress", 0)
        return StaffBotResponse(
            conversation_id=conversation.id,
            message=f"Lab pending workload: {pending} order(s) need collection, result entry, or verification.",
            intent="lab_pending",
            source_module="Laboratory Module",
            used_database=True,
            used_gemini=False,
            details=[StaffBotDetailRow(label=key.replace("_", " ").title(), value=str(value)) for key, value in sorted(rows.items())],
            next_action="Open Laboratory worklist to enter or verify results.",
            quick_replies=["Review verification checklist", "Highlight abnormal results"],
        )

    def _radiology_pending_summary(self, actor: User, conversation: StaffBotConversation) -> StaffBotResponse:
        stmt = select(RadiologyOrder.status, func.count(RadiologyOrder.id)).group_by(RadiologyOrder.status)
        if actor.branch_id:
            stmt = stmt.where(RadiologyOrder.branch_id == actor.branch_id)
        rows = {str(status or "unknown"): int(count or 0) for status, count in self.db.execute(stmt)}
        pending = rows.get("pending", 0) + rows.get("in_progress", 0) + rows.get("reported", 0)
        return StaffBotResponse(
            conversation_id=conversation.id,
            message=f"Radiology pending workload: {pending} order(s) need imaging, upload, report, or verification.",
            intent="radiology_pending",
            source_module="Radiology Module",
            used_database=True,
            used_gemini=False,
            details=[StaffBotDetailRow(label=key.replace("_", " ").title(), value=str(value)) for key, value in sorted(rows.items())],
            next_action="Open Radiology worklist to review reports and PACS status.",
            quick_replies=["Check pending PACS uploads", "Review verification checklist"],
        )

    def _payroll_exception_stub(self, actor: User, conversation: StaffBotConversation) -> StaffBotResponse:
        return StaffBotResponse(
            conversation_id=conversation.id,
            message="Payroll exception review is available from HR payroll data. I can summarize runs, approvals, and deduction issues when payroll records are selected.",
            intent="payroll_exceptions",
            source_module="Payroll Module",
            used_database=True,
            used_gemini=False,
            details=[],
            next_action="Open HR Payroll and select a payroll run for record-specific review.",
            quick_replies=["Show salary processing status", "Check payroll approval checklist"],
        )

    def _ipd_admitted_under_me(self, actor: User, conversation: StaffBotConversation) -> StaffBotResponse:
        branch_id = actor.branch_id
        stmt = select(IPDAdmission).where(IPDAdmission.status == "admitted", IPDAdmission.attending_doctor_user_id == actor.id)
        if branch_id:
            stmt = stmt.where(IPDAdmission.branch_id == branch_id)
        rows = list(self.db.scalars(stmt.order_by(IPDAdmission.admitted_at.desc()).limit(6)))
        count_stmt = select(func.count(IPDAdmission.id)).where(IPDAdmission.status == "admitted", IPDAdmission.attending_doctor_user_id == actor.id)
        if branch_id:
            count_stmt = count_stmt.where(IPDAdmission.branch_id == branch_id)
        total = int(self.db.scalar(count_stmt) or 0)

        message = f"You have {total} admitted IPD patient(s) under you."
        details = [StaffBotDetailRow(label="Total admitted", value=str(total))]
        for item in rows:
            details.append(StaffBotDetailRow(label=item.admission_number, value=f"{item.ward_name} / Bed {item.bed_number}"))

        return StaffBotResponse(
            conversation_id=conversation.id,
            message=message,
            intent="ipd_admitted_under_me",
            source_module="IPD Module",
            used_database=True,
            used_gemini=False,
            details=details,
            next_action="Open IPD module to view full admission list.",
            quick_replies=["Show IPD occupancy", "Show discharges today"],
        )

    def _opd_today_summary(self, actor: User, conversation: StaffBotConversation) -> StaffBotResponse:
        today = date.today()
        branch_id = actor.branch_id
        base = select(func.count(OPDVisit.id)).where(OPDVisit.visit_date == today)
        if branch_id:
            base = base.where(OPDVisit.branch_id == branch_id)
        total = int(self.db.scalar(base) or 0)

        breakdown_stmt = select(OPDVisit.status, func.count(OPDVisit.id)).where(OPDVisit.visit_date == today)
        if branch_id:
            breakdown_stmt = breakdown_stmt.where(OPDVisit.branch_id == branch_id)
        breakdown_stmt = breakdown_stmt.group_by(OPDVisit.status)
        breakdown = {str(status or "unknown"): int(count or 0) for status, count in self.db.execute(breakdown_stmt)}

        details = [StaffBotDetailRow(label="Total", value=str(total))]
        for key in ["completed", "waiting", "in_consultation", "cancelled", "billed"]:
            if key in breakdown:
                details.append(StaffBotDetailRow(label=key.replace("_", " ").title(), value=str(breakdown[key])))

        message = f"Today’s OPD summary: {total} total visits."
        if breakdown:
            parts = []
            for key, label in [("completed", "completed"), ("waiting", "waiting"), ("cancelled", "cancelled")]:
                if key in breakdown:
                    parts.append(f"{breakdown[key]} {label}")
            if parts:
                message += " " + ", ".join(parts) + "."

        conversation.context = {**(conversation.context or {}), "active_date": today.isoformat()}
        self.db.commit()

        return StaffBotResponse(
            conversation_id=conversation.id,
            message=message,
            intent="opd_today_summary",
            source_module="OPD Module",
            used_database=True,
            used_gemini=False,
            details=details,
            next_action="Open OPD module to view the queue.",
            quick_replies=["Show waiting OPD patients", "Show today's appointments", "Show IPD occupancy"],
        )

    def _ipd_bed_occupancy(self, actor: User, conversation: StaffBotConversation) -> StaffBotResponse:
        branch_id = actor.branch_id
        available_stmt = select(func.count(IPDBed.id)).where(IPDBed.status == "available")
        occupied_stmt = select(func.count(IPDBed.id)).where(IPDBed.status.in_(["occupied", "booked"]))
        if branch_id:
            available_stmt = available_stmt.where(IPDBed.branch_id == branch_id)
            occupied_stmt = occupied_stmt.where(IPDBed.branch_id == branch_id)
        available = int(self.db.scalar(available_stmt) or 0)
        occupied = int(self.db.scalar(occupied_stmt) or 0)
        total = available + occupied
        pct = round((occupied / total) * 100, 1) if total else 0

        message = f"IPD bed occupancy: {occupied} occupied, {available} available ({pct}% occupied)."
        return StaffBotResponse(
            conversation_id=conversation.id,
            message=message,
            intent="ipd_bed_occupancy",
            source_module="IPD Module",
            used_database=True,
            used_gemini=False,
            details=[
                StaffBotDetailRow(label="Occupied", value=str(occupied)),
                StaffBotDetailRow(label="Available", value=str(available)),
                StaffBotDetailRow(label="Occupancy %", value=str(pct)),
            ],
            next_action="Open IPD module to manage beds/admissions.",
            quick_replies=["Show admitted patients today", "Show discharges today", "Show OT today"],
        )

    def _pharmacy_stock(self, actor: User, conversation: StaffBotConversation, normalized: str) -> StaffBotResponse:
        query = self._extract_medicine_query(normalized)
        if not query:
            return StaffBotResponse(
                conversation_id=conversation.id,
                message="Please provide the medicine name or generic name.",
                intent="pharmacy_stock",
                source_module="Pharmacy Module",
                used_database=False,
                used_gemini=False,
                follow_up=True,
                required_fields=["medicine_name_or_generic"],
                quick_replies=["Is Napa 500 available?", "Show low-stock medicines", "Show near-expiry medicines"],
            )

        branch_id = actor.branch_id
        stmt = select(PharmacyMedicine).where(
            or_(
                PharmacyMedicine.name.ilike(f"%{query}%"),
                PharmacyMedicine.strength.ilike(f"%{query}%"),
                PharmacyMedicine.dosage_form.ilike(f"%{query}%"),
            )
        )
        if branch_id:
            stmt = stmt.where(PharmacyMedicine.branch_id == branch_id)
        items = list(self.db.scalars(stmt.limit(5)))
        if not items:
            return StaffBotResponse(
                conversation_id=conversation.id,
                message=f"I could not find any medicine matching “{query}” in the pharmacy catalog.",
                intent="pharmacy_stock",
                source_module="Pharmacy Module",
                used_database=True,
                used_gemini=False,
                details=[],
                next_action="Check spelling or search by generic name.",
                quick_replies=["Search by generic name", "Show low-stock medicines"],
            )

        top = items[0]
        expiry_stmt = select(func.min(PharmacyPurchase.expiry_date)).where(PharmacyPurchase.medicine_id == top.id, PharmacyPurchase.expiry_date.is_not(None))
        if branch_id:
            expiry_stmt = expiry_stmt.where(PharmacyPurchase.branch_id == branch_id)
        nearest_expiry = self.db.scalar(expiry_stmt)

        message = f"{top.name} is available. Current stock: {float(top.stock_quantity):,.0f}."
        if nearest_expiry:
            message += f" Nearest expiry batch: {nearest_expiry.isoformat()}."
        message += " Please verify dosage with a doctor or pharmacist."

        details = [
            StaffBotDetailRow(label="Medicine", value=top.name),
            StaffBotDetailRow(label="Stock", value=f"{float(top.stock_quantity):,.0f}"),
        ]
        if top.strength:
            details.append(StaffBotDetailRow(label="Strength", value=top.strength))
        if top.dosage_form:
            details.append(StaffBotDetailRow(label="Form", value=top.dosage_form))
        if nearest_expiry:
            details.append(StaffBotDetailRow(label="Nearest expiry", value=nearest_expiry.isoformat()))

        conversation.context = {**(conversation.context or {}), "active_medicine_id": str(top.id), "active_medicine_name": top.name}
        self.db.commit()

        return StaffBotResponse(
            conversation_id=conversation.id,
            message=message,
            intent="pharmacy_stock",
            source_module="Pharmacy Module",
            used_database=True,
            used_gemini=False,
            details=details,
            next_action="Open Pharmacy module to view batches/purchases/sales.",
            quick_replies=["Show near-expiry medicines", "Show low-stock medicines"],
        )

    def _billing_due(self, actor: User, conversation: StaffBotConversation, normalized: str) -> StaffBotResponse:
        token = self._extract_patient_token(normalized) or (conversation.context or {}).get("active_patient_token")
        if not token:
            return StaffBotResponse(
                conversation_id=conversation.id,
                message="Please provide the patient ID/number, visit/admission number, or invoice number.",
                intent="billing_due",
                source_module="Billing Module",
                used_database=False,
                used_gemini=False,
                follow_up=True,
                required_fields=["patient_or_invoice_reference"],
                quick_replies=["Show due for PAT-DEMO-0001", "Show pending invoices for patient 1023"],
            )

        patient = self._find_patient(token, actor.branch_id)
        if not patient:
            return StaffBotResponse(
                conversation_id=conversation.id,
                message=f"I could not find a patient matching “{token}”. Please provide patient number/phone or the invoice number.",
                intent="billing_due",
                source_module="Billing Module",
                used_database=True,
                used_gemini=False,
                details=[],
                follow_up=True,
                required_fields=["patient_or_invoice_reference"],
            )

        stmt = select(BillingInvoice).where(BillingInvoice.patient_id == patient.id, BillingInvoice.status == "posted", BillingInvoice.due_amount > 0)
        if actor.branch_id:
            stmt = stmt.where(BillingInvoice.branch_id == actor.branch_id)
        invoices = list(self.db.scalars(stmt.order_by(BillingInvoice.created_at.desc()).limit(10)))
        if not invoices:
            conversation.context = {**(conversation.context or {}), "active_patient_token": token, "active_patient_id": str(patient.id)}
            self.db.commit()
            return StaffBotResponse(
                conversation_id=conversation.id,
                message=f"No pending due invoices found for {patient.patient_number} ({patient.first_name} {patient.last_name}).",
                intent="billing_due",
                source_module="Billing Module",
                used_database=True,
                used_gemini=False,
                details=[
                    StaffBotDetailRow(label="Patient", value=f"{patient.patient_number} - {patient.first_name} {patient.last_name}"),
                    StaffBotDetailRow(label="Due invoices", value="0"),
                ],
                next_action="You can create a new invoice or review billing history.",
            )

        total_due = float(sum(inv.due_amount for inv in invoices))
        total_bill = float(sum(inv.total_amount for inv in invoices))
        total_paid = float(sum(inv.paid_amount for inv in invoices))

        details = [
            StaffBotDetailRow(label="Patient", value=f"{patient.patient_number} - {patient.first_name} {patient.last_name}"),
            StaffBotDetailRow(label="Total bill (latest)", value=f"{total_bill:,.0f} BDT"),
            StaffBotDetailRow(label="Paid (latest)", value=f"{total_paid:,.0f} BDT"),
            StaffBotDetailRow(label="Due (latest)", value=f"{total_due:,.0f} BDT"),
        ]
        for inv in invoices[:5]:
            details.append(StaffBotDetailRow(label=f"Invoice {inv.invoice_number}", value=f"{float(inv.due_amount):,.0f} BDT due"))

        conversation.context = {**(conversation.context or {}), "active_patient_token": token, "active_patient_id": str(patient.id)}
        self.db.commit()

        message = f"{patient.patient_number} has {len(invoices)} pending invoice(s). Total due: {total_due:,.0f} BDT."
        return StaffBotResponse(
            conversation_id=conversation.id,
            message=message,
            intent="billing_due",
            source_module="Billing Module",
            used_database=True,
            used_gemini=False,
            details=details,
            next_action="Open Billing to collect payment or print receipt.",
            quick_replies=["Open billing desk", "Show pending payments today"],
        )

    def _pending_payments(self, actor: User, conversation: StaffBotConversation, normalized: str) -> StaffBotResponse:
        today = date.today()
        branch_id = actor.branch_id
        stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.status == "posted", BillingInvoice.payment_status.in_(["unpaid", "partial"]))
        if branch_id:
            stmt = stmt.where(BillingInvoice.branch_id == branch_id)
        count = int(self.db.scalar(stmt) or 0)

        collected_stmt = select(func.coalesce(func.sum(BillingPayment.amount), 0)).where(cast(BillingPayment.received_at, Date) == today)
        if branch_id:
            collected_stmt = collected_stmt.where(BillingPayment.branch_id == branch_id)
        collected = float(self.db.scalar(collected_stmt) or 0)

        message = f"Pending payments: {count} invoice(s) have unpaid/partial status. Today’s collection: {collected:,.0f} BDT."
        return StaffBotResponse(
            conversation_id=conversation.id,
            message=message,
            intent="pending_payments",
            source_module="Invoice / Payment Module",
            used_database=True,
            used_gemini=False,
            details=[
                StaffBotDetailRow(label="Pending invoices", value=str(count)),
                StaffBotDetailRow(label="Today collection", value=f"{collected:,.0f} BDT"),
            ],
            next_action="Open Billing desk to review dues.",
            quick_replies=["Show due for a patient", "Show today's revenue"],
        )

    def _appointments_today(self, actor: User, conversation: StaffBotConversation) -> StaffBotResponse:
        today = date.today()
        branch_id = actor.branch_id
        stmt = select(func.count(Appointment.id)).where(cast(Appointment.appointment_at, Date) == today)
        if branch_id:
            stmt = stmt.where(Appointment.branch_id == branch_id)
        total = int(self.db.scalar(stmt) or 0)

        breakdown_stmt = select(Appointment.status, func.count(Appointment.id)).where(cast(Appointment.appointment_at, Date) == today)
        if branch_id:
            breakdown_stmt = breakdown_stmt.where(Appointment.branch_id == branch_id)
        breakdown_stmt = breakdown_stmt.group_by(Appointment.status)
        breakdown = {str(status or "unknown"): int(count or 0) for status, count in self.db.execute(breakdown_stmt)}

        message = f"Today’s appointments: {total} total."
        details = [StaffBotDetailRow(label="Total", value=str(total))]
        for status, label in [("scheduled", "Scheduled"), ("confirmed", "Confirmed"), ("completed", "Completed"), ("cancelled", "Cancelled")]:
            if status in breakdown:
                details.append(StaffBotDetailRow(label=label, value=str(breakdown[status])))
        return StaffBotResponse(
            conversation_id=conversation.id,
            message=message,
            intent="appointment_status",
            source_module="Appointment / Visit Module",
            used_database=True,
            used_gemini=False,
            details=details,
            next_action="Open Appointments module for details.",
            quick_replies=["Show OPD summary today", "Show my appointments today"],
        )

    def _hospital_summary(self, actor: User, conversation: StaffBotConversation) -> StaffBotResponse:
        today = date.today()
        branch_id = actor.branch_id

        opd_stmt = select(func.count(OPDVisit.id)).where(OPDVisit.visit_date == today)
        apt_stmt = select(func.count(Appointment.id)).where(cast(Appointment.appointment_at, Date) == today)
        due_stmt = select(func.coalesce(func.sum(BillingInvoice.due_amount), 0)).where(BillingInvoice.status == "posted")
        collection_stmt = select(func.coalesce(func.sum(BillingPayment.amount), 0)).where(cast(BillingPayment.received_at, Date) == today)
        occupied_stmt = select(func.count(IPDBed.id)).where(IPDBed.status.in_(["occupied", "booked"]))
        bed_total_stmt = select(func.count(IPDBed.id))
        low_stock_stmt = select(func.count(PharmacyMedicine.id)).where(PharmacyMedicine.stock_quantity <= PharmacyMedicine.reorder_level)

        if branch_id:
            opd_stmt = opd_stmt.where(OPDVisit.branch_id == branch_id)
            apt_stmt = apt_stmt.where(Appointment.branch_id == branch_id)
            due_stmt = due_stmt.where(BillingInvoice.branch_id == branch_id)
            collection_stmt = collection_stmt.where(BillingPayment.branch_id == branch_id)
            occupied_stmt = occupied_stmt.where(IPDBed.branch_id == branch_id)
            bed_total_stmt = bed_total_stmt.where(IPDBed.branch_id == branch_id)
            low_stock_stmt = low_stock_stmt.where(PharmacyMedicine.branch_id == branch_id)

        opd_total = int(self.db.scalar(opd_stmt) or 0)
        apt_total = int(self.db.scalar(apt_stmt) or 0)
        due_total = float(self.db.scalar(due_stmt) or 0)
        collection_total = float(self.db.scalar(collection_stmt) or 0)
        occupied = int(self.db.scalar(occupied_stmt) or 0)
        bed_total = int(self.db.scalar(bed_total_stmt) or 0)
        low_stock = int(self.db.scalar(low_stock_stmt) or 0)
        occupancy_pct = round((occupied / bed_total) * 100, 1) if bed_total else 0

        return StaffBotResponse(
            conversation_id=conversation.id,
            message=(
                f"Today summary: OPD {opd_total}, Appointments {apt_total}, "
                f"Collection {collection_total:,.0f} BDT, Due {due_total:,.0f} BDT."
            ),
            intent="hospital_summary",
            source_module="Dashboard Analytics",
            used_database=True,
            used_gemini=False,
            details=[
                StaffBotDetailRow(label="OPD visits (today)", value=str(opd_total)),
                StaffBotDetailRow(label="Appointments (today)", value=str(apt_total)),
                StaffBotDetailRow(label="IPD occupancy", value=f"{occupied}/{bed_total} ({occupancy_pct}%)"),
                StaffBotDetailRow(label="Pharmacy low stock", value=str(low_stock)),
                StaffBotDetailRow(label="Today collection", value=f"{collection_total:,.0f} BDT"),
                StaffBotDetailRow(label="Total due", value=f"{due_total:,.0f} BDT"),
            ],
            next_action="Open Dashboard for full module-wise analysis.",
            quick_replies=["Show revenue analysis", "Show pending payments", "Show IPD occupancy"],
        )

    def _revenue_analysis(self, actor: User, conversation: StaffBotConversation, normalized: str) -> StaffBotResponse:
        scope_days = 30
        if "weekly" in normalized or "week" in normalized:
            scope_days = 7
        elif "year" in normalized or "yearly" in normalized:
            scope_days = 365
        elif "month" in normalized or "monthly" in normalized:
            scope_days = 30
        start_date = date.today().fromordinal(date.today().toordinal() - scope_days + 1)

        billed_stmt = select(func.coalesce(func.sum(BillingInvoice.total_amount), 0)).where(
            BillingInvoice.status == "posted",
            cast(BillingInvoice.created_at, Date) >= start_date,
        )
        discount_stmt = select(func.coalesce(func.sum(BillingInvoice.discount_amount), 0)).where(
            BillingInvoice.status == "posted",
            cast(BillingInvoice.created_at, Date) >= start_date,
        )
        collected_stmt = select(func.coalesce(func.sum(BillingPayment.amount), 0)).where(cast(BillingPayment.received_at, Date) >= start_date)
        due_stmt = select(func.coalesce(func.sum(BillingInvoice.due_amount), 0)).where(BillingInvoice.status == "posted")
        if actor.branch_id:
            billed_stmt = billed_stmt.where(BillingInvoice.branch_id == actor.branch_id)
            discount_stmt = discount_stmt.where(BillingInvoice.branch_id == actor.branch_id)
            collected_stmt = collected_stmt.where(BillingPayment.branch_id == actor.branch_id)
            due_stmt = due_stmt.where(BillingInvoice.branch_id == actor.branch_id)

        billed = float(self.db.scalar(billed_stmt) or 0)
        discount = float(self.db.scalar(discount_stmt) or 0)
        collected = float(self.db.scalar(collected_stmt) or 0)
        due = float(self.db.scalar(due_stmt) or 0)
        realization_pct = round((collected / billed) * 100, 1) if billed else 0

        return StaffBotResponse(
            conversation_id=conversation.id,
            message=f"Revenue analysis ({scope_days} days): billed {billed:,.0f} BDT, collected {collected:,.0f} BDT, due {due:,.0f} BDT.",
            intent="revenue_analysis",
            source_module="Billing Analytics",
            used_database=True,
            used_gemini=False,
            details=[
                StaffBotDetailRow(label="Billed amount", value=f"{billed:,.0f} BDT"),
                StaffBotDetailRow(label="Collected amount", value=f"{collected:,.0f} BDT"),
                StaffBotDetailRow(label="Discount", value=f"{discount:,.0f} BDT"),
                StaffBotDetailRow(label="Outstanding due", value=f"{due:,.0f} BDT"),
                StaffBotDetailRow(label="Realization", value=f"{realization_pct}%"),
            ],
            next_action="Open Billing Overview for trend charts.",
            quick_replies=["Show pending payments", "Show today's collection", "Show hospital summary"],
        )

    def _book_opd_appointment(self, actor: User, conversation: StaffBotConversation, normalized: str) -> StaffBotResponse:
        context = dict(conversation.context or {})
        booking = dict(context.get("opd_booking") or {})
        booking["patient_token"] = booking.get("patient_token") or self._extract_patient_token(normalized)
        booking["doctor_token"] = booking.get("doctor_token") or self._extract_doctor_token(normalized)
        parsed_datetime = self._extract_datetime(normalized)
        if parsed_datetime:
            booking["slot_at"] = parsed_datetime.isoformat()
        context["opd_booking"] = booking
        conversation.context = context
        self.db.commit()

        missing: list[str] = []
        if not booking.get("patient_token"):
            missing.append("patient ID/number")
        if not booking.get("doctor_token"):
            missing.append("doctor name")
        if not booking.get("slot_at"):
            missing.append("date and time")
        if missing:
            return StaffBotResponse(
                conversation_id=conversation.id,
                message=f"To book OPD appointment, please provide: {', '.join(missing)}.",
                intent="opd_booking",
                source_module="Appointment / OPD Module",
                used_database=False,
                used_gemini=False,
                follow_up=True,
                required_fields=missing,
                quick_replies=[
                    "Book OPD for PAT-DEMO-0001 with Dr Rahman tomorrow 10:30",
                    "Book OPD for PAT-DEMO-0002 with Dr Karim today 17:00",
                ],
            )

        patient = self._find_patient(str(booking["patient_token"]), actor.branch_id)
        if not patient:
            return StaffBotResponse(
                conversation_id=conversation.id,
                message=f"Patient not found for “{booking['patient_token']}”. Please provide valid patient number/phone/name.",
                intent="opd_booking",
                source_module="Patient Module",
                used_database=True,
                used_gemini=False,
                follow_up=True,
                required_fields=["patient ID/number"],
            )
        doctor = self._find_doctor(str(booking["doctor_token"]), actor.branch_id)
        if not doctor:
            return StaffBotResponse(
                conversation_id=conversation.id,
                message=f"Doctor not found for “{booking['doctor_token']}”. Please provide a valid doctor name.",
                intent="opd_booking",
                source_module="Doctor / Department Module",
                used_database=True,
                used_gemini=False,
                follow_up=True,
                required_fields=["doctor name"],
            )

        slot_at = datetime.fromisoformat(str(booking["slot_at"]))
        if slot_at.tzinfo is None:
            slot_at = slot_at.replace(tzinfo=UTC)

        created = AppointmentsService(self.db).create_appointment(
            AppointmentCreate(
                patient_id=patient.id,
                doctor_user_id=doctor.id,
                appointment_at=slot_at,
                slot_start_at=slot_at,
                reason="Booked from Staff Assistant",
                note="Staff Assistant OPD booking",
            ),
            actor,
        )
        conversation.context = {**context, "active_patient_id": str(patient.id), "opd_booking": {}}
        self.db.commit()
        return StaffBotResponse(
            conversation_id=conversation.id,
            message=f"OPD appointment booked successfully. {created.appointment_number} at {created.appointment_at.isoformat()} with {created.doctor_name}.",
            intent="opd_booking",
            source_module="Appointment / OPD Module",
            used_database=True,
            used_gemini=False,
            details=[
                StaffBotDetailRow(label="Appointment", value=created.appointment_number),
                StaffBotDetailRow(label="Patient", value=created.patient_name),
                StaffBotDetailRow(label="Doctor", value=created.doctor_name),
                StaffBotDetailRow(label="Time", value=created.appointment_at.isoformat()),
            ],
            next_action="Open Appointments list to confirm or check-in.",
            quick_replies=["Show today's appointments", "Show OPD summary today", "Book another OPD appointment"],
        )

    def _patient_lookup(self, actor: User, conversation: StaffBotConversation, normalized: str) -> StaffBotResponse:
        token = self._extract_patient_token(normalized) or (conversation.context or {}).get("active_patient_token")
        if not token:
            return StaffBotResponse(
                conversation_id=conversation.id,
                message="Please provide the patient ID/number, phone number, or registered name.",
                intent="patient_info",
                source_module="Patient Module",
                used_database=False,
                used_gemini=False,
                follow_up=True,
                required_fields=["patient_id_or_phone_or_name"],
                quick_replies=["Show patient PAT-DEMO-0001", "Show patient by phone 01XXXXXXXXX"],
            )

        patient = self._find_patient(token, actor.branch_id)
        if not patient:
            return StaffBotResponse(
                conversation_id=conversation.id,
                message=f"I could not find a patient matching “{token}”. Please check the patient number/phone/name.",
                intent="patient_info",
                source_module="Patient Module",
                used_database=True,
                used_gemini=False,
                details=[],
                follow_up=True,
                required_fields=["patient_id_or_phone_or_name"],
            )

        conversation.context = {**(conversation.context or {}), "active_patient_token": token, "active_patient_id": str(patient.id)}
        self.db.commit()

        message = f"Patient found: {patient.patient_number} - {patient.first_name} {patient.last_name}."
        details = [
            StaffBotDetailRow(label="Patient No", value=patient.patient_number),
            StaffBotDetailRow(label="Name", value=f"{patient.first_name} {patient.last_name}"),
        ]
        if patient.phone:
            details.append(StaffBotDetailRow(label="Phone", value=patient.phone))
        if patient.gender:
            details.append(StaffBotDetailRow(label="Gender", value=patient.gender))
        return StaffBotResponse(
            conversation_id=conversation.id,
            message=message,
            intent="patient_info",
            source_module="Patient Module",
            used_database=True,
            used_gemini=False,
            details=details,
            next_action="Open Patients module to view full history.",
            quick_replies=["Show patient due", "Show OPD visits today", "Show prescriptions"],
        )

    def _gemini_fallback(self, actor: User, *, question: str, conversation: StaffBotConversation) -> str:
        context = conversation.context or {}
        context_text = ""
        if context.get("active_patient_token"):
            context_text += f"Active patient reference: {context.get('active_patient_token')}\n"
        if context.get("active_medicine_name"):
            context_text += f"Active medicine: {context.get('active_medicine_name')}\n"
        permissions = ", ".join(self.auth.get_effective_permissions(actor)[:50])

        user_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Logged-in user permissions: {permissions}\n"
            f"Conversation context:\n{context_text or '(none)'}\n\n"
            f"User question: {question}\n\n"
            "If the question asks for restricted data, respond with access denial guidance.\n"
            "Keep it concise."
        )
        return self._call_gemini(user_prompt)

    def _call_gemini(self, prompt: str) -> str:
        if not self.app_settings.gemini_api_key:
            return "Gemini is not configured on this server."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.app_settings.gemini_model}:generateContent?key={self.app_settings.gemini_api_key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 500},
        }
        data = str(payload).encode("utf-8")
        # Patient bot uses urllib with json dumps; keep lightweight here.
        import json

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as res:
                parsed = json.loads(res.read().decode("utf-8"))
                text = (
                    parsed.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text")
                )
                return text or "I couldn't generate a helpful response."
        except urllib.error.HTTPError as exc:
            raise AppException(502, "gemini_error", f"Gemini API error: {exc.code}")
        except urllib.error.URLError:
            raise AppException(502, "gemini_unavailable", "Gemini API is unreachable")

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return normalized

    def _detect_intent(self, normalized: str) -> str:
        if any(key in normalized for key in ["hospital summary", "today summary", "overall summary", "dashboard summary"]):
            return "hospital_summary"
        if any(key in normalized for key in ["low-stock", "low stock", "reorder", "stock out"]):
            return "low_stock"
        if any(key in normalized for key in ["pending lab", "pending tests", "lab pending", "abnormal result", "verification checklist"]):
            return "lab_pending"
        if any(key in normalized for key in ["pending pacs", "pacs upload", "imaging order", "radiology pending", "pending radiology"]):
            return "radiology_pending"
        if any(key in normalized for key in ["payroll exception", "deduction issue", "salary processing", "payroll approval"]):
            return "payroll_exceptions"
        if any(key in normalized for key in ["revenue analysis", "collection analysis", "billing analysis", "revenue trend"]):
            return "revenue_analysis"
        if any(key in normalized for key in ["book opd", "opd booking", "book appointment", "register opd visit"]):
            return "opd_booking"
        if any(key in normalized for key in ["pending payment", "pending payments", "unpaid invoice", "unpaid invoices"]):
            return "pending_payments"
        if any(key in normalized for key in ["opd", "opd patients", "opd summary", "today opd"]):
            return "opd_today_summary" if "today" in normalized or "opd" in normalized else "opd_today_summary"
        if "occupied" in normalized and "bed" in normalized:
            return "ipd_bed_occupancy"
        if "admitted" in normalized and ("under me" in normalized or "under my" in normalized):
            return "ipd_admitted_under_me"
        if ("ipd" in normalized and "occupancy" in normalized) or any(key in normalized for key in ["ipd bed", "bed occupancy", "beds occupied", "available beds"]):
            return "ipd_bed_occupancy"
        if any(key in normalized for key in ["medicine", "stock", "available", "pharmacy"]):
            if "bill" not in normalized and "invoice" not in normalized:
                return "pharmacy_stock"
        if any(key in normalized for key in ["due", "bill", "invoice"]):
            return "billing_due"
        if "appointment" in normalized:
            return "appointment_status"
        if "patient" in normalized and any(key in normalized for key in ["detail", "info", "show", "find"]):
            return "patient_info"
        if any(key in normalized for key in ["permission", "role", "can i", "allowed"]):
            return "permission_check"
        if any(key in normalized for key in ["symptom", "fever", "cough", "rash", "chest pain", "diet", "what should i do"]):
            return "general_health_guidance"
        return "unknown"

    def _get_or_create_conversation(self, conversation_id: UUID | None, actor: User, *, assistant_context: StaffBotContext | None) -> StaffBotConversation:
        if conversation_id:
            item = self.db.get(StaffBotConversation, conversation_id)
            if item and item.user_id == actor.id and item.is_active:
                return item
        return self._create_conversation(actor, assistant_context=assistant_context)

    def _create_conversation(self, actor: User, *, assistant_context: StaffBotContext | None) -> StaffBotConversation:
        context = self._context_to_dict(assistant_context)
        item = StaffBotConversation(
            branch_id=actor.branch_id,
            user_id=actor.id,
            title="Staff Assistant",
            context=context or {"context": "staff-dashboard"},
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def _merge_context(self, conversation: StaffBotConversation, assistant_context: StaffBotContext | None) -> None:
        context = self._context_to_dict(assistant_context)
        if not context:
            return
        conversation.context = {**(conversation.context or {}), **context}
        conversation.updated_at = datetime.now(UTC)
        self.db.commit()

    @staticmethod
    def _coerce_context(raw_context: StaffBotContext | str | None) -> StaffBotContext | None:
        if raw_context is None:
            return None
        if isinstance(raw_context, StaffBotContext):
            return raw_context
        return StaffBotContext(module=raw_context, page=raw_context, path=raw_context)

    @staticmethod
    def _context_to_dict(assistant_context: StaffBotContext | None) -> dict[str, Any]:
        if not assistant_context:
            return {}
        return assistant_context.model_dump(exclude_none=True)

    def _save_message(self, conversation: StaffBotConversation, sender: str, message: str, *, meta: dict[str, Any]) -> None:
        self.db.add(
            StaffBotMessage(
                conversation_id=conversation.id,
                sender=sender,
                message=message,
                meta=meta,
                created_by=conversation.user_id,
                updated_by=conversation.user_id,
            )
        )
        self.db.commit()

    def _audit(
        self,
        actor: User,
        conversation: StaffBotConversation,
        question: str,
        *,
        intent: str,
        source_module: str,
        used_db: bool,
        used_gemini: bool,
        response_summary: str,
    ) -> None:
        self.db.add(
            StaffBotAuditLog(
                branch_id=actor.branch_id,
                user_id=actor.id,
                conversation_id=conversation.id,
                question=question,
                intent=intent,
                source_module=source_module,
                used_database=used_db,
                used_gemini=used_gemini,
                response_summary=response_summary,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
        self.db.commit()

    def _find_patient(self, token: str, branch_id: UUID | None) -> Patient | None:
        token = token.strip()
        stmt = select(Patient).where(Patient.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(Patient.branch_id == branch_id)
        if token.upper().startswith("PAT"):
            stmt = stmt.where(Patient.patient_number == token)
            return self.db.scalar(stmt)
        # phone or name
        stmt = stmt.where(or_(Patient.phone == token, func.concat(Patient.first_name, " ", Patient.last_name).ilike(f"%{token}%")))
        return self.db.scalar(stmt)

    def _find_doctor(self, token: str, branch_id: UUID | None) -> User | None:
        token = token.strip()
        stmt = select(User).where(User.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(User.branch_id == branch_id)
        if token.startswith("dr "):
            token = token[3:]
        stmt = stmt.where(User.full_name.ilike(f"%{token}%"))
        doctors = list(self.db.scalars(stmt.limit(20)))
        for doctor in doctors:
            if any(role.is_doctor_role or role.code == "DOCTOR" for role in doctor.roles):
                return doctor
        return None

    @staticmethod
    def _extract_medicine_query(normalized: str) -> str | None:
        # Prefer quoted string if present
        m = re.search(r"\"([^\"]{2,80})\"", normalized)
        if m:
            return m.group(1).strip()
        # Common patterns: "is X available", "check X stock"
        m = re.search(r"(?:is|check|stock of|available)\s+([a-z0-9][a-z0-9 \-]{1,40})", normalized)
        if m:
            return m.group(1).strip()
        # Fallback: last token after "medicine"
        if "medicine" in normalized:
            tail = normalized.split("medicine", 1)[1].strip()
            return tail[:50] if tail else None
        return None

    @staticmethod
    def _extract_patient_token(normalized: str) -> str | None:
        # PAT- style
        m = re.search(r"(pat[\w\-]{2,40})", normalized, re.IGNORECASE)
        if m:
            return m.group(1).strip().upper()
        # "patient 1023"
        m = re.search(r"patient\s+([a-z0-9\-]{3,40})", normalized)
        if m:
            return m.group(1).strip().upper()
        return None

    @staticmethod
    def _extract_doctor_token(normalized: str) -> str | None:
        m = re.search(r"(?:dr\.?|doctor)\s+([a-z][a-z ]{1,40})", normalized)
        if m:
            return m.group(1).strip().title()
        return None

    @staticmethod
    def _extract_datetime(normalized: str) -> datetime | None:
        # yyyy-mm-dd hh:mm
        iso_match = re.search(r"(20\d{2}-\d{2}-\d{2})\s+([01]\d|2[0-3]):([0-5]\d)", normalized)
        if iso_match:
            d = iso_match.group(1)
            h = iso_match.group(2)
            m = iso_match.group(3)
            return datetime.fromisoformat(f"{d}T{h}:{m}:00+00:00")
        # today/tomorrow HH:MM
        rel_match = re.search(r"(today|tomorrow)\s+([01]?\d|2[0-3]):([0-5]\d)", normalized)
        if rel_match:
            day_key = rel_match.group(1)
            hour = int(rel_match.group(2))
            minute = int(rel_match.group(3))
            base = date.today()
            if day_key == "tomorrow":
                base = date.fromordinal(base.toordinal() + 1)
            return datetime(base.year, base.month, base.day, hour, minute, tzinfo=UTC)
        return None
