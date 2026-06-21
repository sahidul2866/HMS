from datetime import UTC, date, datetime
from secrets import token_hex

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models.patient import Patient
from app.models.scanner import ScanCode, ScanSetting
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.patients.repository import PatientsRepository
from app.schemas.encounter import OPDVisitRead
from app.schemas.patient import (
    PatientClinicalHistoryRead,
    PatientCreate,
    PatientHistoryBillingInvoiceRead,
    PatientHistoryBillingPaymentRead,
    PatientHistoryIPDAdmissionRead,
    PatientIdCardRead,
    PatientIdCardTemplateRead,
    PatientIdCardTemplateWrite,
    PatientMobileLookupRead,
    PatientHistoryAppointmentRead,
    PatientLookupResult,
    PatientHistoryOPDVisitRead,
    PatientHistoryOrderRead,
    PatientHistoryPharmacyDispenseRead,
    PatientRead,
)
from app.utils.enums import AuditAction
from app.utils.phone import normalize_phone


class PatientsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PatientsRepository(db)

    def list_patients(self, actor: User) -> list[Patient]:
        branch_scope = actor.branch_id
        return self.repository.list_patients(branch_scope)

    def search_patients(self, query: str, actor: User, *, limit: int = 10) -> list[PatientLookupResult]:
        branch_scope = actor.branch_id
        patients = self.repository.search_patients(query, branch_scope, limit=limit)
        return [
            PatientLookupResult(
                **PatientRead.model_validate(item, from_attributes=True).model_dump(),
                full_name=f"{item.first_name} {item.last_name}".strip(),
            )
            for item in patients
        ]

    def lookup_patients_by_mobile(self, mobile: str, actor: User, *, limit: int = 25) -> PatientMobileLookupRead:
        normalized_mobile = normalize_phone(mobile)
        if not normalized_mobile:
            raise AppException(400, "invalid_mobile", "A valid mobile number is required")

        branch_scope = actor.branch_id
        patients = self.repository.list_patients_by_phone(normalized_mobile, branch_scope, limit=limit)
        max_allowed = get_settings().max_patients_per_mobile
        return PatientMobileLookupRead(
            mobile=mobile,
            normalized_mobile=normalized_mobile,
            max_patients_allowed=max_allowed,
            current_patient_count=len(patients),
            can_add_more=len(patients) < max_allowed,
            patients=[
                PatientLookupResult(
                    **PatientRead.model_validate(item, from_attributes=True).model_dump(),
                    full_name=f"{item.first_name} {item.last_name}".strip(),
                )
                for item in patients
            ],
        )

    def get_patient(self, patient_id, actor: User) -> Patient:
        patient = self.repository.get_patient(patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")
        return patient

    def get_clinical_history(self, patient_id, actor: User) -> PatientClinicalHistoryRead:
        patient = self.get_patient(patient_id, actor)
        opd_visits = self.repository.list_opd_visits(patient.id)
        appointments = self.repository.list_appointments(patient.id)
        ipd_admissions = self.repository.list_ipd_admissions(patient.id)
        billing_invoices = self.repository.list_billing_invoices(patient.id)
        pharmacy_dispenses = self.repository.list_pharmacy_dispenses(patient.id)
        return PatientClinicalHistoryRead(
            patient=PatientRead.model_validate(patient, from_attributes=True),
            opd_visits=[
                PatientHistoryOPDVisitRead(
                    id=visit.id,
                    visit_number=visit.visit_number,
                    visit_date=visit.visit_date,
                    department_name=visit.department_name,
                    consulting_doctor_name=visit.consulting_doctor_name,
                    chief_complaint=visit.chief_complaint,
                    history_of_present_illness=visit.history_of_present_illness,
                    past_history=visit.past_history,
                    vital_signs=visit.vital_signs,
                    examination_note=visit.examination_note,
                    provisional_diagnosis=visit.provisional_diagnosis,
                    final_diagnosis=visit.final_diagnosis,
                    follow_up_date=visit.follow_up_date,
                    follow_up_note=visit.follow_up_note,
                    note=visit.note,
                    status=visit.status,
                    orders=[
                        PatientHistoryOrderRead(
                            id=order.id,
                            order_type=order.order_type,
                            service_area=order.service_area,
                            item_name=order.item_name,
                            quantity=str(order.quantity),
                            status=order.status,
                            instructions=order.instructions,
                            result_text=order.result_text,
                            completed_at=order.completed_at,
                        )
                        for order in visit.orders
                    ],
                )
                for visit in opd_visits
            ],
            appointments=[
                PatientHistoryAppointmentRead(
                    id=appointment.id,
                    appointment_number=appointment.appointment_number,
                    doctor_name=appointment.doctor.full_name,
                    appointment_at=appointment.appointment_at,
                    status=appointment.status,
                    reason=appointment.reason,
                    note=appointment.note,
                )
                for appointment in appointments
            ],
            ipd_admissions=[
                PatientHistoryIPDAdmissionRead(
                    id=admission.id,
                    admission_number=admission.admission_number,
                    admitted_at=admission.admitted_at,
                    attending_doctor_name=admission.attending_doctor_name,
                    diagnosis=admission.diagnosis,
                    status=admission.status,
                    ward_name=admission.ward_name,
                    bed_number=admission.bed_number,
                    discharged_at=admission.discharged_at,
                    active_doctors=[
                        assignment.staff_name
                        for assignment in admission.staff_assignments
                        if assignment.role_type == "doctor" and not assignment.ended_at
                    ],
                    active_nurses=[
                        assignment.staff_name
                        for assignment in admission.staff_assignments
                        if assignment.role_type == "nurse" and not assignment.ended_at
                    ],
                    tracking=[
                        {
                            "title": event.title,
                            "detail": event.detail,
                            "time": event.occurred_at.isoformat() if event.occurred_at else None,
                            "type": event.event_type,
                        }
                        for event in sorted(admission.timeline_events, key=lambda item: item.occurred_at, reverse=True)[:8]
                    ],
                )
                for admission in ipd_admissions
            ],
            billing_invoices=[
                PatientHistoryBillingInvoiceRead(
                    id=invoice.id,
                    invoice_number=invoice.invoice_number,
                    created_at=invoice.created_at,
                    status=invoice.status,
                    payment_status=invoice.payment_status,
                    total_amount=str(invoice.total_amount),
                    paid_amount=str(invoice.paid_amount),
                    due_amount=str(invoice.due_amount),
                    referred_doctor_name=invoice.referred_doctor_name,
                )
                for invoice in billing_invoices
            ],
            billing_payments=[
                PatientHistoryBillingPaymentRead(
                    id=payment.id,
                    invoice_number=invoice.invoice_number,
                    receipt_number=payment.receipt_number,
                    payment_method=payment.payment_method,
                    amount=str(payment.amount),
                    received_at=payment.received_at,
                    note=payment.note,
                )
                for invoice in billing_invoices
                for payment in invoice.payments
            ],
            pharmacy_dispenses=[
                PatientHistoryPharmacyDispenseRead(
                    id=dispense.id,
                    prescription_ref=dispense.prescription_ref,
                    medicine_name=dispense.medicine_name,
                    quantity=str(dispense.quantity),
                    total_price=str(dispense.total_price),
                    created_at=dispense.created_at,
                )
                for dispense in pharmacy_dispenses
            ],
        )

    def get_patient_opd_visits(self, patient_id, actor: User) -> list:
        patient = self.get_patient(patient_id, actor)
        return self.repository.list_opd_visits(patient.id)

    def create_patient(self, payload: PatientCreate, actor: User, context: dict[str, str | None]) -> Patient:
        normalized_phone = normalize_phone(payload.phone)
        if not normalized_phone or len(normalized_phone) < 6:
            raise AppException(400, "invalid_mobile", "A valid mobile number is required")
        branch_scope = payload.branch_id or actor.branch_id
        existing_count = self.repository.count_patients_by_phone(normalized_phone, branch_scope)
        max_allowed = get_settings().max_patients_per_mobile
        if existing_count >= max_allowed:
            raise AppException(
                400,
                "mobile_patient_limit_reached",
                f"This mobile number already has the maximum allowed {max_allowed} patient records",
            )

        sequence = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        patient = Patient(
            **payload.model_dump(exclude={"phone", "branch_id"}),
            phone=normalized_phone,
            patient_number=f"PAT-{sequence}-{token_hex(2).upper()}",
            branch_id=branch_scope,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_patient(patient)
        self._ensure_patient_id_card_code(patient, actor)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.PATIENT_CREATE,
            module="patients",
            entity_type="patient",
            entity_id=str(patient.id),
            detail={"patient_number": patient.patient_number, "name": f"{patient.first_name} {patient.last_name}"},
            context=context,
        )
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def get_id_card(self, patient_id, actor: User, context: dict[str, str | None], *, log_action: str | None = None, is_reprint: bool = False) -> PatientIdCardRead:
        patient = self.get_patient(patient_id, actor)
        code = self._ensure_patient_id_card_code(patient, actor)
        if log_action:
            AuditService(self.db).log(
                user_id=actor.id,
                action=log_action,
                module="patients",
                entity_type="patient_id_card",
                entity_id=str(patient.id),
                detail={"patient_number": patient.patient_number, "scan_code_id": str(code.id), "is_reprint": is_reprint},
                context=context,
            )
            self.db.commit()
        return self._card_read(patient, code, is_reprint=is_reprint)

    def generate_id_card(self, patient_id, actor: User, context: dict[str, str | None]) -> PatientIdCardRead:
        return self.get_id_card(patient_id, actor, context, log_action="patient.id_card.generate")

    def print_id_card(self, patient_id, actor: User, context: dict[str, str | None], *, reprint: bool = False) -> PatientIdCardRead:
        return self.get_id_card(patient_id, actor, context, log_action="patient.id_card.reprint" if reprint else "patient.id_card.print", is_reprint=reprint)

    def get_id_card_template(self, actor: User) -> PatientIdCardTemplateRead:
        setting = self.db.scalar(
            select(ScanSetting).where(
                ScanSetting.branch_id == actor.branch_id,
                ScanSetting.department_id.is_(None),
                ScanSetting.setting_key == "patient_id_card_template",
            )
        )
        if not setting:
            return PatientIdCardTemplateRead()
        return PatientIdCardTemplateRead(**(setting.setting_value or {}))

    def update_id_card_template(self, payload: PatientIdCardTemplateWrite, actor: User, context: dict[str, str | None]) -> PatientIdCardTemplateRead:
        setting = self.db.scalar(
            select(ScanSetting).where(
                ScanSetting.branch_id == actor.branch_id,
                ScanSetting.department_id.is_(None),
                ScanSetting.setting_key == "patient_id_card_template",
            )
        )
        if not setting:
            setting = ScanSetting(
                branch_id=actor.branch_id,
                department_id=None,
                setting_key="patient_id_card_template",
                setting_value=payload.model_dump(),
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.db.add(setting)
        else:
            setting.setting_value = payload.model_dump()
            setting.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action="patient.id_card.template.update",
            module="patients",
            entity_type="patient_id_card_template",
            entity_id=str(setting.id) if setting.id else None,
            detail=payload.model_dump(),
            context=context,
        )
        self.db.commit()
        self.db.refresh(setting)
        return PatientIdCardTemplateRead(**setting.setting_value)

    def _ensure_patient_id_card_code(self, patient: Patient, actor: User) -> ScanCode:
        existing = self.db.scalar(
            select(ScanCode).where(
                ScanCode.record_type == "patient",
                ScanCode.record_id == patient.id,
                ScanCode.purpose == "patient_id_card",
                ScanCode.is_active.is_(True),
            )
        )
        if existing:
            return existing
        code = ScanCode(
            branch_id=patient.branch_id or actor.branch_id,
            code_value=self._patient_card_code(),
            code_type="code39",
            purpose="patient_id_card",
            record_type="patient",
            record_id=patient.id,
            display_value=patient.patient_number,
            meta={"patient_number": patient.patient_number},
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(code)
        self.db.flush()
        AuditService(self.db).log(
            user_id=actor.id,
            action="patient.id_card.generate",
            module="patients",
            entity_type="patient_id_card",
            entity_id=str(patient.id),
            detail={"patient_number": patient.patient_number, "scan_code_id": str(code.id), "auto_generated": True},
            context={"ip_address": None, "user_agent": None},
        )
        return code

    def _patient_card_code(self) -> str:
        return f"HMS-PATIENT-CARD-{token_hex(12).upper()}"

    def _card_read(self, patient: Patient, code: ScanCode, *, is_reprint: bool = False) -> PatientIdCardRead:
        return PatientIdCardRead(
            patient=PatientRead.model_validate(patient, from_attributes=True),
            hospital_name=get_settings().app_name,
            scan_code=code.code_value,
            code_type=code.code_type,
            issue_date=date.today(),
            is_reprint=is_reprint,
            template=self.get_id_card_template(type("Actor", (), {"branch_id": patient.branch_id})()),
        )
