from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.accounting import Expense, ExpenseCategory
from app.models.billing import BillingInvoice, BillingPayment
from app.models.patient import Patient
from app.scripts.seed_demo_workflows import build_invoice, get_demo_context


def seed_dashboard_timeseries(days: int = 30) -> str:
    session = SessionLocal()
    try:
        ctx = get_demo_context(session)
        branch = ctx["branch"]  # type: ignore[assignment]
        accountant = ctx["accountant"]  # type: ignore[assignment]
        patient_users = ctx["patient_users"]  # type: ignore[assignment]
        services = ctx["services"]  # type: ignore[assignment]

        categories = list(
            session.scalars(
                select(ExpenseCategory).where(
                    ExpenseCategory.is_active.is_(True),
                    (ExpenseCategory.branch_id == branch.id) | (ExpenseCategory.branch_id.is_(None)),
                )
            )
        )
        if not categories:
            # fallback: no categories -> nothing to seed for expenses
            categories = []

        patient_list: list[Patient] = []
        for user in patient_users.values():
            if user.patient:
                patient_list.append(user.patient)
        if not patient_list:
            # last resort: pick any patient from branch
            patient_list = list(session.scalars(select(Patient).where(Patient.branch_id == branch.id).limit(10)))

        if not patient_list:
            return "No demo patients available to seed timeseries."

        created_invoices = 0
        created_expenses = 0

        for offset in range(days - 1, -1, -1):
            day = date.today() - timedelta(days=offset)
            day_dt = datetime(day.year, day.month, day.day, 10, 0, tzinfo=UTC)

            # Create 2 payments per day (idempotent by invoice number)
            for idx in range(1, 3):
                invoice_number = f"INV-TS-{day.strftime('%Y%m%d')}-{idx:02d}"
                exists = session.scalar(select(BillingInvoice.id).where(BillingInvoice.invoice_number == invoice_number))
                if exists:
                    continue

                patient = patient_list[(offset + idx) % len(patient_list)]
                items = [
                    (services["OPD-CONS-GEN"], Decimal("1")),
                    (services["INV-LAB-CBC"], Decimal("1")) if idx == 1 else (services["INV-RAD-CXR"], Decimal("1")),
                ]
                paid_amount = sum(service.unit_price * qty for service, qty in items)

                invoice = build_invoice(
                    branch_id=branch.id,
                    patient_id=patient.id,
                    accountant_id=accountant.id,
                    invoice_number=invoice_number,
                    note="Auto-seeded dashboard timeseries invoice",
                    items=items,
                    paid_amount=paid_amount,
                )
                # force timestamps near the day
                invoice.created_at = day_dt
                invoice.updated_at = day_dt
                session.add(invoice)
                session.flush()

                payment = BillingPayment(
                    invoice_id=invoice.id,
                    patient_id=patient.id,
                    branch_id=branch.id,
                    receipt_number=f"RCT-TS-{day.strftime('%Y%m%d')}-{idx:02d}",
                    payment_method="cash" if idx == 1 else "card",
                    amount=paid_amount,
                    note="Auto-seeded dashboard timeseries payment",
                    received_at=day_dt + timedelta(hours=1),
                    collected_by_user_id=accountant.id,
                    created_by=accountant.id,
                    updated_by=accountant.id,
                )
                session.add(payment)
                created_invoices += 1

            # Create 1–2 expenses per day (idempotent by expense_number)
            if categories:
                for idx in range(1, 3):
                    expense_number = f"EXP-TS-{day.strftime('%Y%m%d')}-{idx:02d}"
                    exists = session.scalar(select(Expense.id).where(Expense.expense_number == expense_number))
                    if exists:
                        continue
                    category = categories[(offset + idx) % len(categories)]
                    amount = Decimal("1200.00") + Decimal((offset + idx) % 7) * Decimal("350.00")
                    expense = Expense(
                        branch_id=branch.id,
                        category_id=category.id,
                        expense_number=expense_number,
                        expense_date=day,
                        vendor_name="Demo Vendor",
                        department_name="Administration",
                        amount=amount,
                        payment_method="cash",
                        recurring=False,
                        status="approved",
                        description="Auto-seeded dashboard timeseries expense",
                        approved_by_user_id=accountant.id,
                        created_by=accountant.id,
                        updated_by=accountant.id,
                    )
                    session.add(expense)
                    created_expenses += 1
                    if idx == 1:
                        break  # 1 expense most days

        session.commit()
        return f"Seeded dashboard timeseries: {created_invoices} invoices/payments and {created_expenses} expenses."
    finally:
        session.close()


def main() -> None:
    print(seed_dashboard_timeseries())


if __name__ == "__main__":
    main()
