from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.encounter import ERVisit, ERAmbulanceRecord
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.er.repository import ERRepository
from app.modules.ipd.service import IPDService
from app.modules.patients.repository import PatientsRepository
from app.modules.users.repository import UsersRepository
from app.schemas.encounter import (
    ERVisitAmbulanceCreate,
    ERVisitAssignmentUpdate,
    ERVisitConvertToIPD,
    ERVisitCreate,
    ERVisitStatusUpdate,
    ERVisitTriageUpdate,
    ERVisitTreatmentUpdate,
)
from app.utils.enums import AuditAction


class ERService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ERRepository(db)
        self.patients = PatientsRepository(db)
        self.users = UsersRepository(db)

    def list_visits(self, actor: User) -> list[ERVisit]:
        return self.repository.list_visits(actor.branch_id)

    def get_visit(self, visit_id, actor: User) -> ERVisit:
        visit = self.repository.get_visit(visit_id)
        if not visit:
            raise AppException(404, "er_visit_not_found", "ER visit not found")
        if actor.branch_id and visit.branch_id and actor.branch_id != visit.branch_id:
            raise AppException(403, "forbidden", "ER visit belongs to a different branch")
        return visit

    def get_summary(self, actor: User):
        totals = self.repository.get_summary(actor.branch_id)
        return {
            "total_visits": totals[0],
            "waiting_visits": totals[1],
            "triaged_visits": totals[2],
            "assigned_visits": totals[3],
            "in_treatment_visits": totals[4],
            "admitted_visits": totals[5],
            "discharged_visits": totals[6],
            "referred_visits": totals[7],
        }

    def create_visit(self, payload: ERVisitCreate, actor: User, context: dict[str, str | None]) -> ERVisit:
        patient = self.patients.get_patient(payload.patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")

        assigned_doctor = self._get_doctor(payload.preferred_doctor_user_id, actor) if payload.preferred_doctor_user_id else None
        assigned_nurse = self._get_user(payload.assigned_nurse_user_id, actor) if payload.assigned_nurse_user_id else None

        visit = ERVisit(
            **payload.model_dump(exclude={"preferred_doctor_user_id", "assigned_nurse_user_id"}),
            visit_number=f"ER-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            branch_id=patient.branch_id or actor.branch_id,
            assigned_doctor_user_id=assigned_doctor.id if assigned_doctor else None,
            assigned_nurse_user_id=assigned_nurse.id if assigned_nurse else None,
            status="waiting",
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_visit(visit)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.ER_VISIT_CREATE,
            module="er",
            entity_type="er_visit",
            entity_id=str(visit.id),
            detail={"visit_number": visit.visit_number, "arrival_mode": visit.arrival_mode},
            context=context,
        )
        self.db.commit()
        self.db.refresh(visit)
        return self.repository.get_visit(visit.id) or visit

    def update_triage(self, visit_id, payload: ERVisitTriageUpdate, actor: User, context: dict[str, str | None]) -> ERVisit:
        visit = self.get_visit(visit_id, actor)
        visit.triage_category = payload.triage_category
        visit.triage_level = payload.triage_level
        visit.vitals = payload.vitals
        visit.status = "triaged"
        visit.updated_by = actor.id
        self._audit_visit(actor, visit, AuditAction.ER_VISIT_TRIAGE_UPDATE, {"triage_category": payload.triage_category, "triage_level": payload.triage_level}, context)
        self.db.commit()
        self.db.refresh(visit)
        return visit

    def assign_team(self, visit_id, payload: ERVisitAssignmentUpdate, actor: User, context: dict[str, str | None]) -> ERVisit:
        visit = self.get_visit(visit_id, actor)
        if payload.assigned_doctor_user_id:
            doctor = self._get_doctor(payload.assigned_doctor_user_id, actor)
            visit.assigned_doctor_user_id = doctor.id
        if payload.assigned_nurse_user_id:
            nurse = self._get_user(payload.assigned_nurse_user_id, actor)
            visit.assigned_nurse_user_id = nurse.id
        visit.assigned_location = payload.assigned_location
        visit.status = "assigned"
        visit.updated_by = actor.id
        self._audit_visit(actor, visit, AuditAction.ER_VISIT_ASSIGNMENT_UPDATE, {"assigned_location": payload.assigned_location}, context)
        self.db.commit()
        self.db.refresh(visit)
        return visit

    def update_treatment(self, visit_id, payload: ERVisitTreatmentUpdate, actor: User, context: dict[str, str | None]) -> ERVisit:
        visit = self.get_visit(visit_id, actor)
        visit.treatment_status = payload.treatment_status
        visit.treatment_notes = payload.treatment_notes
        visit.disposition = payload.disposition
        visit.referral_hospital = payload.referral_hospital
        visit.referral_doctor_name = payload.referral_doctor_name
        visit.disposition_note = payload.disposition_note
        if payload.treatment_status == "completed" and visit.status not in {"admitted", "discharged", "referred"}:
            visit.status = "in_treatment"
        visit.updated_by = actor.id
        self._audit_visit(actor, visit, AuditAction.ER_VISIT_TREATMENT_UPDATE, {"treatment_status": payload.treatment_status}, context)
        self.db.commit()
        self.db.refresh(visit)
        return visit

    def update_status(self, visit_id, payload: ERVisitStatusUpdate, actor: User, context: dict[str, str | None]) -> ERVisit:
        visit = self.get_visit(visit_id, actor)
        visit.status = payload.status
        if payload.status == "discharged":
            visit.discharged_at = datetime.now(UTC)
        visit.updated_by = actor.id
        self._audit_visit(actor, visit, AuditAction.ER_VISIT_STATUS_UPDATE, {"status": payload.status, "note": payload.note}, context)
        self.db.commit()
        self.db.refresh(visit)
        return visit

    def create_ambulance_record(self, visit_id, payload: ERVisitAmbulanceCreate, actor: User, context: dict[str, str | None]) -> ERAmbulanceRecord:
        visit = self.get_visit(visit_id, actor)
        ambulance = ERAmbulanceRecord(
            er_visit_id=visit.id,
            **payload.model_dump(),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_ambulance_record(ambulance)
        self._audit_visit(actor, visit, AuditAction.ER_VISIT_AMBULANCE_CREATE, {"ambulance_service": ambulance.ambulance_service}, context)
        self.db.commit()
        self.db.refresh(visit)
        return ambulance

    def convert_to_ipd(self, visit_id, payload: ERVisitConvertToIPD, actor: User, context: dict[str, str | None]) -> ERVisit:
        visit = self.get_visit(visit_id, actor)
        admission = IPDService(self.db).create_admission(
            payload,
            actor,
            context,
        )
        visit.admitted_to_ipd_admission_id = admission.id
        visit.status = "admitted"
        visit.updated_by = actor.id
        self._audit_visit(actor, visit, AuditAction.ER_VISIT_IPD_TRANSFER, {"admission_number": admission.admission_number}, context)
        self.db.commit()
        self.db.refresh(visit)
        return visit

    def _get_doctor(self, user_id, actor: User) -> User:
        doctor = self.users.get_user(user_id)
        if not doctor or not doctor.is_active:
            raise AppException(404, "doctor_not_found", "Doctor user not found")
        if actor.branch_id and doctor.branch_id and actor.branch_id != doctor.branch_id:
            raise AppException(403, "forbidden", "Doctor belongs to a different branch")
        if not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(400, "invalid_doctor_user", "Selected user is not configured as a doctor")
        return doctor

    def _get_user(self, user_id, actor: User) -> User:
        user = self.users.get_user(user_id)
        if not user or not user.is_active:
            raise AppException(404, "user_not_found", "User not found")
        if actor.branch_id and user.branch_id and actor.branch_id != user.branch_id:
            raise AppException(403, "forbidden", "User belongs to a different branch")
        return user

    def _audit_visit(self, actor: User, visit: ERVisit, action: str, detail: dict[str, str | None], context: dict[str, str | None]) -> None:
        AuditService(self.db).log(
            user_id=actor.id,
            action=action,
            module="er",
            entity_type="er_visit",
            entity_id=str(visit.id),
            detail=detail,
            context=context,
        )
