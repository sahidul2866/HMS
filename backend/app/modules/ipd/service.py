from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.encounter import IPDAdmission, IPDBed
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.ipd.repository import IPDRepository
from app.modules.patients.repository import PatientsRepository
from app.modules.users.repository import UsersRepository
from app.schemas.encounter import IPDAdmissionCreate, IPDBedCreate, IPDSummary
from app.utils.enums import AuditAction


class IPDService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = IPDRepository(db)
        self.patients = PatientsRepository(db)
        self.users = UsersRepository(db)

    def list_admissions(self, actor: User) -> list[IPDAdmission]:
        return self.repository.list_admissions(actor.branch_id)

    def list_beds(self, actor: User) -> list[IPDBed]:
        return self.repository.list_beds(actor.branch_id)

    def get_summary(self, actor: User) -> IPDSummary:
        totals = self.repository.get_summary(actor.branch_id)
        return IPDSummary(
            total_admissions=totals[0],
            active_admissions=totals[1],
            discharged_admissions=totals[2],
            occupied_beds=totals[3],
        )

    def create_admission(self, payload: IPDAdmissionCreate, actor: User, context: dict[str, str | None]) -> IPDAdmission:
        patient = self.patients.get_patient(payload.patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")

        bed = None
        if payload.bed_id:
            bed = self.repository.get_bed(payload.bed_id)
            if not bed:
                raise AppException(404, "ipd_bed_not_found", "IPD bed not found")
            if actor.branch_id and bed.branch_id and actor.branch_id != bed.branch_id:
                raise AppException(403, "forbidden", "IPD bed belongs to a different branch")
            if bed.status != "available":
                raise AppException(409, "ipd_bed_unavailable", "Selected bed is not available")

        admission_data = payload.model_dump()
        attending_doctor = self._get_doctor(payload.doctor_user_id, actor) if payload.doctor_user_id else None
        admission_data["ward_name"] = bed.ward_name if bed else payload.ward_name
        admission_data["bed_number"] = bed.bed_number if bed else payload.bed_number
        admission_data["daily_charge"] = bed.daily_rate if bed and payload.daily_charge == 0 else payload.daily_charge
        admission_data.pop("doctor_user_id", None)

        admission = IPDAdmission(
            **admission_data,
            admission_number=f"IPD-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            branch_id=patient.branch_id or actor.branch_id,
            attending_doctor_user_id=attending_doctor.id if attending_doctor else None,
            admitted_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        if bed:
            bed.status = "occupied"
            bed.updated_by = actor.id
        self.repository.create_admission(admission)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.IPD_ADMISSION_CREATE,
            module="ipd",
            entity_type="ipd_admission",
            entity_id=str(admission.id),
            detail={"admission_number": admission.admission_number, "patient_id": str(admission.patient_id)},
            context=context,
        )
        self.db.commit()
        self.db.refresh(admission)
        return self.repository.get_admission(admission.id) or admission

    def discharge(self, admission_id, discharge_note: str | None, actor: User, context: dict[str, str | None]) -> IPDAdmission:
        admission = self.repository.get_admission(admission_id)
        if not admission:
            raise AppException(404, "ipd_admission_not_found", "IPD admission not found")
        if admission.status == "discharged":
            raise AppException(409, "ipd_already_discharged", "Patient already discharged")
        if actor.branch_id and admission.branch_id and actor.branch_id != admission.branch_id:
            raise AppException(403, "forbidden", "IPD admission belongs to a different branch")

        admission.status = "discharged"
        admission.discharge_note = discharge_note
        admission.discharged_at = datetime.now(UTC)
        admission.discharged_by_user_id = actor.id
        admission.updated_by = actor.id
        if admission.bed:
            admission.bed.status = "available"
            admission.bed.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.IPD_ADMISSION_DISCHARGE,
            module="ipd",
            entity_type="ipd_admission",
            entity_id=str(admission.id),
            detail={"admission_number": admission.admission_number},
            context=context,
        )
        self.db.commit()
        self.db.refresh(admission)
        return admission

    def create_bed(self, payload: IPDBedCreate, actor: User, context: dict[str, str | None]) -> IPDBed:
        existing = self.repository.get_bed_by_number(actor.branch_id, payload.ward_name, payload.bed_number)
        if existing:
            raise AppException(409, "ipd_bed_exists", "Ward and bed number already exist")

        bed = IPDBed(
            **payload.model_dump(),
            branch_id=actor.branch_id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_bed(bed)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.IPD_BED_CREATE,
            module="ipd",
            entity_type="ipd_bed",
            entity_id=str(bed.id),
            detail={"ward_name": bed.ward_name, "bed_number": bed.bed_number},
            context=context,
        )
        self.db.commit()
        self.db.refresh(bed)
        return bed

    def _get_doctor(self, user_id, actor: User) -> User:
        doctor = self.users.get_user(user_id)
        if not doctor or not doctor.is_active:
            raise AppException(404, "doctor_not_found", "Doctor user not found")
        if actor.branch_id and doctor.branch_id and actor.branch_id != doctor.branch_id:
            raise AppException(403, "forbidden", "Doctor belongs to a different branch")
        if not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(400, "invalid_doctor_user", "Selected user is not configured as a doctor")
        return doctor
