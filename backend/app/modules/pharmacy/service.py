from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from math import ceil
from typing import Type
from uuid import uuid4

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.billing import BillingInvoice, BillingInvoiceItem
from app.models.pharmacy import (
    PharmacyCompany,
    PharmacyCustomer,
    PharmacyDispense,
    PharmacyGeneric,
    PharmacyInvestigation,
    PharmacyInvestigationItem,
    PharmacyInvestigationSetting,
    PharmacyMedicine,
    PharmacyMedicineType,
    PharmacyPurchase,
    PharmacySale,
    PharmacySaleItem,
    PharmacySaleReturn,
    PharmacyStockMovement,
)
from app.models.inventory import InventoryItem, InventoryStockTransaction, InventoryStoreItem, StockBatch
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.opd.repository import OPDRepository
from app.modules.patients.repository import PatientsRepository
from app.modules.pharmacy.repository import PharmacyRepository
from app.schemas.pharmacy import (
    PaginatedResponse,
    PharmacyDraftMedicineSuggestionRead,
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
    PharmacyInvestigationDraftItemRead,
    PharmacyInvestigationDraftRead,
    PharmacyInvestigationItemRead,
    PharmacyInvestigationItemWrite,
    PharmacyInvestigationRead,
    PharmacyInvestigationSettingCreate,
    PharmacyInvestigationSettingRead,
    PharmacyInvestigationSettingUpdate,
    PharmacyInvestigationUpdate,
    PharmacyMedicineCreate,
    PharmacyMedicineAvailabilityRead,
    PharmacyMedicineBatchAvailabilityRead,
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
    PharmacySalesDraftItemRead,
    PharmacySalesDraftRead,
    PharmacySaleItemRead,
    PharmacySaleItemWrite,
    PharmacySaleRead,
    PharmacySaleReturnCreate,
    PharmacySaleReturnRead,
    PharmacySaleReturnUpdate,
    PharmacySaleUpdate,
    PharmacyStockMovementRead,
    PharmacySummaryRead,
)


class PharmacyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PharmacyRepository(db)
        self.opd_repository = OPDRepository(db)
        self.patients_repository = PatientsRepository(db)

    def _normalize_pagination(self, page: int, page_size: int) -> tuple[int, int]:
        return max(page, 1), min(max(page_size, 1), 100)

    def _paginate(self, stmt, *, page: int, page_size: int):
        page, page_size = self._normalize_pagination(page, page_size)
        items, total = self.repository.paginate(stmt, page=page, page_size=page_size)
        return items, PaginatedResponse(items=[], total=total, page=page, page_size=page_size)

    def _commit_and_log(self, *, actor: User, action: str, entity_type: str, entity_id: str, detail: dict, context: dict[str, str | None]):
        AuditService(self.db).log(
            user_id=actor.id,
            action=action,
            module="pharmacy",
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            context=context,
        )
        self.db.commit()

    def _generate_number(self, model: Type, prefix: str) -> str:
        count = int(self.db.scalar(select(func.count(model.id))) or 0) + 1
        return f"{prefix}-{date.today().strftime('%Y%m%d')}-{count:04d}"

    def _ensure_unique_name(self, model: Type, name: str, *, exclude_id=None):
        stmt = select(model).where(func.lower(model.name) == name.strip().lower(), model.is_active.is_(True))
        if exclude_id:
            stmt = stmt.where(model.id != exclude_id)
        if self.db.scalar(stmt):
            raise AppException(409, "duplicate_master_data", f"{model.__name__.replace('Pharmacy', '').replace('InvestigationSetting', 'Investigation setting')} already exists")

    def _ensure_branch_scope(self, entity, actor: User):
        branch_id = getattr(entity, "branch_id", None)
        if actor.branch_id and branch_id and actor.branch_id != branch_id:
            raise AppException(403, "forbidden", "Record belongs to a different branch")

    def _resolve_sale_customer(self, *, customer_id=None, patient_id=None, actor: User) -> PharmacyCustomer:
        customer = self.repository.get_customer(customer_id) if customer_id else None
        if customer:
            if not customer.is_active:
                raise AppException(404, "customer_not_found", "Customer information not found")
            self._ensure_branch_scope(customer, actor)
            return customer
        if not patient_id:
            raise AppException(422, "customer_or_patient_required", "Customer or patient context is required for medicine sales")
        patient = self.patients_repository.get_patient(patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")
        existing_customer = self.repository.get_customer_by_patient(patient.id)
        if existing_customer:
            self._ensure_branch_scope(existing_customer, actor)
            return existing_customer
        customer = PharmacyCustomer(
            branch_id=actor.branch_id or patient.branch_id,
            patient_id=patient.id,
            customer_number=self._generate_number(PharmacyCustomer, "CUS"),
            name=f"{patient.first_name} {patient.last_name}".strip(),
            phone=patient.phone,
            email=patient.email,
            address=patient.address,
            note="Auto-created from patient context for pharmacy workflow",
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(customer)
        return customer

    def _resolve_patient(self, patient_id, actor: User) -> Patient | None:
        if not patient_id:
            return None
        patient = self.patients_repository.get_patient(patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")
        return patient

    def _suggest_medicines(self, order_text: str, actor: User) -> list[PharmacyDraftMedicineSuggestionRead]:
        pattern = f"%{order_text.strip().lower()}%"
        stmt = (
            select(PharmacyMedicine)
            .options(joinedload(PharmacyMedicine.generic), joinedload(PharmacyMedicine.company))
            .where(
                PharmacyMedicine.is_active.is_(True),
                PharmacyMedicine.stock_quantity > 0,
                or_(
                    func.lower(PharmacyMedicine.name).like(pattern),
                    func.lower(func.coalesce(PharmacyMedicine.strength, "")).like(pattern),
                    func.lower(PharmacyGeneric.name).like(pattern),
                ),
            )
            .join(PharmacyMedicine.generic)
        )
        if actor.branch_id:
            stmt = stmt.where(PharmacyMedicine.branch_id == actor.branch_id)
        medicines = list(self.db.scalars(stmt.limit(8)).unique())
        ranked: list[tuple[int, PharmacyMedicine, str]] = []
        normalized = order_text.strip().lower()
        for medicine in medicines:
            brand = medicine.name.lower()
            generic = medicine.generic.name.lower() if medicine.generic else ""
            score = 0
            reason = "keyword"
            if brand == normalized:
                score += 10
                reason = "brand exact"
            if generic == normalized:
                score += 9
                reason = "generic exact"
            if normalized in brand:
                score += 5
            if normalized in generic:
                score += 4
            score += min(int(Decimal(medicine.stock_quantity)), 20)
            ranked.append((score, medicine, reason))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            PharmacyDraftMedicineSuggestionRead(
                medicine_id=medicine.id,
                medicine_name=medicine.name,
                generic_name=medicine.generic.name if medicine.generic else None,
                company_name=medicine.company.name if medicine.company else None,
                stock_quantity=medicine.stock_quantity,
                sale_price=medicine.sale_price,
                match_reason=reason,
            )
            for _, medicine, reason in ranked[:5]
        ]

    def _match_investigation_setting(self, order_text: str, service_area: str, actor: User) -> PharmacyInvestigationSetting | None:
        pattern = f"%{order_text.strip().lower()}%"
        stmt = (
            select(PharmacyInvestigationSetting)
            .where(
                PharmacyInvestigationSetting.is_active.is_(True),
                PharmacyInvestigationSetting.service_area == service_area,
                or_(
                    func.lower(PharmacyInvestigationSetting.test_name).like(pattern),
                    func.lower(PharmacyInvestigationSetting.code).like(pattern),
                    func.lower(PharmacyInvestigationSetting.category_name).like(pattern),
                ),
            )
            .order_by(PharmacyInvestigationSetting.test_name.asc())
        )
        if actor.branch_id:
            stmt = stmt.where(PharmacyInvestigationSetting.branch_id == actor.branch_id)
        return self.db.scalar(stmt)

    def _normalize_text(self, value: str | None) -> str | None:
        normalized = (value or "").strip()
        return normalized or None

    def _medicine_name_pattern(self, medicine_name: str) -> str:
        normalized = medicine_name.strip().lower()
        return f"%{normalized}%"

    def _find_inventory_item_for_medicine(self, medicine_name: str, actor: User) -> InventoryItem | None:
        normalized = medicine_name.strip()
        if not normalized:
            return None
        pattern = self._medicine_name_pattern(normalized)
        stmt = (
            select(InventoryItem)
            .where(
                InventoryItem.is_active.is_(True),
                or_(
                    func.lower(InventoryItem.name) == normalized.lower(),
                    func.lower(InventoryItem.name).like(pattern),
                    func.lower(func.coalesce(InventoryItem.item_code, "")).like(pattern),
                ),
            )
            .order_by(
                (func.lower(InventoryItem.name) == normalized.lower()).desc(),
                InventoryItem.name.asc(),
            )
        )
        if actor.branch_id:
            stmt = stmt.where(InventoryItem.branch_id == actor.branch_id)
        return self.db.scalar(stmt.limit(1))

    def _available_inventory_quantity(self, item: InventoryItem) -> Decimal:
        today = date.today()
        total = Decimal("0")
        batch_stmt = (
            select(StockBatch, InventoryStoreItem)
            .join(InventoryStoreItem, (InventoryStoreItem.item_id == StockBatch.item_id) & (InventoryStoreItem.store_id == StockBatch.store_id))
            .where(
                StockBatch.item_id == item.id,
                StockBatch.quantity > 0,
                StockBatch.is_active.is_(True),
                InventoryStoreItem.is_active.is_(True),
                InventoryStoreItem.quantity_on_hand > InventoryStoreItem.reserved_quantity,
                or_(StockBatch.expiry_date.is_(None), StockBatch.expiry_date >= today),
            )
        )
        batch_store_ids = set()
        for batch, balance in self.db.execute(batch_stmt).all():
            batch_store_ids.add(balance.store_id)
            total += min(
                Decimal(batch.quantity or 0),
                max(Decimal("0"), Decimal(balance.quantity_on_hand or 0) - Decimal(balance.reserved_quantity or 0)),
            )
        balance_stmt = select(InventoryStoreItem).where(
            InventoryStoreItem.item_id == item.id,
            InventoryStoreItem.is_active.is_(True),
            InventoryStoreItem.quantity_on_hand > InventoryStoreItem.reserved_quantity,
        )
        if batch_store_ids:
            balance_stmt = balance_stmt.where(InventoryStoreItem.store_id.notin_(batch_store_ids))
        for balance in self.db.scalars(balance_stmt):
            total += max(Decimal("0"), Decimal(balance.quantity_on_hand or 0) - Decimal(balance.reserved_quantity or 0))
        return total

    def _deduct_inventory_for_dispense(self, *, item: InventoryItem, quantity: Decimal, actor: User, reference_id, note: str | None) -> Decimal:
        remaining = Decimal(quantity)
        today = date.today()

        batch_stmt = (
            select(StockBatch)
            .options(joinedload(StockBatch.store))
            .where(
                StockBatch.item_id == item.id,
                StockBatch.quantity > 0,
                StockBatch.is_active.is_(True),
                or_(StockBatch.expiry_date.is_(None), StockBatch.expiry_date >= today),
            )
            .order_by(StockBatch.expiry_date.is_(None), StockBatch.expiry_date.asc(), StockBatch.created_at.asc())
        )
        for batch in self.db.scalars(batch_stmt).unique():
            if remaining <= 0:
                break
            balance = self.db.scalar(
                select(InventoryStoreItem).where(
                    InventoryStoreItem.item_id == item.id,
                    InventoryStoreItem.store_id == batch.store_id,
                    InventoryStoreItem.is_active.is_(True),
                )
            )
            if not balance:
                continue
            available = min(
                max(Decimal("0"), Decimal(balance.quantity_on_hand or 0) - Decimal(balance.reserved_quantity or 0)),
                Decimal(batch.quantity or 0),
            )
            if available <= 0:
                continue
            issued = min(remaining, available)
            self._post_inventory_dispense_transaction(item=item, balance=balance, actor=actor, reference_id=reference_id, quantity=-issued, batch=batch, note=note)
            batch.quantity = Decimal(batch.quantity or 0) - issued
            batch.total_cost = max(Decimal("0"), Decimal(batch.quantity or 0) * Decimal(batch.unit_cost or 0))
            batch.updated_by = actor.id
            remaining -= issued

        if remaining > 0:
            balance_stmt = (
                select(InventoryStoreItem)
                .options(joinedload(InventoryStoreItem.store))
                .where(
                    InventoryStoreItem.item_id == item.id,
                    InventoryStoreItem.is_active.is_(True),
                    InventoryStoreItem.quantity_on_hand > InventoryStoreItem.reserved_quantity,
                )
                .order_by(InventoryStoreItem.updated_at.asc())
            )
            for balance in self.db.scalars(balance_stmt).unique():
                if remaining <= 0:
                    break
                available = max(Decimal("0"), Decimal(balance.quantity_on_hand or 0) - Decimal(balance.reserved_quantity or 0))
                if available <= 0:
                    continue
                issued = min(remaining, available)
                self._post_inventory_dispense_transaction(item=item, balance=balance, actor=actor, reference_id=reference_id, quantity=-issued, batch=None, note=note)
                remaining -= issued

        deducted = Decimal(quantity) - remaining
        if deducted:
            item.stock_quantity = max(Decimal("0"), Decimal(item.stock_quantity or 0) - deducted)
            item.updated_by = actor.id
        return deducted

    def _post_inventory_dispense_transaction(self, *, item: InventoryItem, balance: InventoryStoreItem, actor: User, reference_id, quantity: Decimal, batch: StockBatch | None, note: str | None) -> None:
        stock_before = Decimal(balance.quantity_on_hand or 0)
        stock_after = stock_before + Decimal(quantity)
        if stock_after < 0:
            raise AppException(409, "inventory_stock_conflict", f"{item.name} stock would go below zero")
        balance.quantity_on_hand = stock_after
        balance.updated_by = actor.id
        self.repository.create(
            InventoryStockTransaction(
                id=uuid4(),
                item_id=item.id,
                batch_id=batch.id if batch else None,
                store_id=balance.store_id,
                transaction_type="dispense_out",
                reference_type="pharmacy_dispense",
                reference_id=reference_id,
                quantity_change=Decimal(quantity),
                stock_before=stock_before,
                stock_after=stock_after,
                note=self._normalize_text(note),
                created_by=actor.id,
                updated_by=actor.id,
            )
        )

    def _resolve_or_create_dispense_billing(
        self,
        *,
        payload: PharmacyDispenseCreate,
        actor: User,
        patient_id,
        source_order,
        medicine_name: str,
        quantity: Decimal,
        unit_price: Decimal,
        total_price: Decimal,
        prescription_ref: str | None,
    ) -> tuple[BillingInvoice | None, BillingInvoiceItem | None, bool]:
        invoice = None
        invoice_item = None
        created_invoice = False

        if payload.billing_invoice_id:
            invoice = self.db.get(BillingInvoice, payload.billing_invoice_id)
            if not invoice or not invoice.is_active or invoice.status == "void":
                raise AppException(404, "billing_invoice_not_found", "Billing invoice for this dispense was not found")
            if actor.branch_id and invoice.branch_id and actor.branch_id != invoice.branch_id:
                raise AppException(403, "forbidden", "Billing invoice belongs to a different branch")
            if patient_id and invoice.patient_id != patient_id:
                raise AppException(409, "billing_patient_mismatch", "Billing invoice patient does not match dispense patient")

        if payload.billing_invoice_item_id:
            invoice_item = self.db.get(BillingInvoiceItem, payload.billing_invoice_item_id)
            if not invoice_item:
                raise AppException(404, "billing_invoice_item_not_found", "Billing invoice item for this dispense was not found")
            if invoice and invoice_item.invoice_id != invoice.id:
                raise AppException(409, "billing_item_invoice_mismatch", "Billing invoice item does not belong to the selected invoice")
            invoice = invoice or self.db.get(BillingInvoice, invoice_item.invoice_id)

        if not invoice_item and source_order:
            invoice_item = self.db.scalar(
                select(BillingInvoiceItem)
                .join(BillingInvoice, BillingInvoiceItem.invoice_id == BillingInvoice.id)
                .where(
                    BillingInvoiceItem.source_opd_visit_order_id == source_order.id,
                    BillingInvoice.status != "void",
                    BillingInvoice.is_active.is_(True),
                    BillingInvoiceItem.is_active.is_(True),
                )
                .order_by(BillingInvoice.created_at.desc())
            )
            if invoice_item:
                invoice = self.db.get(BillingInvoice, invoice_item.invoice_id)

        if invoice:
            return invoice, invoice_item, created_invoice

        if not patient_id:
            return None, None, created_invoice

        now_stamp = f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:4].upper()}"
        branch_id = payload.branch_id or actor.branch_id or (source_order.visit.branch_id if source_order else None)
        invoice = BillingInvoice(
            patient_id=patient_id,
            source_opd_visit_id=source_order.visit_id if source_order else payload.source_visit_id,
            source_ipd_admission_id=None,
            source_module="pharmacy",
            billing_stage="pharmacy_dispense",
            invoice_number=f"INV-PH-{now_stamp}",
            branch_id=branch_id,
            sub_total=total_price,
            item_discount_amount=Decimal("0"),
            discount_percentage=Decimal("0"),
            invoice_discount_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            total_amount=total_price,
            paid_amount=Decimal("0"),
            refunded_amount=Decimal("0"),
            due_amount=total_price,
            payment_status="unpaid",
            referred_doctor_amount=Decimal("0"),
            status="posted",
            note=f"Auto-created from pharmacy dispense for {medicine_name}{f' / {prescription_ref}' if prescription_ref else ''}",
            billed_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        invoice_item = BillingInvoiceItem(
            source_opd_visit_order_id=source_order.id if source_order else payload.source_visit_order_id,
            source_label=medicine_name,
            source_module="pharmacy",
            service_name=medicine_name,
            quantity=quantity,
            unit_price=unit_price,
            discount_percentage=Decimal("0"),
            discount_amount=Decimal("0"),
            line_total=total_price,
            doctor_share_percentage=Decimal("0"),
            doctor_share_amount=Decimal("0"),
            created_by=actor.id,
            updated_by=actor.id,
        )
        invoice.items.append(invoice_item)
        self.repository.create(invoice)
        created_invoice = True
        return invoice, invoice_item, created_invoice

    def get_medicine_availability(self, medicine_name: str, actor: User) -> PharmacyMedicineAvailabilityRead:
        normalized = medicine_name.strip()
        if len(normalized) < 2:
            raise AppException(422, "medicine_name_required", "Medicine name is required")

        medicine_stmt = select(PharmacyMedicine).where(
            PharmacyMedicine.is_active.is_(True),
            func.lower(PharmacyMedicine.name) == normalized.lower(),
        )
        if actor.branch_id:
            medicine_stmt = medicine_stmt.where(PharmacyMedicine.branch_id == actor.branch_id)
        pharmacy_medicine = self.db.scalar(medicine_stmt)

        item_stmt = (
            select(InventoryItem)
            .where(
                InventoryItem.is_active.is_(True),
                or_(
                    func.lower(InventoryItem.name) == normalized.lower(),
                    func.lower(InventoryItem.name).like(self._medicine_name_pattern(normalized)),
                    func.lower(func.coalesce(InventoryItem.item_code, "")).like(self._medicine_name_pattern(normalized)),
                ),
            )
            .order_by(InventoryItem.name.asc())
        )
        if actor.branch_id:
            item_stmt = item_stmt.where(InventoryItem.branch_id == actor.branch_id)
        inventory_item = self.db.scalar(item_stmt.limit(1))

        today = date.today()
        near_expiry_cutoff = today + timedelta(days=90)
        batches: list[PharmacyMedicineBatchAvailabilityRead] = []
        total_available = Decimal("0")
        total_reserved = Decimal("0")

        if inventory_item:
            balance_stmt = (
                select(InventoryStoreItem)
                .options(joinedload(InventoryStoreItem.store), joinedload(InventoryStoreItem.item))
                .where(InventoryStoreItem.item_id == inventory_item.id, InventoryStoreItem.is_active.is_(True))
            )
            balances = list(self.db.scalars(balance_stmt).unique())
            for balance in balances:
                available = max(Decimal("0"), Decimal(balance.quantity_on_hand or 0) - Decimal(balance.reserved_quantity or 0))
                total_available += available
                total_reserved += Decimal(balance.reserved_quantity or 0)
                batch_stmt = (
                    select(StockBatch)
                    .where(
                        StockBatch.item_id == inventory_item.id,
                        StockBatch.store_id == balance.store_id,
                        StockBatch.quantity > 0,
                        StockBatch.is_active.is_(True),
                    )
                    .order_by(StockBatch.expiry_date.is_(None), StockBatch.expiry_date.asc(), StockBatch.created_at.asc())
                )
                stock_batches = list(self.db.scalars(batch_stmt))
                if stock_batches:
                    for batch in stock_batches:
                        is_expired = bool(batch.expiry_date and batch.expiry_date < today)
                        batch_available = Decimal("0") if is_expired else Decimal(batch.quantity or 0)
                        batches.append(
                            PharmacyMedicineBatchAvailabilityRead(
                                store_id=balance.store_id,
                                store_name=balance.store.name if balance.store else None,
                                store_type=balance.store.store_type if balance.store else None,
                                department_name=balance.store.department_name if balance.store else None,
                                batch_id=batch.id,
                                batch_no=batch.batch_no,
                                expiry_date=batch.expiry_date,
                                available_quantity=batch_available,
                                reserved_quantity=balance.reserved_quantity,
                                is_expired=is_expired,
                                is_near_expiry=bool(batch.expiry_date and today <= batch.expiry_date <= near_expiry_cutoff),
                                source="inventory",
                            )
                        )
                elif available > 0:
                    batches.append(
                        PharmacyMedicineBatchAvailabilityRead(
                            store_id=balance.store_id,
                            store_name=balance.store.name if balance.store else None,
                            store_type=balance.store.store_type if balance.store else None,
                            department_name=balance.store.department_name if balance.store else None,
                            available_quantity=available,
                            reserved_quantity=balance.reserved_quantity,
                            source="inventory",
                        )
                    )

        pharmacy_stock = Decimal(pharmacy_medicine.stock_quantity or 0) if pharmacy_medicine else Decimal("0")
        if pharmacy_stock > 0 and not batches:
            total_available += pharmacy_stock
            batches.append(
                PharmacyMedicineBatchAvailabilityRead(
                    store_name="Pharmacy Store",
                    store_type="pharmacy",
                    available_quantity=pharmacy_stock,
                    source="pharmacy",
                )
            )

        usable_batches = [batch for batch in batches if batch.available_quantity > 0 and not batch.is_expired]
        usable_batches.sort(key=lambda batch: (batch.expiry_date is None, batch.expiry_date or date.max, batch.store_name or ""))
        preferred = usable_batches[0] if usable_batches else None
        status = "out_of_stock"
        if usable_batches:
            status = "available"
        elif total_available > 0:
            status = "expired_only"

        return PharmacyMedicineAvailabilityRead(
            medicine_name=normalized,
            pharmacy_medicine_id=pharmacy_medicine.id if pharmacy_medicine else None,
            inventory_item_id=inventory_item.id if inventory_item else None,
            total_available_quantity=total_available,
            total_reserved_quantity=total_reserved,
            pharmacy_stock_quantity=pharmacy_stock,
            status=status,
            preferred_batch_id=preferred.batch_id if preferred else None,
            preferred_batch_no=preferred.batch_no if preferred else None,
            preferred_expiry_date=preferred.expiry_date if preferred else None,
            batches=batches,
        )

    def _validate_purchase_payload(self, payload: PharmacyPurchaseCreate | PharmacyPurchaseUpdate) -> None:
        if payload.expiry_date and payload.expiry_date < payload.purchase_date:
            raise AppException(422, "invalid_expiry_date", "Expiry date cannot be earlier than purchase date")

    def _serialize_stock_movement(self, item: PharmacyStockMovement) -> PharmacyStockMovementRead:
        return PharmacyStockMovementRead(
            id=item.id,
            medicine_id=item.medicine_id,
            medicine_name=item.medicine.name,
            movement_type=item.movement_type,
            reference_type=item.reference_type,
            reference_id=item.reference_id,
            quantity_change=item.quantity_change,
            stock_before=item.stock_before,
            stock_after=item.stock_after,
            batch_no=item.batch_no,
            expiry_date=item.expiry_date,
            unit_cost=item.unit_cost,
            sale_price=item.sale_price,
            note=item.note,
            created_at=item.created_at,
        )

    def _change_stock(
        self,
        *,
        medicine: PharmacyMedicine,
        delta: Decimal,
        actor: User,
        movement_type: str,
        reference_type: str,
        reference_id,
        batch_no: str | None = None,
        expiry_date: date | None = None,
        unit_cost: Decimal | None = None,
        sale_price: Decimal | None = None,
        note: str | None = None,
    ) -> PharmacyStockMovement:
        stock_before = Decimal(medicine.stock_quantity)
        stock_after = stock_before + Decimal(delta)
        if stock_after < 0:
            raise AppException(409, "stock_conflict", f"Stock update would reduce {medicine.name} below zero")
        medicine.stock_quantity = stock_after
        medicine.updated_by = actor.id
        movement = PharmacyStockMovement(
            id=uuid4(),
            branch_id=medicine.branch_id or actor.branch_id,
            medicine_id=medicine.id,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            quantity_change=Decimal(delta),
            stock_before=stock_before,
            stock_after=stock_after,
            batch_no=self._normalize_text(batch_no),
            expiry_date=expiry_date,
            unit_cost=unit_cost,
            sale_price=sale_price,
            note=self._normalize_text(note),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(movement)
        return movement

    def _serialize_type(self, item: PharmacyMedicineType) -> PharmacyMedicineTypeRead:
        return PharmacyMedicineTypeRead(id=item.id, name=item.name, description=item.description, created_at=item.created_at.date() if item.created_at else None)

    def _serialize_generic(self, item: PharmacyGeneric) -> PharmacyGenericRead:
        return PharmacyGenericRead(id=item.id, name=item.name, description=item.description)

    def _serialize_company(self, item: PharmacyCompany) -> PharmacyCompanyRead:
        return PharmacyCompanyRead(
            id=item.id,
            name=item.name,
            contact_person=item.contact_person,
            phone=item.phone,
            email=item.email,
            address=item.address,
            note=item.note,
        )

    def _serialize_customer(self, item: PharmacyCustomer) -> PharmacyCustomerRead:
        patient_name = None
        if item.patient:
            patient_name = f"{item.patient.first_name} {item.patient.last_name}".strip()
        return PharmacyCustomerRead(
            id=item.id,
            patient_id=item.patient_id,
            customer_number=item.customer_number,
            name=item.name,
            phone=item.phone,
            email=item.email,
            address=item.address,
            note=item.note,
            patient_name=patient_name,
            patient_number=item.patient.patient_number if item.patient else None,
        )

    def _serialize_medicine(self, item: PharmacyMedicine) -> PharmacyMedicineRead:
        return PharmacyMedicineRead(
            id=item.id,
            medicine_type_id=item.medicine_type_id,
            generic_id=item.generic_id,
            company_id=item.company_id,
            name=item.name,
            strength=item.strength,
            dosage_form=item.dosage_form,
            sku=item.sku,
            barcode=item.barcode,
            purchase_price=item.purchase_price,
            sale_price=item.sale_price,
            reorder_level=item.reorder_level,
            description=item.description,
            stock_quantity=item.stock_quantity,
            medicine_type_name=item.medicine_type.name,
            generic_name=item.generic.name,
            company_name=item.company.name,
        )

    def _serialize_purchase(self, item: PharmacyPurchase) -> PharmacyPurchaseRead:
        return PharmacyPurchaseRead(
            id=item.id,
            medicine_id=item.medicine_id,
            purchase_number=item.purchase_number,
            purchase_date=item.purchase_date,
            supplier_name=item.supplier_name,
            invoice_number=item.invoice_number,
            batch_no=item.batch_no,
            expiry_date=item.expiry_date,
            quantity=item.quantity,
            bonus_quantity=item.bonus_quantity,
            unit_cost=item.unit_cost,
            sale_price=item.sale_price,
            note=item.note,
            total_amount=item.total_amount,
            medicine_name=item.medicine.name,
            purchased_by_name=item.purchased_by.full_name if item.purchased_by else None,
        )

    def _serialize_sale_item(self, item: PharmacySaleItem) -> PharmacySaleItemRead:
        return PharmacySaleItemRead(
            id=item.id,
            medicine_id=item.medicine_id,
            source_visit_order_id=item.source_visit_order_id,
            medicine_name=item.medicine.name,
            batch_no=item.batch_no,
            expiry_date=item.expiry_date,
            quantity=item.quantity,
            returned_quantity=item.returned_quantity,
            available_return_quantity=max(Decimal("0"), item.quantity - item.returned_quantity),
            unit_price=item.unit_price,
            line_total=item.line_total,
            note=item.note,
        )

    def _serialize_sale(self, item: PharmacySale) -> PharmacySaleRead:
        patient_name = None
        if item.patient:
            patient_name = f"{item.patient.first_name} {item.patient.last_name}".strip()
        elif item.customer and item.customer.patient:
            patient_name = f"{item.customer.patient.first_name} {item.customer.patient.last_name}".strip()
        return PharmacySaleRead(
            id=item.id,
            customer_id=item.customer_id,
            patient_id=item.patient_id,
            source_visit_id=item.source_visit_id,
            sale_number=item.sale_number,
            sale_date=item.sale_date,
            customer_name=item.customer.name,
            patient_name=patient_name,
            subtotal=item.subtotal,
            discount_amount=item.discount_amount,
            return_amount=item.return_amount,
            net_payable=item.net_payable,
            status=item.status,
            note=item.note,
            sold_by_name=item.sold_by.full_name if item.sold_by else None,
            items=[self._serialize_sale_item(sale_item) for sale_item in item.items if sale_item.is_active],
        )

    def _serialize_return(self, item: PharmacySaleReturn) -> PharmacySaleReturnRead:
        return PharmacySaleReturnRead(
            id=item.id,
            sale_id=item.sale_id,
            sale_item_id=item.sale_item_id,
            customer_id=item.customer_id,
            medicine_id=item.medicine_id,
            return_number=item.return_number,
            sale_number=item.sale.sale_number,
            customer_name=item.customer.name,
            medicine_name=item.medicine.name,
            batch_no=item.batch_no,
            expiry_date=item.expiry_date,
            returned_at=item.returned_at,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_amount=item.total_amount,
            note=item.note,
            returned_by_name=item.returned_by.full_name if item.returned_by else None,
        )

    def _serialize_setting(self, item: PharmacyInvestigationSetting) -> PharmacyInvestigationSettingRead:
        return PharmacyInvestigationSettingRead(
            id=item.id,
            category_name=item.category_name,
            test_name=item.test_name,
            code=item.code,
            service_area=item.service_area,
            fee=item.fee,
            room_number=item.room_number,
            normal_range=item.normal_range,
            unit=item.unit,
            description=item.description,
            specimen_type=item.specimen_type,
            turnaround_time=item.turnaround_time,
            report_header=item.report_header,
            report_template=item.report_template,
            report_note_template=item.report_note_template,
            requires_report=item.requires_report,
            is_active=item.is_active,
        )

    def _serialize_investigation_item(self, item: PharmacyInvestigationItem) -> PharmacyInvestigationItemRead:
        return PharmacyInvestigationItemRead(
            id=item.id,
            setting_id=item.setting_id,
            source_visit_order_id=item.source_visit_order_id,
            test_name=item.setting.test_name,
            setting_code=item.setting.code,
            category_name=item.setting.category_name,
            service_area=item.setting.service_area,
            status=item.status,
            fee=item.fee,
            result_text=item.result_text,
            note=item.note,
            normal_range=item.normal_range_snapshot,
            unit=item.unit_snapshot,
            description=item.description_snapshot,
            report_header=item.report_header_snapshot,
            report_template=item.report_template_snapshot,
            report_note_template=item.report_note_template_snapshot,
            requires_report=item.requires_report,
        )

    def _serialize_investigation(self, item: PharmacyInvestigation) -> PharmacyInvestigationRead:
        patient_name = None
        patient_number = None
        if item.patient:
            patient_name = f"{item.patient.first_name} {item.patient.last_name}".strip()
            patient_number = item.patient.patient_number
        elif item.customer and item.customer.patient:
            patient_name = f"{item.customer.patient.first_name} {item.customer.patient.last_name}".strip()
            patient_number = item.customer.patient.patient_number
        active_items = [investigation_item for investigation_item in item.items if investigation_item.is_active]
        first_item = active_items[0] if active_items else None
        legacy_setting = item.setting if not active_items else None
        return PharmacyInvestigationRead(
            id=item.id,
            customer_id=item.customer_id,
            patient_id=item.patient_id,
            source_visit_id=item.source_visit_id,
            investigation_number=item.investigation_number,
            ordered_at=item.ordered_at,
            status=item.status,
            fee=item.fee,
            discount_amount=item.discount_amount,
            total_amount=item.total_amount,
            report_note=item.report_note,
            note=item.note,
            report_title=item.report_title,
            report_footer_note=item.report_footer_note,
            printable_schema=item.printable_schema,
            customer_name=item.customer.name if item.customer else None,
            patient_name=patient_name,
            patient_number=patient_number,
            setting_name=first_item.setting.test_name if first_item else (legacy_setting.test_name if legacy_setting else None),
            setting_code=first_item.setting.code if first_item else (legacy_setting.code if legacy_setting else None),
            category_name=first_item.setting.category_name if first_item else (legacy_setting.category_name if legacy_setting else None),
            service_area=first_item.setting.service_area if first_item else (legacy_setting.service_area if legacy_setting else None),
            test_count=len(active_items) if active_items else (1 if legacy_setting else 0),
            items=[self._serialize_investigation_item(investigation_item) for investigation_item in active_items],
        )

    def list_medicine_types(self, actor: User, *, page: int, page_size: int, q: str | None) -> PaginatedResponse[PharmacyMedicineTypeRead]:
        stmt = select(PharmacyMedicineType).where(PharmacyMedicineType.is_active.is_(True)).order_by(PharmacyMedicineType.name.asc())
        if actor.branch_id:
            stmt = stmt.where(or_(PharmacyMedicineType.branch_id == actor.branch_id, PharmacyMedicineType.branch_id.is_(None)))
        if q:
            stmt = stmt.where(func.lower(PharmacyMedicineType.name).like(f"%{q.strip().lower()}%"))
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_type(item) for item in items]
        return meta

    def create_medicine_type(self, payload: PharmacyMedicineTypeCreate, actor: User, context: dict[str, str | None]) -> PharmacyMedicineTypeRead:
        self._ensure_unique_name(PharmacyMedicineType, payload.name)
        item = PharmacyMedicineType(branch_id=actor.branch_id, name=payload.name.strip(), description=payload.description, created_by=actor.id, updated_by=actor.id)
        self.repository.create(item)
        self._commit_and_log(actor=actor, action="pharmacy.medicine_type.create", entity_type="pharmacy_medicine_type", entity_id=str(item.id), detail={"name": item.name}, context=context)
        self.db.refresh(item)
        return self._serialize_type(item)

    def get_medicine_type(self, entity_id, actor: User) -> PharmacyMedicineTypeRead:
        item = self.repository.get_medicine_type(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "medicine_type_not_found", "Medicine type not found")
        self._ensure_branch_scope(item, actor)
        return self._serialize_type(item)

    def update_medicine_type(self, entity_id, payload: PharmacyMedicineTypeUpdate, actor: User, context: dict[str, str | None]) -> PharmacyMedicineTypeRead:
        item = self.repository.get_medicine_type(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "medicine_type_not_found", "Medicine type not found")
        self._ensure_branch_scope(item, actor)
        self._ensure_unique_name(PharmacyMedicineType, payload.name, exclude_id=item.id)
        item.name = payload.name.strip()
        item.description = payload.description
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.medicine_type.update", entity_type="pharmacy_medicine_type", entity_id=str(item.id), detail={"name": item.name}, context=context)
        self.db.refresh(item)
        return self._serialize_type(item)

    def delete_medicine_type(self, entity_id, actor: User, context: dict[str, str | None]) -> None:
        item = self.repository.get_medicine_type(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "medicine_type_not_found", "Medicine type not found")
        self._ensure_branch_scope(item, actor)
        item.is_active = False
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.medicine_type.delete", entity_type="pharmacy_medicine_type", entity_id=str(item.id), detail={"name": item.name}, context=context)

    def list_generics(self, actor: User, *, page: int, page_size: int, q: str | None) -> PaginatedResponse[PharmacyGenericRead]:
        stmt = select(PharmacyGeneric).where(PharmacyGeneric.is_active.is_(True)).order_by(PharmacyGeneric.name.asc())
        if actor.branch_id:
            stmt = stmt.where(or_(PharmacyGeneric.branch_id == actor.branch_id, PharmacyGeneric.branch_id.is_(None)))
        if q:
            stmt = stmt.where(func.lower(PharmacyGeneric.name).like(f"%{q.strip().lower()}%"))
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_generic(item) for item in items]
        return meta

    def create_generic(self, payload: PharmacyGenericCreate, actor: User, context: dict[str, str | None]) -> PharmacyGenericRead:
        self._ensure_unique_name(PharmacyGeneric, payload.name)
        item = PharmacyGeneric(branch_id=actor.branch_id, name=payload.name.strip(), description=payload.description, created_by=actor.id, updated_by=actor.id)
        self.repository.create(item)
        self._commit_and_log(actor=actor, action="pharmacy.generic.create", entity_type="pharmacy_generic", entity_id=str(item.id), detail={"name": item.name}, context=context)
        self.db.refresh(item)
        return self._serialize_generic(item)

    def get_generic(self, entity_id, actor: User) -> PharmacyGenericRead:
        item = self.repository.get_generic(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "generic_not_found", "Generic information not found")
        self._ensure_branch_scope(item, actor)
        return self._serialize_generic(item)

    def update_generic(self, entity_id, payload: PharmacyGenericUpdate, actor: User, context: dict[str, str | None]) -> PharmacyGenericRead:
        item = self.repository.get_generic(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "generic_not_found", "Generic information not found")
        self._ensure_branch_scope(item, actor)
        self._ensure_unique_name(PharmacyGeneric, payload.name, exclude_id=item.id)
        item.name = payload.name.strip()
        item.description = payload.description
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.generic.update", entity_type="pharmacy_generic", entity_id=str(item.id), detail={"name": item.name}, context=context)
        self.db.refresh(item)
        return self._serialize_generic(item)

    def delete_generic(self, entity_id, actor: User, context: dict[str, str | None]) -> None:
        item = self.repository.get_generic(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "generic_not_found", "Generic information not found")
        self._ensure_branch_scope(item, actor)
        item.is_active = False
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.generic.delete", entity_type="pharmacy_generic", entity_id=str(item.id), detail={"name": item.name}, context=context)

    def list_companies(self, actor: User, *, page: int, page_size: int, q: str | None) -> PaginatedResponse[PharmacyCompanyRead]:
        stmt = select(PharmacyCompany).where(PharmacyCompany.is_active.is_(True)).order_by(PharmacyCompany.name.asc())
        if actor.branch_id:
            stmt = stmt.where(or_(PharmacyCompany.branch_id == actor.branch_id, PharmacyCompany.branch_id.is_(None)))
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(PharmacyCompany.name).like(pattern),
                    func.lower(func.coalesce(PharmacyCompany.contact_person, "")).like(pattern),
                    func.lower(func.coalesce(PharmacyCompany.phone, "")).like(pattern),
                )
            )
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_company(item) for item in items]
        return meta

    def create_company(self, payload: PharmacyCompanyCreate, actor: User, context: dict[str, str | None]) -> PharmacyCompanyRead:
        self._ensure_unique_name(PharmacyCompany, payload.name)
        item = PharmacyCompany(branch_id=actor.branch_id, **payload.model_dump(), name=payload.name.strip(), created_by=actor.id, updated_by=actor.id)
        self.repository.create(item)
        self._commit_and_log(actor=actor, action="pharmacy.company.create", entity_type="pharmacy_company", entity_id=str(item.id), detail={"name": item.name}, context=context)
        self.db.refresh(item)
        return self._serialize_company(item)

    def get_company(self, entity_id, actor: User) -> PharmacyCompanyRead:
        item = self.repository.get_company(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "company_not_found", "Medicine company not found")
        self._ensure_branch_scope(item, actor)
        return self._serialize_company(item)

    def update_company(self, entity_id, payload: PharmacyCompanyUpdate, actor: User, context: dict[str, str | None]) -> PharmacyCompanyRead:
        item = self.repository.get_company(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "company_not_found", "Medicine company not found")
        self._ensure_branch_scope(item, actor)
        self._ensure_unique_name(PharmacyCompany, payload.name, exclude_id=item.id)
        for key, value in payload.model_dump().items():
            setattr(item, key, value.strip() if isinstance(value, str) and key == "name" else value)
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.company.update", entity_type="pharmacy_company", entity_id=str(item.id), detail={"name": item.name}, context=context)
        self.db.refresh(item)
        return self._serialize_company(item)

    def delete_company(self, entity_id, actor: User, context: dict[str, str | None]) -> None:
        item = self.repository.get_company(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "company_not_found", "Medicine company not found")
        self._ensure_branch_scope(item, actor)
        item.is_active = False
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.company.delete", entity_type="pharmacy_company", entity_id=str(item.id), detail={"name": item.name}, context=context)

    def list_customers(self, actor: User, *, page: int, page_size: int, q: str | None) -> PaginatedResponse[PharmacyCustomerRead]:
        stmt = select(PharmacyCustomer).options(joinedload(PharmacyCustomer.patient)).where(PharmacyCustomer.is_active.is_(True)).order_by(PharmacyCustomer.created_at.desc())
        if actor.branch_id:
            stmt = stmt.where(PharmacyCustomer.branch_id == actor.branch_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(PharmacyCustomer.customer_number).like(pattern),
                    func.lower(PharmacyCustomer.name).like(pattern),
                    func.lower(func.coalesce(PharmacyCustomer.phone, "")).like(pattern),
                    func.lower(func.coalesce(PharmacyCustomer.email, "")).like(pattern),
                )
            )
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_customer(item) for item in items]
        return meta

    def create_customer(self, payload: PharmacyCustomerCreate, actor: User, context: dict[str, str | None]) -> PharmacyCustomerRead:
        item = PharmacyCustomer(
            branch_id=actor.branch_id,
            customer_number=self._generate_number(PharmacyCustomer, "CUS"),
            **payload.model_dump(),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(item)
        self._commit_and_log(actor=actor, action="pharmacy.customer.create", entity_type="pharmacy_customer", entity_id=str(item.id), detail={"name": item.name}, context=context)
        self.db.refresh(item)
        item = self.repository.get_customer(item.id)
        return self._serialize_customer(item)

    def get_customer(self, entity_id, actor: User) -> PharmacyCustomerRead:
        item = self.repository.get_customer(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "customer_not_found", "Customer information not found")
        self._ensure_branch_scope(item, actor)
        return self._serialize_customer(item)

    def update_customer(self, entity_id, payload: PharmacyCustomerUpdate, actor: User, context: dict[str, str | None]) -> PharmacyCustomerRead:
        item = self.repository.get_customer(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "customer_not_found", "Customer information not found")
        self._ensure_branch_scope(item, actor)
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.customer.update", entity_type="pharmacy_customer", entity_id=str(item.id), detail={"name": item.name}, context=context)
        self.db.refresh(item)
        item = self.repository.get_customer(item.id)
        return self._serialize_customer(item)

    def delete_customer(self, entity_id, actor: User, context: dict[str, str | None]) -> None:
        item = self.repository.get_customer(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "customer_not_found", "Customer information not found")
        self._ensure_branch_scope(item, actor)
        item.is_active = False
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.customer.delete", entity_type="pharmacy_customer", entity_id=str(item.id), detail={"name": item.name}, context=context)

    def list_medicines(
        self,
        actor: User,
        *,
        page: int,
        page_size: int,
        q: str | None,
        medicine_type_id=None,
        generic_id=None,
        company_id=None,
        low_stock: bool = False,
    ) -> PaginatedResponse[PharmacyMedicineRead]:
        stmt = (
            select(PharmacyMedicine)
            .options(
                joinedload(PharmacyMedicine.medicine_type),
                joinedload(PharmacyMedicine.generic),
                joinedload(PharmacyMedicine.company),
            )
            .where(PharmacyMedicine.is_active.is_(True))
            .order_by(PharmacyMedicine.name.asc())
        )
        if actor.branch_id:
            stmt = stmt.where(PharmacyMedicine.branch_id == actor.branch_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(PharmacyMedicine.name).like(pattern),
                    func.lower(func.coalesce(PharmacyMedicine.strength, "")).like(pattern),
                    func.lower(func.coalesce(PharmacyMedicine.sku, "")).like(pattern),
                )
            )
        if medicine_type_id:
            stmt = stmt.where(PharmacyMedicine.medicine_type_id == medicine_type_id)
        if generic_id:
            stmt = stmt.where(PharmacyMedicine.generic_id == generic_id)
        if company_id:
            stmt = stmt.where(PharmacyMedicine.company_id == company_id)
        if low_stock:
            stmt = stmt.where(PharmacyMedicine.stock_quantity <= PharmacyMedicine.reorder_level)
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_medicine(item) for item in items]
        return meta

    def _ensure_medicine_uniqueness(self, payload: PharmacyMedicineCreate | PharmacyMedicineUpdate, *, exclude_id=None):
        stmt = select(PharmacyMedicine).where(
            PharmacyMedicine.is_active.is_(True),
            func.lower(PharmacyMedicine.name) == payload.name.strip().lower(),
            PharmacyMedicine.company_id == payload.company_id,
            func.lower(func.coalesce(PharmacyMedicine.strength, "")) == (payload.strength or "").strip().lower(),
        )
        if exclude_id:
            stmt = stmt.where(PharmacyMedicine.id != exclude_id)
        if self.db.scalar(stmt):
            raise AppException(409, "duplicate_medicine", "Medicine information already exists for this company and strength")
        if payload.sku:
            sku_stmt = select(PharmacyMedicine).where(PharmacyMedicine.sku == payload.sku, PharmacyMedicine.is_active.is_(True))
            if exclude_id:
                sku_stmt = sku_stmt.where(PharmacyMedicine.id != exclude_id)
            if self.db.scalar(sku_stmt):
                raise AppException(409, "duplicate_medicine_sku", "Medicine SKU already exists")

    def create_medicine(self, payload: PharmacyMedicineCreate, actor: User, context: dict[str, str | None]) -> PharmacyMedicineRead:
        self._ensure_medicine_uniqueness(payload)
        item = PharmacyMedicine(branch_id=actor.branch_id, stock_quantity=Decimal("0"), **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.repository.create(item)
        self._commit_and_log(actor=actor, action="pharmacy.medicine.create", entity_type="pharmacy_medicine", entity_id=str(item.id), detail={"name": item.name}, context=context)
        self.db.refresh(item)
        item = self.repository.get_medicine(item.id)
        return self._serialize_medicine(item)

    def get_medicine(self, entity_id, actor: User) -> PharmacyMedicineRead:
        item = self.repository.get_medicine(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "medicine_not_found", "Medicine information not found")
        self._ensure_branch_scope(item, actor)
        return self._serialize_medicine(item)

    def update_medicine(self, entity_id, payload: PharmacyMedicineUpdate, actor: User, context: dict[str, str | None]) -> PharmacyMedicineRead:
        item = self.repository.get_medicine(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "medicine_not_found", "Medicine information not found")
        self._ensure_branch_scope(item, actor)
        self._ensure_medicine_uniqueness(payload, exclude_id=item.id)
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.medicine.update", entity_type="pharmacy_medicine", entity_id=str(item.id), detail={"name": item.name}, context=context)
        self.db.refresh(item)
        item = self.repository.get_medicine(item.id)
        return self._serialize_medicine(item)

    def delete_medicine(self, entity_id, actor: User, context: dict[str, str | None]) -> None:
        item = self.repository.get_medicine(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "medicine_not_found", "Medicine information not found")
        self._ensure_branch_scope(item, actor)
        if item.stock_quantity > 0:
            raise AppException(409, "medicine_has_stock", "Medicine with remaining stock cannot be deleted")
        item.is_active = False
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.medicine.delete", entity_type="pharmacy_medicine", entity_id=str(item.id), detail={"name": item.name}, context=context)

    def list_purchases(self, actor: User, *, page: int, page_size: int, q: str | None, medicine_id=None) -> PaginatedResponse[PharmacyPurchaseRead]:
        stmt = (
            select(PharmacyPurchase)
            .options(joinedload(PharmacyPurchase.medicine), joinedload(PharmacyPurchase.purchased_by))
            .where(PharmacyPurchase.is_active.is_(True))
            .order_by(PharmacyPurchase.purchase_date.desc(), PharmacyPurchase.created_at.desc())
        )
        if actor.branch_id:
            stmt = stmt.where(PharmacyPurchase.branch_id == actor.branch_id)
        if medicine_id:
            stmt = stmt.where(PharmacyPurchase.medicine_id == medicine_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.join(PharmacyPurchase.medicine).where(
                or_(
                    func.lower(PharmacyPurchase.purchase_number).like(pattern),
                    func.lower(func.coalesce(PharmacyPurchase.invoice_number, "")).like(pattern),
                    func.lower(func.coalesce(PharmacyPurchase.supplier_name, "")).like(pattern),
                    func.lower(PharmacyMedicine.name).like(pattern),
                )
            )
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_purchase(item) for item in items]
        return meta

    def create_purchase(self, payload: PharmacyPurchaseCreate, actor: User, context: dict[str, str | None]) -> PharmacyPurchaseRead:
        self._validate_purchase_payload(payload)
        medicine = self.repository.get_medicine(payload.medicine_id, for_update=True)
        if not medicine or not medicine.is_active:
            raise AppException(404, "medicine_not_found", "Medicine information not found")
        self._ensure_branch_scope(medicine, actor)
        effective_qty = payload.quantity + payload.bonus_quantity
        total_amount = payload.quantity * payload.unit_cost
        item = PharmacyPurchase(
            branch_id=actor.branch_id,
            purchase_number=self._generate_number(PharmacyPurchase, "PUR"),
            total_amount=total_amount,
            purchased_by_user_id=actor.id,
            **payload.model_dump(),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(item)
        self._change_stock(
            medicine=medicine,
            delta=effective_qty,
            actor=actor,
            movement_type="purchase_in",
            reference_type="purchase",
            reference_id=item.id,
            batch_no=payload.batch_no,
            expiry_date=payload.expiry_date,
            unit_cost=payload.unit_cost,
            sale_price=payload.sale_price,
            note=payload.note,
        )
        medicine.purchase_price = payload.unit_cost
        if payload.sale_price is not None:
            medicine.sale_price = payload.sale_price
        self._commit_and_log(actor=actor, action="pharmacy.purchase.create", entity_type="pharmacy_purchase", entity_id=str(item.id), detail={"purchase_number": item.purchase_number, "medicine": medicine.name}, context=context)
        self.db.refresh(item)
        item = self.repository.get_purchase(item.id)
        return self._serialize_purchase(item)

    def get_purchase(self, entity_id, actor: User) -> PharmacyPurchaseRead:
        item = self.repository.get_purchase(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "purchase_not_found", "Purchase history record not found")
        self._ensure_branch_scope(item, actor)
        return self._serialize_purchase(item)

    def update_purchase(self, entity_id, payload: PharmacyPurchaseUpdate, actor: User, context: dict[str, str | None]) -> PharmacyPurchaseRead:
        self._validate_purchase_payload(payload)
        item = self.repository.get_purchase(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "purchase_not_found", "Purchase history record not found")
        self._ensure_branch_scope(item, actor)
        medicine = self.repository.get_medicine(payload.medicine_id, for_update=True)
        if not medicine or not medicine.is_active:
            raise AppException(404, "medicine_not_found", "Medicine information not found")
        old_medicine = item.medicine
        old_effective = Decimal(item.quantity) + Decimal(item.bonus_quantity)
        new_effective = payload.quantity + payload.bonus_quantity
        if old_medicine.id != medicine.id:
            self._change_stock(
                medicine=old_medicine,
                delta=-old_effective,
                actor=actor,
                movement_type="purchase_reversal_out",
                reference_type="purchase",
                reference_id=item.id,
                batch_no=item.batch_no,
                expiry_date=item.expiry_date,
                unit_cost=item.unit_cost,
                sale_price=item.sale_price,
                note="Purchase reassigned to another medicine",
            )
            self._change_stock(
                medicine=medicine,
                delta=new_effective,
                actor=actor,
                movement_type="purchase_adjustment_in",
                reference_type="purchase",
                reference_id=item.id,
                batch_no=payload.batch_no,
                expiry_date=payload.expiry_date,
                unit_cost=payload.unit_cost,
                sale_price=payload.sale_price,
                note=payload.note,
            )
        else:
            delta = new_effective - old_effective
            if delta != 0:
                self._change_stock(
                    medicine=medicine,
                    delta=delta,
                    actor=actor,
                    movement_type="purchase_adjustment",
                    reference_type="purchase",
                    reference_id=item.id,
                    batch_no=payload.batch_no,
                    expiry_date=payload.expiry_date,
                    unit_cost=payload.unit_cost,
                    sale_price=payload.sale_price,
                    note=payload.note,
                )
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        item.total_amount = payload.quantity * payload.unit_cost
        item.updated_by = actor.id
        medicine.purchase_price = payload.unit_cost
        if payload.sale_price is not None:
            medicine.sale_price = payload.sale_price
        medicine.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.purchase.update", entity_type="pharmacy_purchase", entity_id=str(item.id), detail={"purchase_number": item.purchase_number}, context=context)
        self.db.refresh(item)
        item = self.repository.get_purchase(item.id)
        return self._serialize_purchase(item)

    def delete_purchase(self, entity_id, actor: User, context: dict[str, str | None]) -> None:
        item = self.repository.get_purchase(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "purchase_not_found", "Purchase history record not found")
        self._ensure_branch_scope(item, actor)
        effective_qty = Decimal(item.quantity) + Decimal(item.bonus_quantity)
        self._change_stock(
            medicine=item.medicine,
            delta=-effective_qty,
            actor=actor,
            movement_type="purchase_delete_out",
            reference_type="purchase",
            reference_id=item.id,
            batch_no=item.batch_no,
            expiry_date=item.expiry_date,
            unit_cost=item.unit_cost,
            sale_price=item.sale_price,
            note="Purchase deleted",
        )
        item.is_active = False
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.purchase.delete", entity_type="pharmacy_purchase", entity_id=str(item.id), detail={"purchase_number": item.purchase_number}, context=context)

    def _resolve_sale_items(self, items: list[PharmacySaleItemWrite], actor: User, *, sale_date: date) -> tuple[list[tuple[PharmacyMedicine, Decimal, Decimal, str | None, str | None, date | None, object | None]], Decimal]:
        resolved: list[tuple[PharmacyMedicine, Decimal, Decimal, str | None, str | None, date | None, object | None]] = []
        subtotal = Decimal("0")
        seen: set[tuple[str, str | None]] = set()
        for line in items:
            batch_no = self._normalize_text(line.batch_no)
            duplicate_key = (str(line.medicine_id), batch_no)
            if duplicate_key in seen:
                raise AppException(409, "duplicate_sale_item", "Duplicate medicine line detected in the same sale")
            seen.add(duplicate_key)
            source_order = None
            if line.source_visit_order_id:
                if self.repository.has_sale_item_for_opd_order(line.source_visit_order_id):
                    raise AppException(409, "sale_order_duplicate", "One or more prescription lines are already linked to a sale")
                source_order = self.opd_repository.get_order(line.source_visit_order_id)
                if not source_order:
                    raise AppException(404, "opd_order_not_found", "Prescription source order not found")
                if source_order.order_type != "prescription":
                    raise AppException(400, "invalid_opd_order_type", "Only prescription orders can be linked to pharmacy sales")
            medicine = self.repository.get_medicine(line.medicine_id, for_update=True)
            if not medicine or not medicine.is_active:
                raise AppException(404, "medicine_not_found", "Medicine information not found")
            self._ensure_branch_scope(medicine, actor)
            source_purchase = self.repository.get_latest_purchase_for_medicine(medicine.id, batch_no=batch_no)
            if batch_no and not source_purchase:
                raise AppException(409, "batch_not_found", f"Batch {batch_no} is not available for {medicine.name}")
            expiry_date = line.expiry_date or (source_purchase.expiry_date if source_purchase else None)
            resolved_batch = batch_no or (source_purchase.batch_no if source_purchase else None)
            if expiry_date and expiry_date < sale_date:
                raise AppException(409, "expired_batch", f"{medicine.name} batch is expired for the sale date")
            unit_price = line.unit_price if line.unit_price is not None else medicine.sale_price
            if medicine.stock_quantity < line.quantity:
                raise AppException(409, "insufficient_stock", f"Insufficient stock for {medicine.name}")
            subtotal += line.quantity * unit_price
            resolved.append((medicine, line.quantity, unit_price, line.note, resolved_batch, expiry_date, source_order))
        return resolved, subtotal

    def _apply_sale_status(self, sale: PharmacySale):
        active_items = [item for item in sale.items if item.is_active]
        if not active_items:
            sale.status = "cancelled"
            return
        total_qty = sum(Decimal(item.quantity) for item in active_items)
        total_returned = sum(Decimal(item.returned_quantity) for item in active_items)
        if total_returned == 0:
            sale.status = "sold"
        elif total_returned >= total_qty:
            sale.status = "returned"
        else:
            sale.status = "partially_returned"
        sale.net_payable = max(Decimal("0"), Decimal(sale.subtotal) - Decimal(sale.discount_amount) - Decimal(sale.return_amount))

    def list_sales(self, actor: User, *, page: int, page_size: int, q: str | None, customer_id=None, status: str | None = None) -> PaginatedResponse[PharmacySaleRead]:
        stmt = (
            select(PharmacySale)
            .options(
                joinedload(PharmacySale.customer).joinedload(PharmacyCustomer.patient),
                joinedload(PharmacySale.patient),
                joinedload(PharmacySale.sold_by),
                joinedload(PharmacySale.items).joinedload(PharmacySaleItem.medicine),
                joinedload(PharmacySale.returns),
            )
            .where(PharmacySale.is_active.is_(True))
            .order_by(PharmacySale.sale_date.desc(), PharmacySale.created_at.desc())
        )
        if actor.branch_id:
            stmt = stmt.where(PharmacySale.branch_id == actor.branch_id)
        if customer_id:
            stmt = stmt.where(PharmacySale.customer_id == customer_id)
        if status:
            stmt = stmt.where(PharmacySale.status == status)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.join(PharmacySale.customer).where(
                or_(
                    func.lower(PharmacySale.sale_number).like(pattern),
                    func.lower(PharmacyCustomer.name).like(pattern),
                )
            )
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_sale(item) for item in items]
        return meta

    def create_sale(self, payload: PharmacySaleCreate, actor: User, context: dict[str, str | None]) -> PharmacySaleRead:
        customer = self._resolve_sale_customer(customer_id=payload.customer_id, patient_id=payload.patient_id, actor=actor)
        resolved_items, subtotal = self._resolve_sale_items(payload.items, actor, sale_date=payload.sale_date)
        discount = min(Decimal(payload.discount_amount), subtotal)
        sale = PharmacySale(
            branch_id=actor.branch_id,
            customer_id=customer.id,
            patient_id=payload.patient_id or customer.patient_id,
            source_visit_id=payload.source_visit_id,
            sale_number=self._generate_number(PharmacySale, "SAL"),
            sale_date=payload.sale_date,
            subtotal=subtotal,
            discount_amount=discount,
            return_amount=Decimal("0"),
            net_payable=max(Decimal("0"), subtotal - discount),
            status="sold",
            note=payload.note,
            sold_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(sale)
        for medicine, quantity, unit_price, note, batch_no, expiry_date, source_order in resolved_items:
            sale_item = PharmacySaleItem(
                id=uuid4(),
                sale_id=sale.id,
                medicine_id=medicine.id,
                source_visit_order_id=source_order.id if source_order else None,
                batch_no=batch_no,
                expiry_date=expiry_date,
                quantity=quantity,
                returned_quantity=Decimal("0"),
                unit_price=unit_price,
                line_total=quantity * unit_price,
                note=note,
                created_by=actor.id,
                updated_by=actor.id,
            )
            sale.items.append(sale_item)
            self._change_stock(
                medicine=medicine,
                delta=-quantity,
                actor=actor,
                movement_type="sale_out",
                reference_type="sale_item",
                reference_id=sale_item.id,
                batch_no=batch_no,
                expiry_date=expiry_date,
                sale_price=unit_price,
                note=note,
            )
            if source_order:
                source_order.status = "completed"
                source_order.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.sale.create", entity_type="pharmacy_sale", entity_id=str(sale.id), detail={"sale_number": sale.sale_number, "subtotal": str(sale.subtotal)}, context=context)
        self.db.refresh(sale)
        sale = self.repository.get_sale(sale.id)
        return self._serialize_sale(sale)

    def get_sale(self, entity_id, actor: User) -> PharmacySaleRead:
        sale = self.repository.get_sale(entity_id)
        if not sale or not sale.is_active:
            raise AppException(404, "sale_not_found", "Medicine sale not found")
        self._ensure_branch_scope(sale, actor)
        return self._serialize_sale(sale)

    def update_sale(self, entity_id, payload: PharmacySaleUpdate, actor: User, context: dict[str, str | None]) -> PharmacySaleRead:
        sale = self.repository.get_sale(entity_id)
        if not sale or not sale.is_active:
            raise AppException(404, "sale_not_found", "Medicine sale not found")
        self._ensure_branch_scope(sale, actor)
        active_returns = [item for item in sale.returns if item.is_active]
        if active_returns:
            raise AppException(409, "sale_has_returns", "Sale with returns cannot be edited")
        for line in sale.items:
            if line.is_active:
                self._change_stock(
                    medicine=line.medicine,
                    delta=Decimal(line.quantity),
                    actor=actor,
                    movement_type="sale_reversal_in",
                    reference_type="sale_item",
                    reference_id=line.id,
                    batch_no=line.batch_no,
                    expiry_date=line.expiry_date,
                    sale_price=line.unit_price,
                    note="Sale updated",
                )
                line.is_active = False
                line.updated_by = actor.id
        customer = self._resolve_sale_customer(customer_id=payload.customer_id, patient_id=payload.patient_id, actor=actor)
        resolved_items, subtotal = self._resolve_sale_items(payload.items, actor, sale_date=payload.sale_date)
        discount = min(Decimal(payload.discount_amount), subtotal)
        sale.customer_id = customer.id
        sale.patient_id = payload.patient_id or customer.patient_id
        sale.source_visit_id = payload.source_visit_id
        sale.sale_date = payload.sale_date
        sale.subtotal = subtotal
        sale.discount_amount = discount
        sale.note = payload.note
        sale.return_amount = Decimal("0")
        sale.updated_by = actor.id
        for medicine, quantity, unit_price, note, batch_no, expiry_date, source_order in resolved_items:
            sale_item = PharmacySaleItem(
                id=uuid4(),
                sale_id=sale.id,
                medicine_id=medicine.id,
                source_visit_order_id=source_order.id if source_order else None,
                batch_no=batch_no,
                expiry_date=expiry_date,
                quantity=quantity,
                returned_quantity=Decimal("0"),
                unit_price=unit_price,
                line_total=quantity * unit_price,
                note=note,
                created_by=actor.id,
                updated_by=actor.id,
            )
            sale.items.append(sale_item)
            self._change_stock(
                medicine=medicine,
                delta=-quantity,
                actor=actor,
                movement_type="sale_out",
                reference_type="sale_item",
                reference_id=sale_item.id,
                batch_no=batch_no,
                expiry_date=expiry_date,
                sale_price=unit_price,
                note=note,
            )
            if source_order:
                source_order.status = "completed"
                source_order.updated_by = actor.id
        self._apply_sale_status(sale)
        self._commit_and_log(actor=actor, action="pharmacy.sale.update", entity_type="pharmacy_sale", entity_id=str(sale.id), detail={"sale_number": sale.sale_number}, context=context)
        self.db.refresh(sale)
        sale = self.repository.get_sale(sale.id)
        return self._serialize_sale(sale)

    def delete_sale(self, entity_id, actor: User, context: dict[str, str | None]) -> None:
        sale = self.repository.get_sale(entity_id)
        if not sale or not sale.is_active:
            raise AppException(404, "sale_not_found", "Medicine sale not found")
        self._ensure_branch_scope(sale, actor)
        active_returns = [item for item in sale.returns if item.is_active]
        if active_returns:
            raise AppException(409, "sale_has_returns", "Sale with returns cannot be deleted")
        for line in sale.items:
            if line.is_active:
                self._change_stock(
                    medicine=line.medicine,
                    delta=Decimal(line.quantity),
                    actor=actor,
                    movement_type="sale_delete_reversal_in",
                    reference_type="sale_item",
                    reference_id=line.id,
                    batch_no=line.batch_no,
                    expiry_date=line.expiry_date,
                    sale_price=line.unit_price,
                    note="Sale deleted",
                )
                line.is_active = False
                line.updated_by = actor.id
        sale.status = "cancelled"
        sale.is_active = False
        sale.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.sale.delete", entity_type="pharmacy_sale", entity_id=str(sale.id), detail={"sale_number": sale.sale_number}, context=context)

    def list_returns(self, actor: User, *, page: int, page_size: int, q: str | None, sale_id=None) -> PaginatedResponse[PharmacySaleReturnRead]:
        stmt = (
            select(PharmacySaleReturn)
            .options(
                joinedload(PharmacySaleReturn.sale),
                joinedload(PharmacySaleReturn.customer),
                joinedload(PharmacySaleReturn.medicine),
                joinedload(PharmacySaleReturn.returned_by),
            )
            .where(PharmacySaleReturn.is_active.is_(True))
            .order_by(PharmacySaleReturn.returned_at.desc(), PharmacySaleReturn.created_at.desc())
        )
        if actor.branch_id:
            stmt = stmt.where(PharmacySaleReturn.branch_id == actor.branch_id)
        if sale_id:
            stmt = stmt.where(PharmacySaleReturn.sale_id == sale_id)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.join(PharmacySaleReturn.sale).join(PharmacySaleReturn.customer).join(PharmacySaleReturn.medicine).where(
                or_(
                    func.lower(PharmacySaleReturn.return_number).like(pattern),
                    func.lower(PharmacySale.sale_number).like(pattern),
                    func.lower(PharmacyCustomer.name).like(pattern),
                    func.lower(PharmacyMedicine.name).like(pattern),
                )
            )
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_return(item) for item in items]
        return meta

    def create_return(self, payload: PharmacySaleReturnCreate, actor: User, context: dict[str, str | None]) -> PharmacySaleReturnRead:
        sale = self.repository.get_sale(payload.sale_id)
        if not sale or not sale.is_active:
            raise AppException(404, "sale_not_found", "Medicine sale not found")
        self._ensure_branch_scope(sale, actor)
        sale_item = next((item for item in sale.items if item.id == payload.sale_item_id and item.is_active), None)
        if not sale_item:
            raise AppException(404, "sale_item_not_found", "Sale item not found")
        available = Decimal(sale_item.quantity) - Decimal(sale_item.returned_quantity)
        if payload.quantity > available:
            raise AppException(409, "return_exceeds_sold_quantity", "Return quantity exceeds sold quantity")
        if payload.returned_at < sale.sale_date:
            raise AppException(422, "invalid_return_date", "Return date cannot be earlier than sale date")
        sale_item.returned_quantity = Decimal(sale_item.returned_quantity) + payload.quantity
        sale_item.updated_by = actor.id
        total_amount = payload.quantity * Decimal(sale_item.unit_price)
        sale.return_amount = Decimal(sale.return_amount) + total_amount
        sale.updated_by = actor.id
        self._apply_sale_status(sale)
        item = PharmacySaleReturn(
            id=uuid4(),
            branch_id=actor.branch_id,
            sale_id=sale.id,
            sale_item_id=sale_item.id,
            customer_id=sale.customer_id,
            medicine_id=sale_item.medicine_id,
            return_number=self._generate_number(PharmacySaleReturn, "RET"),
            returned_at=payload.returned_at,
            batch_no=sale_item.batch_no,
            expiry_date=sale_item.expiry_date,
            quantity=payload.quantity,
            unit_price=sale_item.unit_price,
            total_amount=total_amount,
            note=payload.note,
            returned_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(item)
        self._change_stock(
            medicine=sale_item.medicine,
            delta=payload.quantity,
            actor=actor,
            movement_type="sale_return_in",
            reference_type="sale_return",
            reference_id=item.id,
            batch_no=sale_item.batch_no,
            expiry_date=sale_item.expiry_date,
            sale_price=sale_item.unit_price,
            note=payload.note,
        )
        self._commit_and_log(actor=actor, action="pharmacy.return.create", entity_type="pharmacy_sale_return", entity_id=str(item.id), detail={"return_number": item.return_number}, context=context)
        self.db.refresh(item)
        item = self.repository.get_sale_return(item.id)
        return self._serialize_return(item)

    def get_return(self, entity_id, actor: User) -> PharmacySaleReturnRead:
        item = self.repository.get_sale_return(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "return_not_found", "Medicine return not found")
        self._ensure_branch_scope(item, actor)
        return self._serialize_return(item)

    def update_return(self, entity_id, payload: PharmacySaleReturnUpdate, actor: User, context: dict[str, str | None]) -> PharmacySaleReturnRead:
        item = self.repository.get_sale_return(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "return_not_found", "Medicine return not found")
        self._ensure_branch_scope(item, actor)
        sale_item = item.sale_item
        sale = item.sale
        old_quantity = Decimal(item.quantity)
        available = Decimal(sale_item.quantity) - Decimal(sale_item.returned_quantity) + old_quantity
        if payload.quantity > available:
            raise AppException(409, "return_exceeds_sold_quantity", "Return quantity exceeds sold quantity")
        delta = Decimal(payload.quantity) - old_quantity
        if payload.returned_at < sale.sale_date:
            raise AppException(422, "invalid_return_date", "Return date cannot be earlier than sale date")
        sale_item.returned_quantity = Decimal(sale_item.returned_quantity) + delta
        sale_item.updated_by = actor.id
        if delta != 0:
            self._change_stock(
                medicine=sale_item.medicine,
                delta=delta,
                actor=actor,
                movement_type="sale_return_adjustment",
                reference_type="sale_return",
                reference_id=item.id,
                batch_no=item.batch_no,
                expiry_date=item.expiry_date,
                sale_price=item.unit_price,
                note=payload.note,
            )
        sale.return_amount = Decimal(sale.return_amount) + (payload.quantity - old_quantity) * Decimal(item.unit_price)
        sale.updated_by = actor.id
        item.returned_at = payload.returned_at
        item.quantity = payload.quantity
        item.total_amount = payload.quantity * Decimal(item.unit_price)
        item.note = payload.note
        item.updated_by = actor.id
        self._apply_sale_status(sale)
        self._commit_and_log(actor=actor, action="pharmacy.return.update", entity_type="pharmacy_sale_return", entity_id=str(item.id), detail={"return_number": item.return_number}, context=context)
        self.db.refresh(item)
        item = self.repository.get_sale_return(item.id)
        return self._serialize_return(item)

    def delete_return(self, entity_id, actor: User, context: dict[str, str | None]) -> None:
        item = self.repository.get_sale_return(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "return_not_found", "Medicine return not found")
        self._ensure_branch_scope(item, actor)
        item.sale_item.returned_quantity = Decimal(item.sale_item.returned_quantity) - Decimal(item.quantity)
        item.sale_item.updated_by = actor.id
        self._change_stock(
            medicine=item.medicine,
            delta=-Decimal(item.quantity),
            actor=actor,
            movement_type="sale_return_delete_out",
            reference_type="sale_return",
            reference_id=item.id,
            batch_no=item.batch_no,
            expiry_date=item.expiry_date,
            sale_price=item.unit_price,
            note="Return deleted",
        )
        item.sale.return_amount = Decimal(item.sale.return_amount) - Decimal(item.total_amount)
        item.sale.updated_by = actor.id
        self._apply_sale_status(item.sale)
        item.is_active = False
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.return.delete", entity_type="pharmacy_sale_return", entity_id=str(item.id), detail={"return_number": item.return_number}, context=context)

    def list_stock_movements(
        self,
        actor: User,
        *,
        page: int,
        page_size: int,
        medicine_id=None,
        reference_type: str | None = None,
        reference_id=None,
    ) -> PaginatedResponse[PharmacyStockMovementRead]:
        stmt = (
            select(PharmacyStockMovement)
            .options(joinedload(PharmacyStockMovement.medicine))
            .where(PharmacyStockMovement.is_active.is_(True))
            .order_by(PharmacyStockMovement.created_at.desc())
        )
        if actor.branch_id:
            stmt = stmt.where(PharmacyStockMovement.branch_id == actor.branch_id)
        if medicine_id:
            stmt = stmt.where(PharmacyStockMovement.medicine_id == medicine_id)
        if reference_type:
            stmt = stmt.where(PharmacyStockMovement.reference_type == reference_type)
        if reference_id:
            stmt = stmt.where(PharmacyStockMovement.reference_id == reference_id)
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_stock_movement(item) for item in items]
        return meta

    def list_investigation_settings(
        self,
        actor: User,
        *,
        page: int,
        page_size: int,
        q: str | None,
        service_area: str | None = None,
        is_active: bool | None = None,
    ) -> PaginatedResponse[PharmacyInvestigationSettingRead]:
        stmt = select(PharmacyInvestigationSetting).order_by(PharmacyInvestigationSetting.category_name.asc(), PharmacyInvestigationSetting.test_name.asc())
        if actor.branch_id:
            stmt = stmt.where(PharmacyInvestigationSetting.branch_id == actor.branch_id)
        if is_active is not None:
            stmt = stmt.where(PharmacyInvestigationSetting.is_active.is_(is_active))
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(PharmacyInvestigationSetting.test_name).like(pattern),
                    func.lower(PharmacyInvestigationSetting.category_name).like(pattern),
                    func.lower(PharmacyInvestigationSetting.code).like(pattern),
                )
            )
        if service_area:
            stmt = stmt.where(PharmacyInvestigationSetting.service_area == service_area)
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_setting(item) for item in items]
        return meta

    def _ensure_setting_uniqueness(self, payload: PharmacyInvestigationSettingCreate | PharmacyInvestigationSettingUpdate, *, exclude_id=None):
        code_stmt = select(PharmacyInvestigationSetting).where(
            func.lower(PharmacyInvestigationSetting.code) == payload.code.strip().lower(),
            PharmacyInvestigationSetting.is_active.is_(True),
        )
        if exclude_id:
            code_stmt = code_stmt.where(PharmacyInvestigationSetting.id != exclude_id)
        if self.db.scalar(code_stmt):
            raise AppException(409, "duplicate_investigation_code", "Investigation setting code already exists")
        name_stmt = select(PharmacyInvestigationSetting).where(
            func.lower(PharmacyInvestigationSetting.test_name) == payload.test_name.strip().lower(),
            func.lower(PharmacyInvestigationSetting.category_name) == payload.category_name.strip().lower(),
            PharmacyInvestigationSetting.is_active.is_(True),
        )
        if exclude_id:
            name_stmt = name_stmt.where(PharmacyInvestigationSetting.id != exclude_id)
        if self.db.scalar(name_stmt):
            raise AppException(409, "duplicate_investigation_setting", "Investigation setting already exists in this category")

    def _derive_investigation_status(self, statuses: list[str], fallback: str) -> str:
        normalized = [status.strip().lower() for status in statuses if status]
        if not normalized:
            return fallback
        if all(status == "verified" for status in normalized):
            return "verified"
        if all(status in {"completed", "verified"} for status in normalized):
            return "completed"
        if any(status == "processing" for status in normalized):
            return "processing"
        if any(status == "collected" for status in normalized):
            return "collected"
        return normalized[0]

    def _resolve_investigation_items(
        self,
        items: list[PharmacyInvestigationItemWrite],
        actor: User,
        *,
        exclude_investigation_id=None,
    ) -> tuple[list[tuple], Decimal]:
        resolved: list[tuple] = []
        total_fee = Decimal("0")
        seen: set[str] = set()
        for item in items:
            key = f"{item.setting_id}:{item.source_visit_order_id or ''}"
            if key in seen:
                raise AppException(409, "duplicate_investigation_test", "The same investigation test cannot be selected twice in one order")
            seen.add(key)
            source_order = None
            if item.source_visit_order_id:
                if self.repository.has_investigation_item_for_opd_order(item.source_visit_order_id, exclude_investigation_id=exclude_investigation_id):
                    raise AppException(409, "duplicate_investigation_order", "One or more OPD investigation lines are already linked")
                source_order = self.opd_repository.get_order(item.source_visit_order_id)
                if not source_order:
                    raise AppException(404, "opd_order_not_found", "Investigation source order not found")
                if source_order.order_type != "investigation":
                    raise AppException(400, "invalid_opd_order_type", "Only investigation orders can be linked")
            setting = self.repository.get_investigation_setting(item.setting_id)
            if not setting or not setting.is_active:
                raise AppException(404, "investigation_setting_not_found", "Investigation setting not found")
            self._ensure_branch_scope(setting, actor)
            fee = Decimal(item.fee) if item.fee is not None else Decimal(setting.fee)
            if fee < 0:
                raise AppException(422, "invalid_investigation_fee", "Investigation item fee cannot be negative")
            total_fee += fee
            resolved.append(
                (
                    setting,
                    fee,
                    item.status.strip().lower(),
                    self._normalize_text(item.result_text),
                    self._normalize_text(item.note),
                    setting.normal_range,
                    setting.unit,
                    setting.description,
                    setting.report_header,
                    setting.report_template,
                    setting.report_note_template,
                    setting.requires_report,
                    source_order,
                )
            )
        return resolved, total_fee

    def create_investigation_setting(self, payload: PharmacyInvestigationSettingCreate, actor: User, context: dict[str, str | None]) -> PharmacyInvestigationSettingRead:
        self._ensure_setting_uniqueness(payload)
        item = PharmacyInvestigationSetting(branch_id=actor.branch_id, **payload.model_dump(), code=payload.code.strip().upper(), created_by=actor.id, updated_by=actor.id)
        self.repository.create(item)
        self._commit_and_log(actor=actor, action="pharmacy.investigation_setting.create", entity_type="pharmacy_investigation_setting", entity_id=str(item.id), detail={"code": item.code}, context=context)
        self.db.refresh(item)
        return self._serialize_setting(item)

    def get_investigation_setting(self, entity_id, actor: User) -> PharmacyInvestigationSettingRead:
        item = self.repository.get_investigation_setting(entity_id)
        if not item:
            raise AppException(404, "investigation_setting_not_found", "Investigation setting not found")
        self._ensure_branch_scope(item, actor)
        return self._serialize_setting(item)

    def update_investigation_setting(self, entity_id, payload: PharmacyInvestigationSettingUpdate, actor: User, context: dict[str, str | None]) -> PharmacyInvestigationSettingRead:
        item = self.repository.get_investigation_setting(entity_id)
        if not item:
            raise AppException(404, "investigation_setting_not_found", "Investigation setting not found")
        self._ensure_branch_scope(item, actor)
        self._ensure_setting_uniqueness(payload, exclude_id=item.id)
        for key, value in payload.model_dump().items():
            setattr(item, key, value.strip().upper() if key == "code" and isinstance(value, str) else value)
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.investigation_setting.update", entity_type="pharmacy_investigation_setting", entity_id=str(item.id), detail={"code": item.code}, context=context)
        self.db.refresh(item)
        return self._serialize_setting(item)

    def delete_investigation_setting(self, entity_id, actor: User, context: dict[str, str | None]) -> None:
        item = self.repository.get_investigation_setting(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "investigation_setting_not_found", "Investigation setting not found")
        self._ensure_branch_scope(item, actor)
        item.is_active = False
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.investigation_setting.delete", entity_type="pharmacy_investigation_setting", entity_id=str(item.id), detail={"code": item.code}, context=context)

    def list_investigations(
        self,
        actor: User,
        *,
        page: int,
        page_size: int,
        q: str | None,
        status: str | None = None,
        service_area: str | None = None,
        customer_id=None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PaginatedResponse[PharmacyInvestigationRead]:
        stmt = (
            select(PharmacyInvestigation)
            .options(
                joinedload(PharmacyInvestigation.setting),
                joinedload(PharmacyInvestigation.customer).joinedload(PharmacyCustomer.patient),
                joinedload(PharmacyInvestigation.patient),
                joinedload(PharmacyInvestigation.items).joinedload(PharmacyInvestigationItem.setting),
            )
            .where(PharmacyInvestigation.is_active.is_(True))
            .order_by(PharmacyInvestigation.ordered_at.desc(), PharmacyInvestigation.created_at.desc())
        )
        if actor.branch_id:
            stmt = stmt.where(PharmacyInvestigation.branch_id == actor.branch_id)
        if status:
            stmt = stmt.where(PharmacyInvestigation.status == status)
        if customer_id:
            stmt = stmt.where(PharmacyInvestigation.customer_id == customer_id)
        if service_area:
            stmt = stmt.outerjoin(PharmacyInvestigation.items).outerjoin(PharmacyInvestigationItem.setting).where(
                or_(
                    PharmacyInvestigationSetting.service_area == service_area,
                    PharmacyInvestigation.setting.has(PharmacyInvestigationSetting.service_area == service_area),
                )
            )
        if date_from:
            stmt = stmt.where(PharmacyInvestigation.ordered_at >= date_from)
        if date_to:
            stmt = stmt.where(PharmacyInvestigation.ordered_at <= date_to)
        if q:
            pattern = f"%{q.strip().lower()}%"
            stmt = stmt.outerjoin(PharmacyInvestigation.items).outerjoin(PharmacyInvestigationItem.setting).outerjoin(PharmacyInvestigation.customer).where(
                or_(
                    func.lower(PharmacyInvestigation.investigation_number).like(pattern),
                    func.lower(PharmacyInvestigationSetting.test_name).like(pattern),
                    func.lower(PharmacyInvestigationSetting.code).like(pattern),
                    func.lower(func.coalesce(PharmacyCustomer.name, "")).like(pattern),
                )
            )
        items, meta = self._paginate(stmt, page=page, page_size=page_size)
        meta.items = [self._serialize_investigation(item) for item in items]
        return meta

    def create_investigation(self, payload: PharmacyInvestigationCreate, actor: User, context: dict[str, str | None]) -> PharmacyInvestigationRead:
        customer = self.repository.get_customer(payload.customer_id) if payload.customer_id else None
        if payload.customer_id and (not customer or not customer.is_active):
            raise AppException(404, "customer_not_found", "Customer information not found")
        if customer:
            self._ensure_branch_scope(customer, actor)
        patient = self._resolve_patient(payload.patient_id or (customer.patient_id if customer else None), actor)
        resolved_customer = customer or (self.repository.get_customer_by_patient(patient.id) if patient else None)
        resolved_items, subtotal = self._resolve_investigation_items(payload.items, actor)
        primary_setting = resolved_items[0][0]
        discount = min(Decimal(payload.discount_amount), Decimal(subtotal))
        item = PharmacyInvestigation(
            branch_id=actor.branch_id,
            setting_id=primary_setting.id,
            customer_id=resolved_customer.id if resolved_customer else None,
            patient_id=patient.id if patient else None,
            source_visit_id=payload.source_visit_id,
            investigation_number=self._generate_number(PharmacyInvestigation, "INV"),
            ordered_at=payload.ordered_at,
            status=self._derive_investigation_status([entry[2] for entry in resolved_items], payload.status),
            fee=subtotal,
            discount_amount=discount,
            total_amount=max(Decimal("0"), Decimal(subtotal) - discount),
            report_note=payload.report_note,
            note=payload.note,
            report_title=payload.report_title or f"Investigation Report - {primary_setting.category_name}",
            report_footer_note=payload.report_footer_note,
            printable_schema=payload.printable_schema,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(item)
        for setting, fee, status_value, result_text, note, normal_range, unit, description, report_header, report_template, report_note_template, requires_report, source_order in resolved_items:
            item.items.append(
                PharmacyInvestigationItem(
                    id=uuid4(),
                    investigation_id=item.id,
                    setting_id=setting.id,
                    source_visit_order_id=source_order.id if source_order else None,
                    status=status_value,
                    fee=fee,
                    result_text=result_text,
                    note=note,
                    normal_range_snapshot=normal_range,
                    unit_snapshot=unit,
                    description_snapshot=description,
                    report_header_snapshot=report_header,
                    report_template_snapshot=report_template,
                    report_note_template_snapshot=report_note_template,
                    requires_report=requires_report,
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )
            if source_order:
                source_order.status = "in_progress"
                source_order.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.investigation.create", entity_type="pharmacy_investigation", entity_id=str(item.id), detail={"investigation_number": item.investigation_number}, context=context)
        self.db.refresh(item)
        item = self.repository.get_investigation(item.id)
        return self._serialize_investigation(item)

    def get_investigation(self, entity_id, actor: User) -> PharmacyInvestigationRead:
        item = self.repository.get_investigation(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "investigation_not_found", "Investigation not found")
        self._ensure_branch_scope(item, actor)
        return self._serialize_investigation(item)

    def update_investigation(self, entity_id, payload: PharmacyInvestigationUpdate, actor: User, context: dict[str, str | None]) -> PharmacyInvestigationRead:
        item = self.repository.get_investigation(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "investigation_not_found", "Investigation not found")
        self._ensure_branch_scope(item, actor)
        customer = self.repository.get_customer(payload.customer_id) if payload.customer_id else None
        if payload.customer_id and (not customer or not customer.is_active):
            raise AppException(404, "customer_not_found", "Customer information not found")
        if customer:
            self._ensure_branch_scope(customer, actor)
        patient = self._resolve_patient(payload.patient_id or (customer.patient_id if customer else None), actor)
        resolved_customer = customer or (self.repository.get_customer_by_patient(patient.id) if patient else None)
        resolved_items, subtotal = self._resolve_investigation_items(payload.items, actor, exclude_investigation_id=item.id)
        primary_setting = resolved_items[0][0]
        discount = min(Decimal(payload.discount_amount), Decimal(subtotal))
        item.setting_id = primary_setting.id
        item.customer_id = resolved_customer.id if resolved_customer else None
        item.patient_id = patient.id if patient else None
        item.source_visit_id = payload.source_visit_id
        item.ordered_at = payload.ordered_at
        item.status = self._derive_investigation_status([entry[2] for entry in resolved_items], payload.status)
        item.fee = subtotal
        item.discount_amount = discount
        item.total_amount = max(Decimal("0"), Decimal(subtotal) - discount)
        item.report_note = payload.report_note
        item.note = payload.note
        item.report_title = payload.report_title or f"Investigation Report - {primary_setting.category_name}"
        item.report_footer_note = payload.report_footer_note
        item.printable_schema = payload.printable_schema
        item.updated_by = actor.id
        for existing in item.items:
            if existing.is_active:
                if existing.source_visit_order:
                    existing.source_visit_order.status = "pending"
                    existing.source_visit_order.updated_by = actor.id
                existing.is_active = False
                existing.updated_by = actor.id
        for setting, fee, status_value, result_text, note, normal_range, unit, description, report_header, report_template, report_note_template, requires_report, source_order in resolved_items:
            item.items.append(
                PharmacyInvestigationItem(
                    id=uuid4(),
                    investigation_id=item.id,
                    setting_id=setting.id,
                    source_visit_order_id=source_order.id if source_order else None,
                    status=status_value,
                    fee=fee,
                    result_text=result_text,
                    note=note,
                    normal_range_snapshot=normal_range,
                    unit_snapshot=unit,
                    description_snapshot=description,
                    report_header_snapshot=report_header,
                    report_template_snapshot=report_template,
                    report_note_template_snapshot=report_note_template,
                    requires_report=requires_report,
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )
            if source_order:
                source_order.status = "in_progress"
                source_order.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.investigation.update", entity_type="pharmacy_investigation", entity_id=str(item.id), detail={"investigation_number": item.investigation_number}, context=context)
        self.db.refresh(item)
        item = self.repository.get_investigation(item.id)
        return self._serialize_investigation(item)

    def delete_investigation(self, entity_id, actor: User, context: dict[str, str | None]) -> None:
        item = self.repository.get_investigation(entity_id)
        if not item or not item.is_active:
            raise AppException(404, "investigation_not_found", "Investigation not found")
        self._ensure_branch_scope(item, actor)
        for child in item.items:
            if child.is_active:
                if child.source_visit_order:
                    child.source_visit_order.status = "pending"
                    child.source_visit_order.updated_by = actor.id
                child.is_active = False
                child.updated_by = actor.id
        item.is_active = False
        item.updated_by = actor.id
        self._commit_and_log(actor=actor, action="pharmacy.investigation.delete", entity_type="pharmacy_investigation", entity_id=str(item.id), detail={"investigation_number": item.investigation_number}, context=context)

    def list_dispenses(self, actor: User) -> list[PharmacyDispense]:
        return self.repository.list_dispenses(actor.branch_id)

    def get_summary(self, actor: User) -> PharmacySummaryRead:
        totals = self.repository.get_summary(actor.branch_id)
        return PharmacySummaryRead(
            total_dispenses=totals[0],
            today_dispenses=totals[1],
            pending_prescriptions=totals[2],
            billed_prescriptions=totals[3],
            partial_dispenses=totals[4],
            returned_dispenses=totals[5],
        )

    def get_dashboard_summary(self, actor: User) -> PharmacyDashboardSummaryRead:
        totals = self.repository.get_dashboard_summary(actor.branch_id)
        return PharmacyDashboardSummaryRead(
            total_medicines=totals[0],
            low_stock_medicines=totals[1],
            total_customers=totals[2],
            total_sales=totals[3],
            total_returns=totals[4],
            total_investigations=totals[5],
        )

    def build_sales_draft_from_visit(self, visit_id, actor: User) -> PharmacySalesDraftRead:
        visit = self.opd_repository.get_visit(visit_id)
        if not visit:
            raise AppException(404, "opd_visit_not_found", "OPD visit not found")
        self._ensure_branch_scope(visit, actor)
        customer = self.repository.get_customer_by_patient(visit.patient_id)
        prescription_orders = [order for order in visit.orders if order.is_active and order.order_type == "prescription"]
        draft_items: list[PharmacySalesDraftItemRead] = []
        for order in prescription_orders:
            if self.repository.has_sale_item_for_opd_order(order.id):
                continue
            suggestions = self._suggest_medicines(order.item_name, actor)
            draft_items.append(
                PharmacySalesDraftItemRead(
                    source_visit_order_id=order.id,
                    source_label=order.item_name,
                    quantity=order.quantity,
                    medicine_suggestions=suggestions,
                    instruction=order.instructions,
                    warning=None if suggestions else "No in-stock brand match found. Choose a substitute manually.",
                )
            )
        if not draft_items:
            raise AppException(409, "pharmacy_draft_unavailable", "No pending prescription lines are available for pharmacy sales draft")
        return PharmacySalesDraftRead(
            patient_id=visit.patient_id,
            patient_name=f"{visit.patient.first_name} {visit.patient.last_name}",
            customer_id=customer.id if customer else None,
            source_visit_id=visit.id,
            source_visit_number=visit.visit_number,
            note=f"Auto-drafted from OPD prescription {visit.visit_number} · Doctor {visit.consulting_doctor_name}",
            items=draft_items,
            message="Review medicine suggestions before posting the sale.",
        )

    def build_investigation_draft_from_visit(self, visit_id, actor: User) -> PharmacyInvestigationDraftRead:
        visit = self.opd_repository.get_visit(visit_id)
        if not visit:
            raise AppException(404, "opd_visit_not_found", "OPD visit not found")
        self._ensure_branch_scope(visit, actor)
        customer = self.repository.get_customer_by_patient(visit.patient_id)
        investigation_orders = [order for order in visit.orders if order.is_active and order.order_type == "investigation"]
        draft_items: list[PharmacyInvestigationDraftItemRead] = []
        for order in investigation_orders:
            if self.repository.has_investigation_item_for_opd_order(order.id):
                continue
            setting = self._match_investigation_setting(order.item_name, order.service_area or "laboratory", actor)
            draft_items.append(
                PharmacyInvestigationDraftItemRead(
                    source_visit_order_id=order.id,
                    setting_id=setting.id if setting else None,
                    test_name=order.item_name,
                    category_name=setting.category_name if setting else None,
                    service_area=order.service_area or "laboratory",
                    fee=setting.fee if setting else None,
                    instruction=order.instructions,
                    warning=None if setting else f"No investigation setting matched {order.item_name}.",
                )
            )
        if not draft_items:
            raise AppException(409, "investigation_draft_unavailable", "No pending investigation lines are available for intake draft")
        return PharmacyInvestigationDraftRead(
            patient_id=visit.patient_id,
            patient_name=f"{visit.patient.first_name} {visit.patient.last_name}",
            customer_id=customer.id if customer else None,
            source_visit_id=visit.id,
            source_visit_number=visit.visit_number,
            report_title=f"Investigation Report - {visit.visit_number}",
            note=f"Auto-drafted from OPD investigation orders for {visit.visit_number}",
            items=draft_items,
            message="Matched tests are ready for the investigation worklist.",
        )

    def list_pending_prescriptions(self, actor: User) -> list[PharmacyPendingPrescriptionRead]:
        orders = self.opd_repository.list_pending_prescription_orders(actor.branch_id)
        pending: list[PharmacyPendingPrescriptionRead] = []
        for order in orders:
            dispensed_quantity = Decimal(str(self.repository.get_net_dispensed_quantity(order.id)))
            remaining_quantity = max(Decimal("0"), order.quantity - dispensed_quantity)
            if remaining_quantity <= 0:
                continue
            availability = self.get_medicine_availability(order.item_name, actor)
            usable_quantity = sum(batch.available_quantity for batch in availability.batches if not batch.is_expired)
            if usable_quantity <= 0:
                availability_status = "out_of_stock"
            elif usable_quantity >= remaining_quantity:
                availability_status = "available"
            else:
                availability_status = "partially_available"
            prescription_status = "pending"
            if dispensed_quantity > 0:
                prescription_status = "partially_dispensed"
            elif availability_status == "available":
                prescription_status = "available"
            elif availability_status == "partially_available":
                prescription_status = "partially_available"
            pending.append(
                PharmacyPendingPrescriptionRead(
                order_id=order.id,
                visit_id=order.visit_id,
                visit_number=order.visit.visit_number,
                patient_id=order.visit.patient_id,
                patient_number=order.visit.patient.patient_number,
                patient_name=f"{order.visit.patient.first_name} {order.visit.patient.last_name}",
                doctor_name=order.visit.consulting_doctor_name,
                visit_date=order.visit.visit_date.isoformat(),
                visit_status=order.visit.status,
                item_name=order.item_name,
                quantity=order.quantity,
                dispensed_quantity=dispensed_quantity,
                remaining_quantity=remaining_quantity,
                instructions=order.instructions,
                chief_complaint=order.visit.chief_complaint,
                diagnosis=order.visit.final_diagnosis or order.visit.provisional_diagnosis,
                prescription_status=prescription_status,
                payment_status="paid" if order.visit.status in ["billed", "completed"] else "unpaid",
                availability_status=availability_status,
                available_quantity=usable_quantity,
                reserved_quantity=availability.total_reserved_quantity,
                preferred_batch_no=availability.preferred_batch_no,
                preferred_expiry_date=availability.preferred_expiry_date,
                available_stores=[batch.store_name for batch in availability.batches if batch.store_name and batch.available_quantity > 0 and not batch.is_expired],
            )
            )
        return pending

    def dispense(self, payload: PharmacyDispenseCreate, actor: User, context: dict[str, str | None]) -> PharmacyDispense:
        source_order = None
        if payload.source_visit_order_id:
            source_order = self.opd_repository.get_order(payload.source_visit_order_id)
            if not source_order:
                raise AppException(404, "opd_order_not_found", "OPD prescription order not found")
            if source_order.order_type != "prescription":
                raise AppException(400, "invalid_opd_order_type", "Only prescription orders can be dispensed")
            if actor.branch_id and source_order.visit.branch_id and actor.branch_id != source_order.visit.branch_id:
                raise AppException(403, "forbidden", "Prescription order belongs to a different branch")

        patient_id = payload.patient_id or (source_order.visit.patient_id if source_order else None)
        prescription_ref = payload.prescription_ref or (source_order.visit.visit_number if source_order else None)
        medicine_name = payload.medicine_name or (source_order.item_name if source_order else None)
        quantity = payload.quantity or (source_order.quantity if source_order else None)
        if not medicine_name or quantity is None:
            raise AppException(400, "invalid_dispense_payload", "Medicine name and quantity are required")
        requested_quantity = source_order.quantity if source_order else payload.quantity
        if source_order:
            already_dispensed = Decimal(str(self.repository.get_net_dispensed_quantity(source_order.id)))
            remaining_quantity = source_order.quantity - already_dispensed
            if remaining_quantity <= 0:
                raise AppException(409, "opd_order_already_dispensed", "Prescription order has no remaining quantity to dispense")
            if quantity > remaining_quantity:
                raise AppException(409, "pharmacy_dispense_exceeds_remaining", "Dispense quantity exceeds remaining prescription quantity")
        else:
            remaining_quantity = quantity
        total_price = quantity * payload.unit_price
        billing_invoice, billing_invoice_item, billing_created = self._resolve_or_create_dispense_billing(
            payload=payload,
            actor=actor,
            patient_id=patient_id,
            source_order=source_order,
            medicine_name=medicine_name,
            quantity=quantity,
            unit_price=payload.unit_price,
            total_price=total_price,
            prescription_ref=prescription_ref,
        )
        order_remaining_after = remaining_quantity - quantity if source_order else Decimal("0")
        dispense_status = "partial" if source_order and order_remaining_after > 0 else "dispensed"
        dispense = None
        if source_order:
            dispense = self.db.scalar(
                select(PharmacyDispense).where(
                    PharmacyDispense.source_visit_order_id == source_order.id,
                    PharmacyDispense.status == "pending",
                    PharmacyDispense.is_active.is_(True),
                )
            )
        if dispense:
            dispense.patient_id = patient_id
            dispense.source_visit_id = source_order.visit_id if source_order else payload.source_visit_id
            dispense.source_visit_order_id = source_order.id if source_order else payload.source_visit_order_id
            dispense.prescription_ref = prescription_ref
            dispense.medicine_name = medicine_name
            dispense.billing_invoice_id = billing_invoice.id if billing_invoice else None
            dispense.billing_invoice_item_id = billing_invoice_item.id if billing_invoice_item else None
            dispense.requested_quantity = requested_quantity
            dispense.quantity = quantity
            dispense.returned_quantity = Decimal("0")
            dispense.unit_price = payload.unit_price
            dispense.total_price = total_price
            dispense.status = dispense_status
            dispense.note = payload.note
            dispense.dispensed_by_user_id = actor.id
            dispense.updated_by = actor.id
        else:
            dispense = PharmacyDispense(
                patient_id=patient_id,
                billing_invoice_id=billing_invoice.id if billing_invoice else payload.billing_invoice_id,
                billing_invoice_item_id=billing_invoice_item.id if billing_invoice_item else payload.billing_invoice_item_id,
                branch_id=payload.branch_id or actor.branch_id,
                source_visit_id=source_order.visit_id if source_order else payload.source_visit_id,
                source_visit_order_id=source_order.id if source_order else payload.source_visit_order_id,
                prescription_ref=prescription_ref,
                medicine_name=medicine_name,
                requested_quantity=requested_quantity,
                quantity=quantity,
                returned_quantity=Decimal("0"),
                unit_price=payload.unit_price,
                total_price=total_price,
                status=dispense_status,
                note=payload.note,
                dispensed_by_user_id=actor.id,
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.repository.create(dispense)
        matched_medicine_query = select(PharmacyMedicine).where(
            PharmacyMedicine.is_active.is_(True),
            func.lower(PharmacyMedicine.name) == medicine_name.strip().lower(),
        )
        if actor.branch_id:
            matched_medicine_query = matched_medicine_query.where(PharmacyMedicine.branch_id == actor.branch_id)
        matched_medicine = self.db.scalar(matched_medicine_query)
        inventory_item = self._find_inventory_item_for_medicine(medicine_name, actor)
        inventory_available = self._available_inventory_quantity(inventory_item) if inventory_item else Decimal("0")
        dispensed_from_inventory = False
        if inventory_item and inventory_available >= Decimal(quantity):
            deducted = self._deduct_inventory_for_dispense(
                item=inventory_item,
                quantity=Decimal(quantity),
                actor=actor,
                reference_id=dispense.id,
                note=payload.note,
            )
            dispensed_from_inventory = deducted == Decimal(quantity)
            if not dispensed_from_inventory:
                raise AppException(409, "inventory_stock_conflict", f"Could not issue enough non-expired inventory stock for {medicine_name}")
        if not dispensed_from_inventory and matched_medicine:
            if Decimal(matched_medicine.stock_quantity) < Decimal(quantity):
                raise AppException(409, "insufficient_stock", f"Insufficient stock for {matched_medicine.name}")
            self._change_stock(
                medicine=matched_medicine,
                delta=-Decimal(quantity),
                actor=actor,
                movement_type="dispense_out",
                reference_type="dispense",
                reference_id=dispense.id,
                note=payload.note,
            )
        elif not dispensed_from_inventory:
            raise AppException(409, "insufficient_stock", f"No available stock found for {medicine_name}")
        if source_order:
            source_order.status = "completed" if order_remaining_after <= 0 else "in_progress"
            source_order.updated_by = actor.id
        self._commit_and_log(
            actor=actor,
            action="pharmacy.dispense",
            entity_type="pharmacy_dispense",
            entity_id=str(dispense.id),
            detail={
                "medicine_name": dispense.medicine_name,
                "total_price": str(dispense.total_price),
                "billing_invoice_id": str(dispense.billing_invoice_id) if dispense.billing_invoice_id else None,
                "billing_invoice_number": billing_invoice.invoice_number if billing_invoice else None,
                "billing_created": billing_created,
            },
            context=context,
        )
        self.db.refresh(dispense)
        return dispense

    def return_dispense(self, dispense_id, payload: PharmacyDispenseReturnCreate, actor: User, context: dict[str, str | None]) -> PharmacyDispense:
        dispense = self.repository.get_dispense(dispense_id)
        if not dispense:
            raise AppException(404, "pharmacy_dispense_not_found", "Pharmacy dispense not found")
        if actor.branch_id and dispense.branch_id and actor.branch_id != dispense.branch_id:
            raise AppException(403, "forbidden", "Dispense belongs to a different branch")

        remaining_returnable = dispense.quantity - dispense.returned_quantity
        if payload.quantity > remaining_returnable:
            raise AppException(409, "pharmacy_return_exceeds_dispense", "Return quantity exceeds remaining dispensed quantity")

        dispense.returned_quantity += payload.quantity
        dispense.return_note = payload.note
        dispense.updated_by = actor.id
        if dispense.returned_quantity == dispense.quantity:
            dispense.status = "returned"
        else:
            dispense.status = "partially_returned"

        matched_medicine_query = select(PharmacyMedicine).where(
            PharmacyMedicine.is_active.is_(True),
            func.lower(PharmacyMedicine.name) == dispense.medicine_name.strip().lower(),
        )
        if actor.branch_id:
            matched_medicine_query = matched_medicine_query.where(PharmacyMedicine.branch_id == actor.branch_id)
        matched_medicine = self.db.scalar(matched_medicine_query)
        if matched_medicine:
            self._change_stock(
                medicine=matched_medicine,
                delta=Decimal(payload.quantity),
                actor=actor,
                movement_type="dispense_return_in",
                reference_type="dispense",
                reference_id=dispense.id,
                note=payload.note,
            )

        if dispense.source_visit_order:
            net_dispensed = Decimal(str(self.repository.get_net_dispensed_quantity(dispense.source_visit_order.id)))
            remaining_on_order = dispense.source_visit_order.quantity - net_dispensed
            dispense.source_visit_order.status = "completed" if remaining_on_order <= 0 else "in_progress"
            dispense.source_visit_order.updated_by = actor.id

        self._commit_and_log(actor=actor, action="pharmacy.dispense.return", entity_type="pharmacy_dispense", entity_id=str(dispense.id), detail={"medicine_name": dispense.medicine_name, "returned_quantity": str(payload.quantity)}, context=context)
        self.db.refresh(dispense)
        return dispense
