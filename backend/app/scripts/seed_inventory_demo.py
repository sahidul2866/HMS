from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.inventory import (
    InventoryCategory,
    InventoryItem,
    PurchaseRequest,
    Reagent,
    ReagentBatch,
    ReagentUsage,
    StockBatch,
    StockReceiving,
    Supplier,
)
from app.models.user import User


def main() -> None:
    db = SessionLocal()
    try:
        branch = db.scalars(select(Branch).order_by(Branch.created_at)).first()
        actor = db.scalars(select(User).order_by(User.created_at)).first()
        if not branch or not actor:
            print("Inventory demo seed skipped: branch or actor missing.")
            return
        supplier_map = _suppliers(db, branch, actor)
        category_map = _categories(db, branch, actor)
        items = _items(db, branch, actor, supplier_map, category_map)
        _stock(db, actor, items, supplier_map)
        reagents = _reagents(db, branch, actor, supplier_map)
        _requests(db, actor, items, supplier_map)
        db.commit()
        print(f"Inventory demo seed completed: {len(items)} items, {len(reagents)} reagents.")
    finally:
        db.close()


def _suppliers(db, branch: Branch, actor: User) -> dict[str, Supplier]:
    data = [
        ("MediSupply Bangladesh", "Rahim Uddin", "01711000001", "30 days"),
        ("SterileCare Imports", "Nabila Ahmed", "01711000002", "15 days"),
        ("LabTech Reagents", "Hasan Karim", "01711000003", "30 days"),
    ]
    result: dict[str, Supplier] = {}
    for name, contact, phone, terms in data:
        supplier = db.scalar(select(Supplier).where(Supplier.branch_id == branch.id, Supplier.name == name))
        if not supplier:
            supplier = Supplier(
                branch_id=branch.id,
                name=name,
                contact_person=contact,
                phone=phone,
                payment_terms=terms,
                rating=4,
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.add(supplier)
            db.flush()
        result[name] = supplier
    return result


def _categories(db, branch: Branch, actor: User) -> dict[str, InventoryCategory]:
    data = [
        ("OT Consumables", "consumable"),
        ("Ward Supplies", "consumable"),
        ("Lab Reagents", "reagent"),
        ("Implants", "implant"),
        ("Equipment Accessories", "equipment"),
    ]
    result: dict[str, InventoryCategory] = {}
    for name, item_type in data:
        category = db.scalar(select(InventoryCategory).where(InventoryCategory.branch_id == branch.id, InventoryCategory.name == name))
        if not category:
            category = InventoryCategory(branch_id=branch.id, name=name, item_type=item_type, created_by=actor.id, updated_by=actor.id)
            db.add(category)
            db.flush()
        result[name] = category
    return result


def _items(db, branch: Branch, actor: User, suppliers: dict[str, Supplier], categories: dict[str, InventoryCategory]) -> list[InventoryItem]:
    data = [
        ("INV-OT-001", "Surgical Drape Set", "OT Consumables", "MediSupply Bangladesh", "consumable", "set", "OT Store", 120, 25, "850"),
        ("INV-OT-002", "Sterile Gloves 7.5", "OT Consumables", "SterileCare Imports", "consumable", "pair", "OT Store", 18, 40, "55"),
        ("INV-OT-003", "Suture Vicryl 2-0", "OT Consumables", "MediSupply Bangladesh", "consumable", "piece", "OT Store", 220, 50, "310"),
        ("INV-WD-001", "IV Cannula 20G", "Ward Supplies", "MediSupply Bangladesh", "consumable", "piece", "Ward Store", 35, 60, "42"),
        ("INV-WD-002", "Normal Saline 500ml", "Ward Supplies", "MediSupply Bangladesh", "consumable", "bag", "Ward Store", 240, 80, "65"),
        ("INV-IM-001", "Orthopedic Screw Set", "Implants", "SterileCare Imports", "implant", "set", "Implant Cabinet", 8, 5, "12500"),
        ("INV-EQ-001", "ECG Electrode Pack", "Equipment Accessories", "SterileCare Imports", "equipment", "pack", "Equipment Store", 60, 20, "420"),
    ]
    items: list[InventoryItem] = []
    for code, name, category_name, supplier_name, item_type, unit, location, qty, reorder, cost in data:
        item = db.scalar(select(InventoryItem).where(InventoryItem.branch_id == branch.id, InventoryItem.item_code == code))
        if not item:
            unit_cost = Decimal(cost)
            stock_quantity = Decimal(qty)
            item = InventoryItem(
                branch_id=branch.id,
                category_id=categories[category_name].id,
                supplier_id=suppliers[supplier_name].id,
                item_code=code,
                barcode=f"BC-{code}",
                name=name,
                item_type=item_type,
                unit_of_measurement=unit,
                is_batch_tracked=True,
                reorder_level=Decimal(reorder),
                minimum_stock_level=Decimal(reorder),
                maximum_stock_level=Decimal(qty * 3),
                storage_location=location,
                stock_quantity=stock_quantity,
                stock_value=stock_quantity * unit_cost,
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.add(item)
            db.flush()
        items.append(item)
    return items


def _stock(db, actor: User, items: list[InventoryItem], suppliers: dict[str, Supplier]) -> None:
    today = date.today()
    for index, item in enumerate(items):
        batch = db.scalar(select(StockBatch).where(StockBatch.item_id == item.id, StockBatch.batch_no == f"B-{item.item_code}"))
        unit_cost = Decimal(item.stock_value or 0) / Decimal(item.stock_quantity or 1)
        if not batch:
            batch = StockBatch(
                item_id=item.id,
                batch_no=f"B-{item.item_code}",
                expiry_date=today + timedelta(days=20 + index * 45),
                manufacturing_date=today - timedelta(days=90),
                quantity=item.stock_quantity,
                location=item.storage_location,
                unit_cost=unit_cost,
                total_cost=item.stock_value,
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.add(batch)
        receiving = db.scalar(select(StockReceiving).where(StockReceiving.item_id == item.id, StockReceiving.invoice_number == f"RCV-{item.item_code}"))
        if not receiving:
            receiving = StockReceiving(
                item_id=item.id,
                supplier_id=item.supplier_id,
                invoice_number=f"RCV-{item.item_code}",
                received_date=today,
                department="Central Store",
                batch_no=f"B-{item.item_code}",
                expiry_date=today + timedelta(days=20 + index * 45),
                quantity=item.stock_quantity,
                unit_cost=unit_cost,
                total_cost=item.stock_value,
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.add(receiving)


def _reagents(db, branch: Branch, actor: User, suppliers: dict[str, Supplier]) -> list[Reagent]:
    today = date.today()
    data = [
        ("REG-CBC-001", "CBC Diluent", "hematology", "LabTech Reagents", 18, "2-8C"),
        ("REG-GLU-001", "Glucose Reagent", "biochemistry", "LabTech Reagents", 42, "2-8C"),
        ("REG-CRP-001", "CRP Latex Kit", "immunology", "LabTech Reagents", 9, "2-8C"),
    ]
    reagents: list[Reagent] = []
    for code, name, category, supplier_name, balance, storage in data:
        reagent = db.scalar(select(Reagent).where(Reagent.branch_id == branch.id, Reagent.reagent_code == code))
        if not reagent:
            reagent = Reagent(
                branch_id=branch.id,
                reagent_code=code,
                name=name,
                category=category,
                manufacturer="Demo Diagnostics Ltd",
                supplier_id=suppliers[supplier_name].id,
                storage_condition=storage,
                opening_date=today - timedelta(days=5),
                opening_balance=Decimal(balance),
                opened_balance=Decimal(balance),
                closed_balance=Decimal(balance),
                stability_days=30,
                status="active",
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.add(reagent)
            db.flush()
            batch = ReagentBatch(
                reagent_id=reagent.id,
                batch_no=f"RB-{code}",
                lot_number=f"LOT-{code}",
                expiry_date=today + timedelta(days=60),
                quantity_received=Decimal(balance),
                quantity_available=Decimal(balance),
                supplier_id=suppliers[supplier_name].id,
                status="in_use",
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.add(batch)
            db.flush()
            db.add(ReagentUsage(reagent_id=reagent.id, batch_id=batch.id, analyzer_name="Demo Analyzer", test_name=name.split()[0], quantity_used=Decimal("2"), used_at=today, created_by=actor.id, updated_by=actor.id))
        reagents.append(reagent)
    return reagents


def _requests(db, actor: User, items: list[InventoryItem], suppliers: dict[str, Supplier]) -> None:
    for item in items[:3]:
        request = db.scalar(select(PurchaseRequest).where(PurchaseRequest.item_id == item.id, PurchaseRequest.status == "requested"))
        if not request:
            db.add(
                PurchaseRequest(
                    item_id=item.id,
                    supplier_id=item.supplier_id or next(iter(suppliers.values())).id,
                    department="Central Store",
                    requested_quantity=max(Decimal("25"), Decimal(item.reorder_level or 0)),
                    priority="urgent" if Decimal(item.stock_quantity or 0) <= Decimal(item.reorder_level or 0) else "normal",
                    expected_date=date.today() + timedelta(days=3),
                    status="requested",
                    requested_by=actor.id,
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )


if __name__ == "__main__":
    main()
