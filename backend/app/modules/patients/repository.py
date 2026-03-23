from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.billing import BillingInvoice
from app.models.encounter import IPDAdmission, OPDVisit
from app.models.patient import Patient
from app.models.pharmacy import PharmacyDispense


class PatientsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_patients(self, branch_id=None) -> list[Patient]:
        stmt = select(Patient).order_by(Patient.created_at.desc())
        if branch_id:
            stmt = stmt.where(Patient.branch_id == branch_id)
        return list(self.db.scalars(stmt))

    def get_patient(self, patient_id) -> Patient | None:
        return self.db.get(Patient, patient_id)

    def get_patient_with_history(self, patient_id) -> Patient | None:
        stmt = select(Patient).where(Patient.id == patient_id)
        return self.db.scalar(stmt)

    def list_opd_visits(self, patient_id) -> list[OPDVisit]:
        stmt = (
            select(OPDVisit)
            .options(joinedload(OPDVisit.orders))
            .where(OPDVisit.patient_id == patient_id)
            .order_by(OPDVisit.visit_date.desc(), OPDVisit.created_at.desc())
        )
        return list(self.db.scalars(stmt).unique())

    def list_ipd_admissions(self, patient_id) -> list[IPDAdmission]:
        stmt = select(IPDAdmission).where(IPDAdmission.patient_id == patient_id).order_by(IPDAdmission.admitted_at.desc())
        return list(self.db.scalars(stmt))

    def list_billing_invoices(self, patient_id) -> list[BillingInvoice]:
        stmt = select(BillingInvoice).where(BillingInvoice.patient_id == patient_id).order_by(BillingInvoice.created_at.desc())
        return list(self.db.scalars(stmt))

    def list_pharmacy_dispenses(self, patient_id) -> list[PharmacyDispense]:
        stmt = select(PharmacyDispense).where(PharmacyDispense.patient_id == patient_id).order_by(PharmacyDispense.created_at.desc())
        return list(self.db.scalars(stmt))

    def create_patient(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.flush()
        return patient
