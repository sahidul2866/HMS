from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.pharmacy.service import PharmacyService
from app.schemas.pharmacy import (
    PaginatedResponse,
    PharmacyCompanyCreate,
    PharmacyCompanyRead,
    PharmacyCompanyUpdate,
    PharmacyCustomerCreate,
    PharmacyCustomerRead,
    PharmacyCustomerUpdate,
    PharmacyDashboardSummaryRead,
    PharmacyDispenseCreate,
    PharmacyDispenseRead,
    PharmacyDispenseReturnCreate,
    PharmacyGenericCreate,
    PharmacyGenericRead,
    PharmacyGenericUpdate,
    PharmacyInvestigationCreate,
    PharmacyInvestigationDraftRead,
    PharmacyInvestigationRead,
    PharmacyInvestigationSettingCreate,
    PharmacyInvestigationSettingRead,
    PharmacyInvestigationSettingUpdate,
    PharmacyInvestigationUpdate,
    PharmacyMedicineCreate,
    PharmacyMedicineRead,
    PharmacyMedicineTypeCreate,
    PharmacyMedicineTypeRead,
    PharmacyMedicineTypeUpdate,
    PharmacyMedicineUpdate,
    PharmacyPendingPrescriptionRead,
    PharmacyPurchaseCreate,
    PharmacyPurchaseRead,
    PharmacyPurchaseUpdate,
    PharmacySaleCreate,
    PharmacySalesDraftRead,
    PharmacySaleRead,
    PharmacySaleReturnCreate,
    PharmacySaleReturnRead,
    PharmacySaleReturnUpdate,
    PharmacySaleUpdate,
    PharmacyStockMovementRead,
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


@router.get("/dashboard-summary", response_model=PharmacyDashboardSummaryRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_dashboard_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> PharmacyDashboardSummaryRead:
    return PharmacyService(db).get_dashboard_summary(user)


@router.get("/medicine-types", response_model=PaginatedResponse[PharmacyMedicineTypeRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_medicine_types(
    page: int = 1,
    page_size: int = 10,
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).list_medicine_types(user, page=page, page_size=page_size, q=q)


@router.post("/medicine-types", response_model=PharmacyMedicineTypeRead, dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def create_medicine_type(payload: PharmacyMedicineTypeCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).create_medicine_type(payload, user, context)


@router.get("/medicine-types/{entity_id}", response_model=PharmacyMedicineTypeRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_medicine_type(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_medicine_type(entity_id, user)


@router.put("/medicine-types/{entity_id}", response_model=PharmacyMedicineTypeRead, dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def update_medicine_type(entity_id: UUID, payload: PharmacyMedicineTypeUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).update_medicine_type(entity_id, payload, user, context)


@router.delete("/medicine-types/{entity_id}", dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def delete_medicine_type(entity_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    PharmacyService(db).delete_medicine_type(entity_id, user, context)
    return {"success": True}


@router.get("/generics", response_model=PaginatedResponse[PharmacyGenericRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_generics(page: int = 1, page_size: int = 10, q: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).list_generics(user, page=page, page_size=page_size, q=q)


@router.post("/generics", response_model=PharmacyGenericRead, dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def create_generic(payload: PharmacyGenericCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).create_generic(payload, user, context)


@router.get("/generics/{entity_id}", response_model=PharmacyGenericRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_generic(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_generic(entity_id, user)


@router.put("/generics/{entity_id}", response_model=PharmacyGenericRead, dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def update_generic(entity_id: UUID, payload: PharmacyGenericUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).update_generic(entity_id, payload, user, context)


@router.delete("/generics/{entity_id}", dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def delete_generic(entity_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    PharmacyService(db).delete_generic(entity_id, user, context)
    return {"success": True}


@router.get("/companies", response_model=PaginatedResponse[PharmacyCompanyRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_companies(page: int = 1, page_size: int = 10, q: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).list_companies(user, page=page, page_size=page_size, q=q)


@router.post("/companies", response_model=PharmacyCompanyRead, dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def create_company(payload: PharmacyCompanyCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).create_company(payload, user, context)


@router.get("/companies/{entity_id}", response_model=PharmacyCompanyRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_company(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_company(entity_id, user)


@router.put("/companies/{entity_id}", response_model=PharmacyCompanyRead, dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def update_company(entity_id: UUID, payload: PharmacyCompanyUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).update_company(entity_id, payload, user, context)


@router.delete("/companies/{entity_id}", dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def delete_company(entity_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    PharmacyService(db).delete_company(entity_id, user, context)
    return {"success": True}


@router.get("/customers", response_model=PaginatedResponse[PharmacyCustomerRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_customers(page: int = 1, page_size: int = 10, q: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).list_customers(user, page=page, page_size=page_size, q=q)


@router.post("/customers", response_model=PharmacyCustomerRead, dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def create_customer(payload: PharmacyCustomerCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).create_customer(payload, user, context)


@router.get("/customers/{entity_id}", response_model=PharmacyCustomerRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_customer(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_customer(entity_id, user)


@router.put("/customers/{entity_id}", response_model=PharmacyCustomerRead, dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def update_customer(entity_id: UUID, payload: PharmacyCustomerUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).update_customer(entity_id, payload, user, context)


@router.delete("/customers/{entity_id}", dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def delete_customer(entity_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    PharmacyService(db).delete_customer(entity_id, user, context)
    return {"success": True}


@router.get("/medicines", response_model=PaginatedResponse[PharmacyMedicineRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_medicines(
    page: int = 1,
    page_size: int = 10,
    q: str | None = None,
    medicine_type_id: UUID | None = None,
    generic_id: UUID | None = None,
    company_id: UUID | None = None,
    low_stock: bool = False,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).list_medicines(
        user,
        page=page,
        page_size=page_size,
        q=q,
        medicine_type_id=medicine_type_id,
        generic_id=generic_id,
        company_id=company_id,
        low_stock=low_stock,
    )


@router.post("/medicines", response_model=PharmacyMedicineRead, dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def create_medicine(payload: PharmacyMedicineCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).create_medicine(payload, user, context)


@router.get("/medicines/{entity_id}", response_model=PharmacyMedicineRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_medicine(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_medicine(entity_id, user)


@router.put("/medicines/{entity_id}", response_model=PharmacyMedicineRead, dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def update_medicine(entity_id: UUID, payload: PharmacyMedicineUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).update_medicine(entity_id, payload, user, context)


@router.delete("/medicines/{entity_id}", dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def delete_medicine(entity_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    PharmacyService(db).delete_medicine(entity_id, user, context)
    return {"success": True}


@router.get("/purchases", response_model=PaginatedResponse[PharmacyPurchaseRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_purchases(page: int = 1, page_size: int = 10, q: str | None = None, medicine_id: UUID | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).list_purchases(user, page=page, page_size=page_size, q=q, medicine_id=medicine_id)


@router.post("/purchases", response_model=PharmacyPurchaseRead, dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def create_purchase(payload: PharmacyPurchaseCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).create_purchase(payload, user, context)


@router.get("/purchases/{entity_id}", response_model=PharmacyPurchaseRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_purchase(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_purchase(entity_id, user)


@router.put("/purchases/{entity_id}", response_model=PharmacyPurchaseRead, dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def update_purchase(entity_id: UUID, payload: PharmacyPurchaseUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).update_purchase(entity_id, payload, user, context)


@router.delete("/purchases/{entity_id}", dependencies=[Depends(require_permissions("pharmacy.stock.adjust"))])
def delete_purchase(entity_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    PharmacyService(db).delete_purchase(entity_id, user, context)
    return {"success": True}


@router.get("/sales", response_model=PaginatedResponse[PharmacySaleRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_sales(
    page: int = 1,
    page_size: int = 10,
    q: str | None = None,
    customer_id: UUID | None = None,
    status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).list_sales(user, page=page, page_size=page_size, q=q, customer_id=customer_id, status=status)


@router.post("/sales", response_model=PharmacySaleRead, dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def create_sale(payload: PharmacySaleCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).create_sale(payload, user, context)


@router.get("/sales/{entity_id}", response_model=PharmacySaleRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_sale(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_sale(entity_id, user)


@router.get("/sales-drafts/opd-visit/{visit_id}", response_model=PharmacySalesDraftRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_sale_draft_for_visit(visit_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).build_sales_draft_from_visit(visit_id, user)


@router.put("/sales/{entity_id}", response_model=PharmacySaleRead, dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def update_sale(entity_id: UUID, payload: PharmacySaleUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).update_sale(entity_id, payload, user, context)


@router.delete("/sales/{entity_id}", dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def delete_sale(entity_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    PharmacyService(db).delete_sale(entity_id, user, context)
    return {"success": True}


@router.get("/returns", response_model=PaginatedResponse[PharmacySaleReturnRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_returns(page: int = 1, page_size: int = 10, q: str | None = None, sale_id: UUID | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).list_returns(user, page=page, page_size=page_size, q=q, sale_id=sale_id)


@router.post("/returns", response_model=PharmacySaleReturnRead, dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def create_return(payload: PharmacySaleReturnCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).create_return(payload, user, context)


@router.get("/returns/{entity_id}", response_model=PharmacySaleReturnRead, dependencies=[Depends(require_permissions("pharmacy.view"))])
def get_return(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_return(entity_id, user)


@router.put("/returns/{entity_id}", response_model=PharmacySaleReturnRead, dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def update_return(entity_id: UUID, payload: PharmacySaleReturnUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).update_return(entity_id, payload, user, context)


@router.delete("/returns/{entity_id}", dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def delete_return(entity_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    PharmacyService(db).delete_return(entity_id, user, context)
    return {"success": True}


@router.get("/stock-movements", response_model=PaginatedResponse[PharmacyStockMovementRead], dependencies=[Depends(require_permissions("pharmacy.view"))])
def list_stock_movements(
    page: int = 1,
    page_size: int = 20,
    medicine_id: UUID | None = None,
    reference_type: str | None = Query(default=None),
    reference_id: UUID | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).list_stock_movements(
        user,
        page=page,
        page_size=page_size,
        medicine_id=medicine_id,
        reference_type=reference_type,
        reference_id=reference_id,
    )


@router.get("/investigation-settings", response_model=PaginatedResponse[PharmacyInvestigationSettingRead], dependencies=[Depends(require_permissions("laboratory.view"))])
def list_investigation_settings(page: int = 1, page_size: int = 10, q: str | None = None, service_area: str | None = None, is_active: bool | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).list_investigation_settings(user, page=page, page_size=page_size, q=q, service_area=service_area, is_active=is_active)


@router.post("/investigation-settings", response_model=PharmacyInvestigationSettingRead, dependencies=[Depends(require_permissions("laboratory.manage"))])
def create_investigation_setting(payload: PharmacyInvestigationSettingCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).create_investigation_setting(payload, user, context)


@router.get("/investigation-settings/{entity_id}", response_model=PharmacyInvestigationSettingRead, dependencies=[Depends(require_permissions("laboratory.view"))])
def get_investigation_setting(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_investigation_setting(entity_id, user)


@router.put("/investigation-settings/{entity_id}", response_model=PharmacyInvestigationSettingRead, dependencies=[Depends(require_permissions("laboratory.manage"))])
def update_investigation_setting(entity_id: UUID, payload: PharmacyInvestigationSettingUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).update_investigation_setting(entity_id, payload, user, context)


@router.delete("/investigation-settings/{entity_id}", dependencies=[Depends(require_permissions("laboratory.manage"))])
def delete_investigation_setting(entity_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    PharmacyService(db).delete_investigation_setting(entity_id, user, context)
    return {"success": True}


@router.get("/investigations", response_model=PaginatedResponse[PharmacyInvestigationRead], dependencies=[Depends(require_permissions("laboratory.view"))])
def list_investigations(
    page: int = 1,
    page_size: int = 10,
    q: str | None = None,
    status: str | None = None,
    service_area: str | None = None,
    customer_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return PharmacyService(db).list_investigations(
        user,
        page=page,
        page_size=page_size,
        q=q,
        status=status,
        service_area=service_area,
        customer_id=customer_id,
        date_from=date.fromisoformat(date_from) if date_from else None,
        date_to=date.fromisoformat(date_to) if date_to else None,
    )


@router.post("/investigations", response_model=PharmacyInvestigationRead, dependencies=[Depends(require_permissions("laboratory.manage"))])
def create_investigation(payload: PharmacyInvestigationCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).create_investigation(payload, user, context)


@router.get("/investigations/{entity_id}", response_model=PharmacyInvestigationRead, dependencies=[Depends(require_permissions("laboratory.view"))])
def get_investigation(entity_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).get_investigation(entity_id, user)


@router.get("/investigation-drafts/opd-visit/{visit_id}", response_model=PharmacyInvestigationDraftRead, dependencies=[Depends(require_permissions("laboratory.view"))])
def get_investigation_draft_for_visit(visit_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).build_investigation_draft_from_visit(visit_id, user)


@router.put("/investigations/{entity_id}", response_model=PharmacyInvestigationRead, dependencies=[Depends(require_permissions("laboratory.manage"))])
def update_investigation(entity_id: UUID, payload: PharmacyInvestigationUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return PharmacyService(db).update_investigation(entity_id, payload, user, context)


@router.delete("/investigations/{entity_id}", dependencies=[Depends(require_permissions("laboratory.manage"))])
def delete_investigation(entity_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    PharmacyService(db).delete_investigation(entity_id, user, context)
    return {"success": True}


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
def dispense(payload: PharmacyDispenseCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> PharmacyDispenseRead:
    dispense_record = PharmacyService(db).dispense(payload, user, context)
    return serialize_dispense(dispense_record)


@router.post("/dispenses/{dispense_id}/return", response_model=PharmacyDispenseRead, dependencies=[Depends(require_permissions("pharmacy.dispense"))])
def return_dispense(dispense_id: UUID, payload: PharmacyDispenseReturnCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> PharmacyDispenseRead:
    item = PharmacyService(db).return_dispense(dispense_id, payload, user, context)
    return serialize_dispense(item)
