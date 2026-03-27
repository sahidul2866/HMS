from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.pharmacy.service import PharmacyService
from app.schemas.pharmacy import (
    PharmacyDispenseCreate,
    PharmacyDispenseRead,
    PharmacyDispenseReturnCreate,
    PharmacyPendingPrescriptionRead,
    PharmacySummaryRead,
)

router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])


def serialize_dispense(item) -> PharmacyDispenseRead:
    return PharmacyDispenseRead(
        id=item.id,
        patient_id=item.patient_id,
        source_visit_id=item.source_visit_id,
        source_visit_order_id=item.source_visit_order_id,
        patient_name=f"{item.patient.first_name} {item.patient.last_name}" if item.patient else None,
        patient_number=item.patient.patient_number if item.patient else None,
        visit_number=item.source_visit.visit_number if item.source_visit else None,
        medicine_name=item.medicine_name,
        requested_quantity=item.requested_quantity,
        quantity=item.quantity,
        returned_quantity=item.returned_quantity,
        remaining_quantity=item.quantity - item.returned_quantity,
        unit_price=item.unit_price,
        total_price=item.total_price,
        status=item.status,
        prescription_ref=item.prescription_ref,
        note=item.note,
        return_note=item.return_note,
        dispensed_at=item.created_at.isoformat(),
        dispensed_by_name=item.dispensed_by.full_name if item.dispensed_by else None,
    )


@router.get("/dispenses", response_model=list[PharmacyDispenseRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_dispenses(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[PharmacyDispenseRead]:
    dispenses = PharmacyService(db).list_dispenses(user)
    return [serialize_dispense(item) for item in dispenses]


@router.get("/summary", response_model=PharmacySummaryRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_pharmacy_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> PharmacySummaryRead:
    return PharmacyService(db).get_summary(user)


@router.get("/opd-prescriptions", response_model=list[PharmacyPendingPrescriptionRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_pending_opd_prescriptions(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[PharmacyPendingPrescriptionRead]:
    return PharmacyService(db).list_pending_prescriptions(user)


@router.post("/dispense", response_model=PharmacyDispenseRead, dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def dispense(
    payload: PharmacyDispenseCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PharmacyDispenseRead:
    dispense_record = PharmacyService(db).dispense(payload, user, context)
    return serialize_dispense(dispense_record)


@router.post("/dispenses/{dispense_id}/return", response_model=PharmacyDispenseRead, dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def return_dispense(
    dispense_id: UUID,
    payload: PharmacyDispenseReturnCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PharmacyDispenseRead:
    item = PharmacyService(db).return_dispense(dispense_id, payload, user, context)
    return serialize_dispense(item)
