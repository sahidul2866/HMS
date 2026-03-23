from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.patient import Patient
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.patients.repository import PatientsRepository
from app.schemas.patient import (
    PatientClinicalHistoryRead,
    PatientCreate,
    PatientHistoryBillingInvoiceRead,
    PatientHistoryIPDAdmissionRead,
    PatientHistoryOPDVisitRead,
    PatientHistoryOrderRead,
    PatientHistoryPharmacyDispenseRead,
    PatientRead,
)
from app.utils.enums import AuditAction


class PatientsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PatientsRepository(db)

    def list_patients(self, actor: User) -> list[Patient]:
        branch_scope = actor.branch_id
        return self.repository.list_patients(branch_scope)

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
                    total_amount=str(invoice.total_amount),
                    referred_doctor_name=invoice.referred_doctor_name,
                )
                for invoice in billing_invoices
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
        sequence = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        patient = Patient(
            **payload.model_dump(),
            patient_number=f"PAT-{sequence}",
            branch_id=payload.branch_id or actor.branch_id,
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
