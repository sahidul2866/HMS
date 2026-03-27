from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.pharmacy import PharmacyDispense
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.opd.repository import OPDRepository
from app.modules.pharmacy.repository import PharmacyRepository
from app.schemas.pharmacy import PharmacyDispenseCreate, PharmacyDispenseReturnCreate, PharmacyPendingPrescriptionRead, PharmacySummaryRead
from app.utils.enums import AuditAction


class PharmacyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PharmacyRepository(db)
        self.opd_repository = OPDRepository(db)

    def list_dispenses(self, actor: User) -> list[PharmacyDispense]:
        return self.repository.list_dispenses(actor.branch_id)

    def get_summary(self, actor: User) -> PharmacySummaryRead:
        totals = self.repository.get_summary(actor.branch_id)
        return PharmacySummaryRead(
            total_dispenses=totals[0],
            today_dispenses=totals[1],
            pending_prescriptions=totals[2],
            billed_prescriptions=totals[3],
            partial_dispenses=totals[4],
            returned_dispenses=totals[5],
        )

    def list_pending_prescriptions(self, actor: User) -> list[PharmacyPendingPrescriptionRead]:
        orders = self.opd_repository.list_pending_prescription_orders(actor.branch_id)
        return [
            PharmacyPendingPrescriptionRead(
                order_id=order.id,
                visit_id=order.visit_id,
                visit_number=order.visit.visit_number,
                patient_id=order.visit.patient_id,
                patient_number=order.visit.patient.patient_number,
                patient_name=f"{order.visit.patient.first_name} {order.visit.patient.last_name}",
                doctor_name=order.visit.consulting_doctor_name,
                visit_date=order.visit.visit_date.isoformat(),
                visit_status=order.visit.status,
                item_name=order.item_name,
                quantity=order.quantity,
                dispensed_quantity=Decimal(str(self.repository.get_net_dispensed_quantity(order.id))),
                remaining_quantity=max(Decimal("0"), order.quantity - Decimal(str(self.repository.get_net_dispensed_quantity(order.id)))),
                instructions=order.instructions,
                chief_complaint=order.visit.chief_complaint,
                diagnosis=order.visit.final_diagnosis or order.visit.provisional_diagnosis,
            )
            for order in orders
            if order.quantity - Decimal(str(self.repository.get_net_dispensed_quantity(order.id))) > 0
        ]

    def dispense(self, payload: PharmacyDispenseCreate, actor: User, context: dict[str, str | None]) -> PharmacyDispense:
        source_order = None
        if payload.source_visit_order_id:
            source_order = self.opd_repository.get_order(payload.source_visit_order_id)
            if not source_order:
                raise AppException(404, "opd_order_not_found", "OPD prescription order not found")
            if source_order.order_type != "prescription":
                raise AppException(400, "invalid_opd_order_type", "Only prescription orders can be dispensed")
            if actor.branch_id and source_order.visit.branch_id and actor.branch_id != source_order.visit.branch_id:
                raise AppException(403, "forbidden", "Prescription order belongs to a different branch")

        patient_id = payload.patient_id or (source_order.visit.patient_id if source_order else None)
        prescription_ref = payload.prescription_ref or (source_order.visit.visit_number if source_order else None)
        medicine_name = payload.medicine_name or (source_order.item_name if source_order else None)
        quantity = payload.quantity or (source_order.quantity if source_order else None)
        if not medicine_name or quantity is None:
            raise AppException(400, "invalid_dispense_payload", "Medicine name and quantity are required")
        requested_quantity = source_order.quantity if source_order else payload.quantity
        if source_order:
            already_dispensed = Decimal(str(self.repository.get_net_dispensed_quantity(source_order.id)))
            remaining_quantity = source_order.quantity - already_dispensed
            if remaining_quantity <= 0:
                raise AppException(409, "opd_order_already_dispensed", "Prescription order has no remaining quantity to dispense")
            if quantity > remaining_quantity:
                raise AppException(409, "pharmacy_dispense_exceeds_remaining", "Dispense quantity exceeds remaining prescription quantity")
        else:
            remaining_quantity = quantity
        total_price = quantity * payload.unit_price
        order_remaining_after = remaining_quantity - quantity if source_order else Decimal("0")
        dispense_status = "partial" if source_order and order_remaining_after > 0 else "dispensed"
        dispense = PharmacyDispense(
            **payload.model_dump(),
            patient_id=patient_id,
            prescription_ref=prescription_ref,
            medicine_name=medicine_name,
            requested_quantity=requested_quantity,
            quantity=quantity,
            returned_quantity=Decimal("0"),
            source_visit_id=source_order.visit_id if source_order else payload.source_visit_id,
            source_visit_order_id=source_order.id if source_order else payload.source_visit_order_id,
            total_price=total_price,
            status=dispense_status,
            branch_id=payload.branch_id or actor.branch_id,
            dispensed_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_dispense(dispense)
        if source_order:
            source_order.status = "completed" if order_remaining_after <= 0 else "in_progress"
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

    def return_dispense(self, dispense_id, payload: PharmacyDispenseReturnCreate, actor: User, context: dict[str, str | None]) -> PharmacyDispense:
        dispense = self.repository.get_dispense(dispense_id)
        if not dispense:
            raise AppException(404, "pharmacy_dispense_not_found", "Pharmacy dispense not found")
        if actor.branch_id and dispense.branch_id and actor.branch_id != dispense.branch_id:
            raise AppException(403, "forbidden", "Dispense belongs to a different branch")

        remaining_returnable = dispense.quantity - dispense.returned_quantity
        if payload.quantity > remaining_returnable:
            raise AppException(409, "pharmacy_return_exceeds_dispense", "Return quantity exceeds remaining dispensed quantity")

        dispense.returned_quantity += payload.quantity
        dispense.return_note = payload.note
        dispense.updated_by = actor.id
        if dispense.returned_quantity == dispense.quantity:
            dispense.status = "returned"
        else:
            dispense.status = "partially_returned"

        if dispense.source_visit_order:
            net_dispensed = Decimal(str(self.repository.get_net_dispensed_quantity(dispense.source_visit_order.id)))
            remaining_on_order = dispense.source_visit_order.quantity - net_dispensed
            dispense.source_visit_order.status = "completed" if remaining_on_order <= 0 else "in_progress"
            dispense.source_visit_order.updated_by = actor.id

        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.PHARMACY_DISPENSE,
            module="pharmacy",
            entity_type="pharmacy_dispense",
            entity_id=str(dispense.id),
            detail={"medicine_name": dispense.medicine_name, "returned_quantity": str(payload.quantity)},
            context=context,
        )
        self.db.commit()
        self.db.refresh(dispense)
        return dispense
