from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.billing import BillingInvoice, BillingInvoiceItem, BillingPayment, BillingService, ReferredDoctor
from app.models.billing import BillingRefund
from app.models.patient import Patient
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.billing.repository import BillingRepository
from app.modules.patients.repository import PatientsRepository
from app.modules.users.repository import UsersRepository
from app.schemas.billing import (
    BillingInvoiceCreate,
    BillingInvoiceFilterParams,
    BillingInvoicePreview,
    BillingInvoicePreviewRequest,
    BillingPaymentCreate,
    BillingRefundCreate,
    BillingInvoiceVoidRequest,
    BillingReferralSummaryRead,
    BillingSummaryRead,
    ReferredDoctorCreate,
    BillingServiceCreate,
)
from app.utils.enums import AuditAction

TWOPLACES = Decimal("0.01")


class BillingServiceManager:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = BillingRepository(db)
        self.patients_repository = PatientsRepository(db)
        self.users_repository = UsersRepository(db)

    def list_services(self, actor: User) -> list[BillingService]:
        return self.repository.list_services(actor.branch_id)

    def create_service(self, payload: BillingServiceCreate, actor: User, context: dict[str, str | None]) -> BillingService:
        if self.repository.find_service_by_code(payload.service_code, actor.branch_id):
            raise AppException(409, "billing_service_exists", "Billing service code already exists")

        service = BillingService(
            **payload.model_dump(),
            branch_id=payload.branch_id or actor.branch_id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_service(service)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.BILLING_SERVICE_CREATE,
            module="billing",
            entity_type="billing_service",
            entity_id=str(service.id),
            detail={"service_code": service.service_code, "name": service.name},
            context=context,
        )
        self.db.commit()
        self.db.refresh(service)
        return service

    def list_doctors(self, actor: User) -> list[ReferredDoctor]:
        return self.repository.list_doctors(actor.branch_id)

    def create_doctor(self, payload: ReferredDoctorCreate, actor: User, context: dict[str, str | None]) -> ReferredDoctor:
        if self.repository.find_doctor_by_code(payload.doctor_code, actor.branch_id):
            raise AppException(409, "referred_doctor_exists", "Referred doctor code already exists")

        doctor = ReferredDoctor(
            **payload.model_dump(),
            branch_id=payload.branch_id or actor.branch_id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_doctor(doctor)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.BILLING_DOCTOR_CREATE,
            module="billing",
            entity_type="referred_doctor",
            entity_id=str(doctor.id),
            detail={"doctor_code": doctor.doctor_code, "full_name": doctor.full_name},
            context=context,
        )
        self.db.commit()
        self.db.refresh(doctor)
        return doctor

    def list_invoices(self, actor: User, filters: BillingInvoiceFilterParams | None = None) -> list[BillingInvoice]:
        return self.repository.list_invoices(actor.branch_id, filters)

    def get_invoice(self, invoice_id: UUID, actor: User) -> BillingInvoice:
        invoice = self.repository.get_invoice(invoice_id)
        if not invoice:
            raise AppException(404, "billing_invoice_not_found", "Billing invoice not found")
        if actor.branch_id and invoice.branch_id and actor.branch_id != invoice.branch_id:
            raise AppException(403, "forbidden", "Billing invoice belongs to a different branch")
        return invoice

    def get_summary(self, actor: User, filters: BillingInvoiceFilterParams | None = None) -> BillingSummaryRead:
        posted_invoice_count, void_invoice_count, gross_amount, discount_amount, net_amount, referred_doctor_amount = self.repository.get_summary(actor.branch_id, filters)
        return BillingSummaryRead(
            posted_invoice_count=posted_invoice_count or 0,
            void_invoice_count=void_invoice_count or 0,
            gross_amount=self._money(gross_amount),
            discount_amount=self._money(discount_amount),
            net_amount=self._money(net_amount),
            referred_doctor_amount=self._money(referred_doctor_amount),
        )

    def get_referral_summary(self, actor: User, filters: BillingInvoiceFilterParams | None = None) -> list[BillingReferralSummaryRead]:
        rows = self.repository.get_referral_summary(actor.branch_id, filters)
        return [
            BillingReferralSummaryRead(
                internal_referral_user_id=row[0],
                referred_doctor_name=row[1] or "Unassigned",
                invoice_count=row[2] or 0,
                net_amount=self._money(row[3]),
                referred_doctor_amount=self._money(row[4]),
            )
            for row in rows
        ]

    def preview_invoice(self, payload: BillingInvoicePreviewRequest, actor: User) -> BillingInvoicePreview:
        return self._build_preview(payload.discount_percentage, payload.items, actor.branch_id)

    def create_invoice(self, payload: BillingInvoiceCreate, actor: User, context: dict[str, str | None]) -> BillingInvoice:
        patient = self._get_patient(payload.patient_id, actor)
        internal_referral_user = self._get_internal_referral_user(payload.internal_referral_user_id, actor) if payload.internal_referral_user_id else None
        preview = self._build_preview(payload.discount_percentage, payload.items, actor.branch_id)
        invoice = BillingInvoice(
            patient_id=patient.id,
            invoice_number=f"INV-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            branch_id=payload.branch_id or actor.branch_id or patient.branch_id,
            internal_referral_user_id=internal_referral_user.id if internal_referral_user else None,
            referred_doctor_id=None,
            referred_doctor_name=internal_referral_user.full_name if internal_referral_user else None,
            sub_total=preview.sub_total,
            discount_percentage=preview.discount_percentage,
            discount_amount=preview.discount_amount,
            total_amount=preview.total_amount,
            paid_amount=Decimal("0.00"),
            refunded_amount=Decimal("0.00"),
            due_amount=preview.total_amount,
            payment_status="unpaid",
            referred_doctor_amount=preview.referred_doctor_amount,
            status="posted",
            note=payload.note,
            billed_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )

        services = {
            service.id: service for service in self.repository.list_services_by_ids(
                [item.billing_service_id for item in payload.items],
                actor.branch_id,
            )
        }
        if len(services) != len({item.billing_service_id for item in payload.items}):
            raise AppException(400, "billing_service_not_found", "One or more billing services could not be found")

        invoice.items = [
            BillingInvoiceItem(
                billing_service_id=item.billing_service_id,
                service_name=services[item.billing_service_id].name,
                quantity=item.quantity,
                unit_price=services[item.billing_service_id].unit_price,
                line_total=self._money(services[item.billing_service_id].unit_price * item.quantity),
                doctor_share_percentage=services[item.billing_service_id].doctor_share_percentage,
                doctor_share_amount=self._money(
                    services[item.billing_service_id].unit_price
                    * item.quantity
                    * services[item.billing_service_id].doctor_share_percentage
                    / Decimal("100")
                ),
                created_by=actor.id,
                updated_by=actor.id,
            )
            for item in payload.items
        ]
        self.repository.create_invoice(invoice)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.BILLING_INVOICE_CREATE,
            module="billing",
            entity_type="billing_invoice",
            entity_id=str(invoice.id),
            detail={"invoice_number": invoice.invoice_number, "patient_id": str(invoice.patient_id)},
            context=context,
        )
        self.db.commit()
        return self.get_invoice(invoice.id, actor)

    def create_payment(self, invoice_id: UUID, payload: BillingPaymentCreate, actor: User, context: dict[str, str | None]) -> BillingInvoice:
        invoice = self.get_invoice(invoice_id, actor)
        if invoice.status == "void":
            raise AppException(409, "billing_invoice_void", "Cannot collect payment for a void invoice")
        if invoice.payment_status == "paid" or invoice.due_amount <= Decimal("0.00"):
            raise AppException(409, "billing_invoice_paid", "Invoice is already fully paid")
        if payload.amount > invoice.due_amount:
            raise AppException(400, "billing_payment_exceeds_due", "Payment amount cannot exceed invoice due amount")

        payment = BillingPayment(
            invoice_id=invoice.id,
            patient_id=invoice.patient_id,
            branch_id=invoice.branch_id,
            receipt_number=f"RCPT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            payment_method=payload.payment_method,
            amount=self._money(payload.amount),
            note=payload.note,
            received_at=payload.received_at or datetime.now(UTC),
            collected_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_payment(payment)

        entity = self.repository.get_invoice_entity(invoice_id)
        if not entity:
            raise AppException(404, "billing_invoice_not_found", "Billing invoice not found")
        entity.paid_amount = self._money(entity.paid_amount + payment.amount)
        self._recalculate_invoice_balance(entity)
        entity.updated_by = actor.id
        self.db.flush()
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.BILLING_PAYMENT_CREATE,
            module="billing",
            entity_type="billing_payment",
            entity_id=str(payment.id),
            detail={
                "invoice_number": entity.invoice_number,
                "receipt_number": payment.receipt_number,
                "amount": str(payment.amount),
                "payment_method": payment.payment_method,
            },
            context=context,
        )
        self.db.commit()
        return self.get_invoice(invoice_id, actor)

    def create_refund(self, invoice_id: UUID, payload: BillingRefundCreate, actor: User, context: dict[str, str | None]) -> BillingInvoice:
        invoice = self.get_invoice(invoice_id, actor)
        if invoice.status == "void":
            raise AppException(409, "billing_invoice_void", "Cannot refund a void invoice")
        if invoice.paid_amount <= Decimal("0.00"):
            raise AppException(409, "billing_invoice_unpaid", "Invoice has no collected amount to refund")
        if payload.amount > invoice.paid_amount:
            raise AppException(400, "billing_refund_exceeds_paid", "Refund amount cannot exceed collected amount")

        payment = None
        if payload.payment_id:
            payment = self.repository.get_payment(payload.payment_id)
            if not payment or payment.invoice_id != invoice.id:
                raise AppException(404, "billing_payment_not_found", "Billing payment not found for this invoice")
            already_refunded = sum((refund.amount for refund in payment.refunds), start=Decimal("0.00"))
            refundable_amount = self._money(payment.amount - already_refunded)
            if payload.amount > refundable_amount:
                raise AppException(400, "billing_refund_exceeds_payment", "Refund amount exceeds refundable balance for this receipt")

        refund = BillingRefund(
            invoice_id=invoice.id,
            payment_id=payment.id if payment else None,
            patient_id=invoice.patient_id,
            branch_id=invoice.branch_id,
            refund_number=f"RFND-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            amount=self._money(payload.amount),
            reason=payload.reason,
            refunded_at=payload.refunded_at or datetime.now(UTC),
            refunded_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_refund(refund)

        entity = self.repository.get_invoice_entity(invoice_id)
        if not entity:
            raise AppException(404, "billing_invoice_not_found", "Billing invoice not found")
        entity.refunded_amount = self._money(entity.refunded_amount + refund.amount)
        entity.paid_amount = self._money(entity.paid_amount - refund.amount)
        self._recalculate_invoice_balance(entity)
        entity.updated_by = actor.id
        self.db.flush()
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.BILLING_REFUND_CREATE,
            module="billing",
            entity_type="billing_refund",
            entity_id=str(refund.id),
            detail={
                "invoice_number": entity.invoice_number,
                "refund_number": refund.refund_number,
                "amount": str(refund.amount),
                "payment_id": str(refund.payment_id) if refund.payment_id else None,
            },
            context=context,
        )
        self.db.commit()
        return self.get_invoice(invoice_id, actor)

    def void_invoice(self, invoice_id: UUID, payload: BillingInvoiceVoidRequest, actor: User, context: dict[str, str | None]) -> BillingInvoice:
        invoice = self.get_invoice(invoice_id, actor)
        if invoice.status == "void":
            raise AppException(409, "billing_invoice_already_void", "Billing invoice is already void")
        if invoice.payments:
            raise AppException(409, "billing_invoice_has_payments", "Refund or settle payments before voiding this invoice")

        entity = self.repository.get_invoice_entity(invoice_id)
        if not entity:
            raise AppException(404, "billing_invoice_not_found", "Billing invoice not found")

        entity.status = "void"
        entity.void_reason = payload.reason
        entity.voided_at = datetime.now(UTC)
        entity.voided_by_user_id = actor.id
        entity.updated_by = actor.id
        self.db.flush()
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.BILLING_INVOICE_VOID,
            module="billing",
            entity_type="billing_invoice",
            entity_id=str(entity.id),
            detail={"invoice_number": entity.invoice_number, "reason": payload.reason},
            context=context,
        )
        self.db.commit()
        return self.get_invoice(invoice_id, actor)

    def _get_patient(self, patient_id: UUID, actor: User) -> Patient:
        patient = self.patients_repository.get_patient(patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")
        return patient

    def _get_internal_referral_user(self, user_id: UUID, actor: User) -> User:
        doctor = self.users_repository.get_user(user_id)
        if not doctor or not doctor.is_active:
            raise AppException(404, "internal_referral_user_not_found", "Referral doctor user not found")
        if actor.branch_id and doctor.branch_id and actor.branch_id != doctor.branch_id:
            raise AppException(403, "forbidden", "Referral doctor belongs to a different branch")
        if not any(role.is_doctor_role and role.is_referral_role for role in doctor.roles):
            raise AppException(400, "invalid_referral_user", "Selected user is not configured as a referral doctor")
        return doctor

    def _build_preview(self, discount_percentage: Decimal, items, branch_id: UUID | None) -> BillingInvoicePreview:
        services = {
            service.id: service
            for service in self.repository.list_services_by_ids([item.billing_service_id for item in items], branch_id)
        }
        if len(services) != len({item.billing_service_id for item in items}):
            raise AppException(400, "billing_service_not_found", "One or more billing services could not be found")

        sub_total = self._money(
            sum((services[item.billing_service_id].unit_price * item.quantity for item in items), start=Decimal("0"))
        )
        referred_doctor_amount = self._money(
            sum(
                (
                    services[item.billing_service_id].unit_price
                    * item.quantity
                    * services[item.billing_service_id].doctor_share_percentage
                    / Decimal("100")
                    for item in items
                ),
                start=Decimal("0"),
            )
        )
        discount_amount = self._money(sub_total * discount_percentage / Decimal("100"))
        total_amount = self._money(sub_total - discount_amount)
        return BillingInvoicePreview(
            sub_total=sub_total,
            discount_percentage=self._money(discount_percentage),
            discount_amount=discount_amount,
            total_amount=total_amount,
            referred_doctor_amount=referred_doctor_amount,
        )

    def _money(self, value: Decimal) -> Decimal:
        return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    def _recalculate_invoice_balance(self, invoice: BillingInvoice) -> None:
        invoice.due_amount = self._money(invoice.total_amount - invoice.paid_amount)
        if invoice.paid_amount <= Decimal("0.00"):
            invoice.payment_status = "unpaid"
        elif invoice.due_amount <= Decimal("0.00"):
            invoice.payment_status = "paid"
        else:
            invoice.payment_status = "partial"
