from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class PharmacyMedicineType(Base, BaseModelMixin):
    __tablename__ = "pharmacy_medicine_types"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")


class PharmacyGeneric(Base, BaseModelMixin):
    __tablename__ = "pharmacy_generics"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")


class PharmacyCompany(Base, BaseModelMixin):
    __tablename__ = "pharmacy_companies"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    contact_person: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")


class PharmacyMedicine(Base, BaseModelMixin):
    __tablename__ = "pharmacy_medicines"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    medicine_type_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_medicine_types.id"), nullable=False)
    generic_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_generics.id"), nullable=False)
    company_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    strength: Mapped[str | None] = mapped_column(String(60))
    dosage_form: Mapped[str | None] = mapped_column(String(60))
    sku: Mapped[str | None] = mapped_column(String(80), unique=True)
    barcode: Mapped[str | None] = mapped_column(String(80))
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    stock_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    reorder_level: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    medicine_type = relationship("PharmacyMedicineType")
    generic = relationship("PharmacyGeneric")
    company = relationship("PharmacyCompany")
    purchases = relationship("PharmacyPurchase", back_populates="medicine")
    sale_items = relationship("PharmacySaleItem", back_populates="medicine")
    returns = relationship("PharmacySaleReturn", back_populates="medicine")
    stock_movements = relationship("PharmacyStockMovement", back_populates="medicine")


class PharmacyPurchase(Base, BaseModelMixin):
    __tablename__ = "pharmacy_purchases"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    medicine_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_medicines.id"), nullable=False)
    purchase_number: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    purchase_date: Mapped[Date] = mapped_column(Date(), nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(150))
    invoice_number: Mapped[str | None] = mapped_column(String(80))
    batch_no: Mapped[str | None] = mapped_column(String(80))
    expiry_date: Mapped[Date | None] = mapped_column(Date())
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    bonus_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    purchased_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    branch = relationship("Branch")
    medicine = relationship("PharmacyMedicine", back_populates="purchases")
    purchased_by = relationship("User")


class PharmacyCustomer(Base, BaseModelMixin):
    __tablename__ = "pharmacy_customers"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    customer_number: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    patient = relationship("Patient")
    sales = relationship("PharmacySale", back_populates="customer")
    investigations = relationship("PharmacyInvestigation", back_populates="customer")


class PharmacySale(Base, BaseModelMixin):
    __tablename__ = "pharmacy_sales"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_customers.id"), nullable=False)
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    source_visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"))
    sale_number: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    sale_date: Mapped[Date] = mapped_column(Date(), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    return_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_payable: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="sold")
    note: Mapped[str | None] = mapped_column(Text)
    sold_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    branch = relationship("Branch")
    customer = relationship("PharmacyCustomer", back_populates="sales")
    patient = relationship("Patient")
    source_visit = relationship("OPDVisit")
    sold_by = relationship("User")
    items = relationship("PharmacySaleItem", back_populates="sale", cascade="all, delete-orphan")
    returns = relationship("PharmacySaleReturn", back_populates="sale", cascade="all, delete-orphan")


class PharmacySaleItem(Base, BaseModelMixin):
    __tablename__ = "pharmacy_sale_items"

    sale_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_sales.id"), nullable=False)
    medicine_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_medicines.id"), nullable=False)
    source_visit_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visit_orders.id"))
    batch_no: Mapped[str | None] = mapped_column(String(80))
    expiry_date: Mapped[Date | None] = mapped_column(Date())
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    returned_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text)

    sale = relationship("PharmacySale", back_populates="items")
    medicine = relationship("PharmacyMedicine", back_populates="sale_items")
    returns = relationship("PharmacySaleReturn", back_populates="sale_item")
    source_visit_order = relationship("OPDVisitOrder")


class PharmacySaleReturn(Base, BaseModelMixin):
    __tablename__ = "pharmacy_sale_returns"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    sale_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_sales.id"), nullable=False)
    sale_item_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_sale_items.id"), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_customers.id"), nullable=False)
    medicine_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_medicines.id"), nullable=False)
    return_number: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    returned_at: Mapped[Date] = mapped_column(Date(), nullable=False)
    batch_no: Mapped[str | None] = mapped_column(String(80))
    expiry_date: Mapped[Date | None] = mapped_column(Date())
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    returned_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    branch = relationship("Branch")
    sale = relationship("PharmacySale", back_populates="returns")
    sale_item = relationship("PharmacySaleItem", back_populates="returns")
    customer = relationship("PharmacyCustomer")
    medicine = relationship("PharmacyMedicine", back_populates="returns")
    returned_by = relationship("User")


class PharmacyStockMovement(Base, BaseModelMixin):
    __tablename__ = "pharmacy_stock_movements"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    medicine_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_medicines.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    stock_before: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    stock_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    batch_no: Mapped[str | None] = mapped_column(String(80))
    expiry_date: Mapped[Date | None] = mapped_column(Date())
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    note: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    medicine = relationship("PharmacyMedicine", back_populates="stock_movements")


class PharmacyInvestigationSetting(Base, BaseModelMixin):
    __tablename__ = "pharmacy_investigation_settings"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    category_name: Mapped[str] = mapped_column(String(120), nullable=False)
    test_name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    service_area: Mapped[str] = mapped_column(String(60), nullable=False, default="laboratory")
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    room_number: Mapped[str | None] = mapped_column(String(60))
    normal_range: Mapped[str | None] = mapped_column(String(180))
    unit: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    specimen_type: Mapped[str | None] = mapped_column(String(120))
    turnaround_time: Mapped[str | None] = mapped_column(String(120))
    report_header: Mapped[str | None] = mapped_column(Text)
    report_template: Mapped[str | None] = mapped_column(Text)
    report_note_template: Mapped[str | None] = mapped_column(Text)
    requires_report: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    branch = relationship("Branch")
    investigations = relationship("PharmacyInvestigation", back_populates="setting")


class PharmacyInvestigation(Base, BaseModelMixin):
    __tablename__ = "pharmacy_investigations"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    setting_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_investigation_settings.id"), nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_customers.id"))
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    source_visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"))
    investigation_number: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    ordered_at: Mapped[Date] = mapped_column(Date(), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ordered")
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    report_title: Mapped[str | None] = mapped_column(String(180))
    report_footer_note: Mapped[str | None] = mapped_column(Text)
    printable_schema: Mapped[str | None] = mapped_column(Text)
    result_text: Mapped[str | None] = mapped_column(Text)
    report_note: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    setting = relationship("PharmacyInvestigationSetting", back_populates="investigations")
    customer = relationship("PharmacyCustomer", back_populates="investigations")
    patient = relationship("Patient")
    source_visit = relationship("OPDVisit")
    items = relationship("PharmacyInvestigationItem", back_populates="investigation", cascade="all, delete-orphan")


class PharmacyInvestigationItem(Base, BaseModelMixin):
    __tablename__ = "pharmacy_investigation_items"

    investigation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_investigations.id"), nullable=False)
    setting_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("pharmacy_investigation_settings.id"), nullable=False)
    source_visit_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visit_orders.id"))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ordered")
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    result_text: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    normal_range_snapshot: Mapped[str | None] = mapped_column(String(180))
    unit_snapshot: Mapped[str | None] = mapped_column(String(60))
    description_snapshot: Mapped[str | None] = mapped_column(Text)
    report_header_snapshot: Mapped[str | None] = mapped_column(Text)
    report_template_snapshot: Mapped[str | None] = mapped_column(Text)
    report_note_template_snapshot: Mapped[str | None] = mapped_column(Text)
    requires_report: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    investigation = relationship("PharmacyInvestigation", back_populates="items")
    setting = relationship("PharmacyInvestigationSetting")
    source_visit_order = relationship("OPDVisitOrder")


class PharmacyDispense(Base, BaseModelMixin):
    __tablename__ = "pharmacy_dispenses"

    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    billing_invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    billing_invoice_item_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoice_items.id"))
    source_visit_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visits.id"))
    source_visit_order_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("opd_visit_orders.id"))
    prescription_ref: Mapped[str | None] = mapped_column(String(80))
    medicine_name: Mapped[str] = mapped_column(String(150), nullable=False)
    requested_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    returned_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="dispensed")
    return_note: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    dispensed_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    patient = relationship("Patient")
    branch = relationship("Branch")
    billing_invoice = relationship("BillingInvoice")
    billing_invoice_item = relationship("BillingInvoiceItem")
    source_visit = relationship("OPDVisit")
    source_visit_order = relationship("OPDVisitOrder")
    dispensed_by = relationship("User")
