from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.pharmacy import PharmacyDispense
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.opd.repository import OPDRepository
from app.modules.pharmacy.repository import PharmacyRepository
from app.schemas.pharmacy import PharmacyDispenseCreate, PharmacyPendingPrescriptionRead
from app.utils.enums import AuditAction


class PharmacyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PharmacyRepository(db)
        self.opd_repository = OPDRepository(db)

    def list_dispenses(self, actor: User) -> list[PharmacyDispense]:
        return self.repository.list_dispenses(actor.branch_id)

    def list_pending_prescriptions(self, actor: User) -> list[PharmacyPendingPrescriptionRead]:
        orders = self.opd_repository.list_pending_prescription_orders(actor.branch_id)
        return [
            PharmacyPendingPrescriptionRead(
                order_id=order.id,
                visit_id=order.visit_id,
                visit_number=order.visit.visit_number,
                patient_id=order.visit.patient_id,
                patient_name=f"{order.visit.patient.first_name} {order.visit.patient.last_name}",
                doctor_name=order.visit.consulting_doctor_name,
                item_name=order.item_name,
                quantity=order.quantity,
                instructions=order.instructions,
            )
            for order in orders
        ]

    def dispense(self, payload: PharmacyDispenseCreate, actor: User, context: dict[str, str | None]) -> PharmacyDispense:
        source_order = None
        if payload.source_visit_order_id:
            source_order = self.opd_repository.get_order(payload.source_visit_order_id)
            if not source_order:
                raise AppException(404, "opd_order_not_found", "OPD prescription order not found")
            if source_order.order_type != "prescription":
                raise AppException(400, "invalid_opd_order_type", "Only prescription orders can be dispensed")
            if source_order.status == "completed":
                raise AppException(409, "opd_order_already_dispensed", "Prescription order already dispensed")
            if actor.branch_id and source_order.visit.branch_id and actor.branch_id != source_order.visit.branch_id:
                raise AppException(403, "forbidden", "Prescription order belongs to a different branch")

        patient_id = payload.patient_id or (source_order.visit.patient_id if source_order else None)
        prescription_ref = payload.prescription_ref or (source_order.visit.visit_number if source_order else None)
        medicine_name = payload.medicine_name or (source_order.item_name if source_order else None)
        quantity = payload.quantity or (source_order.quantity if source_order else None)
        if not medicine_name or quantity is None:
            raise AppException(400, "invalid_dispense_payload", "Medicine name and quantity are required")
        total_price = quantity * payload.unit_price
        dispense = PharmacyDispense(
            **payload.model_dump(),
            patient_id=patient_id,
            prescription_ref=prescription_ref,
            medicine_name=medicine_name,
            quantity=quantity,
            source_visit_id=source_order.visit_id if source_order else payload.source_visit_id,
            source_visit_order_id=source_order.id if source_order else payload.source_visit_order_id,
            total_price=total_price,
            branch_id=payload.branch_id or actor.branch_id,
            dispensed_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_dispense(dispense)
        if source_order:
            source_order.status = "completed"
            source_order.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.PHARMACY_DISPENSE,
            module="pharmacy",
            entity_type="pharmacy_dispense",
            entity_id=str(dispense.id),
            detail={"medicine_name": dispense.medicine_name, "total_price": str(dispense.total_price)},
            context=context,
        )
        self.db.commit()
        self.db.refresh(dispense)
        return dispense
