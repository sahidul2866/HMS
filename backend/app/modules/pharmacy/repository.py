from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.encounter import OPDVisit, OPDVisitOrder
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


class PharmacyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def paginate(self, stmt, *, page: int, page_size: int) -> tuple[list[Any], int]:
        total = int(self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0)
        items = list(self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique())
        return items, total

    def create(self, entity):
        self.db.add(entity)
        self.db.flush()
        return entity

    def list_dispenses(self, branch_id=None) -> list[PharmacyDispense]:
        stmt = (
            select(PharmacyDispense)
            .options(
                joinedload(PharmacyDispense.patient),
                joinedload(PharmacyDispense.source_visit),
                joinedload(PharmacyDispense.dispensed_by),
            )
            .where(PharmacyDispense.is_active.is_(True))
            .order_by(PharmacyDispense.created_at.desc())
        )
        if branch_id:
            stmt = stmt.where(PharmacyDispense.branch_id == branch_id)
        return list(self.db.scalars(stmt))

    def get_dispense(self, dispense_id) -> PharmacyDispense | None:
        stmt = (
            select(PharmacyDispense)
            .options(
                joinedload(PharmacyDispense.patient),
                joinedload(PharmacyDispense.source_visit),
                joinedload(PharmacyDispense.dispensed_by),
                joinedload(PharmacyDispense.source_visit_order),
            )
            .where(PharmacyDispense.id == dispense_id)
        )
        return self.db.scalar(stmt)

    def get_net_dispensed_quantity(self, order_id) -> float:
        stmt = select(func.coalesce(func.sum(PharmacyDispense.quantity - PharmacyDispense.returned_quantity), 0)).where(
            PharmacyDispense.source_visit_order_id == order_id,
            PharmacyDispense.is_active.is_(True),
        )
        return float(self.db.scalar(stmt) or 0)

    def get_summary(self, branch_id=None, summary_date: date | None = None) -> tuple[int, int, int, int, int, int]:
        today = summary_date or date.today()
        dispenses_stmt = select(
            func.count(PharmacyDispense.id),
            func.count().filter(func.date(PharmacyDispense.created_at) == today),
            func.count().filter(PharmacyDispense.status == "partial"),
            func.count().filter(PharmacyDispense.status.in_(["returned", "partially_returned"])),
        ).where(PharmacyDispense.is_active.is_(True))
        if branch_id:
            dispenses_stmt = dispenses_stmt.where(PharmacyDispense.branch_id == branch_id)
        dispense_row = self.db.execute(dispenses_stmt).one()

        pending_stmt = (
            select(
                func.count(OPDVisitOrder.id),
                func.count().filter(OPDVisitOrder.visit.has(OPDVisit.status.in_(["billed", "completed"]))),
            )
            .where(OPDVisitOrder.order_type == "prescription", OPDVisitOrder.status.in_(["pending", "in_progress"]), OPDVisitOrder.is_active.is_(True))
        )
        if branch_id:
            pending_stmt = pending_stmt.where(OPDVisitOrder.visit.has(OPDVisit.branch_id == branch_id))
        pending_row = self.db.execute(pending_stmt).one()

        return dispense_row[0], dispense_row[1], pending_row[0], pending_row[1], dispense_row[2], dispense_row[3]

    def get_dashboard_summary(self, branch_id=None) -> tuple[int, int, int, int, int, int]:
        medicine_stmt = select(
            func.count(PharmacyMedicine.id),
            func.count().filter(PharmacyMedicine.stock_quantity <= PharmacyMedicine.reorder_level),
        ).where(PharmacyMedicine.is_active.is_(True))
        customer_stmt = select(func.count(PharmacyCustomer.id)).where(PharmacyCustomer.is_active.is_(True))
        sale_stmt = select(func.count(PharmacySale.id)).where(PharmacySale.is_active.is_(True))
        return_stmt = select(func.count(PharmacySaleReturn.id)).where(PharmacySaleReturn.is_active.is_(True))
        investigation_stmt = select(func.count(PharmacyInvestigation.id)).where(PharmacyInvestigation.is_active.is_(True))
        if branch_id:
            medicine_stmt = medicine_stmt.where(PharmacyMedicine.branch_id == branch_id)
            customer_stmt = customer_stmt.where(PharmacyCustomer.branch_id == branch_id)
            sale_stmt = sale_stmt.where(PharmacySale.branch_id == branch_id)
            return_stmt = return_stmt.where(PharmacySaleReturn.branch_id == branch_id)
            investigation_stmt = investigation_stmt.where(PharmacyInvestigation.branch_id == branch_id)
        medicine_row = self.db.execute(medicine_stmt).one()
        return (
            medicine_row[0],
            medicine_row[1],
            int(self.db.scalar(customer_stmt) or 0),
            int(self.db.scalar(sale_stmt) or 0),
            int(self.db.scalar(return_stmt) or 0),
            int(self.db.scalar(investigation_stmt) or 0),
        )

    def get_medicine_type(self, entity_id):
        return self.db.get(PharmacyMedicineType, entity_id)

    def get_generic(self, entity_id):
        return self.db.get(PharmacyGeneric, entity_id)

    def get_company(self, entity_id):
        return self.db.get(PharmacyCompany, entity_id)

    def get_customer(self, entity_id):
        stmt = (
            select(PharmacyCustomer)
            .options(joinedload(PharmacyCustomer.patient))
            .where(PharmacyCustomer.id == entity_id)
        )
        return self.db.scalar(stmt)

    def get_customer_by_patient(self, patient_id):
        stmt = (
            select(PharmacyCustomer)
            .options(joinedload(PharmacyCustomer.patient))
            .where(
                PharmacyCustomer.patient_id == patient_id,
                PharmacyCustomer.is_active.is_(True),
            )
            .order_by(PharmacyCustomer.created_at.desc())
        )
        return self.db.scalar(stmt)

    def get_medicine(self, entity_id, *, for_update: bool = False):
        stmt = (
            select(PharmacyMedicine)
            .options(
                joinedload(PharmacyMedicine.medicine_type),
                joinedload(PharmacyMedicine.generic),
                joinedload(PharmacyMedicine.company),
            )
            .where(PharmacyMedicine.id == entity_id)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_purchase(self, entity_id):
        stmt = (
            select(PharmacyPurchase)
            .options(joinedload(PharmacyPurchase.medicine), joinedload(PharmacyPurchase.purchased_by))
            .where(PharmacyPurchase.id == entity_id)
        )
        return self.db.scalar(stmt)

    def get_latest_purchase_for_medicine(self, medicine_id, *, batch_no: str | None = None):
        stmt = (
            select(PharmacyPurchase)
            .where(
                PharmacyPurchase.medicine_id == medicine_id,
                PharmacyPurchase.is_active.is_(True),
            )
            .order_by(PharmacyPurchase.purchase_date.desc(), PharmacyPurchase.created_at.desc())
        )
        if batch_no:
            stmt = stmt.where(PharmacyPurchase.batch_no == batch_no)
        return self.db.scalar(stmt)

    def get_sale(self, entity_id):
        stmt = (
            select(PharmacySale)
            .options(
                joinedload(PharmacySale.customer).joinedload(PharmacyCustomer.patient),
                joinedload(PharmacySale.patient),
                joinedload(PharmacySale.source_visit),
                joinedload(PharmacySale.sold_by),
                joinedload(PharmacySale.items).joinedload(PharmacySaleItem.medicine),
                joinedload(PharmacySale.items).joinedload(PharmacySaleItem.source_visit_order),
                joinedload(PharmacySale.returns),
            )
            .where(PharmacySale.id == entity_id)
        )
        return self.db.scalar(stmt)

    def get_sale_item(self, entity_id):
        stmt = (
            select(PharmacySaleItem)
            .options(joinedload(PharmacySaleItem.medicine), joinedload(PharmacySaleItem.sale))
            .where(PharmacySaleItem.id == entity_id)
        )
        return self.db.scalar(stmt)

    def get_sale_return(self, entity_id):
        stmt = (
            select(PharmacySaleReturn)
            .options(
                joinedload(PharmacySaleReturn.sale),
                joinedload(PharmacySaleReturn.sale_item),
                joinedload(PharmacySaleReturn.customer),
                joinedload(PharmacySaleReturn.medicine),
                joinedload(PharmacySaleReturn.returned_by),
            )
            .where(PharmacySaleReturn.id == entity_id)
        )
        return self.db.scalar(stmt)

    def get_stock_movement(self, entity_id):
        stmt = (
            select(PharmacyStockMovement)
            .options(joinedload(PharmacyStockMovement.medicine))
            .where(PharmacyStockMovement.id == entity_id)
        )
        return self.db.scalar(stmt)

    def get_investigation_setting(self, entity_id):
        return self.db.get(PharmacyInvestigationSetting, entity_id)

    def get_investigation(self, entity_id):
        stmt = (
            select(PharmacyInvestigation)
            .options(
                joinedload(PharmacyInvestigation.setting),
                joinedload(PharmacyInvestigation.customer).joinedload(PharmacyCustomer.patient),
                joinedload(PharmacyInvestigation.patient),
                joinedload(PharmacyInvestigation.source_visit),
                joinedload(PharmacyInvestigation.items).joinedload(PharmacyInvestigationItem.setting),
                joinedload(PharmacyInvestigation.items).joinedload(PharmacyInvestigationItem.source_visit_order),
            )
            .where(PharmacyInvestigation.id == entity_id)
        )
        return self.db.scalar(stmt)

    def has_sale_item_for_opd_order(self, order_id) -> bool:
        stmt = select(PharmacySaleItem.id).join(PharmacySaleItem.sale).where(
            PharmacySaleItem.source_visit_order_id == order_id,
            PharmacySaleItem.is_active.is_(True),
            PharmacySale.is_active.is_(True),
        )
        return self.db.scalar(stmt.limit(1)) is not None

    def has_investigation_item_for_opd_order(self, order_id, *, exclude_investigation_id=None) -> bool:
        stmt = select(PharmacyInvestigationItem.id).join(PharmacyInvestigationItem.investigation).where(
            PharmacyInvestigationItem.source_visit_order_id == order_id,
            PharmacyInvestigationItem.is_active.is_(True),
            PharmacyInvestigation.is_active.is_(True),
        )
        if exclude_investigation_id:
            stmt = stmt.where(PharmacyInvestigation.id != exclude_investigation_id)
        return self.db.scalar(stmt.limit(1)) is not None
