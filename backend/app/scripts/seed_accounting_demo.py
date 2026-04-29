from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.accounting import (
    Account,
    AccountGroup,
    AdvancePayment,
    BankAccount,
    BankTransaction,
    CashClosing,
    CorporateBill,
    Discount,
    DoctorCommission,
    Expense,
    ExpenseCategory,
    InsuranceClaim,
    JournalEntry,
    JournalEntryLine,
    PaymentMethod,
    PayrollAccounting,
    Refund,
    SupplierInvoice,
    SupplierPayment,
)
from app.models.branch import Branch
from app.models.hr import HRPayrollRun
from app.models.user import User


def main() -> None:
    db = SessionLocal()
    try:
        branch = db.scalars(select(Branch).order_by(Branch.created_at)).first()
        actor = db.scalars(select(User).order_by(User.created_at)).first()
        if not branch or not actor:
            print("Accounting demo seed skipped: branch or actor missing.")
            return
        accounts = _accounts(db, branch, actor)
        _payment_methods(db, branch, actor, accounts)
        _finance_workflows(db, branch, actor, accounts)
        db.commit()
        print(f"Accounting demo seed completed: {len(accounts)} accounts and finance workflows.")
    finally:
        db.close()


def _accounts(db, branch: Branch, actor: User) -> dict[str, Account]:
    groups = {}
    for name, category in [
        ("Current Assets", "assets"),
        ("Current Liabilities", "liabilities"),
        ("Operating Revenue", "revenue"),
        ("Operating Expenses", "expenses"),
        ("Equity", "equity"),
    ]:
        group = db.scalar(select(AccountGroup).where(AccountGroup.branch_id == branch.id, AccountGroup.name == name))
        if not group:
            group = AccountGroup(branch_id=branch.id, name=name, category=category, created_by=actor.id, updated_by=actor.id)
            db.add(group)
            db.flush()
        groups[category] = group
    data = [
        ("1001", "Cash", "assets", "debit", "cash", "250000"),
        ("1002", "Bank", "assets", "debit", "bank", "1250000"),
        ("1100", "Accounts Receivable", "assets", "debit", "billing", "0"),
        ("1110", "Insurance Receivable", "assets", "debit", "insurance", "0"),
        ("1120", "Corporate Receivable", "assets", "debit", "corporate", "0"),
        ("1200", "Inventory Asset", "assets", "debit", "inventory", "0"),
        ("2000", "Accounts Payable", "liabilities", "credit", "supplier", "0"),
        ("2100", "Salary Payable", "liabilities", "credit", "payroll", "0"),
        ("4000", "OPD Revenue", "revenue", "credit", "opd", "0"),
        ("4010", "IPD Revenue", "revenue", "credit", "ipd", "0"),
        ("4020", "Emergency Revenue", "revenue", "credit", "er", "0"),
        ("4030", "Pharmacy Revenue", "revenue", "credit", "pharmacy", "0"),
        ("4040", "Lab Revenue", "revenue", "credit", "lab", "0"),
        ("4050", "Radiology Revenue", "revenue", "credit", "radiology", "0"),
        ("4060", "OT Revenue", "revenue", "credit", "ot", "0"),
        ("5000", "Salary Expense", "expenses", "debit", "hr", "0"),
        ("5010", "Medicine Purchase Expense", "expenses", "debit", "pharmacy", "0"),
        ("5020", "Reagent Expense", "expenses", "debit", "lab", "0"),
        ("5030", "Utility Expense", "expenses", "debit", "admin", "0"),
        ("5040", "Maintenance Expense", "expenses", "debit", "admin", "0"),
    ]
    result = {}
    for code, name, category, normal, module, opening in data:
        account = db.scalar(select(Account).where(Account.branch_id == branch.id, Account.account_code == code))
        if not account:
            account = Account(branch_id=branch.id, group_id=groups[category].id, account_code=code, name=name, category=category, normal_balance=normal, module_key=module, opening_balance=Decimal(opening), current_balance=Decimal(opening), created_by=actor.id, updated_by=actor.id)
            db.add(account)
            db.flush()
        result[code] = account
    return result


def _payment_methods(db, branch: Branch, actor: User, accounts: dict[str, Account]) -> None:
    for name, method_type, account_code in [
        ("Cash", "cash", "1001"),
        ("Bank Transfer", "bank", "1002"),
        ("Card", "card", "1002"),
        ("Mobile Banking", "mobile_banking", "1002"),
        ("Cheque", "cheque", "1002"),
        ("Insurance", "insurance", "1110"),
        ("Corporate Credit", "corporate", "1120"),
    ]:
        method = db.scalar(select(PaymentMethod).where(PaymentMethod.branch_id == branch.id, PaymentMethod.name == name))
        if not method:
            db.add(PaymentMethod(branch_id=branch.id, name=name, method_type=method_type, settlement_account_id=accounts[account_code].id, requires_reference=method_type != "cash", created_by=actor.id, updated_by=actor.id))


def _finance_workflows(db, branch: Branch, actor: User, accounts: dict[str, Account]) -> None:
    now = datetime.now(UTC)
    today = date.today()
    if not db.scalar(select(BankAccount).where(BankAccount.branch_id == branch.id, BankAccount.account_number == "HMS-001")):
        bank = BankAccount(branch_id=branch.id, account_name="Hospital Main Collection", bank_name="Demo Bank", account_number="HMS-001", current_balance=Decimal("1250000"), created_by=actor.id, updated_by=actor.id)
        db.add(bank)
        db.flush()
        db.add(BankTransaction(branch_id=branch.id, bank_account_id=bank.id, transaction_date=today, transaction_type="deposit", reference_number="BNK-DEMO-001", amount=Decimal("185000"), reconciliation_status="matched", created_by=actor.id, updated_by=actor.id))
    categories = []
    for name, budget in [("Salary", "900000"), ("Electricity", "120000"), ("Maintenance", "80000"), ("Reagent Purchase", "160000"), ("Cleaning Supplies", "45000")]:
        cat = db.scalar(select(ExpenseCategory).where(ExpenseCategory.branch_id == branch.id, ExpenseCategory.name == name))
        if not cat:
            cat = ExpenseCategory(branch_id=branch.id, name=name, monthly_budget=Decimal(budget), created_by=actor.id, updated_by=actor.id)
            db.add(cat)
            db.flush()
        categories.append(cat)
    if not db.scalar(select(SupplierInvoice).where(SupplierInvoice.branch_id == branch.id, SupplierInvoice.invoice_number == "SUP-DEMO-001")):
        db.add(SupplierInvoice(branch_id=branch.id, supplier_name="LabTech Reagents", invoice_number="SUP-DEMO-001", invoice_date=today - timedelta(days=9), due_date=today + timedelta(days=6), category="reagent", gross_amount=Decimal("145000"), paid_amount=Decimal("45000"), due_amount=Decimal("100000"), status="partial", note="CBC and biochemistry reagent purchase", created_by=actor.id, updated_by=actor.id))
        db.add(SupplierPayment(branch_id=branch.id, payment_number="SPAY-DEMO-001", amount=Decimal("45000"), payment_method="bank", paid_at=now - timedelta(days=2), status="approved", approved_by_user_id=actor.id, created_by=actor.id, updated_by=actor.id))
    for idx, (vendor, amount, category) in enumerate([("DESCO Electricity", "82000", categories[1]), ("Biomedical Maintenance Ltd", "36000", categories[2]), ("CleanCare Services", "22000", categories[4])], start=1):
        if not db.scalar(select(Expense).where(Expense.branch_id == branch.id, Expense.expense_number == f"EXP-DEMO-{idx:03d}")):
            db.add(Expense(branch_id=branch.id, category_id=category.id, expense_number=f"EXP-DEMO-{idx:03d}", expense_date=today - timedelta(days=idx), vendor_name=vendor, department_name="Administration", amount=Decimal(amount), payment_method="bank", status="approved", description=f"{vendor} monthly expense", approved_by_user_id=actor.id, created_by=actor.id, updated_by=actor.id))
    for model, key, entity in [
        (AdvancePayment, "receipt_number", AdvancePayment(branch_id=branch.id, receipt_number="ADV-DEMO-001", source_module="ipd", amount=Decimal("50000"), adjusted_amount=Decimal("12000"), balance_amount=Decimal("38000"), payment_method="cash", status="active", collected_by_user_id=actor.id, created_by=actor.id, updated_by=actor.id)),
        (Refund, "refund_number", Refund(branch_id=branch.id, refund_number="REF-DEMO-001", refund_type="overpayment", amount=Decimal("3500"), payment_method="cash", reason="Overpayment refund", status="pending", processed_by_user_id=actor.id, created_by=actor.id, updated_by=actor.id)),
        (Discount, "discount_category", Discount(branch_id=branch.id, discount_category="poor_patient", requested_amount=Decimal("6000"), approved_amount=Decimal("6000"), reason="Management approved patient support", status="approved", approved_by_user_id=actor.id, created_by=actor.id, updated_by=actor.id)),
        (InsuranceClaim, "claim_number", InsuranceClaim(branch_id=branch.id, claim_number="INS-DEMO-001", provider_name="Pragati Insurance", claim_amount=Decimal("85000"), approved_amount=Decimal("65000"), patient_payable_amount=Decimal("20000"), status="approved", submitted_at=now - timedelta(days=4), due_date=today + timedelta(days=10), created_by=actor.id, updated_by=actor.id)),
        (CorporateBill, "bill_number", CorporateBill(branch_id=branch.id, company_name="ABC Garments Ltd", bill_number="CORP-DEMO-001", bill_month=today.strftime("%Y-%m"), gross_amount=Decimal("180000"), discount_amount=Decimal("12000"), net_amount=Decimal("168000"), paid_amount=Decimal("50000"), due_amount=Decimal("118000"), due_date=today + timedelta(days=20), status="partial", created_by=actor.id, updated_by=actor.id)),
        (DoctorCommission, "reference_number", DoctorCommission(branch_id=branch.id, doctor_name="Dr. Rahman", source_module="opd", reference_number="DOC-COM-DEMO-001", gross_amount=Decimal("45000"), commission_percentage=Decimal("20"), commission_amount=Decimal("9000"), status="payable", created_by=actor.id, updated_by=actor.id)),
        (CashClosing, "closing_date", CashClosing(branch_id=branch.id, cashier_user_id=actor.id, closing_date=today, opening_balance=Decimal("25000"), cash_collection=Decimal("76000"), refunds=Decimal("3500"), cash_expenses=Decimal("4200"), expected_cash=Decimal("93300"), actual_cash=Decimal("93200"), difference_amount=Decimal("-100"), status="pending", remarks="Minor rounding difference", created_by=actor.id, updated_by=actor.id)),
    ]:
        value = getattr(entity, key)
        if not db.scalar(select(model).where(model.branch_id == branch.id, getattr(model, key) == value)):
            db.add(entity)
    payroll = db.scalars(select(HRPayrollRun).where(HRPayrollRun.branch_id == branch.id).order_by(HRPayrollRun.created_at.desc())).first()
    if payroll and not db.scalar(select(PayrollAccounting).where(PayrollAccounting.payroll_run_id == payroll.id)):
        db.add(PayrollAccounting(branch_id=branch.id, payroll_run_id=payroll.id, payroll_month=payroll.payroll_month, gross_salary=payroll.total_gross_salary, deductions=payroll.total_deductions, net_salary_payable=payroll.total_net_salary, status="payable", created_by=actor.id, updated_by=actor.id))
    if not db.scalar(select(JournalEntry).where(JournalEntry.branch_id == branch.id, JournalEntry.journal_number == "JE-DEMO-001")):
        entry = JournalEntry(branch_id=branch.id, journal_number="JE-DEMO-001", journal_date=today, source_module="demo", source_reference="Opening finance control", narration="Opening bank balance and equity posting", status="posted", total_debit=Decimal("1250000"), total_credit=Decimal("1250000"), posted_at=now, approved_by_user_id=actor.id, created_by=actor.id, updated_by=actor.id)
        entry.lines.append(JournalEntryLine(account_id=accounts["1002"].id, account_code="1002", account_name="Bank", debit_amount=Decimal("1250000"), credit_amount=Decimal("0"), created_by=actor.id, updated_by=actor.id))
        entry.lines.append(JournalEntryLine(account_code="3000", account_name="Owner Equity", debit_amount=Decimal("0"), credit_amount=Decimal("1250000"), created_by=actor.id, updated_by=actor.id))
        db.add(entry)


if __name__ == "__main__":
    main()
