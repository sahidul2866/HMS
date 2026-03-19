from sqlalchemy.orm import Session

from app.models.pharmacy import PharmacyDispense
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.pharmacy.repository import PharmacyRepository
from app.schemas.pharmacy import PharmacyDispenseCreate
from app.utils.enums import AuditAction


class PharmacyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PharmacyRepository(db)

    def list_dispenses(self, actor: User) -> list[PharmacyDispense]:
        return self.repository.list_dispenses(actor.branch_id)

    def dispense(self, payload: PharmacyDispenseCreate, actor: User, context: dict[str, str | None]) -> PharmacyDispense:
        total_price = payload.quantity * payload.unit_price
        dispense = PharmacyDispense(
            **payload.model_dump(),
            total_price=total_price,
            branch_id=payload.branch_id or actor.branch_id,
            dispensed_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_dispense(dispense)
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

