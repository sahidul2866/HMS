from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe
from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.accounting import AccountingJournal, JournalEntry
from app.models.billing import BillingInvoice
from app.models.blood_bank import BloodIssue, BloodRequest, BloodUnit
from app.models.encounter import Appointment, ERVisit, IPDAdmission, IPDBed, OPDVisit
from app.models.hr import HREmployee
from app.models.inventory import InventoryItem, InventoryStore, StockBatch
from app.models.laboratory import LabOrder, LabResult
from app.models.patient import Patient
from app.models.pharmacy import PharmacyDispense, PharmacyMedicine
from app.models.queue import QueueToken
from app.models.radiology import RadiologyOrder, RadiologyReport
from app.models.scanner import ScanCode, ScanEvent, ScanSetting
from app.modules.auth.service import AuthService
from app.schemas.scanner import ScanCodeCreate, ScanResolveRequest, ScanResolveResponse, ScanResolvedRecord, ScanSettingWrite


class ScannerService:
    def __init__(self, db: Session):
        self.db = db

    def resolve(self, payload: ScanResolveRequest, user, context: dict | None = None) -> ScanResolveResponse:
        code = self._normalize(payload.code)
        records = self._resolve_registered(code) or self._resolve_known_identifiers(code)
        allowed_records: list[ScanResolvedRecord] = []
        denied = False
        permissions = set(AuthService(self.db).get_effective_permissions(user))

        for record in records:
            if payload.expected_record_type and record.record_type != payload.expected_record_type:
                record.safety["mismatch"] = "record_type"
            if payload.expected_patient_id:
                patient_id = record.data.get("patient_id") or (str(record.record_id) if record.record_type == "patient" else None)
                if patient_id and patient_id != str(payload.expected_patient_id):
                    record.safety["mismatch"] = "patient"
            if record.permission in permissions:
                allowed_records.append(record)
            else:
                denied = True

        success = bool(allowed_records)
        message = "Record found" if success else "Permission denied" if denied else "Invalid barcode"
        self._log_scan(payload, code, user, success, message, allowed_records[0] if allowed_records else None, context)
        return ScanResolveResponse(success=success, message=message, code=code, match_count=len(allowed_records), records=allowed_records, action=payload.action)

    def create_code(self, payload: ScanCodeCreate, user, context: dict | None = None) -> ScanCode:
        code = ScanCode(
            branch_id=getattr(user, "branch_id", None),
            code_value=self._secure_code(payload.record_type, payload.purpose),
            code_type=payload.code_type,
            purpose=payload.purpose,
            record_type=payload.record_type,
            record_id=payload.record_id,
            display_value=payload.display_value,
            expires_at=payload.expires_at,
            meta=payload.meta or {},
            created_by=user.id,
            updated_by=user.id,
        )
        self.db.add(code)
        self.db.flush()
        self._log_scan(
            ScanResolveRequest(code=code.code_value, module="scanner", action="generate"),
            code.code_value,
            user,
            True,
            "Barcode generated",
            ScanResolvedRecord(record_type=code.record_type, record_id=code.record_id, display=code.display_value or code.record_type, module="scanner", permission="scanner.generate"),
            context,
        )
        self.db.commit()
        self.db.refresh(code)
        return code

    def list_settings(self, user):
        return self.db.scalars(
            select(ScanSetting).where(or_(ScanSetting.branch_id == getattr(user, "branch_id", None), ScanSetting.branch_id.is_(None))).order_by(ScanSetting.setting_key)
        ).all()

    def upsert_setting(self, payload: ScanSettingWrite, user):
        setting = self.db.scalar(
            select(ScanSetting).where(
                ScanSetting.branch_id == getattr(user, "branch_id", None),
                ScanSetting.department_id.is_(payload.department_id) if payload.department_id is None else ScanSetting.department_id == payload.department_id,
                ScanSetting.setting_key == payload.setting_key,
            )
        )
        if not setting:
            setting = ScanSetting(branch_id=getattr(user, "branch_id", None), department_id=payload.department_id, setting_key=payload.setting_key, created_by=user.id)
            self.db.add(setting)
        setting.setting_value = payload.setting_value
        setting.updated_by = user.id
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def _resolve_registered(self, code: str) -> list[ScanResolvedRecord]:
        scan_code = self.db.scalar(select(ScanCode).where(func.lower(ScanCode.code_value) == code.lower(), ScanCode.is_active.is_(True)))
        if not scan_code or (scan_code.expires_at and scan_code.expires_at < datetime.now(UTC)):
            return []
        return self._record_by_type(scan_code.record_type, scan_code.record_id)

    def _resolve_known_identifiers(self, code: str) -> list[ScanResolvedRecord]:
        records: list[ScanResolvedRecord] = []
        lower = code.lower()

        patient = self.db.scalar(select(Patient).where(func.lower(Patient.patient_number) == lower))
        if patient:
            records.append(self._patient_record(patient))

        appointment = self.db.scalar(select(Appointment).where(func.lower(Appointment.appointment_number) == lower))
        if appointment:
            records.append(self._record("appointment", appointment.id, appointment.appointment_number, "appointment", "appointment.view", f"/appointments", {"patient_id": str(appointment.patient_id), "status": appointment.status}))

        opd = self.db.scalar(select(OPDVisit).where(func.lower(OPDVisit.visit_number) == lower))
        if opd:
            records.append(self._record("opd_visit", opd.id, opd.visit_number, "opd", "opd.view", "/opd/visits", {"patient_id": str(opd.patient_id), "status": opd.status}))

        queue_token = self.db.scalar(select(QueueToken).where(or_(func.lower(QueueToken.token_number) == lower, func.lower(func.concat("queue:", QueueToken.token_number, ":", QueueToken.id)) == lower)))
        if queue_token:
            records.append(self._record("queue_token", queue_token.id, queue_token.token_number, queue_token.module, "queue.view", "/queue", {"patient_id": str(queue_token.patient_id) if queue_token.patient_id else None, "queue_scope": queue_token.queue_scope, "status": queue_token.status}))

        ipd = self.db.scalar(select(IPDAdmission).where(func.lower(IPDAdmission.admission_number) == lower))
        if ipd:
            records.append(self._record("ipd_admission", ipd.id, ipd.admission_number, "ipd", "ipd.view", "/ipd/admissions", {"patient_id": str(ipd.patient_id), "status": ipd.status, "bed": ipd.bed_number}))

        er = self.db.scalar(select(ERVisit).where(func.lower(ERVisit.visit_number) == lower))
        if er:
            records.append(self._record("er_visit", er.id, er.visit_number, "emergency", "er.view", "/er", {"patient_id": str(er.patient_id), "status": er.status}))

        invoice = self.db.scalar(select(BillingInvoice).where(func.lower(BillingInvoice.invoice_number) == lower))
        if invoice:
            records.append(self._record("billing_invoice", invoice.id, invoice.invoice_number, "billing", "billing.view", "/billing/list", {"patient_id": str(invoice.patient_id), "payment_status": invoice.payment_status, "due_amount": str(invoice.due_amount)}))

        lab_order = self.db.scalar(select(LabOrder).where(func.lower(LabOrder.order_number) == lower))
        if lab_order:
            records.append(self._record("lab_order", lab_order.id, lab_order.order_number, "laboratory", "laboratory.view", "/laboratory", {"patient_id": str(lab_order.patient_id), "status": lab_order.status}))

        lab_result = self.db.scalar(select(LabResult).where(func.lower(LabResult.report_number) == lower))
        if lab_result:
            records.append(self._record("lab_report", lab_result.id, lab_result.report_number, "laboratory", "laboratory.view", "/laboratory", {"order_id": str(lab_result.order_id), "status": lab_result.status}))

        radiology_order = self.db.scalar(select(RadiologyOrder).where(func.lower(RadiologyOrder.order_number) == lower))
        if radiology_order:
            records.append(self._record("radiology_order", radiology_order.id, radiology_order.order_number, "radiology", "radiology.view", "/radiology", {"patient_id": str(radiology_order.patient_id), "status": radiology_order.status}))

        radiology_report = self.db.scalar(select(RadiologyReport).where(func.lower(RadiologyReport.report_number) == lower))
        if radiology_report:
            records.append(self._record("radiology_report", radiology_report.id, radiology_report.report_number, "radiology", "radiology.view", "/radiology", {"order_id": str(radiology_report.order_id), "status": radiology_report.status}))

        medicine = self.db.scalar(select(PharmacyMedicine).where(or_(func.lower(func.coalesce(PharmacyMedicine.barcode, "")) == lower, func.lower(func.coalesce(PharmacyMedicine.sku, "")) == lower)))
        if medicine:
            safety = {"expired": False, "stock_available": str(medicine.stock_quantity)}
            records.append(self._record("pharmacy_medicine", medicine.id, medicine.name, "pharmacy", "pharmacy.view", "/pharmacy/medicines", {"barcode": medicine.barcode, "stock_quantity": str(medicine.stock_quantity)}, safety))

        dispense = self.db.scalar(select(PharmacyDispense).where(func.lower(PharmacyDispense.prescription_ref) == lower))
        if dispense:
            records.append(self._record("pharmacy_dispense", dispense.id, dispense.prescription_ref or str(dispense.id), "pharmacy", "pharmacy.dispense", "/pharmacy/dispense", {"patient_id": str(dispense.patient_id), "status": dispense.status}))

        item = self.db.scalar(select(InventoryItem).where(or_(func.lower(func.coalesce(InventoryItem.barcode, "")) == lower, func.lower(func.coalesce(InventoryItem.item_code, "")) == lower)))
        if item:
            records.append(self._record("inventory_item", item.id, item.name, "inventory", "inventory.view", "/inventory", {"barcode": item.barcode, "stock_quantity": str(item.stock_quantity)}))

        batch = self.db.scalar(select(StockBatch).where(func.lower(func.coalesce(StockBatch.batch_no, "")) == lower))
        if batch:
            records.append(self._record("stock_batch", batch.id, batch.batch_no or str(batch.id), "inventory", "inventory.view", "/inventory", {"item_id": str(batch.item_id), "expiry_date": str(batch.expiry_date) if batch.expiry_date else None, "quantity": str(batch.quantity)}))

        store = self.db.scalar(select(InventoryStore).where(func.lower(InventoryStore.code) == lower))
        if store:
            records.append(self._record("inventory_store", store.id, store.name, "inventory", "inventory.store.manage", "/inventory", {"code": store.code, "store_type": store.store_type}))

        unit = self.db.scalar(select(BloodUnit).where(func.lower(BloodUnit.unit_number) == lower))
        if unit:
            safety = {"issuable": unit.status in {"available", "crossmatched", "reserved"} and unit.testing_status == "completed", "testing_status": unit.testing_status}
            records.append(self._record("blood_unit", unit.id, unit.unit_number, "blood_bank", "blood_bank.stock.view", "/blood-bank", {"blood_group": unit.blood_group, "component_type": unit.component_type, "status": unit.status}, safety))

        blood_request = self.db.scalar(select(BloodRequest).where(func.lower(BloodRequest.request_number) == lower))
        if blood_request:
            records.append(self._record("blood_request", blood_request.id, blood_request.request_number, "blood_bank", "blood_bank.view", "/blood-bank", {"patient_id": str(blood_request.patient_id), "status": blood_request.status}))

        employee = self.db.scalar(select(HREmployee).where(func.lower(HREmployee.staff_code) == lower))
        if employee:
            records.append(self._record("employee", employee.id, f"{employee.staff_code} - {employee.full_name}", "hr", "hr.view", "/hr", {"employment_status": employee.employment_status}))

        journal = self.db.scalar(select(JournalEntry).where(or_(func.lower(JournalEntry.journal_number) == lower, func.lower(func.coalesce(JournalEntry.source_reference, "")) == lower)))
        if journal:
            records.append(self._record("accounting_voucher", journal.id, journal.journal_number, "accounting", "accounting.view", "/accounting", {"status": journal.status, "source_reference": journal.source_reference}))

        legacy_journal = self.db.scalar(select(AccountingJournal).where(or_(func.lower(AccountingJournal.journal_number) == lower, func.lower(func.coalesce(AccountingJournal.reference, "")) == lower)))
        if legacy_journal:
            records.append(self._record("accounting_journal", legacy_journal.id, legacy_journal.journal_number, "accounting", "accounting.view", "/accounting", {"status": legacy_journal.status, "reference": legacy_journal.reference}))

        bed = self.db.scalar(select(IPDBed).where(or_(func.lower(IPDBed.bed_number) == lower, func.lower(func.coalesce(IPDBed.ward_name, "")) == lower)))
        if bed:
            records.append(self._record("ipd_bed", bed.id, f"{bed.ward_name} / {bed.bed_number}", "ipd", "ipd.view", "/ipd/settings", {"status": bed.status}))

        return records

    def _record_by_type(self, record_type: str, record_id: UUID) -> list[ScanResolvedRecord]:
        model_map = {
            "patient": (Patient, self._patient_record),
            "appointment": (Appointment, lambda x: self._record("appointment", x.id, x.appointment_number, "appointment", "appointment.view", "/appointments", {"patient_id": str(x.patient_id), "status": x.status})),
            "opd_visit": (OPDVisit, lambda x: self._record("opd_visit", x.id, x.visit_number, "opd", "opd.view", "/opd/visits", {"patient_id": str(x.patient_id), "status": x.status})),
            "ipd_admission": (IPDAdmission, lambda x: self._record("ipd_admission", x.id, x.admission_number, "ipd", "ipd.view", "/ipd/admissions", {"patient_id": str(x.patient_id), "status": x.status})),
            "billing_invoice": (BillingInvoice, lambda x: self._record("billing_invoice", x.id, x.invoice_number, "billing", "billing.view", "/billing/list", {"patient_id": str(x.patient_id), "payment_status": x.payment_status})),
            "blood_unit": (BloodUnit, lambda x: self._record("blood_unit", x.id, x.unit_number, "blood_bank", "blood_bank.stock.view", "/blood-bank", {"status": x.status, "blood_group": x.blood_group})),
            "blood_request": (BloodRequest, lambda x: self._record("blood_request", x.id, x.request_number, "blood_bank", "blood_bank.view", "/blood-bank", {"patient_id": str(x.patient_id), "status": x.status, "blood_group": x.blood_group, "component_type": x.component_type})),
            "queue_token": (QueueToken, lambda x: self._record("queue_token", x.id, x.token_number, x.module, "queue.view", "/queue", {"patient_id": str(x.patient_id) if x.patient_id else None, "queue_scope": x.queue_scope, "status": x.status})),
        }
        entry = model_map.get(record_type)
        if not entry:
            return []
        model, factory = entry
        item = self.db.get(model, record_id)
        return [factory(item)] if item else []

    def _patient_record(self, patient: Patient) -> ScanResolvedRecord:
        active_ipd = self.db.scalar(select(IPDAdmission).where(IPDAdmission.patient_id == patient.id, IPDAdmission.status.notin_(["discharged", "cancelled"])).order_by(IPDAdmission.created_at.desc()))
        active_er = self.db.scalar(select(ERVisit).where(ERVisit.patient_id == patient.id, ERVisit.status.notin_(["discharged", "transferred", "cancelled"])).order_by(ERVisit.created_at.desc()))
        return self._record(
            "patient",
            patient.id,
            f"{patient.patient_number} - {patient.first_name} {patient.last_name}",
            "patients",
            "patient.view",
            f"/patients/{patient.id}",
            {
                "patient_number": patient.patient_number,
                "name": f"{patient.first_name} {patient.last_name}",
                "gender": patient.gender,
                "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else None,
                "phone": patient.phone,
                "address": patient.address,
                "active_admission_id": str(active_ipd.id) if active_ipd else None,
                "active_er_visit_id": str(active_er.id) if active_er else None,
            },
        )

    def _record(self, record_type: str, record_id: UUID, display: str, module: str, permission: str, route: str, data: dict, safety: dict | None = None) -> ScanResolvedRecord:
        return ScanResolvedRecord(record_type=record_type, record_id=record_id, display=display, module=module, permission=permission, route=route, data=data, status=data.get("status"), safety=safety or {})

    def _log_scan(self, payload: ScanResolveRequest, normalized_code: str, user, success: bool, message: str, record: ScanResolvedRecord | None, context: dict | None) -> None:
        self.db.add(
            ScanEvent(
                branch_id=getattr(user, "branch_id", None),
                department_id=getattr(user, "department_id", None),
                user_id=getattr(user, "id", None),
                scanned_code=payload.code,
                normalized_code=normalized_code,
                module=payload.module,
                action=payload.action,
                record_type=record.record_type if record else None,
                record_id=record.record_id if record else None,
                success="true" if success else "false",
                message=message,
                device_label=payload.device_label,
                location_label=payload.location_label,
                ip_address=(context or {}).get("ip_address"),
                user_agent=(context or {}).get("user_agent"),
                meta={"expected_record_type": payload.expected_record_type, "expected_patient_id": str(payload.expected_patient_id) if payload.expected_patient_id else None},
            )
        )
        self.db.commit()

    def _secure_code(self, record_type: str, purpose: str) -> str:
        return f"HMS:{purpose.upper()}:{record_type.upper()}:{token_urlsafe(18)}"

    def _normalize(self, code: str) -> str:
        return code.strip()
