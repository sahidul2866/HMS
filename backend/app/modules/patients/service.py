from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.patient import Patient
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.patients.repository import PatientsRepository
from app.schemas.patient import PatientCreate
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
