from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.encounter import OPDVisit, OPDVisitOrder
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.ipd.service import IPDService
from app.modules.opd.repository import OPDRepository
from app.modules.patients.repository import PatientsRepository
from app.modules.users.repository import UsersRepository
from app.schemas.encounter import (
    IPDAdmissionCreate,
    OPDConvertToIPD,
    OPDSummary,
    OPDVisitConsultationUpdate,
    OPDVisitCreate,
    OPDVisitOrderCreate,
    OPDVisitOrderUpdate,
)
from app.utils.enums import AuditAction


class OPDService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OPDRepository(db)
        self.patients = PatientsRepository(db)
        self.users = UsersRepository(db)

    def list_visits(self, actor: User) -> list[OPDVisit]:
        return self.repository.list_visits(actor.branch_id)

    def get_visit(self, visit_id, actor: User) -> OPDVisit:
        visit = self.repository.get_visit(visit_id)
        if not visit:
            raise AppException(404, "opd_visit_not_found", "OPD visit not found")
        if actor.branch_id and visit.branch_id and actor.branch_id != visit.branch_id:
            raise AppException(403, "forbidden", "OPD visit belongs to a different branch")
        return visit

    def get_summary(self, actor: User) -> OPDSummary:
        totals = self.repository.get_summary(actor.branch_id, datetime.now(UTC).date())
        return OPDSummary(
            total_visits=totals[0],
            waiting_visits=totals[1],
            in_consultation_visits=totals[2],
            completed_visits=totals[3],
        )

    def create_visit(self, payload: OPDVisitCreate, actor: User, context: dict[str, str | None]) -> OPDVisit:
        patient = self.patients.get_patient(payload.patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")

        visit_number = f"OPD-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        consulting_doctor = self._get_doctor(payload.doctor_user_id, actor) if payload.doctor_user_id else None
        visit = OPDVisit(
            **payload.model_dump(exclude={"doctor_user_id"}),
            visit_number=visit_number,
            branch_id=patient.branch_id or actor.branch_id,
            consulting_doctor_user_id=consulting_doctor.id if consulting_doctor else None,
            registered_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_visit(visit)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_CREATE,
            module="opd",
            entity_type="opd_visit",
            entity_id=str(visit.id),
            detail={"visit_number": visit.visit_number, "patient_id": str(visit.patient_id)},
            context=context,
        )
        self.db.commit()
        self.db.refresh(visit)
        return self.repository.get_visit(visit.id) or visit

    def update_status(self, visit_id, status: str, actor: User, context: dict[str, str | None]) -> OPDVisit:
        visit = self.repository.get_visit(visit_id)
        if not visit:
            raise AppException(404, "opd_visit_not_found", "OPD visit not found")
        if actor.branch_id and visit.branch_id and actor.branch_id != visit.branch_id:
            raise AppException(403, "forbidden", "OPD visit belongs to a different branch")
        visit.status = status
        visit.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_STATUS_UPDATE,
            module="opd",
            entity_type="opd_visit",
            entity_id=str(visit.id),
            detail={"visit_number": visit.visit_number, "status": status},
            context=context,
        )
        self.db.commit()
        self.db.refresh(visit)
        return visit

    def update_consultation(self, visit_id, payload: OPDVisitConsultationUpdate, actor: User, context: dict[str, str | None]) -> OPDVisit:
        visit = self.get_visit(visit_id, actor)
        for field, value in payload.model_dump().items():
            setattr(visit, field, value)
        visit.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_STATUS_UPDATE,
            module="opd",
            entity_type="opd_visit",
            entity_id=str(visit.id),
            detail={"visit_number": visit.visit_number, "consultation_updated": True},
            context=context,
        )
        self.db.commit()
        self.db.refresh(visit)
        return visit

    def create_order(self, visit_id, payload: OPDVisitOrderCreate, actor: User, context: dict[str, str | None]) -> OPDVisit:
        visit = self.repository.get_visit(visit_id)
        if not visit:
            raise AppException(404, "opd_visit_not_found", "OPD visit not found")
        if actor.branch_id and visit.branch_id and actor.branch_id != visit.branch_id:
            raise AppException(403, "forbidden", "OPD visit belongs to a different branch")

        order = OPDVisitOrder(
            visit_id=visit.id,
            **payload.model_dump(),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_order(order)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_ORDER_CREATE,
            module="opd",
            entity_type="opd_visit_order",
            entity_id=str(order.id),
            detail={"visit_number": visit.visit_number, "order_type": order.order_type, "item_name": order.item_name},
            context=context,
        )
        self.db.commit()
        return self.repository.get_visit(visit.id) or visit

    def update_order(self, visit_id, order_id, payload: OPDVisitOrderUpdate, actor: User, context: dict[str, str | None]) -> OPDVisit:
        visit = self.repository.get_visit(visit_id)
        if not visit:
            raise AppException(404, "opd_visit_not_found", "OPD visit not found")
        if actor.branch_id and visit.branch_id and actor.branch_id != visit.branch_id:
            raise AppException(403, "forbidden", "OPD visit belongs to a different branch")

        order = self.repository.get_order(order_id)
        if not order or order.visit_id != visit.id:
            raise AppException(404, "opd_order_not_found", "OPD order not found")
        if order.order_type != "procedure":
            raise AppException(400, "invalid_opd_order_type", "Only procedure orders can be updated from the OPD desk")

        order.status = payload.status
        order.result_text = payload.result_text
        if payload.status == "completed":
            order.completed_at = datetime.now(UTC)
            order.completed_by_user_id = actor.id
        else:
            order.completed_at = None
            order.completed_by_user_id = None
        order.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_ORDER_UPDATE,
            module="opd",
            entity_type="opd_visit_order",
            entity_id=str(order.id),
            detail={"visit_number": visit.visit_number, "order_type": order.order_type, "status": payload.status},
            context=context,
        )
        self.db.commit()
        return self.repository.get_visit(visit.id) or visit

    def convert_to_ipd(self, visit_id, payload: OPDConvertToIPD, actor: User, context: dict[str, str | None]):
        visit = self.repository.get_visit(visit_id)
        if not visit:
            raise AppException(404, "opd_visit_not_found", "OPD visit not found")
        if visit.converted_ipd_admission_id:
            raise AppException(409, "opd_already_converted", "OPD visit already converted to IPD")
        if actor.branch_id and visit.branch_id and actor.branch_id != visit.branch_id:
            raise AppException(403, "forbidden", "OPD visit belongs to a different branch")

        ipd_payload = IPDAdmissionCreate(
            patient_id=visit.patient_id,
            bed_id=payload.bed_id,
            admitted_at=payload.admitted_at,
            admission_type=payload.admission_type,
            ward_name=payload.ward_name,
            bed_number=payload.bed_number,
            doctor_user_id=payload.doctor_user_id,
            attending_doctor_name=payload.attending_doctor_name or visit.consulting_doctor_name,
            diagnosis=payload.diagnosis or visit.chief_complaint,
            daily_charge=payload.daily_charge,
            advance_amount=payload.advance_amount,
            expected_discharge_date=payload.expected_discharge_date,
        )
        admission = IPDService(self.db).create_admission(ipd_payload, actor, context)
        visit.converted_ipd_admission_id = admission.id
        visit.status = "completed"
        visit.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.IPD_ADMISSION_CREATE,
            module="opd",
            entity_type="opd_visit",
            entity_id=str(visit.id),
            detail={"visit_number": visit.visit_number, "admission_number": admission.admission_number},
            context=context,
        )
        self.db.commit()
        return admission

    def _get_doctor(self, user_id, actor: User) -> User:
        doctor = self.users.get_user(user_id)
        if not doctor or not doctor.is_active:
            raise AppException(404, "doctor_not_found", "Doctor user not found")
        if actor.branch_id and doctor.branch_id and actor.branch_id != doctor.branch_id:
            raise AppException(403, "forbidden", "Doctor belongs to a different branch")
        if not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(400, "invalid_doctor_user", "Selected user is not configured as a doctor")
        return doctor
