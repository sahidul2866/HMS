from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.laboratory import LabOrder, LabOrderItem, LabResult, LabResultItem
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.laboratory.repository import LaboratoryRepository
from app.modules.opd.repository import OPDRepository
from app.schemas.encounter import ClinicalInvestigationResultUpdate, ClinicalInvestigationWorkItemRead
from app.schemas.laboratory import LaboratorySummaryRead
from app.utils.enums import AuditAction


class LaboratoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.legacy_repository = OPDRepository(db)
        self.repository = LaboratoryRepository(db)

    def list_worklist(self, actor: User) -> list[ClinicalInvestigationWorkItemRead]:
        new_orders = self.repository.list_orders(actor.branch_id)
        legacy_orders = self.legacy_repository.list_investigation_orders("laboratory", actor.branch_id)
        # Exclude legacy orders that are already linked to new orders
        linked_legacy_ids = {o.lab_order_id for o in legacy_orders if o.lab_order_id}
        legacy_orders = [o for o in legacy_orders if o.id not in linked_legacy_ids]
        new_items = [self._serialize_new(order) for order in new_orders]
        legacy_items = [self._serialize_legacy(order) for order in legacy_orders]
        # Sort by created_at desc using visit_date as proxy
        return sorted(new_items + legacy_items, key=lambda x: (x.visit_date, x.order_id), reverse=True)

    def get_summary(self, actor: User) -> LaboratorySummaryRead:
        new_counts = self.repository.get_summary_counts(actor.branch_id)
        legacy_items = self.legacy_repository.list_investigation_orders("laboratory", actor.branch_id)
        # Exclude linked legacy orders
        linked_legacy_ids = {o.lab_order_id for o in legacy_items if o.lab_order_id}
        legacy_items = [o for o in legacy_items if o.id not in linked_legacy_ids]
        return LaboratorySummaryRead(
            total_orders=new_counts["total_orders"] + len(legacy_items),
            pending_orders=new_counts["pending_orders"] + len([i for i in legacy_items if i.status == "pending"]),
            collected_orders=new_counts["collected_orders"] + len([i for i in legacy_items if i.status == "collected"]),
            in_progress_orders=new_counts["in_progress_orders"] + len([i for i in legacy_items if i.status == "in_progress"]),
            completed_orders=new_counts["completed_orders"] + len([i for i in legacy_items if i.status == "completed"]),
            verified_orders=new_counts["verified_orders"] + len([i for i in legacy_items if i.status == "verified"]),
        )

    def update_result(self, order_id, payload: ClinicalInvestigationResultUpdate, actor: User, context: dict[str, str | None]) -> ClinicalInvestigationWorkItemRead:
        # Try new table first
        lab_order = self.repository.get_order(order_id)
        if lab_order:
            if actor.branch_id and lab_order.branch_id and actor.branch_id != lab_order.branch_id:
                raise AppException(403, "forbidden", "Laboratory order belongs to a different branch")
            lab_order.status = payload.status
            if payload.status in {"collected", "in_progress", "completed", "verified"} and not lab_order.collected_at:
                lab_order.collected_at = datetime.now(UTC)
                lab_order.collected_by_user_id = actor.id
            if payload.status in {"completed", "verified"}:
                lab_order.completed_at = lab_order.completed_at or datetime.now(UTC)
                lab_order.completed_by_user_id = actor.id
            else:
                lab_order.completed_at = None
                lab_order.completed_by_user_id = None
            if payload.status == "verified":
                lab_order.verified_at = datetime.now(UTC)
                lab_order.verified_by_user_id = actor.id
            else:
                lab_order.verified_at = None
                lab_order.verified_by_user_id = None
            lab_order.updated_by = actor.id
            AuditService(self.db).log(
                user_id=actor.id,
                action=AuditAction.OPD_INVESTIGATION_RESULT_UPDATE,
                module="laboratory",
                entity_type="lab_order",
                entity_id=str(lab_order.id),
                detail={"service_area": "laboratory", "status": payload.status, "order_number": lab_order.order_number},
                context=context,
            )
            self.db.commit()
            self.db.refresh(lab_order)
            return self._serialize_new(lab_order)

        # Fallback to legacy
        order = self.legacy_repository.get_order(order_id)
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
        return self._serialize_legacy(order)

    def _serialize_new(self, order: LabOrder) -> ClinicalInvestigationWorkItemRead:
        visit = order.visit
        patient = order.patient
        item = order.items[0] if order.items else None
        result = order.results[0] if order.results else None
        return ClinicalInvestigationWorkItemRead(
            order_id=order.id,
            visit_id=visit.id if visit else order.visit_id,
            visit_number=visit.visit_number if visit else "",
            visit_date=visit.visit_date if visit else datetime.now(UTC).date(),
            patient_id=patient.id if patient else order.patient_id,
            patient_number=patient.patient_number if patient else "",
            patient_name=f"{patient.first_name} {patient.last_name}" if patient else "",
            consulting_doctor_name=visit.consulting_doctor_name if visit else "",
            service_area="laboratory",
            item_name=item.test_name if item else "Lab Order",
            room_number=None,
            quantity=item.quantity if item else 1,
            instructions=None,
            chief_complaint=visit.chief_complaint if visit else None,
            diagnosis=(visit.final_diagnosis or visit.provisional_diagnosis) if visit else None,
            status=order.status,
            sample_note=None,
            sample_collected_at=order.collected_at,
            result_text=result.overall_interpretation if result else None,
            completed_at=order.completed_at,
            verified_at=order.verified_at,
            lab_order_id=order.id,
            radiology_order_id=None,
        )

    def _serialize_legacy(self, order) -> ClinicalInvestigationWorkItemRead:
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
            lab_order_id=order.lab_order_id,
            radiology_order_id=order.radiology_order_id,
        )
