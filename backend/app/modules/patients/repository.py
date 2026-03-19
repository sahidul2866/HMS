from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.patient import Patient


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

    def create_patient(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.flush()
        return patient

