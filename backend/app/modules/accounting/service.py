from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.accounting import (
    Account,
    AccountingAuditLog,
    AccountingJournal,
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
    PayrollAccounting,
    Refund,
    SupplierInvoice,
)
from app.models.billing import BillingInvoice, BillingPayment, BillingRefund
from app.models.hr import HRPayrollRun
from app.models.inventory import InventoryItem
from app.models.ot import OTBillingItem
from app.models.pharmacy import PharmacySale
from app.models.user import User
from app.modules.accounting.repository import AccountingRepository
from app.modules.audit.service import AuditService
from app.schemas.accounting import (
    AccountCreate,
    AccountingDashboardRead,
    AccountingJournalCreate,
    AccountingKPI,
    AccountingChartPoint,
    AccountingAlert,
    FinanceRecordRead,
    JournalEntryCreate,
)
from app.utils.enums import AuditAction


class AccountingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AccountingRepository(db)

    def list_journals(self, actor: User) -> list[AccountingJournal]:
        return self.repository.list_journals(actor.branch_id)

    def post_journal(self, payload: AccountingJournalCreate, actor: User, context: dict[str, str | None]) -> AccountingJournal:
        sequence = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        journal = AccountingJournal(
            **payload.model_dump(),
            journal_number=f"JRN-{sequence}",
            branch_id=payload.branch_id or actor.branch_id,
            posted_by_user_id=actor.id,
            status="posted",
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_journal(journal)
        self._audit(actor, "accounting.legacy_journal.post", "AccountingJournal", str(journal.id), context, {"journal_number": journal.journal_number})
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.ACCOUNTING_POST,
            module="accounting",
            entity_type="accounting_journal",
            entity_id=str(journal.id),
            detail={"journal_number": journal.journal_number, "reference": journal.reference},
            context=context,
        )
        self.db.commit()
        self.db.refresh(journal)
        return journal

    def dashboard(self, actor: User) -> AccountingDashboardRead:
        branch_id = actor.branch_id
        today = date.today()
        month_start = today.replace(day=1)
        today_start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)

        collection_today = self._sum(BillingPayment.amount, BillingPayment.received_at >= today_start, BillingPayment.branch_id == branch_id)
        monthly_revenue = self._sum(BillingInvoice.total_amount, BillingInvoice.created_at >= month_start, BillingInvoice.branch_id == branch_id, BillingInvoice.status != "void")
        expenses = self._sum(Expense.amount, Expense.expense_date >= month_start, Expense.branch_id == branch_id, Expense.status.in_(["approved", "paid"]))
        pending_due = self._sum(BillingInvoice.due_amount, BillingInvoice.branch_id == branch_id, BillingInvoice.payment_status.in_(["unpaid", "partial"]))
        discounts = self._sum(BillingInvoice.discount_amount, BillingInvoice.created_at >= month_start, BillingInvoice.branch_id == branch_id)
        refunds_today = self._sum(BillingRefund.amount, BillingRefund.refunded_at >= today_start, BillingRefund.branch_id == branch_id)
        insurance_due = self._sum(InsuranceClaim.claim_amount - InsuranceClaim.paid_amount, InsuranceClaim.branch_id == branch_id, InsuranceClaim.status != "paid")
        supplier_due = self._sum(SupplierInvoice.due_amount, SupplierInvoice.branch_id == branch_id, SupplierInvoice.status != "paid")
        payroll_due = self._sum(PayrollAccounting.net_salary_payable - PayrollAccounting.paid_amount, PayrollAccounting.branch_id == branch_id, PayrollAccounting.status != "paid")
        corporate_due = self._sum(CorporateBill.due_amount, CorporateBill.branch_id == branch_id, CorporateBill.status != "paid")
        inventory_value = self._sum(InventoryItem.stock_value, InventoryItem.branch_id == branch_id, InventoryItem.is_active.is_(True))
        pharmacy_revenue = self._sum(PharmacySale.net_payable, PharmacySale.branch_id == branch_id, PharmacySale.created_at >= month_start)
        ot_revenue = self._sum(OTBillingItem.amount, OTBillingItem.created_at >= month_start)

        cash_balance = collection_today - refunds_today - self._sum(Expense.amount, Expense.expense_date == today, Expense.payment_method == "cash", Expense.branch_id == branch_id)
        bank_balance = self._sum(BankAccount.current_balance, BankAccount.branch_id == branch_id)
        net_profit = monthly_revenue - expenses

        return AccountingDashboardRead(
            kpis=[
                AccountingKPI(label="Today's Collection", value=collection_today, tone="good"),
                AccountingKPI(label="Monthly Revenue", value=monthly_revenue, tone="info"),
                AccountingKPI(label="Total Expenses", value=expenses, tone="warn"),
                AccountingKPI(label="Net Profit / Loss", value=net_profit, tone="good" if net_profit >= 0 else "danger"),
                AccountingKPI(label="Cash in Hand", value=cash_balance, tone="info"),
                AccountingKPI(label="Bank Balance", value=bank_balance, tone="info"),
                AccountingKPI(label="Pending Patient Dues", value=pending_due, tone="danger" if pending_due else "good"),
                AccountingKPI(label="Insurance Claims", value=insurance_due, tone="warn"),
                AccountingKPI(label="Supplier Payables", value=supplier_due, tone="warn"),
                AccountingKPI(label="Payroll Payable", value=payroll_due, tone="warn"),
                AccountingKPI(label="Refunds Today", value=refunds_today, tone="danger" if refunds_today else "good"),
                AccountingKPI(label="Discounts Given", value=discounts, tone="warn"),
                AccountingKPI(label="Corporate Bills", value=corporate_due, tone="warn"),
                AccountingKPI(label="Inventory Value", value=inventory_value, tone="info"),
                AccountingKPI(label="Pharmacy Revenue", value=pharmacy_revenue, tone="good"),
                AccountingKPI(label="OT Revenue", value=ot_revenue, tone="good"),
            ],
            revenue_vs_expense=[
                AccountingChartPoint(label="Revenue", value=monthly_revenue),
                AccountingChartPoint(label="Expenses", value=expenses),
                AccountingChartPoint(label="Profit", value=net_profit),
            ],
            department_revenue=self._department_revenue(branch_id),
            payment_methods=self._payment_methods(branch_id, month_start),
            expense_breakdown=self._expense_breakdown(branch_id, month_start),
            due_aging=self._aging_points(BillingInvoice.due_amount, BillingInvoice.created_at, BillingInvoice.branch_id == branch_id, BillingInvoice.due_amount > 0),
            payable_aging=self._aging_points(SupplierInvoice.due_amount, SupplierInvoice.invoice_date, SupplierInvoice.branch_id == branch_id, SupplierInvoice.due_amount > 0),
            cash_flow=self._cash_flow(branch_id),
            alerts=self._alerts(pending_due, insurance_due, supplier_due, payroll_due, refunds_today, discounts),
        )

    def list_accounts(self, actor: User) -> list[Account]:
        stmt = select(Account).where(Account.branch_id == actor.branch_id).order_by(Account.account_code)
        return list(self.db.scalars(stmt))

    def create_account(self, payload: AccountCreate, actor: User, context: dict[str, str | None]) -> Account:
        account = Account(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
        self.db.add(account)
        self._audit(actor, "account.create", "Account", None, context, payload.model_dump(mode="json"))
        self.db.commit()
        self.db.refresh(account)
        return account

    def list_journal_entries(self, actor: User) -> list[JournalEntry]:
        stmt = select(JournalEntry).options(selectinload(JournalEntry.lines)).where(JournalEntry.branch_id == actor.branch_id).order_by(JournalEntry.created_at.desc()).limit(50)
        return list(self.db.scalars(stmt))

    def create_journal_entry(self, payload: JournalEntryCreate, actor: User, context: dict[str, str | None]) -> JournalEntry:
        total_debit = sum(line.debit_amount for line in payload.lines)
        total_credit = sum(line.credit_amount for line in payload.lines)
        entry = JournalEntry(
            branch_id=actor.branch_id,
            journal_number=f"JE-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            journal_date=payload.journal_date,
            source_module=payload.source_module,
            source_reference=payload.source_reference,
            narration=payload.narration,
            status=payload.status,
            total_debit=total_debit,
            total_credit=total_credit,
            posted_at=datetime.now(UTC) if payload.status == "posted" else None,
            approved_by_user_id=actor.id if payload.status == "posted" else None,
            attachment_url=payload.attachment_url,
            created_by=actor.id,
            updated_by=actor.id,
        )
        for line in payload.lines:
            entry.lines.append(JournalEntryLine(**line.model_dump(), created_by=actor.id, updated_by=actor.id))
        self.db.add(entry)
        self._audit(actor, "journal_entry.create", "JournalEntry", None, context, {"journal_number": entry.journal_number})
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def workspace(self, actor: User) -> dict:
        branch_id = actor.branch_id
        return {
            "accounts": self.list_accounts(actor)[:80],
            "journal_entries": self.list_journal_entries(actor),
            "advances": [self._finance_record(row, row.receipt_number, "Advance", row.amount, row.status, row.balance_amount) for row in self._recent(AdvancePayment, branch_id)],
            "discounts": [self._finance_record(row, "DISCOUNT", row.discount_category, row.approved_amount or row.requested_amount, row.status) for row in self._recent(Discount, branch_id)],
            "refunds": [self._finance_record(row, row.refund_number, row.refund_type, row.amount, row.status) for row in self._recent(Refund, branch_id)],
            "insurance_claims": [self._finance_record(row, row.claim_number, row.provider_name, row.claim_amount, row.status, row.claim_amount - row.paid_amount, row.paid_amount) for row in self._recent(InsuranceClaim, branch_id)],
            "corporate_bills": [self._finance_record(row, row.bill_number, row.company_name, row.net_amount, row.status, row.due_amount, row.paid_amount) for row in self._recent(CorporateBill, branch_id)],
            "supplier_invoices": [self._finance_record(row, row.invoice_number, row.supplier_name, row.gross_amount, row.status, row.due_amount, row.paid_amount, row.category) for row in self._recent(SupplierInvoice, branch_id)],
            "expenses": [self._finance_record(row, row.expense_number, row.vendor_name or "Expense", row.amount, row.status, category=row.payment_method) for row in self._recent(Expense, branch_id)],
            "doctor_commissions": [self._finance_record(row, row.reference_number or "COMMISSION", row.doctor_name, row.commission_amount, row.status, category=row.source_module) for row in self._recent(DoctorCommission, branch_id)],
            "cash_closings": [self._finance_record(row, str(row.closing_date), "Cash Closing", row.actual_cash, row.status, row.difference_amount) for row in self._recent(CashClosing, branch_id)],
            "bank_transactions": [self._finance_record(row, row.reference_number or "BANK", row.transaction_type, row.amount, row.reconciliation_status, category=row.transaction_type) for row in self._recent(BankTransaction, branch_id)],
        }

    def create_simple(self, kind: str, payload, actor: User, context: dict[str, str | None]):
        now = datetime.now(UTC)
        today = date.today()
        amount = Decimal(payload.amount)
        prefix = kind.upper().replace("-", "")[:5]
        common = {"branch_id": actor.branch_id, "created_by": actor.id, "updated_by": actor.id}
        if kind == "advance":
            entity = AdvancePayment(receipt_number=f"ADV-{now:%Y%m%d%H%M%S}", amount=amount, balance_amount=amount, payment_method=payload.payment_method, status=payload.status or "active", note=payload.note, collected_by_user_id=actor.id, **common)
        elif kind == "refund":
            entity = Refund(refund_number=f"REF-{now:%Y%m%d%H%M%S}", refund_type=payload.category or "service", amount=amount, payment_method=payload.payment_method, reason=payload.note or "Refund request", status=payload.status, processed_by_user_id=actor.id, **common)
        elif kind == "discount":
            entity = Discount(discount_category=payload.category or "management", requested_amount=amount, approved_amount=amount if payload.status == "approved" else Decimal(0), reason=payload.note, status=payload.status, approved_by_user_id=actor.id if payload.status == "approved" else None, **common)
        elif kind == "insurance":
            entity = InsuranceClaim(claim_number=f"INS-{now:%Y%m%d%H%M%S}", provider_name=payload.name or "Insurance Provider", claim_amount=amount, status=payload.status or "draft", due_date=today + timedelta(days=21), **common)
        elif kind == "corporate":
            entity = CorporateBill(bill_number=f"CORP-{now:%Y%m%d%H%M%S}", company_name=payload.name or "Corporate Client", bill_month=today.strftime("%Y-%m"), gross_amount=amount, net_amount=amount, due_amount=amount, status=payload.status or "open", due_date=today + timedelta(days=30), **common)
        elif kind == "supplier":
            entity = SupplierInvoice(supplier_name=payload.name or "Supplier", invoice_number=payload.reference or f"SUP-{now:%Y%m%d%H%M%S}", invoice_date=today, due_date=today + timedelta(days=15), category=payload.category or "inventory", gross_amount=amount, due_amount=amount, status=payload.status or "pending", note=payload.note, **common)
        elif kind == "expense":
            category = self.db.scalar(select(ExpenseCategory).where(ExpenseCategory.branch_id == actor.branch_id).limit(1))
            entity = Expense(category_id=category.id if category else None, expense_number=f"EXP-{now:%Y%m%d%H%M%S}", expense_date=today, vendor_name=payload.name, amount=amount, payment_method=payload.payment_method, status=payload.status or "pending", description=payload.note, approved_by_user_id=actor.id if payload.status == "approved" else None, **common)
        else:
            raise ValueError("Unsupported accounting workflow")
        self.db.add(entity)
        self._audit(actor, f"{kind}.create", entity.__class__.__name__, None, context, {"amount": str(amount)})
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def _sum(self, column, *conditions) -> Decimal:
        stmt = select(func.coalesce(func.sum(column), 0))
        for condition in conditions:
            if condition is not None:
                stmt = stmt.where(condition)
        return Decimal(self.db.scalar(stmt) or 0)

    def _department_revenue(self, branch_id) -> list[AccountingChartPoint]:
        stmt = select(func.coalesce(BillingInvoice.source_module, "billing"), func.coalesce(func.sum(BillingInvoice.total_amount), 0)).where(BillingInvoice.branch_id == branch_id, BillingInvoice.status != "void").group_by(BillingInvoice.source_module).limit(8)
        rows = self.db.execute(stmt).all()
        return [AccountingChartPoint(label=row[0] or "billing", value=Decimal(row[1] or 0)) for row in rows]

    def _payment_methods(self, branch_id, month_start: date) -> list[AccountingChartPoint]:
        stmt = select(BillingPayment.payment_method, func.coalesce(func.sum(BillingPayment.amount), 0)).where(BillingPayment.branch_id == branch_id, BillingPayment.received_at >= month_start).group_by(BillingPayment.payment_method)
        return [AccountingChartPoint(label=row[0], value=Decimal(row[1] or 0)) for row in self.db.execute(stmt).all()]

    def _expense_breakdown(self, branch_id, month_start: date) -> list[AccountingChartPoint]:
        stmt = select(func.coalesce(Expense.department_name, Expense.payment_method), func.coalesce(func.sum(Expense.amount), 0)).where(Expense.branch_id == branch_id, Expense.expense_date >= month_start).group_by(Expense.department_name, Expense.payment_method)
        return [AccountingChartPoint(label=row[0] or "Expense", value=Decimal(row[1] or 0)) for row in self.db.execute(stmt).all()]

    def _cash_flow(self, branch_id) -> list[AccountingChartPoint]:
        points = []
        for offset in range(6, -1, -1):
            day = date.today() - timedelta(days=offset)
            start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
            end = start + timedelta(days=1)
            inflow = self._sum(BillingPayment.amount, BillingPayment.branch_id == branch_id, BillingPayment.received_at >= start, BillingPayment.received_at < end)
            outflow = self._sum(Expense.amount, Expense.branch_id == branch_id, Expense.expense_date == day)
            points.append(AccountingChartPoint(label=day.strftime("%d %b"), value=inflow - outflow))
        return points

    def _aging_points(self, amount_column, date_column, *conditions) -> list[AccountingChartPoint]:
        buckets = {"0-7": (0, 7), "8-30": (8, 30), "31-60": (31, 60), "60+": (61, 3650)}
        points = []
        today = date.today()
        for label, (start_days, end_days) in buckets.items():
            start_date = today - timedelta(days=end_days)
            end_date = today - timedelta(days=start_days)
            stmt = select(func.coalesce(func.sum(amount_column), 0)).where(date_column >= start_date, date_column <= end_date)
            for condition in conditions:
                stmt = stmt.where(condition)
            points.append(AccountingChartPoint(label=label, value=Decimal(self.db.scalar(stmt) or 0)))
        return points

    def _alerts(self, due, insurance, supplier, payroll, refunds, discounts) -> list[AccountingAlert]:
        alerts = []
        if due > 0:
            alerts.append(AccountingAlert(severity="danger", title="Patient dues", message=f"BDT {due:,.0f} is pending from patient invoices."))
        if insurance > 0:
            alerts.append(AccountingAlert(severity="warn", title="Insurance receivable", message=f"BDT {insurance:,.0f} is waiting for claim settlement."))
        if supplier > 0:
            alerts.append(AccountingAlert(severity="warn", title="Supplier payable", message=f"BDT {supplier:,.0f} supplier bills are unpaid."))
        if payroll > 0:
            alerts.append(AccountingAlert(severity="warn", title="Payroll payable", message=f"BDT {payroll:,.0f} payroll is payable."))
        if refunds > 5000:
            alerts.append(AccountingAlert(severity="danger", title="High refunds", message="Refund value is above the daily review threshold."))
        if discounts > 10000:
            alerts.append(AccountingAlert(severity="warn", title="Discount review", message="Discounts are high this month."))
        return alerts

    def _recent(self, model, branch_id, limit: int = 30):
        stmt = select(model).where(model.branch_id == branch_id).order_by(model.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def _finance_record(self, row, reference, name, amount, status, due=Decimal(0), paid=Decimal(0), category=None) -> FinanceRecordRead:
        return FinanceRecordRead(id=row.id, reference=reference or "-", name=name or "-", amount=amount or Decimal(0), paid_amount=paid or Decimal(0), due_amount=due or Decimal(0), category=category, status=status or "-", created_at=row.created_at)

    def _audit(self, actor: User, action: str, entity_type: str | None, entity_id: str | None, context: dict[str, str | None], detail: dict | None = None) -> None:
        self.db.add(AccountingAuditLog(branch_id=actor.branch_id, actor_user_id=actor.id, action=action, entity_type=entity_type, entity_id=entity_id, new_value=str(detail or {}), ip_address=context.get("ip_address"), user_agent=context.get("user_agent"), created_by=actor.id, updated_by=actor.id))
