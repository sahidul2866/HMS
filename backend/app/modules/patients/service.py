from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models.patient import Patient
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.patients.repository import PatientsRepository
from app.schemas.patient import (
    PatientClinicalHistoryRead,
    PatientCreate,
    PatientHistoryBillingInvoiceRead,
    PatientHistoryBillingPaymentRead,
    PatientHistoryIPDAdmissionRead,
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

    def create_patient(self, payload: PatientCreate, actor: User, context: dict[str, str | None]) -> Patient:
        normalized_phone = normalize_phone(payload.phone)
        branch_scope = payload.branch_id or actor.branch_id
        if normalized_phone:
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
            **payload.model_dump(exclude={"phone"}),
            phone=normalized_phone,
            patient_number=f"PAT-{sequence}",
            branch_id=branch_scope,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_patient(patient)
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
