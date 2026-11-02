from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.billing.service import BillingServiceManager
from app.schemas.billing import (
    BillingDraftRead,
    BillingInvoiceCreate,
    BillingInvoiceFilterParams,
    BillingInvoiceListItem,
    BillingInvoicePreview,
    BillingInvoicePreviewRequest,
    BillingInvoiceRead,
    BillingInvoiceStickerRead,
    BillingSettingsRead,
    BillingSettingsUpdate,
    BillingServiceControlsUpdate,
    BillingInvoiceVoidRequest,
    BillingPaymentCreate,
    BillingRefundCreate,
    BillingReturnCreate,
    BillingReferralSummaryRead,
    BillingSummaryRead,
    BillingServiceCreate,
    BillingServiceRead,
)

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/settings", response_model=BillingSettingsRead, dependencies=[Depends(require_permissions("billing.view"))])
def get_billing_settings(user=Depends(get_current_user), db: Session = Depends(get_db)) -> BillingSettingsRead:
    return BillingServiceManager(db).get_settings(user)


@router.patch("/settings", response_model=BillingSettingsRead, dependencies=[Depends(require_permissions("billing.service.manage"))])
def update_billing_settings(
    payload: BillingSettingsUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingSettingsRead:
    return BillingServiceManager(db).update_settings(payload, user, context)


@router.get("/services", response_model=list[BillingServiceRead], dependencies=[Depends(require_permissions("billing.view"))])
def list_billing_services(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[BillingServiceRead]:
    return [BillingServiceRead.model_validate(item) for item in BillingServiceManager(db).list_services(user)]


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
    return BillingServiceRead.model_validate(service)


@router.patch(
    "/services/{service_id}/controls",
    response_model=BillingServiceRead,
    dependencies=[Depends(require_permissions("billing.service.manage"))],
)
def update_billing_service_controls(
    service_id: UUID,
    payload: BillingServiceControlsUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingServiceRead:
    service = BillingServiceManager(db).update_service_controls(service_id, payload, user, context)
    return BillingServiceRead.model_validate(service)


@router.get("/invoices", response_model=list[BillingInvoiceListItem], dependencies=[Depends(require_permissions("billing.view"))])
def list_billing_invoices(
    q: str | None = None,
    internal_referral_user_id: UUID | None = None,
    status: str | None = None,
    payment_status: str | None = None,
    source_module: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BillingInvoiceListItem]:
    filters = BillingInvoiceFilterParams(
        q=q,
        internal_referral_user_id=internal_referral_user_id,
        status=status,
        payment_status=payment_status,
        source_module=source_module,
        date_from=date_from,
        date_to=date_to,
    )
    return [BillingInvoiceListItem.model_validate(item, from_attributes=True) for item in BillingServiceManager(db).list_invoices(user, filters)]


@router.get("/invoices/{invoice_id}", response_model=BillingInvoiceRead, dependencies=[Depends(require_permissions("billing.view"))])
def get_billing_invoice(invoice_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> BillingInvoiceRead:
    invoice = BillingServiceManager(db).get_invoice(invoice_id, user)
    return BillingInvoiceRead.model_validate(invoice, from_attributes=True)


@router.get(
    "/invoices/{invoice_id}/stickers",
    response_model=list[BillingInvoiceStickerRead],
    dependencies=[Depends(require_permissions("billing.sticker.print"))],
)
def get_billing_invoice_stickers(invoice_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[BillingInvoiceStickerRead]:
    return BillingServiceManager(db).get_invoice_stickers(invoice_id, user)


@router.get("/reports/summary", response_model=BillingSummaryRead, dependencies=[Depends(require_permissions("reporting.financial.view"))])
def get_billing_summary(
    internal_referral_user_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingSummaryRead:
    filters = BillingInvoiceFilterParams(internal_referral_user_id=internal_referral_user_id, date_from=date_from, date_to=date_to)
    return BillingServiceManager(db).get_summary(user, filters)


@router.get("/reports/referrals", response_model=list[BillingReferralSummaryRead], dependencies=[Depends(require_permissions("reporting.financial.view"))])
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


@router.get("/drafts/opd-visit/{visit_id}", response_model=BillingDraftRead, dependencies=[Depends(require_permissions("billing.view"))])
def get_opd_billing_draft(visit_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> BillingDraftRead:
    return BillingServiceManager(db).build_opd_visit_draft(visit_id, user)


@router.get("/drafts/ipd-admission/{admission_id}", response_model=BillingDraftRead, dependencies=[Depends(require_permissions("billing.view"))])
def get_ipd_billing_draft(
    admission_id: UUID,
    stage: str = "interim",
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingDraftRead:
    return BillingServiceManager(db).build_ipd_admission_draft(admission_id, user, stage=stage)


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
    "/invoices/{invoice_id}/payments",
    response_model=BillingInvoiceRead,
    dependencies=[Depends(require_permissions("billing.payment.collect"))],
)
def collect_billing_payment(
    invoice_id: UUID,
    payload: BillingPaymentCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingInvoiceRead:
    invoice = BillingServiceManager(db).create_payment(invoice_id, payload, user, context)
    return BillingInvoiceRead.model_validate(invoice, from_attributes=True)


@router.post(
    "/invoices/{invoice_id}/refunds",
    response_model=BillingInvoiceRead,
    dependencies=[Depends(require_permissions("billing.payment.refund"))],
)
def create_billing_refund(
    invoice_id: UUID,
    payload: BillingRefundCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingInvoiceRead:
    invoice = BillingServiceManager(db).create_refund(invoice_id, payload, user, context)
    return BillingInvoiceRead.model_validate(invoice, from_attributes=True)


@router.post(
    "/invoices/{invoice_id}/return",
    response_model=BillingInvoiceRead,
    dependencies=[Depends(require_permissions("billing.payment.refund"))],
)
def create_billing_return(
    invoice_id: UUID,
    payload: BillingReturnCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingInvoiceRead:
    invoice = BillingServiceManager(db).create_return(invoice_id, payload, user, context)
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

# Operations use billing administration for configuration/corrections and receipt custody.
from fastapi.encoders import jsonable_encoder
from app.modules.billing.operations import BillingOperations
from app.schemas.billing import BillingTypeCreate, BillingInvoiceAmend, BillingHandoverCreate, BillingHandoverAccept


def operation_payload(value):
    # SQLAlchemy public columns only; never serialize internal session state.
    if isinstance(value,list):return [operation_payload(v) for v in value]
    return jsonable_encoder({column.name:getattr(value,column.name) for column in value.__table__.columns})


@router.get('/types', dependencies=[Depends(require_permissions('billing.view'))])
def billing_types(user=Depends(get_current_user),db: Session=Depends(get_db)):
    return operation_payload(BillingOperations(db).types(user))


@router.post('/types', dependencies=[Depends(require_permissions('billing.service.manage'))])
def create_billing_type(payload: BillingTypeCreate,user=Depends(get_current_user),db: Session=Depends(get_db)):
    return operation_payload(BillingOperations(db).create_type(payload,user))


@router.patch('/invoices/{invoice_id}',response_model=BillingInvoiceRead,dependencies=[Depends(require_permissions('billing.service.manage'))])
def amend_billing_invoice(invoice_id: UUID,payload: BillingInvoiceAmend,user=Depends(get_current_user),db: Session=Depends(get_db)):
    return BillingOperations(db).amend(invoice_id,payload,user)


@router.get('/invoices/{invoice_id}/history',dependencies=[Depends(require_permissions('billing.view'))])
def invoice_history(invoice_id: UUID,user=Depends(get_current_user),db: Session=Depends(get_db)):
    return operation_payload(BillingOperations(db).history(invoice_id,user))


@router.get('/cash/balance',dependencies=[Depends(require_permissions('billing.payment.collect'))])
def cashier_balance(user=Depends(get_current_user),db: Session=Depends(get_db)):
    return BillingOperations(db).cash_balance(user)


@router.get('/cash/handovers',dependencies=[Depends(require_permissions('billing.payment.collect'))])
def cash_handovers(user=Depends(get_current_user),db: Session=Depends(get_db)):
    return operation_payload(BillingOperations(db).handovers(user))


@router.post('/cash/handovers',dependencies=[Depends(require_permissions('billing.payment.collect'))])
def submit_cash_handover(payload: BillingHandoverCreate,user=Depends(get_current_user),db: Session=Depends(get_db)):
    return operation_payload(BillingOperations(db).submit_handover(payload,user))


@router.post('/cash/handovers/{handover_id}/accept',dependencies=[Depends(require_permissions('billing.service.manage'))])
def accept_cash_handover(handover_id: UUID,payload: BillingHandoverAccept,user=Depends(get_current_user),db: Session=Depends(get_db)):
    return operation_payload(BillingOperations(db).accept_handover(handover_id,payload,user))


@router.get('/reports/operations',dependencies=[Depends(require_permissions('reporting.financial.view'))])
def billing_operations_report(date_from: date | None=None,date_to: date | None=None,user=Depends(get_current_user),db: Session=Depends(get_db)):
    return BillingOperations(db).statistics(user,date_from,date_to)


@router.get('/cash/receivers',dependencies=[Depends(require_permissions('billing.payment.collect'))])
def cash_receivers(user=Depends(get_current_user),db: Session=Depends(get_db)):
    from sqlalchemy import select
    from app.models.user import User
    from app.modules.auth.service import AuthService
    stmt=select(User).where(User.is_active.is_(True),User.id!=user.id)
    if user.branch_id:stmt=stmt.where(User.branch_id==user.branch_id)
    return [{'id':str(u.id),'name':u.full_name} for u in db.scalars(stmt) if 'billing.service.manage' in AuthService(db).get_effective_permissions(u)]


@router.get('/reports/snapshots',dependencies=[Depends(require_permissions('reporting.financial.view'))])
def saved_billing_reports(user=Depends(get_current_user),db: Session=Depends(get_db)):
    from sqlalchemy import select
    from app.models.billing import BillingReportSnapshot
    stmt=BillingOperations(db).scoped(select(BillingReportSnapshot),BillingReportSnapshot,user).order_by(BillingReportSnapshot.created_at.desc()).limit(100)
    return operation_payload(list(db.scalars(stmt)))
