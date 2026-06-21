from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, NAMESPACE_DNS, uuid4, uuid5

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.billing import BillingInvoice, BillingInvoiceItem, BillingItemConfig, BillingPayment, ReferredDoctor
from app.models.billing import BillingRefund, BillingSetting
from app.models.billing_links import BillingItemLink
from app.models.encounter import IPDAdmission, IPDBed, IPDOrder, OPDVisit, OPDVisitOrder
from app.models.laboratory import LabOrder, LabOrderItem
from app.models.radiology import RadiologyOrder
from app.models.patient import Patient
from app.models.pharmacy import PharmacyDispense, PharmacyInvestigationSetting, PharmacyMedicine
from app.models.inventory import InventoryItem
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
    BillingReturnCreate,
    BillingInvoiceVoidRequest,
    BillingSettingsRead,
    BillingSettingsUpdate,
    BillingServiceControlsUpdate,
    BillingInvoiceStickerRead,
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

    def list_services(self, actor: User) -> list[dict]:
        self._sync_services_from_modules(actor)
        configs = self.repository.list_item_configs(actor.branch_id)
        return [
            {
                "id": item.id,
                "branch_id": item.branch_id,
                "service_code": item.service_code,
                "name": item.service_name,
                "description": item.billing_instruction,
                "unit_price": item.unit_price,
                "doctor_share_percentage": item.doctor_share_percentage,
                "max_discount_percentage": item.max_discount_percentage,
                "max_discount_amount": item.max_discount_amount,
                "room_number": item.room_number,
                "source_module": item.source_module,
                "source_entity_id": item.source_entity_id,
                "billing_instruction": item.billing_instruction,
                "is_active": item.is_active,
            }
            for item in configs
        ]

    def create_service(self, payload: BillingServiceCreate, actor: User, context: dict[str, str | None]) -> dict:
        existing = next((item for item in self.repository.list_item_configs(actor.branch_id) if item.service_code == payload.service_code), None)
        if existing:
            raise AppException(409, "billing_service_exists", "Billing service code already exists")

        config = BillingItemConfig(
            branch_id=payload.branch_id or actor.branch_id,
            source_module="custom",
            source_entity_id=uuid4(),
            service_code=payload.service_code,
            service_name=payload.name,
            unit_price=self._money(payload.unit_price),
            doctor_share_percentage=self._money(payload.doctor_share_percentage),
            billing_instruction=payload.description,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_item_config(config)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.BILLING_SERVICE_CREATE,
            module="billing",
            entity_type="billing_service",
            entity_id=str(config.id),
            detail={"service_code": config.service_code, "name": config.service_name},
            context=context,
        )
        self.db.commit()
        self.db.refresh(config)
        return {
            "id": config.id,
            "branch_id": config.branch_id,
            "service_code": config.service_code,
            "name": config.service_name,
            "description": config.billing_instruction,
            "unit_price": config.unit_price,
            "doctor_share_percentage": config.doctor_share_percentage,
            "max_discount_percentage": config.max_discount_percentage,
            "max_discount_amount": config.max_discount_amount,
            "room_number": config.room_number,
            "source_module": config.source_module,
            "source_entity_id": config.source_entity_id,
            "billing_instruction": config.billing_instruction,
            "is_active": config.is_active,
        }

    def update_service_controls(self, service_id: UUID, payload: BillingServiceControlsUpdate, actor: User, context: dict[str, str | None]) -> dict:
        config = self.repository.get_item_config(service_id, actor.branch_id)
        if not config:
            raise AppException(404, "billing_service_not_found", "Billing item config not found")
        config.max_discount_percentage = self._money(payload.max_discount_percentage) if payload.max_discount_percentage is not None else None
        config.max_discount_amount = self._money(payload.max_discount_amount) if payload.max_discount_amount is not None else None
        config.doctor_share_percentage = self._money(payload.doctor_share_percentage)
        config.room_number = payload.room_number.strip() if payload.room_number else None
        if payload.is_active is not None:
            config.is_active = payload.is_active
        config.updated_by = actor.id
        self.db.flush()
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.BILLING_SETTINGS_UPDATE,
            module="billing",
            entity_type="billing_service",
            entity_id=str(config.id),
            detail={
                "service_code": config.service_code,
                "max_discount_percentage": str(config.max_discount_percentage) if config.max_discount_percentage is not None else None,
                "max_discount_amount": str(config.max_discount_amount) if config.max_discount_amount is not None else None,
                "doctor_share_percentage": str(config.doctor_share_percentage),
                "room_number": config.room_number,
            },
            context=context,
        )
        self.db.commit()
        self.db.refresh(config)
        return {
            "id": config.id,
            "branch_id": config.branch_id,
            "service_code": config.service_code,
            "name": config.service_name,
            "description": config.billing_instruction,
            "unit_price": config.unit_price,
            "doctor_share_percentage": config.doctor_share_percentage,
            "max_discount_percentage": config.max_discount_percentage,
            "max_discount_amount": config.max_discount_amount,
            "room_number": config.room_number,
            "source_module": config.source_module,
            "source_entity_id": config.source_entity_id,
            "billing_instruction": config.billing_instruction,
            "is_active": config.is_active,
        }

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

    def get_invoice_stickers(self, invoice_id: UUID, actor: User) -> list[BillingInvoiceStickerRead]:
        invoice = self.get_invoice(invoice_id, actor)
        patient_name = f"{invoice.patient.first_name} {invoice.patient.last_name}".strip()
        stickers: list[BillingInvoiceStickerRead] = []
        for index, item in enumerate(invoice.items, start=1):
            module = self._normalize_module(item.source_module)
            source_reference = None
            if item.source_opd_visit_order_id:
                order = self.db.get(OPDVisitOrder, item.source_opd_visit_order_id)
                if order:
                    source_reference = str(order.id)
                    if order.lab_order_id:
                        lab_order = self.db.get(LabOrder, order.lab_order_id)
                        source_reference = lab_order.order_number if lab_order else source_reference
                    elif order.radiology_order_id:
                        radiology_order = self.db.get(RadiologyOrder, order.radiology_order_id)
                        source_reference = radiology_order.order_number if radiology_order else source_reference
            token = (
                str(item.source_opd_visit_order_id).replace("-", "").upper()[:10]
                if item.source_opd_visit_order_id
                else f"{invoice.invoice_number}-{index}"
            )
            barcode_value = "|".join(
                [
                    invoice.invoice_number,
                    invoice.patient.patient_number,
                    module or "billing",
                    token,
                ]
            )
            stickers.append(
                BillingInvoiceStickerRead(
                    invoice_id=invoice.id,
                    invoice_number=invoice.invoice_number,
                    invoice_item_id=item.id,
                    patient_id=invoice.patient_id,
                    patient_number=invoice.patient.patient_number,
                    patient_name=patient_name,
                    item_name=item.service_name,
                    source_module=module or "billing",
                    source_reference=source_reference,
                    quantity=item.quantity,
                    room_number=item.room_number,
                    token=token,
                    barcode_value=barcode_value,
                    created_at=item.created_at,
                )
            )
        return stickers

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
                    billing_service_name=consultation_service.service_name if consultation_service else None,
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
                    billing_service_name=service.service_name if service else None,
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
        if existing and stage == "final":
            raise AppException(409, "billing_draft_already_posted", f"{normalized_stage.replace('_', ' ').title()} bill already exists for {admission.admission_number}")

        invoices = self.repository.list_invoices_for_ipd_admission(admission.id)
        total_billable_days = self._calculate_ipd_billable_days(admission, final=stage == "final")
        previously_billed_days = sum(
            Decimal(item.quantity or 0)
            for invoice in invoices
            for item in invoice.items
            if item.source_module == "ipd_bed_charge" or (item.source_module == "ipd" and "bed charge" in (item.source_label or "").lower())
        )
        billable_days = max(Decimal(total_billable_days) - previously_billed_days, Decimal("0"))
        service = self._match_billing_service(
            branch_id=actor.branch_id,
            keywords=[admission.ward_name, "ipd", "bed", stage, "admission"],
            exact_amount=Decimal(admission.daily_charge or Decimal("0")),
        )
        warning = None if service else f"No IPD billing service matched {admission.ward_name} / {stage}."
        items: list[BillingDraftItemRead] = []
        if stage == "final":
            for prior_invoice in invoices:
                if prior_invoice.billing_stage != "ipd_interim":
                    continue
                for prior_item in prior_invoice.items:
                    prior_config = self.repository.find_item_config_by_source(
                        self._normalize_module(prior_item.source_module or "billing"),
                        prior_item.source_entity_id,
                        actor.branch_id,
                    ) if prior_item.source_entity_id else None
                    if not prior_config:
                        prior_config = self._match_billing_service(
                            branch_id=actor.branch_id,
                            keywords=[prior_item.service_name, prior_item.source_label or "", prior_item.source_module or ""],
                            exact_amount=Decimal(prior_item.unit_price or 0),
                        )
                    source_link = next((link for link in prior_item.item_links if link.source_entity_type in {"ipd_order", "ipd_bed_charge"}), None)
                    items.append(
                        BillingDraftItemRead(
                            source_label=f"Interim carry-forward · {prior_item.source_label or prior_item.service_name}",
                            source_module=prior_item.source_module or "ipd",
                            billing_service_id=prior_config.id if prior_config else None,
                            billing_service_name=prior_config.service_name if prior_config else prior_item.service_name,
                            quantity=prior_item.quantity,
                            discount_percentage=prior_item.discount_percentage,
                            source_record_type=source_link.source_entity_type if source_link else None,
                            source_record_id=source_link.source_entity_id if source_link else None,
                            warning=None if prior_config else f"Select a billing service for prior item {prior_item.service_name}.",
                        )
                    )
        if billable_days > 0:
            items.append(BillingDraftItemRead(
                source_label=f"{stage.title()} Bed Charge · {admission.ward_name} / {admission.bed_number}",
                source_module="ipd_bed_charge",
                billing_service_id=service.id if service else None,
                billing_service_name=service.service_name if service else None,
                quantity=billable_days,
                source_record_type="ipd_bed_charge",
                source_record_id=admission.id,
                warning=warning,
            ))
        active_orders = [order for order in admission.orders if order.status not in {"cancelled", "discontinued"} and order.billing_status != "billed"]
        for order in active_orders:
            order_service = self._match_billing_service(
                branch_id=actor.branch_id,
                keywords=[order.item_name, order.order_type, order.service_area or "", "ipd"],
            )
            items.append(
                BillingDraftItemRead(
                    source_label=f"IPD {order.order_type.title()} · {order.item_name}",
                    source_module="ipd_order",
                    billing_service_id=order_service.id if order_service else None,
                    billing_service_name=order_service.service_name if order_service else None,
                    quantity=order.quantity,
                    source_record_type="ipd_order",
                    source_record_id=order.id,
                    warning=None if order_service else f"Select a billing service for {order.item_name}.",
                )
            )
        if not items:
            raise AppException(409, "billing_draft_empty", "No unbilled IPD bed-days or orders remain for this admission")
        return BillingDraftRead(
            patient_id=admission.patient_id,
            patient_name=f"{admission.patient.first_name} {admission.patient.last_name}",
            source_module="ipd",
            billing_stage=normalized_stage,
            source_ipd_admission_id=admission.id,
            internal_referral_user_id=admission.attending_doctor_user_id,
            note=self._build_ipd_note(admission, stage=stage, billable_days=billable_days),
            message=(
                f"Final reconciliation loaded {len(invoices)} interim bill(s), all prior items and payments, plus {billable_days} new bed-day(s). Post once to consolidate the admission ledger."
                if stage == "final"
                else f"Interim billing draft prepared for {billable_days} new bed-day(s); {previously_billed_days} bed-day(s) were already billed."
            ),
            prior_invoice_count=len(invoices) if stage == "final" else 0,
            prior_billed_amount=sum((Decimal(invoice.total_amount or 0) for invoice in invoices), Decimal("0")) if stage == "final" else Decimal("0"),
            prior_paid_amount=sum((Decimal(invoice.paid_amount or 0) for invoice in invoices), Decimal("0")) if stage == "final" else Decimal("0"),
            prior_due_amount=sum((Decimal(invoice.due_amount or 0) for invoice in invoices), Decimal("0")) if stage == "final" else Decimal("0"),
            items=items,
        )

    def create_invoice(self, payload: BillingInvoiceCreate, actor: User, context: dict[str, str | None]) -> BillingInvoice:
        patient = self._get_patient(payload.patient_id, actor)
        internal_referral_user = self._get_internal_referral_user(payload.internal_referral_user_id, actor) if payload.internal_referral_user_id else None
        duplicate_billed_order = next((item.source_opd_visit_order_id for item in payload.items if item.source_opd_visit_order_id and self.repository.has_item_for_opd_order(item.source_opd_visit_order_id)), None)
        if duplicate_billed_order:
            raise AppException(409, "billing_order_duplicate", "One or more OPD orders have already been billed")
        if payload.source_opd_visit_id and payload.billing_stage != "opd_orders" and self.repository.get_invoice_by_source(source_opd_visit_id=payload.source_opd_visit_id, billing_stage=payload.billing_stage):
            raise AppException(409, "billing_invoice_duplicate_source", "Billing invoice already exists for this OPD visit and stage")
        if payload.source_ipd_admission_id and payload.billing_stage == "ipd_final" and self.repository.get_invoice_by_source(source_ipd_admission_id=payload.source_ipd_admission_id, billing_stage=payload.billing_stage):
            raise AppException(409, "billing_invoice_duplicate_source", "Billing invoice already exists for this IPD admission and stage")
        prior_ipd_invoices = self.repository.list_invoices_for_ipd_admission(payload.source_ipd_admission_id) if payload.source_ipd_admission_id and payload.billing_stage == "ipd_final" else []
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

        configs = {
            config.id: config for config in self.repository.list_item_configs_by_ids(
                [item.billing_service_id for item in resolved_items if item.billing_service_id],
                actor.branch_id,
            )
        }
        if len(configs) != len({item.billing_service_id for item in resolved_items if item.billing_service_id}):
            raise AppException(400, "billing_service_not_found", "One or more billing services could not be found")

        settings = self._get_settings_by_branch(actor.branch_id)
        invoice_items: list[BillingInvoiceItem] = []
        for item in resolved_items:
            config = configs[item.billing_service_id]
            source_module = item.source_module or config.source_module
            source_label = item.source_label
            if config.billing_instruction:
                source_label = f"{source_label} · {config.billing_instruction}" if source_label else config.billing_instruction
            invoice_items.append(
                BillingInvoiceItem(
                    source_entity_id=config.source_entity_id,
                    billing_instruction=config.billing_instruction,
                    source_opd_visit_order_id=item.source_opd_visit_order_id,
                    source_label=source_label,
                    source_module=source_module,
                    service_name=config.service_name,
                    quantity=item.quantity,
                    unit_price=config.unit_price,
                    discount_percentage=self._money(item.discount_percentage),
                    discount_amount=self._money(
                        config.unit_price * item.quantity * item.discount_percentage / Decimal("100")
                    ),
                    line_total=self._money(
                        config.unit_price * item.quantity
                        - (config.unit_price * item.quantity * item.discount_percentage / Decimal("100"))
                    ),
                    max_discount_percentage=config.max_discount_percentage
                    if config.max_discount_percentage is not None
                    else settings.max_item_discount_percentage,
                    max_discount_amount=config.max_discount_amount
                    if config.max_discount_amount is not None
                    else settings.max_item_discount_amount,
                    room_number=config.room_number,
                    doctor_share_percentage=config.doctor_share_percentage,
                    doctor_share_amount=self._money(
                        (
                            config.unit_price * item.quantity
                            - (config.unit_price * item.quantity * item.discount_percentage / Decimal("100"))
                        )
                        * config.doctor_share_percentage
                        / Decimal("100")
                    ),
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )
        invoice.items = invoice_items
        self.repository.create_invoice(invoice)
        if payload.billing_stage == "ipd_final":
            carried_payment = Decimal("0")
            consolidated_numbers: list[str] = []
            for prior_invoice in prior_ipd_invoices:
                if prior_invoice.billing_stage != "ipd_interim":
                    continue
                consolidated_numbers.append(prior_invoice.invoice_number)
                for payment in prior_invoice.payments:
                    carried_payment += Decimal(payment.amount or 0)
                    payment.invoice_id = invoice.id
                    payment.updated_by = actor.id
                prior_invoice.status = "consolidated"
                prior_invoice.is_active = False
                prior_invoice.payment_status = "consolidated"
                prior_invoice.paid_amount = Decimal("0")
                prior_invoice.due_amount = Decimal("0")
                prior_invoice.void_reason = f"Consolidated into final invoice {invoice.invoice_number}"
                prior_invoice.updated_by = actor.id
            if carried_payment:
                invoice.paid_amount = min(self._money(carried_payment), invoice.total_amount)
                self._recalculate_invoice_balance(invoice)
            if consolidated_numbers:
                consolidation_note = f"Consolidated interim invoices: {', '.join(consolidated_numbers)}"
                invoice.note = f"{invoice.note} · {consolidation_note}" if invoice.note else consolidation_note
        self._sync_invoice_items_to_worklists(invoice, resolved_items, patient, actor)
        self._ensure_module_records_for_invoice_items(invoice, actor)
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
                else:
                    pharmacy_dispense_id = self.db.scalar(
                        select(PharmacyDispense.id).where(
                            PharmacyDispense.source_visit_order_id == visit_order.id if visit_order else False,
                            PharmacyDispense.is_active.is_(True),
                        )
                    )
                    if pharmacy_dispense_id:
                        link = BillingItemLink(
                            invoice_item_id=item.id,
                            branch_id=invoice.branch_id,
                            source_module="pharmacy",
                            source_entity_type="pharmacy_dispense",
                            source_entity_id=pharmacy_dispense_id,
                            meta={"invoice_number": invoice.invoice_number, "source_label": item.source_label},
                            created_by=actor.id,
                            updated_by=actor.id,
                        )
                        self.billing_links_repository.create_link(link)
            resolved_item = resolved_items[index] if index < len(resolved_items) else None
            if resolved_item and resolved_item.source_record_id and resolved_item.source_record_type:
                self.billing_links_repository.create_link(
                    BillingItemLink(
                        invoice_item_id=item.id,
                        branch_id=invoice.branch_id,
                        source_module="ipd" if resolved_item.source_record_type.startswith("ipd_") else (item.source_module or "billing"),
                        source_entity_type=resolved_item.source_record_type,
                        source_entity_id=resolved_item.source_record_id,
                        meta={"invoice_number": invoice.invoice_number, "billing_stage": invoice.billing_stage, "source_label": item.source_label},
                        created_by=actor.id,
                        updated_by=actor.id,
                    )
                )
                if resolved_item.source_record_type == "ipd_order":
                    ipd_order = self.db.get(IPDOrder, resolved_item.source_record_id)
                    if ipd_order:
                        ipd_order.billing_status = "billed"
                        ipd_order.updated_by = actor.id
        if invoice.source_ipd_admission_id:
            admission = self.db.get(IPDAdmission, invoice.source_ipd_admission_id)
            if admission:
                admission.billing_status = "cleared" if invoice.billing_stage == "ipd_final" and invoice.due_amount <= 0 else ("final_billed" if invoice.billing_stage == "ipd_final" else "interim_billed")
                admission.updated_by = actor.id
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
        if entity.source_ipd_admission_id and entity.billing_stage == "ipd_final" and entity.due_amount <= Decimal("0.00"):
            admission = self.db.get(IPDAdmission, entity.source_ipd_admission_id)
            if admission:
                admission.billing_status = "cleared"
                admission.updated_by = actor.id
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
            refund_type="refund",
            return_items=None,
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

    def create_return(self, invoice_id: UUID, payload: BillingReturnCreate, actor: User, context: dict[str, str | None]) -> BillingInvoice:
        invoice = self.get_invoice(invoice_id, actor)
        if invoice.status == "void":
            raise AppException(409, "billing_invoice_void", "Cannot return items from a void invoice")
        if invoice.paid_amount <= Decimal("0.00"):
            raise AppException(409, "billing_invoice_unpaid", "Invoice has no collected amount to return")

        items_by_id = {item.id: item for item in invoice.items if item.is_active}
        return_items: list[dict] = []
        return_amount = Decimal("0.00")
        seen: set[UUID] = set()
        for requested in payload.items:
            if requested.invoice_item_id in seen:
                raise AppException(400, "billing_return_duplicate_item", "Return item is duplicated")
            seen.add(requested.invoice_item_id)
            invoice_item = items_by_id.get(requested.invoice_item_id)
            if not invoice_item:
                raise AppException(404, "billing_return_item_not_found", "Invoice item was not found for this bill")
            if requested.quantity > invoice_item.quantity:
                raise AppException(400, "billing_return_quantity_exceeds_billed", f"Return quantity cannot exceed billed quantity for {invoice_item.service_name}")
            unit_return_amount = self._money(invoice_item.line_total / invoice_item.quantity)
            line_return_amount = self._money(unit_return_amount * requested.quantity)
            return_amount += line_return_amount
            return_items.append(
                {
                    "invoice_item_id": str(invoice_item.id),
                    "service_name": invoice_item.service_name,
                    "quantity": str(requested.quantity),
                    "billed_quantity": str(invoice_item.quantity),
                    "unit_return_amount": str(unit_return_amount),
                    "return_amount": str(line_return_amount),
                }
            )

        return_amount = self._money(return_amount)
        if return_amount <= Decimal("0.00"):
            raise AppException(400, "billing_return_empty", "Return amount must be greater than zero")
        if return_amount > invoice.paid_amount:
            raise AppException(400, "billing_return_exceeds_paid", "Return amount cannot exceed current collected balance")

        payment = None
        if payload.payment_id:
            payment = self.repository.get_payment(payload.payment_id)
            if not payment or payment.invoice_id != invoice.id:
                raise AppException(404, "billing_payment_not_found", "Billing payment not found for this invoice")
            already_refunded = sum((refund.amount for refund in payment.refunds), start=Decimal("0.00"))
            refundable_amount = self._money(payment.amount - already_refunded)
            if return_amount > refundable_amount:
                raise AppException(400, "billing_return_exceeds_payment", "Return amount exceeds refundable balance for this receipt")

        refund = BillingRefund(
            invoice_id=invoice.id,
            payment_id=payment.id if payment else None,
            patient_id=invoice.patient_id,
            branch_id=invoice.branch_id,
            refund_number=f"RTRN-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            amount=return_amount,
            refund_type="return",
            return_items=return_items,
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
            entity_type="billing_return",
            entity_id=str(refund.id),
            detail={
                "invoice_number": entity.invoice_number,
                "return_number": refund.refund_number,
                "amount": str(refund.amount),
                "items": return_items,
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

    def _match_billing_service(self, *, branch_id: UUID | None, keywords: list[str], exact_amount: Decimal | None = None) -> BillingItemConfig | None:
        services = self.repository.list_item_configs(branch_id)
        ranked: list[tuple[int, BillingItemConfig]] = []
        normalized_keywords = [keyword.strip().lower() for keyword in keywords if keyword and keyword.strip()]
        for service in services:
            if not service.is_active:
                continue
            haystack = f"{service.service_code} {service.service_name} {service.billing_instruction or ''}".lower()
            score = 0
            for keyword in normalized_keywords:
                if keyword == haystack:
                    score += 10
                elif keyword in haystack:
                    score += 4
            if exact_amount is not None and Decimal(service.unit_price or 0) == Decimal(exact_amount):
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
        self._sync_services_from_modules(actor)
        for item in items:
            self._ensure_item_permission(item, actor)
            original_source_module = item.source_module
            config: BillingItemConfig | None = None
            if item.source_item_id and item.source_module:
                config = self.repository.find_item_config_by_source(self._normalize_module(item.source_module), item.source_item_id, actor.branch_id)
            if not config and item.billing_service_id:
                config = self.repository.get_item_config(item.billing_service_id, actor.branch_id)
            if not config:
                raise AppException(400, "billing_item_source_required", "Select a valid billable item from module catalog")
            item.billing_service_id = config.id
            item.source_module = "ipd_bed_charge" if original_source_module == "ipd_bed_charge" else config.source_module
            room_suffix = f" · Room {config.room_number}" if config.room_number else ""
            item.source_label = item.source_label or f"{config.service_name}{room_suffix}"
            item.source_item_id = config.source_entity_id
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
        if source_type == "investigation_setting" or source_module in {"laboratory", "lab", "radiology", "opd_investigation"}:
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


    def _sync_invoice_items_to_worklists(self, invoice: BillingInvoice, items, patient: Patient, actor: User) -> None:
        handoff_items = [
            (index, item)
            for index, item in enumerate(items)
            if not item.source_opd_visit_order_id
            and not (item.source_label or "").startswith("Interim carry-forward")
            and self._normalize_module(item.source_module) in {"laboratory", "radiology", "pharmacy"}
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
            module = self._normalize_module(item.source_module)
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

    def _ensure_module_records_for_invoice_items(self, invoice: BillingInvoice, actor: User) -> None:
        for item in invoice.items:
            if not item.source_opd_visit_order_id:
                continue
            order = self.db.get(OPDVisitOrder, item.source_opd_visit_order_id)
            if not order:
                continue
            module = self._normalize_module(item.source_module or order.service_area)
            if module == "laboratory" and not order.lab_order_id:
                lab_order = LabOrder(
                    branch_id=invoice.branch_id,
                    patient_id=invoice.patient_id,
                    visit_id=order.visit_id,
                    order_number=f"LAB-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                    status="pending",
                    created_by=actor.id,
                    updated_by=actor.id,
                )
                self.db.add(lab_order)
                self.db.flush()
                self.db.add(
                    LabOrderItem(
                        order_id=lab_order.id,
                        test_name=order.item_name or item.service_name,
                        quantity=order.quantity or item.quantity,
                        created_by=actor.id,
                        updated_by=actor.id,
                    )
                )
                order.lab_order_id = lab_order.id
            elif module == "radiology" and not order.radiology_order_id:
                rad_order = RadiologyOrder(
                    branch_id=invoice.branch_id,
                    patient_id=invoice.patient_id,
                    visit_id=order.visit_id,
                    order_number=f"RAD-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                    study_description=order.item_name or item.service_name,
                    status="pending",
                    created_by=actor.id,
                    updated_by=actor.id,
                )
                self.db.add(rad_order)
                self.db.flush()
                order.radiology_order_id = rad_order.id
            elif module == "pharmacy":
                existing_dispense = self.db.scalar(
                    select(PharmacyDispense).where(
                        PharmacyDispense.source_visit_order_id == order.id,
                        PharmacyDispense.is_active.is_(True),
                    )
                )
                if existing_dispense:
                    existing_dispense.billing_invoice_id = invoice.id
                    existing_dispense.billing_invoice_item_id = item.id
                    existing_dispense.updated_by = actor.id
                else:
                    dispense = PharmacyDispense(
                        patient_id=invoice.patient_id,
                        branch_id=invoice.branch_id,
                        billing_invoice_id=invoice.id,
                        billing_invoice_item_id=item.id,
                        source_visit_id=order.visit_id,
                        source_visit_order_id=order.id,
                        prescription_ref=invoice.invoice_number,
                        medicine_name=order.item_name or item.service_name,
                        requested_quantity=order.quantity or item.quantity,
                        quantity=order.quantity or item.quantity,
                        unit_price=item.unit_price,
                        total_price=item.line_total,
                        status="pending",
                        note=f"Auto-created from invoice {invoice.invoice_number}",
                        dispensed_by_user_id=actor.id,
                        created_by=actor.id,
                        updated_by=actor.id,
                    )
                    self.db.add(dispense)

    @staticmethod
    def _normalize_module(value: str | None) -> str:
        normalized = (value or "").strip().lower()
        if normalized == "lab":
            return "laboratory"
        if normalized in {"medicine", "medicines"}:
            return "pharmacy"
        if normalized == "ipd_bed_charge":
            return "ipd"
        return normalized


    def _build_preview(self, discount_percentage: Decimal, items, branch_id: UUID | None) -> BillingInvoicePreview:
        settings = self._get_settings_by_branch(branch_id)
        if discount_percentage > settings.max_invoice_discount_percentage:
            raise AppException(
                400,
                "billing_invoice_discount_limit_exceeded",
                f"Invoice discount cannot exceed {settings.max_invoice_discount_percentage}%",
            )
        configs = {
            config.id: config
            for config in self.repository.list_item_configs_by_ids([item.billing_service_id for item in items if item.billing_service_id], branch_id)
        }
        if len(configs) != len({item.billing_service_id for item in items}):
            raise AppException(400, "billing_service_not_found", "One or more billing services could not be found")

        sub_total = Decimal("0.00")
        item_discount_amount = Decimal("0.00")
        referred_doctor_amount = Decimal("0.00")
        for item in items:
            config = configs[item.billing_service_id]
            item_discount_cap = config.max_discount_percentage if config.max_discount_percentage is not None else settings.max_item_discount_percentage
            if item.discount_percentage > item_discount_cap:
                raise AppException(
                    400,
                    "billing_item_discount_limit_exceeded",
                    f"{config.service_name} discount cannot exceed {item_discount_cap}%",
                )
            gross_line_total = config.unit_price * item.quantity
            line_discount_amount = self._money(gross_line_total * item.discount_percentage / Decimal("100"))
            item_discount_amount_cap = config.max_discount_amount if config.max_discount_amount is not None else settings.max_item_discount_amount
            if item_discount_amount_cap is not None and line_discount_amount > item_discount_amount_cap:
                raise AppException(
                    400,
                    "billing_item_discount_amount_limit_exceeded",
                    f"{config.service_name} discount amount cannot exceed {item_discount_amount_cap}",
                )
            net_line_total = self._money(gross_line_total - line_discount_amount)
            sub_total += net_line_total
            item_discount_amount += line_discount_amount
            referred_doctor_amount += self._money(net_line_total * config.doctor_share_percentage / Decimal("100"))

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

    def _sync_services_from_modules(self, actor: User) -> None:
        branch_id = actor.branch_id
        default_referral = self._get_settings_by_branch(branch_id).default_referral_percentage

        doctor_stmt = select(User).where(User.is_active.is_(True))
        if branch_id:
            doctor_stmt = doctor_stmt.where((User.branch_id == branch_id) | (User.branch_id.is_(None)))
        for doctor in self.db.scalars(doctor_stmt).all():
            if not any(role.is_doctor_role and role.is_active for role in doctor.roles):
                continue
            consult_source_id = uuid5(NAMESPACE_DNS, f"opd:{doctor.id}:consult")
            followup_source_id = uuid5(NAMESPACE_DNS, f"opd:{doctor.id}:followup")
            consult_fee = Decimal(doctor.opd_consultation_fee or Decimal("0"))
            followup_fee = Decimal(doctor.opd_follow_up_fee or Decimal("0"))
            self._upsert_item_config(
                actor=actor,
                source_module="opd",
                source_entity_id=consult_source_id,
                service_code=f"OPD-CONS-{doctor.username.upper()}",
                service_name=f"OPD Consultation · {doctor.full_name}",
                unit_price=consult_fee if consult_fee > 0 else Decimal("15.00"),
                room_number=None,
                instruction="OPD visit consultation fee",
                default_referral=default_referral,
            )
            self._upsert_item_config(
                actor=actor,
                source_module="opd",
                source_entity_id=followup_source_id,
                service_code=f"OPD-FOLLOWUP-{doctor.username.upper()}",
                service_name=f"OPD Follow-up · {doctor.full_name}",
                unit_price=followup_fee if followup_fee > 0 else Decimal("10.00"),
                room_number=None,
                instruction="OPD follow-up visit fee",
                default_referral=default_referral,
            )

        med_stmt = select(PharmacyMedicine).where(PharmacyMedicine.is_active.is_(True))
        if branch_id:
            med_stmt = med_stmt.where((PharmacyMedicine.branch_id == branch_id) | (PharmacyMedicine.branch_id.is_(None)))
        for medicine in self.db.scalars(med_stmt).all():
            self._upsert_item_config(
                actor=actor,
                source_module="pharmacy",
                source_entity_id=medicine.id,
                service_code=medicine.sku or medicine.barcode or f"MED-{str(medicine.id)[:8]}",
                service_name=medicine.name,
                unit_price=medicine.sale_price,
                room_number=None,
                instruction=medicine.description or f"Pharmacy medicine · {medicine.generic.name if medicine.generic else ''}",
                default_referral=default_referral,
            )

        inv_stmt = select(PharmacyInvestigationSetting).where(PharmacyInvestigationSetting.is_active.is_(True))
        if branch_id:
            inv_stmt = inv_stmt.where((PharmacyInvestigationSetting.branch_id == branch_id) | (PharmacyInvestigationSetting.branch_id.is_(None)))
        for setting in self.db.scalars(inv_stmt).all():
            self._upsert_item_config(
                actor=actor,
                source_module=self._normalize_module(setting.service_area),
                source_entity_id=setting.id,
                service_code=setting.code,
                service_name=setting.test_name,
                unit_price=setting.fee,
                room_number=setting.room_number,
                instruction=setting.description or f"{setting.service_area.title()} · {setting.category_name}",
                default_referral=default_referral,
            )

        bed_stmt = select(IPDBed).where(IPDBed.is_active.is_(True))
        if branch_id:
            bed_stmt = bed_stmt.where((IPDBed.branch_id == branch_id) | (IPDBed.branch_id.is_(None)))
        for bed in self.db.scalars(bed_stmt).all():
            self._upsert_item_config(
                actor=actor,
                source_module="ipd",
                source_entity_id=bed.id,
                service_code=bed.bed_number,
                service_name=f"IPD Bed {bed.ward_name} {bed.bed_number}",
                unit_price=bed.daily_rate,
                room_number=bed.bed_number,
                instruction=bed.note or f"IPD {bed.bed_type} bed charge",
                default_referral=default_referral,
            )

        item_stmt = select(InventoryItem).where(InventoryItem.is_active.is_(True))
        if branch_id:
            item_stmt = item_stmt.where((InventoryItem.branch_id == branch_id) | (InventoryItem.branch_id.is_(None)))
        for inv in self.db.scalars(item_stmt).all():
            self._upsert_item_config(
                actor=actor,
                source_module="inventory",
                source_entity_id=inv.id,
                service_code=inv.item_code or inv.barcode or f"INV-{str(inv.id)[:8]}",
                service_name=inv.name,
                unit_price=Decimal(inv.stock_value / inv.stock_quantity) if inv.stock_quantity and inv.stock_quantity > 0 else Decimal("0.00"),
                room_number=inv.storage_location,
                instruction=inv.description or f"Inventory {inv.item_type}",
                default_referral=default_referral,
            )

        legacy_opd = self.db.scalars(
            select(BillingItemConfig).where(
                BillingItemConfig.service_code.in_(["OPD-CONS-GEN", "OPD-FOLLOWUP"])
            )
        ).all()
        for item in legacy_opd:
            item.is_active = False
            item.updated_by = actor.id

        self.db.flush()

    def _upsert_item_config(
        self,
        *,
        actor: User,
        source_module: str,
        source_entity_id: UUID,
        service_code: str,
        service_name: str,
        unit_price: Decimal,
        room_number: str | None,
        instruction: str | None,
        default_referral: Decimal,
    ) -> BillingItemConfig:
        config = self.repository.find_item_config_by_source(source_module, source_entity_id, actor.branch_id)
        if not config:
            config = BillingItemConfig(
                branch_id=actor.branch_id,
                source_module=source_module,
                source_entity_id=source_entity_id,
                service_code=service_code,
                service_name=service_name,
                unit_price=self._money(unit_price),
                room_number=room_number,
                doctor_share_percentage=default_referral,
                billing_instruction=instruction,
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.repository.create_item_config(config)
            return config
        config.service_code = service_code
        config.service_name = service_name
        config.unit_price = self._money(unit_price)
        config.room_number = room_number
        if not config.billing_instruction:
            config.billing_instruction = instruction
        config.updated_by = actor.id
        self.db.flush()
        return config

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
