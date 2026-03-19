from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.pharmacy.service import PharmacyService
from app.schemas.pharmacy import PharmacyDispenseCreate, PharmacyDispenseRead

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])


@router.get("/dispenses", response_model=list[PharmacyDispenseRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_dispenses(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[PharmacyDispenseRead]:
    return [PharmacyDispenseRead.model_validate(item, from_attributes=True) for item in PharmacyService(db).list_dispenses(user)]


@router.post("/dispense", response_model=PharmacyDispenseRead, dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def dispense(
    payload: PharmacyDispenseCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PharmacyDispenseRead:
    dispense_record = PharmacyService(db).dispense(payload, user, context)
    return PharmacyDispenseRead.model_validate(dispense_record, from_attributes=True)

