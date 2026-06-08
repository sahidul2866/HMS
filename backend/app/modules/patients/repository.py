from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.billing import BillingInvoice
from app.models.encounter import Appointment, IPDAdmission, OPDVisit
from app.models.patient import Patient
from app.models.pharmacy import PharmacyDispense
from app.utils.phone import normalize_phone_expr


class PatientsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_patients(self, branch_id=None) -> list[Patient]:
        stmt = select(Patient).order_by(Patient.created_at.desc())
        if branch_id:
            stmt = stmt.where(Patient.branch_id == branch_id)
        return list(self.db.scalars(stmt))

    def search_patients(self, query: str, branch_id=None, *, limit: int = 10) -> list[Patient]:
        normalized = query.strip()
        if not normalized:
            return []

        pattern = f"%{normalized.lower()}%"
        normalized_phone = "".join(char for char in normalized if char.isdigit())
        full_name = func.lower(
            func.concat(
                Patient.first_name,
                cast(" ", String),
                Patient.last_name,
            )
        )
        stmt = (
            select(Patient)
            .where(
                or_(
                    cast(Patient.id, String).ilike(pattern),
                    func.lower(Patient.patient_number).like(pattern),
                    func.lower(Patient.first_name).like(pattern),
                    func.lower(Patient.last_name).like(pattern),
                    full_name.like(pattern),
                    func.lower(func.coalesce(Patient.phone, "")).like(pattern),
                    func.lower(func.coalesce(Patient.email, "")).like(pattern),
                    normalize_phone_expr(Patient.phone).like(f"%{normalized_phone}%") if normalized_phone else False,
                )
            )
            .order_by(Patient.updated_at.desc(), Patient.created_at.desc())
            .limit(limit)
        )
        if branch_id:
            stmt = stmt.where(Patient.branch_id == branch_id)
        return list(self.db.scalars(stmt))

    def get_patient(self, patient_id) -> Patient | None:
        return self.db.get(Patient, patient_id)

    def list_patients_by_phone(self, phone: str, branch_id=None, *, limit: int = 25) -> list[Patient]:
        normalized = phone.strip()
        if not normalized:
          return []

        stmt = (
            select(Patient)
            .where(normalize_phone_expr(Patient.phone) == normalized)
            .order_by(Patient.updated_at.desc(), Patient.created_at.desc())
            .limit(limit)
        )
        if branch_id:
            stmt = stmt.where(Patient.branch_id == branch_id)
        return list(self.db.scalars(stmt))

    def count_patients_by_phone(self, phone: str, branch_id=None) -> int:
        normalized = phone.strip()
        if not normalized:
            return 0

        stmt = select(func.count(Patient.id)).where(normalize_phone_expr(Patient.phone) == normalized)
        if branch_id:
            stmt = stmt.where(Patient.branch_id == branch_id)
        return int(self.db.scalar(stmt) or 0)

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
        stmt = (
            select(IPDAdmission)
            .options(joinedload(IPDAdmission.staff_assignments), joinedload(IPDAdmission.timeline_events))
            .where(IPDAdmission.patient_id == patient_id)
            .order_by(IPDAdmission.admitted_at.desc())
        )
        return list(self.db.scalars(stmt).unique())

    def list_billing_invoices(self, patient_id) -> list[BillingInvoice]:
        stmt = (
            select(BillingInvoice)
            .options(joinedload(BillingInvoice.payments))
            .where(BillingInvoice.patient_id == patient_id)
            .order_by(BillingInvoice.created_at.desc())
        )
        return list(self.db.scalars(stmt).unique())

    def list_appointments(self, patient_id) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .options(joinedload(Appointment.doctor))
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.appointment_at.desc())
        )
        return list(self.db.scalars(stmt).unique())

    def list_pharmacy_dispenses(self, patient_id) -> list[PharmacyDispense]:
        stmt = select(PharmacyDispense).where(PharmacyDispense.patient_id == patient_id).order_by(PharmacyDispense.created_at.desc())
        return list(self.db.scalars(stmt))

    def create_patient(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.flush()
        return patient
