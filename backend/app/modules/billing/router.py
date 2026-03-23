from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.billing.service import BillingServiceManager
from app.schemas.billing import (
    BillingInvoiceCreate,
    BillingInvoiceFilterParams,
    BillingInvoiceListItem,
    BillingInvoicePreview,
    BillingInvoicePreviewRequest,
    BillingInvoiceRead,
    BillingInvoiceVoidRequest,
    BillingReferralSummaryRead,
    BillingSummaryRead,
    BillingServiceCreate,
    BillingServiceRead,
)

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/services", response_model=list[BillingServiceRead], dependencies=[Depends(require_permissions("billing.view"))])
def list_billing_services(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[BillingServiceRead]:
    return [BillingServiceRead.model_validate(item, from_attributes=True) for item in BillingServiceManager(db).list_services(user)]


@router.post(
    "/services",
    response_model=BillingServiceRead,
    dependencies=[Depends(require_permissions("billing.service.manage"))],
)
def create_billing_service(
    payload: BillingServiceCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingServiceRead:
    service = BillingServiceManager(db).create_service(payload, user, context)
    return BillingServiceRead.model_validate(service, from_attributes=True)


@router.get("/invoices", response_model=list[BillingInvoiceListItem], dependencies=[Depends(require_permissions("billing.view"))])
def list_billing_invoices(
    q: str | None = None,
    internal_referral_user_id: UUID | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BillingInvoiceListItem]:
    filters = BillingInvoiceFilterParams(
        q=q,
        internal_referral_user_id=internal_referral_user_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return [BillingInvoiceListItem.model_validate(item, from_attributes=True) for item in BillingServiceManager(db).list_invoices(user, filters)]


@router.get("/invoices/{invoice_id}", response_model=BillingInvoiceRead, dependencies=[Depends(require_permissions("billing.view"))])
def get_billing_invoice(invoice_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> BillingInvoiceRead:
    invoice = BillingServiceManager(db).get_invoice(invoice_id, user)
    return BillingInvoiceRead.model_validate(invoice, from_attributes=True)


@router.get("/reports/summary", response_model=BillingSummaryRead, dependencies=[Depends(require_permissions("reporting.view"))])
def get_billing_summary(
    internal_referral_user_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingSummaryRead:
    filters = BillingInvoiceFilterParams(internal_referral_user_id=internal_referral_user_id, date_from=date_from, date_to=date_to)
    return BillingServiceManager(db).get_summary(user, filters)


@router.get("/reports/referrals", response_model=list[BillingReferralSummaryRead], dependencies=[Depends(require_permissions("reporting.view"))])
def get_billing_referral_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BillingReferralSummaryRead]:
    filters = BillingInvoiceFilterParams(date_from=date_from, date_to=date_to)
    return BillingServiceManager(db).get_referral_summary(user, filters)


@router.post("/invoices/preview", response_model=BillingInvoicePreview, dependencies=[Depends(require_permissions("billing.view"))])
def preview_billing_invoice(
    payload: BillingInvoicePreviewRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingInvoicePreview:
    return BillingServiceManager(db).preview_invoice(payload, user)


@router.post(
    "/invoices",
    response_model=BillingInvoiceRead,
    dependencies=[Depends(require_permissions("billing.invoice.create"))],
)
def create_billing_invoice(
    payload: BillingInvoiceCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingInvoiceRead:
    invoice = BillingServiceManager(db).create_invoice(payload, user, context)
    return BillingInvoiceRead.model_validate(invoice, from_attributes=True)


@router.post(
    "/invoices/{invoice_id}/void",
    response_model=BillingInvoiceRead,
    dependencies=[Depends(require_permissions("billing.invoice.void"))],
)
def void_billing_invoice(
    invoice_id: UUID,
    payload: BillingInvoiceVoidRequest,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingInvoiceRead:
    invoice = BillingServiceManager(db).void_invoice(invoice_id, payload, user, context)
    return BillingInvoiceRead.model_validate(invoice, from_attributes=True)
