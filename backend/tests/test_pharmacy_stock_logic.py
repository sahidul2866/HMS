from __future__ import annotations

import sys
import unittest
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.exceptions import AppException
from app.models.patient import Patient
from app.models.pharmacy import (
    PharmacyCustomer,
    PharmacyMedicine,
    PharmacyPurchase,
    PharmacySale,
    PharmacySaleReturn,
    PharmacyStockMovement,
)
from app.models.user import User
from app.modules.pharmacy.service import PharmacyService
from app.schemas.pharmacy import PharmacyPurchaseCreate, PharmacySaleCreate, PharmacySaleItemWrite, PharmacySaleReturnCreate


class FakeDB:
    def refresh(self, _entity) -> None:
        return None


class FakePharmacyRepository:
    def __init__(self, *, medicines: list[PharmacyMedicine], customers: list[PharmacyCustomer], users: list[User]) -> None:
        self.medicines = {item.id: item for item in medicines}
        self.customers = {item.id: item for item in customers}
        self.users = {item.id: item for item in users}
        self.purchases: dict = {}
        self.sales: dict = {}
        self.returns: dict = {}
        self.stock_movements: dict = {}

    def create(self, entity):
        if isinstance(entity, PharmacyPurchase):
            entity.medicine = self.medicines[entity.medicine_id]
            entity.purchased_by = self.users.get(entity.purchased_by_user_id)
            self.purchases[entity.id] = entity
        elif isinstance(entity, PharmacySale):
            entity.customer = self.customers[entity.customer_id]
            if entity.items is None:
                entity.items = []
            if entity.returns is None:
                entity.returns = []
            self.sales[entity.id] = entity
        elif isinstance(entity, PharmacySaleReturn):
            entity.sale = self.sales[entity.sale_id]
            entity.sale_item = self.get_sale_item(entity.sale_item_id)
            entity.customer = self.customers[entity.customer_id]
            entity.medicine = self.medicines[entity.medicine_id]
            entity.returned_by = self.users.get(entity.returned_by_user_id)
            entity.sale.returns.append(entity)
            self.returns[entity.id] = entity
        elif isinstance(entity, PharmacyStockMovement):
            entity.medicine = self.medicines[entity.medicine_id]
            self.stock_movements[entity.id] = entity
        return entity

    def get_medicine(self, entity_id, *, for_update: bool = False):  # noqa: ARG002
        return self.medicines.get(entity_id)

    def get_customer(self, entity_id):
        return self.customers.get(entity_id)

    def get_purchase(self, entity_id):
        item = self.purchases.get(entity_id)
        if item:
            item.medicine = self.medicines[item.medicine_id]
            item.purchased_by = self.users.get(item.purchased_by_user_id)
        return item

    def get_latest_purchase_for_medicine(self, medicine_id, *, batch_no: str | None = None):
        items = [item for item in self.purchases.values() if item.is_active and item.medicine_id == medicine_id]
        if batch_no:
            items = [item for item in items if item.batch_no == batch_no]
        items.sort(key=lambda item: (item.purchase_date, item.created_at), reverse=True)
        return items[0] if items else None

    def get_sale(self, entity_id):
        sale = self.sales.get(entity_id)
        if not sale:
            return None
        sale.customer = self.customers[sale.customer_id]
        for line in sale.items:
            line.medicine = self.medicines[line.medicine_id]
        for item in sale.returns:
            item.sale = sale
            item.sale_item = self.get_sale_item(item.sale_item_id)
            item.customer = self.customers[item.customer_id]
            item.medicine = self.medicines[item.medicine_id]
        return sale

    def get_sale_item(self, entity_id):
        for sale in self.sales.values():
            for line in sale.items:
                if line.id == entity_id:
                    line.medicine = self.medicines[line.medicine_id]
                    line.sale = sale
                    return line
        return None

    def get_sale_return(self, entity_id):
        item = self.returns.get(entity_id)
        if item:
            item.sale = self.sales[item.sale_id]
            item.sale_item = self.get_sale_item(item.sale_item_id)
            item.customer = self.customers[item.customer_id]
            item.medicine = self.medicines[item.medicine_id]
            item.returned_by = self.users.get(item.returned_by_user_id)
        return item


class PharmacyStockLogicTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.branch_id = uuid4()
        self.patient = Patient(
            id=uuid4(),
            branch_id=self.branch_id,
            patient_number="P-0001",
            first_name="Fatema",
            last_name="Aktar",
        )
        self.actor = User(
            id=uuid4(),
            branch_id=self.branch_id,
            username="pharmacist",
            email="pharmacist@example.com",
            full_name="Pharmacist Nadia",
            hashed_password="hashed",
        )
        self.medicine = PharmacyMedicine(
            id=uuid4(),
            branch_id=self.branch_id,
            medicine_type_id=uuid4(),
            generic_id=uuid4(),
            company_id=uuid4(),
            name="Napa 500",
            purchase_price=Decimal("1.50"),
            sale_price=Decimal("2.50"),
            stock_quantity=Decimal("10"),
            reorder_level=Decimal("2"),
        )
        self.customer = PharmacyCustomer(
            id=uuid4(),
            branch_id=self.branch_id,
            patient_id=self.patient.id,
            customer_number="CUST-001",
            name="Fatema Aktar",
        )
        self.customer.patient = self.patient

        self.service = PharmacyService(FakeDB())  # type: ignore[arg-type]
        self.service.repository = FakePharmacyRepository(medicines=[self.medicine], customers=[self.customer], users=[self.actor])
        self.service._commit_and_log = lambda **kwargs: None  # type: ignore[method-assign]
        self.service._generate_number = lambda model, prefix: f"{prefix}-TEST-0001"  # type: ignore[method-assign]

    def _create_purchase(self) -> PharmacyPurchase:
        purchase = self.service.create_purchase(
            PharmacyPurchaseCreate(
                medicine_id=self.medicine.id,
                purchase_date=date(2026, 4, 20),
                supplier_name="Demo Supplier",
                invoice_number="INV-001",
                batch_no="BATCH-01",
                expiry_date=date(2027, 4, 20),
                quantity=Decimal("5"),
                bonus_quantity=Decimal("2"),
                unit_cost=Decimal("1.80"),
                sale_price=Decimal("2.60"),
                note="Demo purchase",
            ),
            self.actor,
            {},
        )
        return self.service.repository.get_purchase(purchase.id)

    def test_purchase_increases_stock_and_records_movement(self) -> None:
        created = self._create_purchase()

        self.assertEqual(self.medicine.stock_quantity, Decimal("17"))
        self.assertEqual(created.total_amount, Decimal("9.00"))

        movements = list(self.service.repository.stock_movements.values())
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].movement_type, "purchase_in")
        self.assertEqual(movements[0].quantity_change, Decimal("7"))
        self.assertEqual(movements[0].stock_before, Decimal("10"))
        self.assertEqual(movements[0].stock_after, Decimal("17"))
        self.assertEqual(movements[0].batch_no, "BATCH-01")

    def test_sale_decreases_stock_and_records_movement(self) -> None:
        self._create_purchase()

        sale = self.service.create_sale(
            PharmacySaleCreate(
                customer_id=self.customer.id,
                patient_id=self.patient.id,
                sale_date=date(2026, 4, 20),
                discount_amount=Decimal("2.00"),
                note="Counter sale",
                items=[
                    PharmacySaleItemWrite(
                        medicine_id=self.medicine.id,
                        quantity=Decimal("4"),
                        unit_price=Decimal("2.60"),
                    )
                ],
            ),
            self.actor,
            {},
        )

        self.assertEqual(self.medicine.stock_quantity, Decimal("13"))
        self.assertEqual(sale.subtotal, Decimal("10.40"))
        self.assertEqual(sale.net_payable, Decimal("8.40"))
        self.assertEqual(sale.items[0].batch_no, "BATCH-01")

        movements = list(self.service.repository.stock_movements.values())
        self.assertEqual(len(movements), 2)
        self.assertEqual(movements[-1].movement_type, "sale_out")
        self.assertEqual(movements[-1].quantity_change, Decimal("-4"))
        self.assertEqual(movements[-1].stock_before, Decimal("17"))
        self.assertEqual(movements[-1].stock_after, Decimal("13"))

    def test_sale_blocks_when_stock_is_insufficient(self) -> None:
        with self.assertRaises(AppException) as context:
            self.service.create_sale(
                PharmacySaleCreate(
                    customer_id=self.customer.id,
                    patient_id=self.patient.id,
                    sale_date=date(2026, 4, 20),
                    discount_amount=Decimal("0"),
                    note="Oversell",
                    items=[
                        PharmacySaleItemWrite(
                            medicine_id=self.medicine.id,
                            quantity=Decimal("11"),
                            unit_price=Decimal("2.50"),
                        )
                    ],
                ),
                self.actor,
                {},
            )

        self.assertEqual(context.exception.code, "insufficient_stock")
        self.assertEqual(self.medicine.stock_quantity, Decimal("10"))
        self.assertEqual(len(self.service.repository.stock_movements), 0)

    def test_return_restores_stock_and_records_movement(self) -> None:
        self._create_purchase()
        sale = self.service.create_sale(
            PharmacySaleCreate(
                customer_id=self.customer.id,
                patient_id=self.patient.id,
                sale_date=date(2026, 4, 20),
                discount_amount=Decimal("0"),
                note="Counter sale",
                items=[
                    PharmacySaleItemWrite(
                        medicine_id=self.medicine.id,
                        quantity=Decimal("3"),
                        unit_price=Decimal("2.60"),
                    )
                ],
            ),
            self.actor,
            {},
        )

        return_record = self.service.create_return(
            PharmacySaleReturnCreate(
                sale_id=sale.id,
                sale_item_id=sale.items[0].id,
                returned_at=date(2026, 4, 20),
                quantity=Decimal("1"),
                note="Customer returned one unit",
            ),
            self.actor,
            {},
        )

        refreshed_sale = self.service.repository.get_sale(sale.id)
        self.assertEqual(self.medicine.stock_quantity, Decimal("15"))
        self.assertEqual(return_record.total_amount, Decimal("2.60"))
        self.assertEqual(refreshed_sale.status, "partially_returned")
        self.assertEqual(refreshed_sale.return_amount, Decimal("2.60"))

        movements = list(self.service.repository.stock_movements.values())
        self.assertEqual(len(movements), 3)
        self.assertEqual(movements[-1].movement_type, "sale_return_in")
        self.assertEqual(movements[-1].quantity_change, Decimal("1"))
        self.assertEqual(movements[-1].stock_before, Decimal("14"))
        self.assertEqual(movements[-1].stock_after, Decimal("15"))


if __name__ == "__main__":
    unittest.main()
