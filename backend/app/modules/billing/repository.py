from uuid import UUID

from sqlalchemy import Date, case, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.billing import BillingInvoice, BillingInvoiceItem, BillingPayment, BillingRefund, BillingService, ReferredDoctor, BillingSetting
from app.models.patient import Patient
from app.models.user import User
from app.schemas.billing import BillingInvoiceFilterParams


class BillingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_services(self, branch_id: UUID | None) -> list[BillingService]:
        stmt = select(BillingService).order_by(BillingService.name.asc())
        if branch_id:
            stmt = stmt.where((BillingService.branch_id == branch_id) | (BillingService.branch_id.is_(None)))
        return list(self.db.scalars(stmt))

    def find_service_by_code(self, service_code: str, branch_id: UUID | None) -> BillingService | None:
        stmt = select(BillingService).where(BillingService.service_code == service_code)
        if branch_id:
            stmt = stmt.where((BillingService.branch_id == branch_id) | (BillingService.branch_id.is_(None)))
        return self.db.scalar(stmt)

    def list_services_by_ids(self, service_ids: list[UUID], branch_id: UUID | None) -> list[BillingService]:
        stmt = select(BillingService).where(BillingService.id.in_(service_ids))
        if branch_id:
            stmt = stmt.where((BillingService.branch_id == branch_id) | (BillingService.branch_id.is_(None)))
        return list(self.db.scalars(stmt))

    def get_service(self, service_id: UUID, branch_id: UUID | None) -> BillingService | None:
        stmt = select(BillingService).where(BillingService.id == service_id)
        if branch_id:
            stmt = stmt.where((BillingService.branch_id == branch_id) | (BillingService.branch_id.is_(None)))
        return self.db.scalar(stmt)

    def create_service(self, service: BillingService) -> BillingService:
        self.db.add(service)
        self.db.flush()
        return service

    def list_doctors(self, branch_id: UUID | None) -> list[ReferredDoctor]:
        stmt = select(ReferredDoctor).order_by(ReferredDoctor.full_name.asc())
        if branch_id:
            stmt = stmt.where((ReferredDoctor.branch_id == branch_id) | (ReferredDoctor.branch_id.is_(None)))
        return list(self.db.scalars(stmt))

    def find_doctor_by_code(self, doctor_code: str, branch_id: UUID | None) -> ReferredDoctor | None:
        stmt = select(ReferredDoctor).where(ReferredDoctor.doctor_code == doctor_code)
        if branch_id:
            stmt = stmt.where((ReferredDoctor.branch_id == branch_id) | (ReferredDoctor.branch_id.is_(None)))
        return self.db.scalar(stmt)

    def get_doctor(self, doctor_id: UUID) -> ReferredDoctor | None:
        return self.db.get(ReferredDoctor, doctor_id)

    def get_invoice_entity(self, invoice_id: UUID) -> BillingInvoice | None:
        return self.db.get(BillingInvoice, invoice_id)

    def create_doctor(self, doctor: ReferredDoctor) -> ReferredDoctor:
        self.db.add(doctor)
        self.db.flush()
        return doctor

    def list_invoices(self, branch_id: UUID | None, filters: BillingInvoiceFilterParams | None = None) -> list[BillingInvoice]:
        stmt = (
            select(BillingInvoice)
            .options(joinedload(BillingInvoice.patient), joinedload(BillingInvoice.referred_doctor))
            .order_by(BillingInvoice.created_at.desc())
        )
        if branch_id:
            stmt = stmt.where(BillingInvoice.branch_id == branch_id)
        if filters:
            if filters.q:
                q = f"%{filters.q.strip()}%"
                stmt = stmt.join(Patient, BillingInvoice.patient_id == Patient.id).where(
                    or_(
                        BillingInvoice.invoice_number.ilike(q),
                        BillingInvoice.referred_doctor_name.ilike(q),
                        func.concat_ws(" ", Patient.first_name, Patient.last_name).ilike(q),
                        Patient.patient_number.ilike(q),
                    )
                )
            if filters.internal_referral_user_id:
                stmt = stmt.where(BillingInvoice.internal_referral_user_id == filters.internal_referral_user_id)
            if filters.status:
                stmt = stmt.where(BillingInvoice.status == filters.status)
            if filters.date_from:
                stmt = stmt.where(cast(BillingInvoice.created_at, Date) >= filters.date_from)
            if filters.date_to:
                stmt = stmt.where(cast(BillingInvoice.created_at, Date) <= filters.date_to)
        return list(self.db.scalars(stmt).unique())

    def get_invoice(self, invoice_id: UUID) -> BillingInvoice | None:
        stmt = (
            select(BillingInvoice)
            .options(
                joinedload(BillingInvoice.patient),
                joinedload(BillingInvoice.items),
                joinedload(BillingInvoice.referred_doctor),
                joinedload(BillingInvoice.payments),
                joinedload(BillingInvoice.refunds),
            )
            .where(BillingInvoice.id == invoice_id)
        )
        return self.db.scalar(stmt)

    def get_invoice_by_source(self, *, source_opd_visit_id: UUID | None = None, source_ipd_admission_id: UUID | None = None, billing_stage: str | None = None) -> BillingInvoice | None:
        stmt = select(BillingInvoice).where(BillingInvoice.is_active.is_(True), BillingInvoice.status != "void")
        if source_opd_visit_id:
            stmt = stmt.where(BillingInvoice.source_opd_visit_id == source_opd_visit_id)
        if source_ipd_admission_id:
            stmt = stmt.where(BillingInvoice.source_ipd_admission_id == source_ipd_admission_id)
        if billing_stage:
            stmt = stmt.where(BillingInvoice.billing_stage == billing_stage)
        return self.db.scalar(stmt.order_by(BillingInvoice.created_at.desc()))

    def has_item_for_opd_order(self, order_id: UUID) -> bool:
        stmt = select(BillingInvoiceItem.id).join(BillingInvoiceItem.invoice).where(
            BillingInvoiceItem.source_opd_visit_order_id == order_id,
            BillingInvoiceItem.is_active.is_(True),
            BillingInvoice.is_active.is_(True),
            BillingInvoice.status != "void",
        )
        return self.db.scalar(stmt.limit(1)) is not None

    def create_invoice(self, invoice: BillingInvoice) -> BillingInvoice:
        self.db.add(invoice)
        self.db.flush()
        return invoice

    def create_payment(self, payment: BillingPayment) -> BillingPayment:
        self.db.add(payment)
        self.db.flush()
        return payment

    def create_refund(self, refund: BillingRefund) -> BillingRefund:
        self.db.add(refund)
        self.db.flush()
        return refund

    def get_settings(self, branch_id: UUID | None) -> BillingSetting | None:
        stmt = select(BillingSetting)
        if branch_id:
            stmt = stmt.where(BillingSetting.branch_id == branch_id)
        else:
            stmt = stmt.where(BillingSetting.branch_id.is_(None))
        return self.db.scalar(stmt)

    def create_settings(self, settings: BillingSetting) -> BillingSetting:
        self.db.add(settings)
        self.db.flush()
        return settings

    def get_payment(self, payment_id: UUID) -> BillingPayment | None:
        return self.db.get(BillingPayment, payment_id)

    def get_summary(self, branch_id: UUID | None, filters: BillingInvoiceFilterParams | None = None):
        stmt = select(
            func.coalesce(func.sum(case((BillingInvoice.status == "posted", 1), else_=0)), 0),
            func.coalesce(func.sum(case((BillingInvoice.status == "void", 1), else_=0)), 0),
            func.coalesce(func.sum(case((BillingInvoice.status == "posted", BillingInvoice.sub_total), else_=0)), 0),
            func.coalesce(func.sum(case((BillingInvoice.status == "posted", BillingInvoice.discount_amount), else_=0)), 0),
            func.coalesce(func.sum(case((BillingInvoice.status == "posted", BillingInvoice.total_amount), else_=0)), 0),
            func.coalesce(func.sum(case((BillingInvoice.status == "posted", BillingInvoice.referred_doctor_amount), else_=0)), 0),
        )
        if branch_id:
            stmt = stmt.where(BillingInvoice.branch_id == branch_id)
        if filters:
            if filters.internal_referral_user_id:
                stmt = stmt.where(BillingInvoice.internal_referral_user_id == filters.internal_referral_user_id)
            if filters.status:
                stmt = stmt.where(BillingInvoice.status == filters.status)
            if filters.date_from:
                stmt = stmt.where(cast(BillingInvoice.created_at, Date) >= filters.date_from)
            if filters.date_to:
                stmt = stmt.where(cast(BillingInvoice.created_at, Date) <= filters.date_to)
        return self.db.execute(stmt).one()

    def get_referral_summary(self, branch_id: UUID | None, filters: BillingInvoiceFilterParams | None = None):
        stmt = (
            select(
                BillingInvoice.internal_referral_user_id,
                func.coalesce(User.full_name, BillingInvoice.referred_doctor_name, "Unassigned"),
                func.count(BillingInvoice.id),
                func.coalesce(func.sum(BillingInvoice.total_amount), 0),
                func.coalesce(func.sum(BillingInvoice.referred_doctor_amount), 0),
            )
            .select_from(BillingInvoice)
            .outerjoin(User, BillingInvoice.internal_referral_user_id == User.id)
            .where(BillingInvoice.status == "posted")
            .group_by(BillingInvoice.internal_referral_user_id, User.full_name, BillingInvoice.referred_doctor_name)
            .order_by(func.coalesce(func.sum(BillingInvoice.referred_doctor_amount), 0).desc())
        )
        if branch_id:
            stmt = stmt.where(BillingInvoice.branch_id == branch_id)
        if filters:
            if filters.date_from:
                stmt = stmt.where(cast(BillingInvoice.created_at, Date) >= filters.date_from)
            if filters.date_to:
                stmt = stmt.where(cast(BillingInvoice.created_at, Date) <= filters.date_to)
        return list(self.db.execute(stmt).all())
