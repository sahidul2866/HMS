from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.blood_bank.service import BloodBankService
from app.schemas.blood_bank import (
    BloodBankDashboardRead,
    BloodCollectionCreate,
    BloodCollectionRead,
    BloodDiscardCreate,
    BloodDiscardRead,
    BloodDonorCreate,
    BloodDonorRead,
    BloodIssueCreate,
    BloodRequestCreate,
    BloodRequestRead,
    BloodReturnCreate,
    BloodReturnRead,
    BloodTestResultCreate,
    BloodTestResultRead,
    BloodUnitRead,
    ComponentPrepareCreate,
    CrossmatchCreate,
    CrossmatchRead,
    DonorScreeningCreate,
    DonorScreeningRead,
    MoveUnitCreate,
    PaginatedResponse,
    StorageLocationCreate,
    StorageLocationRead,
    TransfusionCreate,
    TransfusionRead,
)

router = APIRouter(prefix="/blood-bank", tags=["Blood Bank"])


@router.get("/dashboard", response_model=BloodBankDashboardRead, dependencies=[Depends(require_permissions("blood_bank.dashboard.view"))])
def dashboard(db: Session = Depends(get_db)):
    return BloodBankService(db).dashboard()


@router.get("/donors", response_model=PaginatedResponse[BloodDonorRead], dependencies=[Depends(require_permissions("blood_bank.view"))])
def list_donors(
    q: str | None = None,
    blood_group: str | None = None,
    eligibility: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return BloodBankService(db).list_donors(q=q, blood_group=blood_group, eligibility=eligibility, page=page, page_size=page_size)


@router.post("/donors", response_model=BloodDonorRead, dependencies=[Depends(require_permissions("blood_bank.donor.create"))])
def create_donor(payload: BloodDonorCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).create_donor(payload, user, context)


@router.post("/screenings", response_model=DonorScreeningRead, dependencies=[Depends(require_permissions("blood_bank.donor.screen"))])
def screen_donor(payload: DonorScreeningCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).screen_donor(payload, user, context)


@router.post("/collections", response_model=BloodCollectionRead, dependencies=[Depends(require_permissions("blood_bank.collection.create"))])
def collect_blood(payload: BloodCollectionCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).collect_blood(payload, user, context)


@router.get("/units", response_model=PaginatedResponse[BloodUnitRead], dependencies=[Depends(require_permissions("blood_bank.stock.view"))])
def list_units(
    blood_group: str | None = None,
    component_type: str | None = None,
    status_value: str | None = None,
    storage_location_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return BloodBankService(db).list_units(blood_group, component_type, status_value, storage_location_id, page, page_size)


@router.post("/tests", response_model=BloodTestResultRead, dependencies=[Depends(require_permissions("blood_bank.testing.update"))])
def update_test(payload: BloodTestResultCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).update_test(payload, user, context)


@router.post("/components", response_model=BloodUnitRead, dependencies=[Depends(require_permissions("blood_bank.component.prepare"))])
def prepare_component(payload: ComponentPrepareCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).prepare_component(payload, user, context)


@router.get("/locations", response_model=list[StorageLocationRead], dependencies=[Depends(require_permissions("blood_bank.stock.view"))])
def list_locations(db: Session = Depends(get_db)):
    return BloodBankService(db).list_locations()


@router.post("/locations", response_model=StorageLocationRead, dependencies=[Depends(require_permissions("blood_bank.component.prepare"))])
def create_location(payload: StorageLocationCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).create_location(payload, user, context)


@router.post("/units/{unit_id}/move", response_model=BloodUnitRead, dependencies=[Depends(require_permissions("blood_bank.component.prepare"))])
def move_unit(unit_id: UUID, payload: MoveUnitCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).move_unit(unit_id, payload, user, context)


@router.get("/requests", response_model=PaginatedResponse[BloodRequestRead], dependencies=[Depends(require_permissions("blood_bank.view"))])
def list_requests(
    status_value: str | None = None,
    urgency: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return BloodBankService(db).list_requests(status_value, urgency, page, page_size)


@router.post("/requests", response_model=BloodRequestRead, dependencies=[Depends(require_permissions("blood_bank.request.create"))])
def create_request(payload: BloodRequestCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).create_request(payload, user, context)


@router.post("/crossmatches", response_model=CrossmatchRead, dependencies=[Depends(require_permissions("blood_bank.crossmatch.perform"))])
def crossmatch(payload: CrossmatchCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).crossmatch(payload, user, context)


@router.post("/issues", dependencies=[Depends(require_permissions("blood_bank.issue"))])
def issue(payload: BloodIssueCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    issue_item = BloodBankService(db).issue(payload, user, context)
    return {
        "id": issue_item.id,
        "issue_number": issue_item.issue_number,
        "request_id": issue_item.request_id,
        "patient_id": issue_item.patient_id,
        "unit_id": issue_item.unit_id,
        "issued_at": issue_item.issued_at,
        "destination": issue_item.destination,
        "received_by": issue_item.received_by,
        "unit_number": issue_item.unit.unit_number if issue_item.unit else None,
        "blood_group": issue_item.unit.blood_group if issue_item.unit else None,
        "component_type": issue_item.unit.component_type if issue_item.unit else None,
    }


@router.post("/transfusions", response_model=TransfusionRead, dependencies=[Depends(require_permissions("blood_bank.transfusion.update"))])
def transfusion(payload: TransfusionCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).transfusion(payload, user, context)


@router.post("/returns", response_model=BloodReturnRead, dependencies=[Depends(require_permissions("blood_bank.return"))])
def return_unit(payload: BloodReturnCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).return_unit(payload, user, context)


@router.post("/discards", response_model=BloodDiscardRead, dependencies=[Depends(require_permissions("blood_bank.discard"))])
def discard(payload: BloodDiscardCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return BloodBankService(db).discard(payload, user, context)


@router.get("/reports", dependencies=[Depends(require_permissions("blood_bank.report.view"))])
def report(report_type: str = "stock", date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db)):
    return BloodBankService(db).report(report_type, date_from, date_to)

