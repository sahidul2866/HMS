from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.opd.repository import OPDRepository
from app.schemas.encounter import ClinicalInvestigationResultUpdate, ClinicalInvestigationWorkItemRead
from app.schemas.laboratory import LaboratorySummaryRead
from app.utils.enums import AuditAction


class LaboratoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OPDRepository(db)

    def list_worklist(self, actor: User) -> list[ClinicalInvestigationWorkItemRead]:
        orders = self.repository.list_investigation_orders("laboratory", actor.branch_id)
        return [self._serialize(order) for order in orders]

    def get_summary(self, actor: User) -> LaboratorySummaryRead:
        items = self.list_worklist(actor)
        return LaboratorySummaryRead(
            total_orders=len(items),
            pending_orders=len([item for item in items if item.status == "pending"]),
            collected_orders=len([item for item in items if item.status == "collected"]),
            in_progress_orders=len([item for item in items if item.status == "in_progress"]),
            completed_orders=len([item for item in items if item.status == "completed"]),
            verified_orders=len([item for item in items if item.status == "verified"]),
        )

    def update_result(self, order_id, payload: ClinicalInvestigationResultUpdate, actor: User, context: dict[str, str | None]) -> ClinicalInvestigationWorkItemRead:
        order = self.repository.get_order(order_id)
        if not order or order.order_type != "investigation" or order.service_area != "laboratory":
            raise AppException(404, "laboratory_order_not_found", "Laboratory work item not found")
        if actor.branch_id and order.visit.branch_id and actor.branch_id != order.visit.branch_id:
            raise AppException(403, "forbidden", "Laboratory order belongs to a different branch")

        order.status = payload.status
        order.sample_note = payload.sample_note
        order.result_text = payload.result_text
        if payload.status in {"collected", "in_progress", "completed", "verified"} and not order.sample_collected_at:
            order.sample_collected_at = datetime.now(UTC)
            order.sample_collected_by_user_id = actor.id
        if payload.status in {"completed", "verified"}:
            order.completed_at = order.completed_at or datetime.now(UTC)
            order.completed_by_user_id = actor.id
        else:
            order.completed_at = None
            order.completed_by_user_id = None
        if payload.status == "verified":
            order.verified_at = datetime.now(UTC)
            order.verified_by_user_id = actor.id
        else:
            order.verified_at = None
            order.verified_by_user_id = None
        order.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_INVESTIGATION_RESULT_UPDATE,
            module="laboratory",
            entity_type="opd_visit_order",
            entity_id=str(order.id),
            detail={"service_area": "laboratory", "status": payload.status, "visit_number": order.visit.visit_number},
            context=context,
        )
        self.db.commit()
        self.db.refresh(order)
        return self._serialize(order)

    def _serialize(self, order) -> ClinicalInvestigationWorkItemRead:
        return ClinicalInvestigationWorkItemRead(
            order_id=order.id,
            visit_id=order.visit_id,
            visit_number=order.visit.visit_number,
            visit_date=order.visit.visit_date,
            patient_id=order.visit.patient_id,
            patient_number=order.visit.patient.patient_number,
            patient_name=f"{order.visit.patient.first_name} {order.visit.patient.last_name}",
            consulting_doctor_name=order.visit.consulting_doctor_name,
            service_area=order.service_area or "laboratory",
            item_name=order.item_name,
            room_number=order.room_number,
            quantity=order.quantity,
            instructions=order.instructions,
            chief_complaint=order.visit.chief_complaint,
            diagnosis=order.visit.final_diagnosis or order.visit.provisional_diagnosis,
            status=order.status,
            sample_note=order.sample_note,
            sample_collected_at=order.sample_collected_at,
            result_text=order.result_text,
            completed_at=order.completed_at,
            verified_at=order.verified_at,
        )
