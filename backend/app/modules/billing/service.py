from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.billing import BillingInvoice, BillingInvoiceItem, BillingPayment, BillingService, ReferredDoctor
from app.models.billing import BillingRefund, BillingSetting
from app.models.billing_links import BillingItemLink
from app.models.encounter import IPDAdmission, OPDVisit, OPDVisitOrder
from app.models.laboratory import LabOrder, LabOrderItem
from app.models.radiology import RadiologyOrder
from app.models.patient import Patient
from app.models.pharmacy import PharmacyInvestigationSetting, PharmacyMedicine
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.billing.repository import BillingRepository
from app.modules.billing_links.repository import BillingLinksRepository
from app.modules.ipd.repository import IPDRepository
from app.modules.opd.repository import OPDRepository
from app.modules.patients.repository import PatientsRepository
from app.modules.users.repository import UsersRepository
from app.schemas.billing import (
    BillingDraftItemRead,
    BillingDraftRead,
    BillingInvoiceCreate,
    BillingInvoiceFilterParams,
    BillingInvoicePreview,
    BillingInvoicePreviewRequest,
    BillingPaymentCreate,
    BillingRefundCreate,
    BillingInvoiceVoidRequest,
    BillingSettingsRead,
    BillingSettingsUpdate,
    BillingServiceControlsUpdate,
    BillingReferralSummaryRead,
    BillingSummaryRead,
    ReferredDoctorCreate,
    BillingServiceCreate,
)
from app.utils.enums import AuditAction

TWOPLACES = Decimal("0.01")
BILLING_ITEM_PERMISSION_LABELS = {
    "billing.item.service": "general billing services",
    "billing.item.medicine": "medicine billing items",
    "billing.item.investigation": "investigation billing items",
}


class BillingServiceManager:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = BillingRepository(db)
        self.billing_links_repository = BillingLinksRepository(db)
        self.opd_repository = OPDRepository(db)
        self.ipd_repository = IPDRepository(db)
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

    def update_service_controls(self, service_id: UUID, payload: BillingServiceControlsUpdate, actor: User, context: dict[str, str | None]) -> BillingService:
        service = self.repository.get_service(service_id, actor.branch_id)
        if not service:
            raise AppException(404, "billing_service_not_found", "Billing service not found")
        service.max_discount_percentage = self._money(payload.max_discount_percentage) if payload.max_discount_percentage is not None else None
        service.max_discount_amount = self._money(payload.max_discount_amount) if payload.max_discount_amount is not None else None
        service.doctor_share_percentage = self._money(payload.doctor_share_percentage)
        service.room_number = payload.room_number.strip() if payload.room_number else None
        if payload.is_active is not None:
            service.is_active = payload.is_active
        service.updated_by = actor.id
        self.db.flush()
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.BILLING_SETTINGS_UPDATE,
            module="billing",
            entity_type="billing_service",
            entity_id=str(service.id),
            detail={
                "service_code": service.service_code,
                "max_discount_percentage": str(service.max_discount_percentage) if service.max_discount_percentage is not None else None,
                "max_discount_amount": str(service.max_discount_amount) if service.max_discount_amount is not None else None,
                "doctor_share_percentage": str(service.doctor_share_percentage),
                "room_number": service.room_number,
            },
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

    def get_settings(self, actor: User) -> BillingSettingsRead:
        settings = self._get_or_create_settings(actor)
        return BillingSettingsRead.model_validate(settings, from_attributes=True)

    def update_settings(self, payload: BillingSettingsUpdate, actor: User, context: dict[str, str | None]) -> BillingSettingsRead:
        settings = self._get_or_create_settings(actor)
        settings.max_item_discount_percentage = self._money(payload.max_item_discount_percentage)
        settings.max_item_discount_amount = self._money(payload.max_item_discount_amount) if payload.max_item_discount_amount is not None else None
        settings.max_invoice_discount_percentage = self._money(payload.max_invoice_discount_percentage)
        settings.max_invoice_discount_amount = self._money(payload.max_invoice_discount_amount) if payload.max_invoice_discount_amount is not None else None
        settings.default_referral_percentage = self._money(payload.default_referral_percentage)
        settings.updated_by = actor.id
        self.db.flush()
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.BILLING_SETTINGS_UPDATE,
            module="billing",
            entity_type="billing_settings",
            entity_id=str(settings.id),
            detail={
                "max_item_discount_percentage": str(settings.max_item_discount_percentage),
                "max_item_discount_amount": str(settings.max_item_discount_amount) if settings.max_item_discount_amount is not None else None,
                "max_invoice_discount_percentage": str(settings.max_invoice_discount_percentage),
                "max_invoice_discount_amount": str(settings.max_invoice_discount_amount) if settings.max_invoice_discount_amount is not None else None,
                "default_referral_percentage": str(settings.default_referral_percentage),
            },
            context=context,
        )
        self.db.commit()
        return BillingSettingsRead.model_validate(settings, from_attributes=True)

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
        return self._build_preview(payload.discount_percentage, self._resolve_invoice_items(payload.items, actor), actor.branch_id)

    def build_opd_visit_draft(self, visit_id: UUID, actor: User) -> BillingDraftRead:
        visit = self.opd_repository.get_visit(visit_id)
        if not visit:
            raise AppException(404, "opd_visit_not_found", "OPD visit not found")
        self._ensure_branch_scope(visit, actor)

        items: list[BillingDraftItemRead] = []
        consultation_invoice = self.repository.get_invoice_by_source(source_opd_visit_id=visit.id, billing_stage="opd")
        if not consultation_invoice:
            consultation_service = self._match_billing_service(
                branch_id=actor.branch_id,
                exact_amount=Decimal(visit.consultation_fee or Decimal("0")),
                keywords=[visit.department_name, "consultation", "opd", "outpatient"],
            )
            items.append(
                BillingDraftItemRead(
                    source_label=f"Consultation · {visit.consulting_doctor_name}",
                    source_module="opd_visit",
                    billing_service_id=consultation_service.id if consultation_service else None,
                    billing_service_name=consultation_service.name if consultation_service else None,
                    quantity=Decimal("1"),
                    warning=None if consultation_service else "Consultation service could not be matched automatically.",
                )
            )
        for order in visit.orders:
            if not order.is_active or order.order_type not in {"prescription", "investigation", "procedure"}:
                continue
            if self.repository.has_item_for_opd_order(order.id):
                continue
            if order.order_type == "prescription":
                medicine = self._match_medicine(order.item_name, actor)
                items.append(
                    BillingDraftItemRead(
                        source_label=f"Medicine · {order.item_name}",
                        source_module="pharmacy",
                        source_item_type="medicine" if medicine else None,
                        source_item_id=medicine.id if medicine else None,
                        billing_service_id=None,
                        billing_service_name=medicine.name if medicine else None,
                        quantity=order.quantity,
                        source_opd_visit_order_id=order.id,
                        warning=None if medicine else f"No pharmacy medicine matched {order.item_name}.",
                    )
                )
                continue
            service = self._match_billing_service(
                branch_id=actor.branch_id,
                keywords=[order.item_name, order.order_type, order.service_area or "", visit.department_name],
            )
            items.append(
                BillingDraftItemRead(
                    source_label=f"{order.order_type.title()} · {order.item_name}",
                    source_module=order.service_area if order.order_type == "investigation" and order.service_area else f"opd_{order.order_type}",
                    billing_service_id=service.id if service else None,
                    billing_service_name=service.name if service else None,
                    quantity=order.quantity,
                    source_opd_visit_order_id=order.id,
                    warning=None if service else f"No billing service matched {order.item_name}.",
                )
            )
        if not items:
            raise AppException(409, "billing_draft_empty", "No unbilled OPD services remain for this visit")
        draft_stage = "opd_orders" if consultation_invoice and any(item.source_opd_visit_order_id for item in items) else "opd"
        message = "Draft prepared from OPD visit, consultation, and billable orders."
        if not any(item.billing_service_id for item in items):
            message = "Draft prepared, but each line still needs a billing service selection."
        return BillingDraftRead(
            patient_id=visit.patient_id,
            patient_name=f"{visit.patient.first_name} {visit.patient.last_name}",
            source_module="opd",
            billing_stage=draft_stage,
            source_opd_visit_id=visit.id,
            internal_referral_user_id=visit.consulting_doctor_user_id,
            note=self._build_opd_note(visit),
            message=message,
            items=items,
        )

    def build_ipd_admission_draft(self, admission_id: UUID, actor: User, *, stage: str) -> BillingDraftRead:
        admission = self.ipd_repository.get_admission(admission_id)
        if not admission:
            raise AppException(404, "ipd_admission_not_found", "IPD admission not found")
        self._ensure_branch_scope(admission, actor)
        if stage not in {"interim", "final"}:
            raise AppException(400, "invalid_billing_stage", "IPD billing stage must be interim or final")
        normalized_stage = "ipd_final" if stage == "final" else "ipd_interim"
        existing = self.repository.get_invoice_by_source(source_ipd_admission_id=admission.id, billing_stage=normalized_stage)
        if existing:
            raise AppException(409, "billing_draft_already_posted", f"{normalized_stage.replace('_', ' ').title()} bill already exists for {admission.admission_number}")

        billable_days = self._calculate_ipd_billable_days(admission, final=stage == "final")
        service = self._match_billing_service(
            branch_id=actor.branch_id,
            keywords=[admission.ward_name, "ipd", "bed", stage, "admission"],
            exact_amount=Decimal(admission.daily_charge or Decimal("0")),
        )
        warning = None if service else f"No IPD billing service matched {admission.ward_name} / {stage}."
        return BillingDraftRead(
            patient_id=admission.patient_id,
            patient_name=f"{admission.patient.first_name} {admission.patient.last_name}",
            source_module="ipd",
            billing_stage=normalized_stage,
            source_ipd_admission_id=admission.id,
            internal_referral_user_id=admission.attending_doctor_user_id,
            note=self._build_ipd_note(admission, stage=stage, billable_days=billable_days),
            message=f"{stage.title()} billing draft prepared for {billable_days} bed-day(s).",
            items=[
                BillingDraftItemRead(
                    source_label=f"{stage.title()} Bed Charge · {admission.ward_name} / {admission.bed_number}",
                    source_module="ipd_bed_charge",
                    billing_service_id=service.id if service else None,
                    billing_service_name=service.name if service else None,
                    quantity=Decimal(str(billable_days)),
                    warning=warning,
                )
            ],
        )

    def create_invoice(self, payload: BillingInvoiceCreate, actor: User, context: dict[str, str | None]) -> BillingInvoice:
        patient = self._get_patient(payload.patient_id, actor)
        internal_referral_user = self._get_internal_referral_user(payload.internal_referral_user_id, actor) if payload.internal_referral_user_id else None
        duplicate_billed_order = next((item.source_opd_visit_order_id for item in payload.items if item.source_opd_visit_order_id and self.repository.has_item_for_opd_order(item.source_opd_visit_order_id)), None)
        if duplicate_billed_order:
            raise AppException(409, "billing_order_duplicate", "One or more OPD orders have already been billed")
        if payload.source_opd_visit_id and payload.billing_stage != "opd_orders" and self.repository.get_invoice_by_source(source_opd_visit_id=payload.source_opd_visit_id, billing_stage=payload.billing_stage):
            raise AppException(409, "billing_invoice_duplicate_source", "Billing invoice already exists for this OPD visit and stage")
        if payload.source_ipd_admission_id and self.repository.get_invoice_by_source(source_ipd_admission_id=payload.source_ipd_admission_id, billing_stage=payload.billing_stage):
            raise AppException(409, "billing_invoice_duplicate_source", "Billing invoice already exists for this IPD admission and stage")
        resolved_items = self._resolve_invoice_items(payload.items, actor)
        preview = self._build_preview(payload.discount_percentage, resolved_items, actor.branch_id)
        invoice = BillingInvoice(
            patient_id=patient.id,
            source_opd_visit_id=payload.source_opd_visit_id,
            source_ipd_admission_id=payload.source_ipd_admission_id,
            source_module=payload.source_module,
            billing_stage=payload.billing_stage,
            invoice_number=f"INV-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            branch_id=payload.branch_id or actor.branch_id or patient.branch_id,
            internal_referral_user_id=internal_referral_user.id if internal_referral_user else None,
            referred_doctor_id=None,
            referred_doctor_name=internal_referral_user.full_name if internal_referral_user else None,
            sub_total=preview.sub_total,
            item_discount_amount=preview.item_discount_amount,
            discount_percentage=preview.discount_percentage,
            invoice_discount_amount=preview.invoice_discount_amount,
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
                [item.billing_service_id for item in resolved_items if item.billing_service_id],
                actor.branch_id,
            )
        }
        if len(services) != len({item.billing_service_id for item in resolved_items if item.billing_service_id}):
            raise AppException(400, "billing_service_not_found", "One or more billing services could not be found")

        settings = self._get_settings_by_branch(actor.branch_id)
        invoice.items = [
            BillingInvoiceItem(
                billing_service_id=item.billing_service_id,
                source_opd_visit_order_id=item.source_opd_visit_order_id,
                source_label=item.source_label,
                source_module=item.source_module,
                service_name=services[item.billing_service_id].name,
                quantity=item.quantity,
                unit_price=services[item.billing_service_id].unit_price,
                discount_percentage=self._money(item.discount_percentage),
                discount_amount=self._money(
                    services[item.billing_service_id].unit_price * item.quantity * item.discount_percentage / Decimal("100")
                ),
                line_total=self._money(
                    services[item.billing_service_id].unit_price * item.quantity
                    - (services[item.billing_service_id].unit_price * item.quantity * item.discount_percentage / Decimal("100"))
                ),
                max_discount_percentage=services[item.billing_service_id].max_discount_percentage
                if services[item.billing_service_id].max_discount_percentage is not None
                else settings.max_item_discount_percentage,
                max_discount_amount=services[item.billing_service_id].max_discount_amount
                if services[item.billing_service_id].max_discount_amount is not None
                else settings.max_item_discount_amount,
                room_number=services[item.billing_service_id].room_number,
                doctor_share_percentage=services[item.billing_service_id].doctor_share_percentage,
                doctor_share_amount=self._money(
                    (
                        services[item.billing_service_id].unit_price * item.quantity
                        - (services[item.billing_service_id].unit_price * item.quantity * item.discount_percentage / Decimal("100"))
                    )
                    * services[item.billing_service_id].doctor_share_percentage
                    / Decimal("100")
                ),
                created_by=actor.id,
                updated_by=actor.id,
            )
            for item in resolved_items
        ]
        self.repository.create_invoice(invoice)
        self._sync_invoice_items_to_worklists(invoice, resolved_items, patient, actor)
        # Create billing_item_links for domain records
        for index, item in enumerate(invoice.items):
            if item.source_opd_visit_order_id:
                visit_order = self.db.get(OPDVisitOrder, item.source_opd_visit_order_id)
                if visit_order and visit_order.lab_order_id:
                    link = BillingItemLink(
                        invoice_item_id=item.id,
                        branch_id=invoice.branch_id,
                        source_module="lab",
                        source_entity_type="lab_order_item",
                        source_entity_id=visit_order.lab_order_id,
                        meta={"invoice_number": invoice.invoice_number, "source_label": item.source_label},
                        created_by=actor.id,
                        updated_by=actor.id,
                    )
                    self.billing_links_repository.create_link(link)
                elif visit_order and visit_order.radiology_order_id:
                    link = BillingItemLink(
                        invoice_item_id=item.id,
                        branch_id=invoice.branch_id,
                        source_module="radiology",
                        source_entity_type="radiology_order",
                        source_entity_id=visit_order.radiology_order_id,
                        meta={"invoice_number": invoice.invoice_number, "source_label": item.source_label},
                        created_by=actor.id,
                        updated_by=actor.id,
                    )
                    self.billing_links_repository.create_link(link)
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

    def _ensure_branch_scope(self, entity: OPDVisit | IPDAdmission, actor: User) -> None:
        if actor.branch_id and entity.branch_id and actor.branch_id != entity.branch_id:
            raise AppException(403, "forbidden", "Source record belongs to a different branch")

    def _match_billing_service(self, *, branch_id: UUID | None, keywords: list[str], exact_amount: Decimal | None = None) -> BillingService | None:
        services = self.repository.list_services(branch_id)
        ranked: list[tuple[int, BillingService]] = []
        normalized_keywords = [keyword.strip().lower() for keyword in keywords if keyword and keyword.strip()]
        for service in services:
            if not service.is_active:
                continue
            haystack = f"{service.service_code} {service.name} {service.description or ''}".lower()
            score = 0
            for keyword in normalized_keywords:
                if keyword == haystack:
                    score += 10
                elif keyword in haystack:
                    score += 4
            if exact_amount is not None and Decimal(service.unit_price) == Decimal(exact_amount):
                score += 6
            if score > 0:
                ranked.append((score, service))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return ranked[0][1] if ranked else None

    def _match_medicine(self, order_text: str, actor: User) -> PharmacyMedicine | None:
        normalized = (order_text or "").strip().lower()
        if not normalized:
            return None
        pattern = f"%{normalized}%"
        stmt = (
            select(PharmacyMedicine)
            .where(
                PharmacyMedicine.is_active.is_(True),
                or_(
                    PharmacyMedicine.name.ilike(pattern),
                    PharmacyMedicine.sku.ilike(pattern),
                    PharmacyMedicine.barcode.ilike(pattern),
                ),
            )
            .order_by(PharmacyMedicine.name.asc())
        )
        if actor.branch_id:
            stmt = stmt.where(PharmacyMedicine.branch_id == actor.branch_id)
        exact_stmt = stmt.where(PharmacyMedicine.name.ilike(normalized))
        return self.db.scalar(exact_stmt) or self.db.scalar(stmt)

    def _calculate_ipd_billable_days(self, admission: IPDAdmission, *, final: bool) -> int:
        end_point = admission.discharged_at.date() if final and admission.discharged_at else datetime.now(UTC).date()
        start_date = admission.admitted_at.date()
        return max((end_point - start_date).days + 1, 1)

    def _build_opd_note(self, visit: OPDVisit) -> str:
        note_parts = [
            f"Auto-generated from OPD visit {visit.visit_number}",
            f"Doctor: {visit.consulting_doctor_name}",
            visit.chief_complaint or "",
        ]
        return " · ".join(part for part in note_parts if part)

    def _build_ipd_note(self, admission: IPDAdmission, *, stage: str, billable_days: int) -> str:
        note_parts = [
            f"Auto-generated from IPD admission {admission.admission_number}",
            f"Stage: {stage}",
            f"Ward/Bed: {admission.ward_name} / {admission.bed_number}",
            f"Billable days: {billable_days}",
        ]
        return " · ".join(note_parts)

    def _resolve_invoice_items(self, items, actor: User):
        for item in items:
            self._ensure_item_permission(item, actor)
            if item.billing_service_id:
                continue
            source_type = item.source_item_type
            if source_type == "medicine":
                medicine = self.db.get(PharmacyMedicine, item.source_item_id) if item.source_item_id else None
                if not medicine or not medicine.is_active:
                    raise AppException(404, "medicine_not_found", "Medicine information not found")
                if actor.branch_id and medicine.branch_id and actor.branch_id != medicine.branch_id:
                    raise AppException(403, "forbidden", "Medicine belongs to a different branch")
                item.billing_service_id = self._get_or_create_catalog_service(
                    code=f"MED-{str(medicine.id)[:8]}",
                    name=medicine.name,
                    unit_price=medicine.sale_price,
                    branch_id=actor.branch_id,
                    actor=actor,
                    description=f"Pharmacy medicine billing item · {medicine.generic.name if medicine.generic else ''}".strip(),
                    referral_percentage=self._get_settings_by_branch(actor.branch_id).default_referral_percentage,
                ).id
                item.source_module = item.source_module or "pharmacy"
                item.source_label = item.source_label or f"Medicine · {medicine.name}"
                continue
            if source_type == "investigation_setting":
                setting = self.db.get(PharmacyInvestigationSetting, item.source_item_id) if item.source_item_id else None
                if not setting or not setting.is_active:
                    raise AppException(404, "investigation_setting_not_found", "Investigation setting not found")
                if actor.branch_id and setting.branch_id and actor.branch_id != setting.branch_id:
                    raise AppException(403, "forbidden", "Investigation setting belongs to a different branch")
                item.billing_service_id = self._get_or_create_catalog_service(
                    code=f"INV-{setting.code}",
                    name=setting.test_name,
                    unit_price=setting.fee,
                    branch_id=actor.branch_id,
                    actor=actor,
                    description=f"{setting.service_area.title()} investigation billing item · {setting.category_name}",
                    referral_percentage=self._get_settings_by_branch(actor.branch_id).default_referral_percentage,
                    room_number=setting.room_number,
                ).id
                item.source_module = item.source_module or setting.service_area
                room_suffix = f" · Room {setting.room_number}" if setting.room_number else ""
                item.source_label = item.source_label or f"{setting.service_area.title()} · {setting.test_name}{room_suffix}"
                continue
            raise AppException(400, "billing_item_source_required", "Select a billing service, medicine, or investigation item")
        return items

    def _ensure_item_permission(self, item, actor: User) -> None:
        permission = self._required_item_permission(item)
        effective_permissions = self._effective_permission_codes(actor)
        if permission not in effective_permissions:
            label = BILLING_ITEM_PERMISSION_LABELS.get(permission, "this billing item type")
            raise AppException(403, "billing_item_forbidden", f"You do not have permission to bill {label}")

    def _required_item_permission(self, item) -> str:
        source_type = (item.source_item_type or "").lower()
        source_module = (item.source_module or "").lower()
        if source_type == "medicine" or source_module == "pharmacy":
            return "billing.item.medicine"
        if source_type == "investigation_setting" or source_module in {"laboratory", "radiology", "opd_investigation"}:
            return "billing.item.investigation"
        if item.source_opd_visit_order_id:
            order = self.opd_repository.get_order(item.source_opd_visit_order_id)
            if order and order.order_type == "investigation":
                return "billing.item.investigation"
            if order and order.order_type == "prescription":
                return "billing.item.medicine"
        return "billing.item.service"

    def _effective_permission_codes(self, actor: User) -> set[str]:
        permissions = {permission.code for permission in actor.direct_permissions if permission.is_active}
        for role in actor.roles:
            if role.is_active:
                permissions.update(permission.code for permission in role.permissions if permission.is_active)
        return permissions

    def _get_or_create_catalog_service(
        self,
        *,
        code: str,
        name: str,
        unit_price: Decimal,
        branch_id: UUID | None,
        actor: User,
        description: str | None = None,
        referral_percentage: Decimal | None = None,
        max_discount_percentage: Decimal | None = None,
        room_number: str | None = None,
    ) -> BillingService:
        existing = self.repository.find_service_by_code(code, branch_id)
        if existing:
            if (
                existing.unit_price != unit_price
                or existing.name != name
                or existing.room_number != room_number
                or (referral_percentage is not None and existing.doctor_share_percentage != referral_percentage)
                or existing.max_discount_percentage != max_discount_percentage
            ):
                existing.name = name
                existing.unit_price = unit_price
                existing.description = description
                if referral_percentage is not None:
                    existing.doctor_share_percentage = referral_percentage
                existing.max_discount_percentage = max_discount_percentage
                existing.room_number = room_number
                existing.updated_by = actor.id
                self.db.flush()
            return existing
        service = BillingService(
            branch_id=branch_id,
            service_code=code,
            name=name,
            description=description,
            unit_price=unit_price,
            doctor_share_percentage=referral_percentage or Decimal("0"),
            max_discount_percentage=max_discount_percentage,
            room_number=room_number,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_service(service)
        return service

    def _sync_invoice_items_to_worklists(self, invoice: BillingInvoice, items, patient: Patient, actor: User) -> None:
        handoff_items = [
            (index, item)
            for index, item in enumerate(items)
            if not item.source_opd_visit_order_id and (item.source_module or "").lower() in {"laboratory", "radiology", "pharmacy"}
        ]
        if not handoff_items:
            return
        visit = invoice.source_opd_visit
        if not visit:
            visit = OPDVisit(
                branch_id=invoice.branch_id or actor.branch_id or patient.branch_id,
                patient_id=patient.id,
                visit_number=f"BILL-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                visit_date=datetime.now(UTC).date(),
                department_name="Billing",
                consulting_doctor_user_id=invoice.internal_referral_user_id,
                consulting_doctor_name=invoice.referred_doctor_name or "Billing Desk",
                status="billed",
                consultation_fee=Decimal("0"),
                consultation_discount=Decimal("0"),
                consultation_total=Decimal("0"),
                consultation_payment_status="paid",
                note=f"Auto-created from billing invoice {invoice.invoice_number}",
                registered_by_user_id=actor.id,
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.opd_repository.create_visit(visit)
            invoice.source_opd_visit_id = visit.id
            invoice.source_module = invoice.source_module or "billing"
        for index, item in handoff_items:
            module = (item.source_module or "").lower()
            order = OPDVisitOrder(
                visit_id=visit.id,
                order_type="prescription" if module == "pharmacy" else "investigation",
                service_area=None if module == "pharmacy" else module,
                item_name=item.source_label or "Billing item",
                room_number=invoice.items[index].room_number if index < len(invoice.items) else None,
                instructions=self._build_order_instruction(invoice.invoice_number, invoice.items[index].room_number if index < len(invoice.items) else None),
                quantity=item.quantity,
                status="pending",
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.opd_repository.create_order(order)
            # Create domain records for lab/radiology
            if module == "laboratory":
                lab_order = LabOrder(
                    branch_id=visit.branch_id,
                    patient_id=visit.patient_id,
                    visit_id=visit.id,
                    order_number=f"LAB-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                    status="pending",
                    created_by=actor.id,
                    updated_by=actor.id,
                )
                self.db.add(lab_order)
                self.db.flush()
                lab_item = LabOrderItem(
                    order_id=lab_order.id,
                    test_name=order.item_name,
                    quantity=order.quantity,
                    created_by=actor.id,
                    updated_by=actor.id,
                )
                self.db.add(lab_item)
                order.lab_order_id = lab_order.id
            elif module == "radiology":
                rad_order = RadiologyOrder(
                    branch_id=visit.branch_id,
                    patient_id=visit.patient_id,
                    visit_id=visit.id,
                    order_number=f"RAD-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                    study_description=order.item_name,
                    status="pending",
                    created_by=actor.id,
                    updated_by=actor.id,
                )
                self.db.add(rad_order)
                self.db.flush()
                order.radiology_order_id = rad_order.id
            item.source_opd_visit_order_id = order.id
            if index < len(invoice.items):
                invoice.items[index].source_opd_visit_order_id = order.id

    def _build_preview(self, discount_percentage: Decimal, items, branch_id: UUID | None) -> BillingInvoicePreview:
        settings = self._get_settings_by_branch(branch_id)
        if discount_percentage > settings.max_invoice_discount_percentage:
            raise AppException(
                400,
                "billing_invoice_discount_limit_exceeded",
                f"Invoice discount cannot exceed {settings.max_invoice_discount_percentage}%",
            )
        services = {
            service.id: service
            for service in self.repository.list_services_by_ids([item.billing_service_id for item in items if item.billing_service_id], branch_id)
        }
        if len(services) != len({item.billing_service_id for item in items}):
            raise AppException(400, "billing_service_not_found", "One or more billing services could not be found")

        sub_total = Decimal("0.00")
        item_discount_amount = Decimal("0.00")
        referred_doctor_amount = Decimal("0.00")
        for item in items:
            service = services[item.billing_service_id]
            item_discount_cap = service.max_discount_percentage if service.max_discount_percentage is not None else settings.max_item_discount_percentage
            if item.discount_percentage > item_discount_cap:
                raise AppException(
                    400,
                    "billing_item_discount_limit_exceeded",
                    f"{service.name} discount cannot exceed {item_discount_cap}%",
                )
            gross_line_total = service.unit_price * item.quantity
            line_discount_amount = self._money(gross_line_total * item.discount_percentage / Decimal("100"))
            item_discount_amount_cap = service.max_discount_amount if service.max_discount_amount is not None else settings.max_item_discount_amount
            if item_discount_amount_cap is not None and line_discount_amount > item_discount_amount_cap:
                raise AppException(
                    400,
                    "billing_item_discount_amount_limit_exceeded",
                    f"{service.name} discount amount cannot exceed {item_discount_amount_cap}",
                )
            net_line_total = self._money(gross_line_total - line_discount_amount)
            sub_total += net_line_total
            item_discount_amount += line_discount_amount
            referred_doctor_amount += self._money(net_line_total * service.doctor_share_percentage / Decimal("100"))

        sub_total = self._money(sub_total)
        item_discount_amount = self._money(item_discount_amount)
        invoice_discount_amount = self._money(sub_total * discount_percentage / Decimal("100"))
        if settings.max_invoice_discount_amount is not None and invoice_discount_amount > settings.max_invoice_discount_amount:
            raise AppException(
                400,
                "billing_invoice_discount_amount_limit_exceeded",
                f"Invoice discount amount cannot exceed {settings.max_invoice_discount_amount}",
            )
        discount_amount = self._money(item_discount_amount + invoice_discount_amount)
        total_amount = self._money(sub_total - invoice_discount_amount)
        referred_doctor_amount = self._money(referred_doctor_amount)
        return BillingInvoicePreview(
            sub_total=sub_total,
            item_discount_amount=item_discount_amount,
            discount_percentage=self._money(discount_percentage),
            invoice_discount_amount=invoice_discount_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            referred_doctor_amount=referred_doctor_amount,
        )

    def _get_or_create_settings(self, actor: User) -> BillingSetting:
        settings = self.repository.get_settings(actor.branch_id)
        if settings:
            return settings
        settings = BillingSetting(
            branch_id=actor.branch_id,
            max_item_discount_percentage=Decimal("100.00"),
            max_item_discount_amount=None,
            max_invoice_discount_percentage=Decimal("100.00"),
            max_invoice_discount_amount=None,
            default_referral_percentage=Decimal("0.00"),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_settings(settings)
        self.db.flush()
        return settings

    def _get_settings_by_branch(self, branch_id: UUID | None) -> BillingSetting:
        settings = self.repository.get_settings(branch_id)
        if settings:
            return settings
        return BillingSetting(
            branch_id=branch_id,
            max_item_discount_percentage=Decimal("100.00"),
            max_item_discount_amount=None,
            max_invoice_discount_percentage=Decimal("100.00"),
            max_invoice_discount_amount=None,
            default_referral_percentage=Decimal("0.00"),
        )

    def _build_order_instruction(self, invoice_number: str, room_number: str | None) -> str:
        parts = [f"Generated from billing invoice {invoice_number}"]
        if room_number:
            parts.append(f"Room {room_number}")
        return " · ".join(parts)

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
