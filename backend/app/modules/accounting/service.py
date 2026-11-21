from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from app.utils.accounting_time import today_local
from decimal import Decimal
from uuid import uuid4

from fastapi import status
from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppException
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
    SupplierPayment,
)
from app.models.billing import BillingInvoice, BillingPayment, BillingRefund
from app.models.hr import HRPayrollRun
from app.models.inventory import InventoryItem
from app.models.ot import OTBillingItem, OTBooking, SurgerySchedule
from app.models.pharmacy import PharmacySale
from app.models.user import User
from app.modules.accounting.repository import AccountingRepository
from app.modules.audit.service import AuditService
from app.schemas.accounting import (
    AccountCreate,
    AccountingDashboardRead,
    AccountingReportSummary,
    AccountingJournalCreate,
    AccountingKPI,
    AccountingChartPoint,
    AccountingAlert,
    FinanceRecordRead,
    GeneralLedgerLineRead,
    JournalEntryCreate,
)
from app.utils.enums import AuditAction


class AccountingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AccountingRepository(db)

    def list_journals(self, actor: User) -> list[AccountingJournal]:
        return list(self.db.scalars(select(AccountingJournal).where(AccountingJournal.branch_id==actor.branch_id).order_by(AccountingJournal.created_at.desc())))

    def post_journal(self, payload: AccountingJournalCreate, actor: User, context: dict[str, str | None]) -> AccountingJournal:
        if payload.branch_id and payload.branch_id!=actor.branch_id:
            raise AppException(403,'accounting_branch','Journal must belong to the active branch')
        if not payload.debit_account_code or not payload.credit_account_code:
            raise AppException(422,'legacy_accounts_required','Select explicit debit and credit accounts; summary-only journals cannot update the GL')
        from app.schemas.accounting import JournalEntryLineCreate
        return self.create_journal_entry(JournalEntryCreate(journal_date=today_local(),source_module='legacy_journal',source_reference=payload.reference or str(uuid4()),narration=payload.description,lines=[JournalEntryLineCreate(account_code=payload.debit_account_code,account_name=payload.debit_account_code,debit_amount=payload.debit_amount),JournalEntryLineCreate(account_code=payload.credit_account_code,account_name=payload.credit_account_code,credit_amount=payload.credit_amount)]),actor,context)

    def dashboard(self, actor: User) -> AccountingDashboardRead:
        branch_id = actor.branch_id
        today = today_local()
        month_start = today.replace(day=1)
        today_start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)

        collection_today = self._sum(BillingPayment.amount, BillingPayment.received_at >= today_start, BillingPayment.branch_id == branch_id)
        # Book revenue excludes carried-forward charges, which were accrued earlier.
        monthly_revenue=self.db.scalar(select(func.coalesce(func.sum(JournalEntryLine.credit_amount-JournalEntryLine.debit_amount),0)).join(JournalEntryLine.journal_entry).where(JournalEntry.branch_id==branch_id,JournalEntry.status=='posted',JournalEntry.journal_date>=month_start,JournalEntryLine.account_code.in_(['4000','4100','4200','4300','4400']))) or Decimal(0)
        from app.models.hr import HRPayrollRun
        expenses = self._sum(Expense.amount, Expense.expense_date >= month_start, Expense.branch_id == branch_id, Expense.status.in_(["approved", "paid"]))
        automatic_expenses=self.db.scalar(select(func.coalesce(func.sum(JournalEntryLine.debit_amount-JournalEntryLine.credit_amount),0)).join(JournalEntryLine.journal_entry).where(JournalEntry.branch_id==branch_id,JournalEntry.status=='posted',JournalEntry.journal_date>=month_start,JournalEntry.source_module.in_(['hr_payroll','catering_stock','transport_fuel','transport_maintenance']),JournalEntryLine.account_code.in_(['5100','5200','5300','5310']))) or Decimal(0)
        expenses+=automatic_expenses
        pending_due = self._sum(BillingInvoice.due_amount, BillingInvoice.branch_id == branch_id, BillingInvoice.payment_status.in_(["unpaid", "partial"]))
        discounts = self._sum(BillingInvoice.discount_amount, BillingInvoice.created_at >= month_start, BillingInvoice.branch_id == branch_id)
        refunds_today = self._sum(BillingRefund.amount, BillingRefund.refunded_at >= today_start, BillingRefund.branch_id == branch_id)
        insurance_due = self._sum(InsuranceClaim.claim_amount - InsuranceClaim.paid_amount, InsuranceClaim.branch_id == branch_id, InsuranceClaim.status != "paid")
        supplier_due = self._sum(SupplierInvoice.due_amount, SupplierInvoice.branch_id == branch_id, SupplierInvoice.status != "paid")
        payroll_due = self._sum(PayrollAccounting.net_salary_payable - PayrollAccounting.paid_amount, PayrollAccounting.branch_id == branch_id, PayrollAccounting.status != "paid")
        payroll_due+=self._sum(HRPayrollRun.total_net_salary,HRPayrollRun.branch_id==branch_id,HRPayrollRun.status.in_(['approved','finalized']))
        corporate_due = self._sum(CorporateBill.due_amount, CorporateBill.branch_id == branch_id, CorporateBill.status != "paid")
        inventory_value = self._sum(InventoryItem.stock_value, InventoryItem.branch_id == branch_id, InventoryItem.is_active.is_(True))
        pharmacy_revenue = self._sum(PharmacySale.net_payable, PharmacySale.branch_id == branch_id, PharmacySale.created_at >= month_start)
        ot_revenue=self.db.scalar(select(func.coalesce(func.sum(OTBillingItem.amount),0)).join(SurgerySchedule,SurgerySchedule.id==OTBillingItem.schedule_id).join(OTBooking,OTBooking.id==SurgerySchedule.booking_id).where(OTBooking.branch_id==branch_id,OTBillingItem.created_at>=month_start,OTBillingItem.is_active.is_(True))) or Decimal(0)

        cash_balance = collection_today - refunds_today - self._sum(Expense.amount, Expense.expense_date == today, Expense.payment_method == "cash", Expense.branch_id == branch_id)
        settlement=self.db.scalar(select(Account.current_balance).where(Account.branch_id==branch_id,Account.account_code=='1001'))
        if settlement is not None:cash_balance=Decimal(settlement)
        bank_balance = self._sum(BankAccount.current_balance, BankAccount.branch_id == branch_id)
        from app.modules.accounting.management import AccountingManagement
        book=AccountingManagement(self.db).statements(actor,month_start,today)
        monthly_revenue=Decimal(book['profit_and_loss']['income'])
        expenses=Decimal(book['profit_and_loss']['expenses'])
        net_profit = monthly_revenue - expenses
        cash_codes={'1001','1011','1012','1013'};bank_codes={'1020'};clearing_codes={'1031','1032','1033','1034'}
        cumulative={row['code']:Decimal(row['signed_balance']) for row in book['trial_balance']}
        cash_balance=sum((value for code,value in cumulative.items() if code in cash_codes),Decimal(0))
        bank_balance=sum((value for code,value in cumulative.items() if code in bank_codes),Decimal(0))
        clearing_balance=sum((value for code,value in cumulative.items() if code in clearing_codes),Decimal(0))
        collection_today=self.db.scalar(select(func.coalesce(func.sum(JournalEntryLine.debit_amount),0)).join(JournalEntry,JournalEntryLine.journal_entry_id==JournalEntry.id).where(JournalEntry.branch_id==branch_id,JournalEntry.posting_applied_at.is_not(None),JournalEntry.journal_date==today,JournalEntryLine.account_code.in_(cash_codes|bank_codes|clearing_codes),or_(JournalEntry.source_module.in_(['billing_payment','patient_advance','pharmacy_sale','opd_external_remittance']),JournalEntry.voucher_type=='receipt'))) or Decimal(0)

        return AccountingDashboardRead(
            kpis=[
                AccountingKPI(label="Today's Collection", value=collection_today, tone="good"),
                AccountingKPI(label="Monthly Revenue (book)", value=monthly_revenue, tone="info"),
                AccountingKPI(label="Total Expenses", value=expenses, tone="warn"),
                AccountingKPI(label="Net Profit / Loss", value=net_profit, tone="good" if net_profit >= 0 else "danger"),
                AccountingKPI(label="Cash in Hand (book)", value=cash_balance, tone="info"),
                AccountingKPI(label="Mobile / Card Clearing (book)", value=clearing_balance, tone="info"),
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
        from app.modules.support_posting.service import lock_branch
        lock_branch(self.db,actor)
        if payload.opening_balance or payload.current_balance:raise AppException(422,'account_opening_voucher','Use a balanced opening voucher instead of setting account balances')
        if self._find_account(actor.branch_id,None,payload.account_code):raise AppException(409,'account_code_exists','Account code already exists in this branch')
        if payload.parent_id:
            parent=self._find_account(actor.branch_id,payload.parent_id,None)
            if not parent or not parent.is_control:raise AppException(422,'account_parent','Choose a control account in this branch')
        if payload.category not in {'assets','liabilities','equity','income','expenses'}:raise AppException(422,'account_category','Choose a standard account category')
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
        from app.modules.accounting.controls import SYSTEM_SOURCES
        if payload.source_module in SYSTEM_SOURCES:raise AppException(422,'reserved_accounting_source','Use the originating HMS workflow for this financial event')
        from app.modules.support_posting.service import lock_branch
        lock_branch(self.db,actor)
        from app.modules.auth.service import AuthService
        permissions=set(AuthService(self.db).get_effective_permissions(actor))
        if payload.status=='posted' and not permissions.intersection({'accounting.journal.post','accounting.voucher.post'}):raise AppException(403,'accounting_post_permission','Posting permission is required')
        if payload.status=='approved':raise AppException(403,'accounting_approval_action','Use the independent approval action')
        if payload.request_key:
            from app.models.accounting_control import AccountingPostingKey
            previous=self.db.scalar(select(AccountingPostingKey).where(AccountingPostingKey.branch_id==actor.branch_id,AccountingPostingKey.source_module=='manual_request',AccountingPostingKey.source_reference==payload.request_key))
            if previous:
                import hashlib
                digest=hashlib.sha256(payload.model_dump_json(exclude={'request_key'}).encode()).hexdigest()
                if previous.fingerprint!=digest:raise AppException(409,'journal_request_conflict','Request key was used for different journal content')
                return self.db.get(JournalEntry,previous.journal_id)
        from app.models.accounting_control import FinancialPeriod
        if self.db.scalar(select(FinancialPeriod.id).where(FinancialPeriod.branch_id==actor.branch_id,FinancialPeriod.start_date<=payload.journal_date,FinancialPeriod.end_date>=payload.journal_date,FinancialPeriod.status!='open')):raise AppException(409,'accounting_period_locked','Cannot create or post a voucher in a locked period')
        from app.modules.accounting.controls import policy_for
        policy=policy_for(self.db,actor.branch_id,payload.journal_date)
        if policy and policy.settings.get('maker_checker') and payload.status in {'approved','posted'}:
            raise AppException(403,'journal_approval_required','Submit the voucher for independent approval before posting')
        if payload.source_module and payload.source_reference and self._source_entry_exists(actor.branch_id, payload.source_module, payload.source_reference):
            raise AppException(status.HTTP_409_CONFLICT, "duplicate_journal_entry", "Accounting entry already exists for this source transaction.")
        if payload.status not in {"draft", "submitted", "approved", "posted"}:
            raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_status", "Voucher status must be Draft, Submitted, Approved, or Posted.")
        total_debit = sum(line.debit_amount for line in payload.lines)
        total_credit = sum(line.credit_amount for line in payload.lines)
        entry = JournalEntry(
            branch_id=actor.branch_id,
            journal_number=f"JE-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex.upper()}",
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
            voucher_type=payload.voucher_type,
            created_by=actor.id,
            updated_by=actor.id,
        )
        for line in payload.lines:
            line_data = line.model_dump()
            account = self._find_account(actor.branch_id, line_data.get("account_id"), line.account_code)
            if account:
                line_data["account_id"] = account.id
                line_data["account_code"] = account.account_code
                line_data["account_name"] = account.name
            entry.lines.append(JournalEntryLine(**line_data, created_by=actor.id, updated_by=actor.id))
        self.db.add(entry)
        if entry.status == "posted":
            self._apply_posting(entry, actor)
        if payload.request_key:
            import hashlib
            self.db.flush()
            self.db.add(AccountingPostingKey(branch_id=actor.branch_id,source_module='manual_request',source_reference=payload.request_key,journal=entry,fingerprint=hashlib.sha256(payload.model_dump_json(exclude={'request_key'}).encode()).hexdigest(),created_by=actor.id,updated_by=actor.id))
        self._audit(actor, "journal_entry.create", "JournalEntry", None, context, {"journal_number": entry.journal_number})
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list_general_ledger(self, actor: User, account_code: str | None = None, source_module: str | None = None, date_from: date | None = None, date_to: date | None = None, limit: int = 200) -> list[GeneralLedgerLineRead]:
        stmt = (
            select(JournalEntryLine, JournalEntry)
            .join(JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id)
            .where(JournalEntry.branch_id == actor.branch_id, JournalEntry.status.in_(["posted","reversed"]))
            .order_by(JournalEntry.journal_date, JournalEntry.created_at, JournalEntryLine.created_at)
        )
        if account_code:
            stmt = stmt.where(JournalEntryLine.account_code == account_code)
        if source_module:
            stmt = stmt.where(JournalEntry.source_module == source_module)
        if date_from:
            stmt = stmt.where(JournalEntry.journal_date >= date_from)
        if date_to:
            stmt = stmt.where(JournalEntry.journal_date <= date_to)

        balances={}
        if date_from:
            opening=select(JournalEntryLine.account_code,func.sum(JournalEntryLine.debit_amount-JournalEntryLine.credit_amount)).join(JournalEntry,JournalEntryLine.journal_entry_id==JournalEntry.id).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.status.in_(['posted','reversed']),JournalEntry.journal_date<date_from)
            if source_module:opening=opening.where(JournalEntry.source_module==source_module)
            balances=dict(self.db.execute(opening.group_by(JournalEntryLine.account_code)).all())
        rows: list[GeneralLedgerLineRead] = []
        for line, entry in self.db.execute(stmt.limit(min(max(limit,1),500))).all():
            balances[line.account_code]=Decimal(balances.get(line.account_code,0))+Decimal(line.debit_amount or 0)-Decimal(line.credit_amount or 0)
            balance=balances[line.account_code]
            rows.append(
                GeneralLedgerLineRead(
                    id=line.id,
                    journal_entry_id=entry.id,
                    journal_number=entry.journal_number,
                    journal_date=entry.journal_date,
                    account_code=line.account_code,
                    account_name=line.account_name,
                    description=line.description or entry.narration,
                    debit_amount=line.debit_amount,
                    credit_amount=line.credit_amount,
                    balance=balance,
                    source_module=entry.source_module,
                    source_reference=entry.source_reference,
                    created_by=entry.created_by,
                )
            )
        return rows

    def voucher_action(self, entry_id, action: str, actor: User, context: dict[str, str | None]) -> JournalEntry:
        from app.modules.support_posting.service import lock_branch
        lock_branch(self.db,actor)
        entry = self.db.scalar(
            select(JournalEntry).options(selectinload(JournalEntry.lines)).where(JournalEntry.id == entry_id, JournalEntry.branch_id == actor.branch_id)
        )
        if not entry:
            raise AppException(status.HTTP_404_NOT_FOUND, "voucher_not_found", "Voucher not found.")
        from app.modules.auth.service import AuthService
        permissions=set(AuthService(self.db).get_effective_permissions(actor))
        needed={'approve':{'accounting.voucher.approve','accounting.approve'},'post':{'accounting.voucher.post','accounting.journal.post'},'reverse':{'accounting.voucher.reverse','accounting.journal.post'}}
        if action in needed and not permissions.intersection(needed[action]):raise AppException(403,'accounting_action_permission','You cannot perform this voucher action')
        from app.modules.accounting.controls import policy_for
        policy=policy_for(self.db,actor.branch_id,entry.journal_date)
        if policy and policy.settings.get('maker_checker'):
            if action in {'approve','post','reverse'} and entry.created_by==actor.id:raise AppException(403,'accounting_maker_checker','The maker cannot approve, post or reverse this voucher')
            if action=='post' and entry.status!='approved':raise AppException(409,'voucher_not_approved','Independent approval is required')
        if action == "submit":
            if entry.status != "draft":
                raise AppException(status.HTTP_409_CONFLICT, "invalid_voucher_state", "Only draft vouchers can be submitted.")
            entry.status = "submitted"
        elif action == "approve":
            if entry.status not in {"submitted", "draft"}:
                raise AppException(status.HTTP_409_CONFLICT, "invalid_voucher_state", "Only draft or submitted vouchers can be approved.")
            entry.status = "approved"
            entry.approved_by_user_id = actor.id
        elif action == "post":
            if entry.status == "posted":
                return entry
            if entry.status not in {"approved", "submitted", "draft"}:
                raise AppException(status.HTTP_409_CONFLICT, "invalid_voucher_state", "Voucher cannot be posted from its current status.")
            entry.approved_by_user_id = entry.approved_by_user_id or actor.id
            self._apply_posting(entry, actor)
        elif action == "cancel":
            if entry.status == "posted":
                raise AppException(status.HTTP_409_CONFLICT, "posted_voucher_locked", "Posted vouchers must be reversed, not cancelled.")
            entry.status = "cancelled"
        elif action == "reverse":
            from app.modules.accounting.controls import SYSTEM_SOURCES
            if entry.source_module in SYSTEM_SOURCES:raise AppException(409,'accounting_source_reversal','Reverse or adjust this transaction through its originating HMS workflow so operational balances remain consistent')
            entry = self.reverse_journal_entry(entry, actor, context)
            return entry
        else:
            raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_action", "Unsupported voucher action.")
        entry.updated_by = actor.id
        self._audit(actor, f"journal_entry.{action}", "JournalEntry", str(entry.id), context, {"journal_number": entry.journal_number, "status": entry.status})
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def reverse_journal_entry(self, entry: JournalEntry, actor: User, context: dict[str, str | None]) -> JournalEntry:
        if entry.branch_id!=actor.branch_id:raise AppException(403,'accounting_branch','Cannot reverse another branch voucher')
        from app.modules.support_posting.service import lock_branch
        lock_branch(self.db,actor);self.db.refresh(entry,with_for_update=True)
        if entry.status != "posted":
            raise AppException(status.HTTP_409_CONFLICT, "voucher_not_posted", "Only posted vouchers can be reversed.")
        if self.db.scalar(select(JournalEntry.id).where(JournalEntry.reversed_entry_id == entry.id, JournalEntry.branch_id == actor.branch_id)):
            raise AppException(status.HTTP_409_CONFLICT, "voucher_already_reversed", "A reversal voucher already exists.")
        reversal = JournalEntry(
            branch_id=actor.branch_id,
            journal_number=f"RV-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex.upper()}",
            journal_date=today_local(),
            source_module="accounting_reversal",
            source_reference=entry.journal_number,
            narration=f"Reversal of {entry.journal_number}: {entry.narration}",
            status="posted",
            total_debit=entry.total_credit,
            total_credit=entry.total_debit,
            posted_at=datetime.now(UTC),
            approved_by_user_id=actor.id,
            reversed_entry_id=entry.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        for line in entry.lines:
            reversal.lines.append(
                JournalEntryLine(
                    account_id=line.account_id,
                    account_code=line.account_code,
                    account_name=line.account_name,
                    description=f"Reversal of {entry.journal_number}",
                    debit_amount=line.credit_amount,
                    credit_amount=line.debit_amount,
                    cost_center=line.cost_center,
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )
        self.db.add(reversal)
        self._apply_posting(reversal, actor)
        self.db.flush([reversal])
        entry.status = "reversed"
        entry.updated_by = actor.id
        self._audit(actor, "journal_entry.reverse", "JournalEntry", str(entry.id), context, {"reversal": reversal.journal_number})
        self.db.commit()
        self.db.refresh(reversal)
        return reversal

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
        from app.modules.support_posting.service import lock_branch
        lock_branch(self.db,actor)
        if payload.status not in {'pending','draft'}:raise AppException(403,'finance_approval_required','Create a pending record and use an authorized approval action')
        if kind=='supplier' and (not payload.reference or not payload.name):raise AppException(422,'supplier_invoice_reference','Supplier name and original invoice reference are required')
        if kind=='supplier' and payload.reference and self.db.scalar(select(SupplierInvoice.id).where(SupplierInvoice.branch_id==actor.branch_id,func.upper(func.trim(SupplierInvoice.invoice_number))==payload.reference.strip().upper(),func.lower(func.trim(SupplierInvoice.supplier_name))==(payload.name or 'Supplier').strip().lower())):
            raise AppException(409,'supplier_invoice_duplicate','This supplier invoice reference already exists')
        now = datetime.now(UTC)
        today = payload.transaction_date or today_local()
        amount = Decimal(payload.amount)
        prefix = kind.upper().replace("-", "")[:5]
        common = {"branch_id": actor.branch_id, "created_by": actor.id, "updated_by": actor.id}
        if kind == "advance":
            entity = AdvancePayment(patient_id=payload.patient_id,receipt_number=f"ADV-{now:%Y%m%d%H%M%S}-{uuid4().hex[:12].upper()}", amount=amount, balance_amount=amount, payment_method=payload.payment_method, status=payload.status or "active", note=payload.note, collected_by_user_id=actor.id, **common)
        elif kind == "refund":
            entity = Refund(refund_number=f"REF-{now:%Y%m%d%H%M%S}-{uuid4().hex[:12].upper()}", refund_type=payload.category or "service", amount=amount, payment_method=payload.payment_method, reason=payload.note or "Refund request", status=payload.status, processed_by_user_id=actor.id, **common)
        elif kind == "discount":
            entity = Discount(discount_category=payload.category or "management", requested_amount=amount, approved_amount=amount if payload.status == "approved" else Decimal(0), reason=payload.note, status=payload.status, approved_by_user_id=actor.id if payload.status == "approved" else None, **common)
        elif kind == "insurance":
            entity = InsuranceClaim(claim_number=f"INS-{now:%Y%m%d%H%M%S}-{uuid4().hex[:12].upper()}", provider_name=payload.name or "Insurance Provider", claim_amount=amount, status=payload.status or "draft", due_date=payload.due_date, **common)
        elif kind == "corporate":
            entity = CorporateBill(bill_number=f"CORP-{now:%Y%m%d%H%M%S}-{uuid4().hex[:12].upper()}", company_name=payload.name or "Corporate Client", bill_month=today.strftime("%Y-%m"), gross_amount=amount, net_amount=amount, due_amount=amount, status=payload.status or "open", due_date=payload.due_date, **common)
        elif kind == "supplier":
            entity = SupplierInvoice(purchase_account_code=payload.purchase_account_code,receiving_id=payload.receiving_id,pharmacy_purchase_id=payload.pharmacy_purchase_id,supplier_name=payload.name or "Supplier", invoice_number=payload.reference or f"SUP-{now:%Y%m%d%H%M%S}-{uuid4().hex[:12].upper()}", invoice_date=today, due_date=payload.due_date, category=payload.category or "inventory", gross_amount=amount, due_amount=amount, status=payload.status or "pending", note=payload.note, **common)
        elif kind == "expense":
            category = self.db.scalar(select(ExpenseCategory).where(ExpenseCategory.branch_id == actor.branch_id,ExpenseCategory.name==payload.category).limit(1))
            entity = Expense(expense_account_code=payload.expense_account_code,cost_center=payload.cost_center,attachment_url=payload.attachment_url,category_id=category.id if category else None, expense_number=f"EXP-{now:%Y%m%d%H%M%S}-{uuid4().hex[:12].upper()}", expense_date=today, vendor_name=payload.name, amount=amount, payment_method=payload.payment_method, status=payload.status or "pending", description=payload.note, approved_by_user_id=actor.id if payload.status == "approved" else None, **common)
        else:
            raise ValueError("Unsupported accounting workflow")
        self.db.add(entity)
        if kind=='advance':
            from app.modules.auth.service import AuthService
            if 'billing.payment.collect' not in AuthService(self.db).get_effective_permissions(actor):raise AppException(403,'advance_collection_permission','Patient advance collection requires cashier collection permission')
            from app.modules.accounting.channels import collection_account
            from app.models.patient import Patient
            patient=self.db.get(Patient,payload.patient_id) if payload.patient_id else None
            if not patient or patient.branch_id!=actor.branch_id:raise AppException(422,'advance_patient','Select a patient in this branch before collecting an advance')
            channel=collection_account(self.db,actor,payload.payment_method)
            entity.status='active'
            self._create_auto_entry(actor,'patient_advance',entity.receipt_number,today,'Patient advance deposit '+entity.receipt_number,[(channel,'Received patient advance',amount,0),('2210','Patient Advance Deposits',0,amount)])
        self._audit(actor, f"{kind}.create", entity.__class__.__name__, None, context, {"amount": str(amount)})
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update_finance_record_status(self, kind: str, record_id, new_status: str, actor: User, context: dict[str, str | None]):
        model_map = {
            "expense": Expense,
            "refund": Refund,
            "discount": Discount,
            "supplier": SupplierInvoice,
            "insurance": InsuranceClaim,
            "corporate": CorporateBill,
        }
        from app.modules.auth.service import AuthService
        permissions=set(AuthService(self.db).get_effective_permissions(actor))
        allowed={'accounting.approve','accounting.manage'} | ({'accounting.expense.approve'} if kind=='expense' else set())
        if not permissions.intersection(allowed):raise AppException(403,'finance_approval_permission','Approval access is required for this financial workflow')
        model = model_map.get(kind)
        if not model:
            raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unsupported_record", "Unsupported finance record type.")
        row = self.db.scalar(select(model).where(model.id == record_id, model.branch_id == actor.branch_id))
        if not row:
            raise AppException(status.HTTP_404_NOT_FOUND, "record_not_found", "Finance record not found.")
        from app.modules.support_posting.service import lock_branch
        lock_branch(self.db,actor);self.db.refresh(row,with_for_update=True)
        old_status=getattr(row,'status',None)
        if old_status==new_status:return row
        transitions={'pending':{'approved','rejected'},'draft':{'approved','rejected'},'approved':{'paid'},'partial':{'paid'}}
        if new_status not in transitions.get(old_status,set()):raise AppException(409,'finance_record_transition','Use an explicit approved financial adjustment for this transition')
        from app.modules.accounting.controls import policy_for
        policy=policy_for(self.db,actor.branch_id,today_local())
        if policy and policy.settings.get('maker_checker') and row.created_by==actor.id:raise AppException(403,'finance_self_approval','An independent approver is required')
        if kind=='expense' and new_status=='approved' and policy:
            limit=Decimal(str(policy.settings.get('expense_approval_limit',0)))
            if row.amount>limit and 'accounting.manage' not in permissions:raise AppException(403,'expense_approval_limit','This expense exceeds delegated approval authority; a finance administrator must approve it')
        if kind=='supplier' and new_status=='paid':raise AppException(422,'supplier_payment_required','Record a supplier payment with amount and reference instead of changing its status')
        if kind=='supplier' and new_status=='approved':
            from app.modules.accounting.coa import ensure_account
            purchase_account=ensure_account(self.db,actor,row.purchase_account_code)
            if purchase_account.category not in {'assets','asset','expenses','expense'} or not purchase_account.is_active or purchase_account.is_control:raise AppException(422,'supplier_purchase_account','Choose an approved active asset or expense purchase account')
            debit_code=row.purchase_account_code
            if row.receiving_id and row.pharmacy_purchase_id:raise AppException(422,'supplier_match_source','Select one receipt source')
            if row.receiving_id:
                from app.models.inventory import StockReceiving
                from app.models.operational_posting import OperationalPosting
                receiving=self.db.get(StockReceiving,row.receiving_id)
                posted=self.db.scalar(select(OperationalPosting).where(OperationalPosting.source_type=='inventory_receiving',OperationalPosting.source_id==row.receiving_id,OperationalPosting.event=='receive',OperationalPosting.branch_id==actor.branch_id))
                used=self.db.scalar(select(SupplierInvoice.id).where(SupplierInvoice.receiving_id==row.receiving_id,SupplierInvoice.id!=row.id,SupplierInvoice.status.in_(['approved','paid','partial'])))
                if not receiving or not posted or used or Decimal(posted.amount)!=row.gross_amount:raise AppException(422,'supplier_receipt_match','Match an unreconciled posted goods receipt with the same amount')
                debit_code='2400'
            if row.pharmacy_purchase_id:
                from app.models.pharmacy import PharmacyPurchase
                purchase=self.db.get(PharmacyPurchase,row.pharmacy_purchase_id)
                used=self.db.scalar(select(SupplierInvoice.id).where(SupplierInvoice.pharmacy_purchase_id==row.pharmacy_purchase_id,SupplierInvoice.id!=row.id,SupplierInvoice.status.in_(['approved','paid','partial'])))
                if not purchase or purchase.branch_id!=actor.branch_id or used or purchase.total_amount!=row.gross_amount or not self._source_entry_exists(actor.branch_id,'pharmacy_purchase',purchase.purchase_number):raise AppException(422,'supplier_pharmacy_match','Match an unreconciled posted pharmacy receipt with the same amount')
                debit_code='2400'
            self._create_auto_entry(actor,'supplier_invoice',str(row.id),row.invoice_date,'Approved supplier invoice '+row.invoice_number,[(debit_code,'Approved receipt / inventory account',row.gross_amount,0),('2100','Accounts Payable',0,row.gross_amount)])
        if kind=='expense':
            from app.modules.accounting.coa import ensure_account
            expense_account=ensure_account(self.db,actor,row.expense_account_code)
            if expense_account.category not in {'expenses','expense'} or expense_account.is_control or not expense_account.is_active:raise AppException(422,'expense_account','Choose an active expense account')
            if new_status=='approved':self._create_auto_entry(actor,'expense_accrual',str(row.id),row.expense_date,'Approved expense '+row.expense_number,[(row.expense_account_code,'Approved expense account',row.amount,0),('2500','Accrued Expenses',0,row.amount)])
            if new_status=='paid':
                from app.modules.accounting.channels import collection_account
                channel=collection_account(self.db,actor,row.payment_method)
                self._create_auto_entry(actor,'expense_payment',str(row.id),today_local(),'Expense payment '+row.expense_number,[('2500','Accrued Expenses',row.amount,0),(channel,'Configured payment account',0,row.amount)])
        setattr(row,'status',new_status)
        if hasattr(row,'approved_by_user_id') and new_status=='approved':row.approved_by_user_id=actor.id
        row.updated_by = actor.id
        self._audit(actor, f"{kind}.status", row.__class__.__name__, str(row.id), context, {"old_status": old_status, "new_status": new_status})
        self.db.commit()
        self.db.refresh(row)
        return row

    def reports(self, actor: User) -> AccountingReportSummary:
        branch_id = actor.branch_id
        from app.modules.accounting.management import AccountingManagement
        book=AccountingManagement(self.db).statements(actor)
        trial_balance=[AccountingChartPoint(label=row['code']+' '+row['name'],value=Decimal(row['signed_balance'])) for row in book['trial_balance']]
        income=Decimal(book['profit_and_loss']['income']);expenses=Decimal(book['profit_and_loss']['expenses'])
        assets=Decimal(book['balance_sheet']['assets']);liabilities=Decimal(book['balance_sheet']['liabilities'])
        equity=Decimal(book['balance_sheet']['equity'])+Decimal(book['balance_sheet']['unclosed_earnings'])
        return AccountingReportSummary(
            trial_balance=trial_balance,
            profit_and_loss=[
                AccountingChartPoint(label="Income", value=income),
                AccountingChartPoint(label="Expenses", value=expenses),
                AccountingChartPoint(label="Net Profit / Loss", value=income - expenses),
            ],
            balance_sheet=[
                AccountingChartPoint(label="Assets", value=assets),
                AccountingChartPoint(label="Liabilities", value=liabilities),
                AccountingChartPoint(label="Equity", value=equity),
                AccountingChartPoint(label="Balance Check", value=assets - liabilities - equity),
            ],
            receivable_aging=self._aging_points(BillingInvoice.due_amount, BillingInvoice.created_at, BillingInvoice.branch_id == branch_id, BillingInvoice.due_amount > 0),
            payable_aging=self._aging_points(SupplierInvoice.due_amount, SupplierInvoice.invoice_date, SupplierInvoice.branch_id == branch_id, SupplierInvoice.due_amount > 0),
            cash_bank=[
                AccountingChartPoint(label="Cash Today", value=self._sum(BillingPayment.amount, BillingPayment.branch_id == branch_id, BillingPayment.received_at >= datetime.combine(today_local(), datetime.min.time(), tzinfo=UTC))),
                AccountingChartPoint(label="Bank Balance", value=self._sum(BankAccount.current_balance, BankAccount.branch_id == branch_id)),
            ],
        )

    def sync_source_entries(self, actor: User, context: dict[str, str | None]) -> dict[str, int | str]:
        # A missing journal is not proof that an old operational row represents
        # a verified, unpaid accounting event. Never manufacture historic cash,
        # cost, tax or payroll entries from summary totals.
        from app.modules.support_posting.service import lock_branch
        lock_branch(self.db, actor)
        counts = {}
        for name, model in (("billing_payments", BillingPayment), ("billing_refunds", BillingRefund),
                            ("pharmacy_sales", PharmacySale), ("supplier_invoices", SupplierInvoice),
                            ("payroll_summaries", PayrollAccounting)):
            counts[name] = self.db.scalar(select(func.count()).select_from(model).where(model.branch_id == actor.branch_id)) or 0
        self._audit(actor, "accounting.integration_sync.review", "JournalEntry", None, context, counts)
        self.db.commit()
        return {"created_entries": 0, "skipped_entries": sum(counts.values()),
                "message": "Source review completed without posting. Current transactions post through their verified workflows. Reconcile historical records to reviewed opening vouchers; summary totals cannot establish cash, inventory cost or unpaid liabilities."}

    def _source_entry_exists(self, branch_id, source_module: str, source_reference: str) -> bool:
        return bool(
            self.db.scalar(
                select(JournalEntry.id).where(
                    JournalEntry.branch_id == branch_id,
                    JournalEntry.source_module == source_module,
                    JournalEntry.source_reference == source_reference,
                    JournalEntry.status != "cancelled",
                )
            )
        )

    def _find_account(self, branch_id, account_id, account_code: str | None) -> Account | None:
        if account_id:
            account = self.db.scalar(select(Account).where(Account.id == account_id, Account.branch_id == branch_id).with_for_update().execution_options(populate_existing=True))
            return account
        if account_code:
            return self.db.scalar(select(Account).where(Account.account_code == account_code, Account.branch_id == branch_id).with_for_update().execution_options(populate_existing=True))
        return None

    def _apply_posting(self, entry: JournalEntry, actor: User) -> None:
        with self.db.no_autoflush:
            from app.modules.accounting.controls import validate_posting
            from app.modules.accounting.coa import ensure_account
            validate_posting(self.db,entry,actor)
            accounts={};deltas={}
            for line in entry.lines:
                account=self._find_account(actor.branch_id,line.account_id,line.account_code)
                if not account and line.account_id:raise AppException(422,'accounting_account_scope','Account identifier does not belong to this branch')
                if not account:account=ensure_account(self.db,actor,line.account_code)
                if not account.is_active or account.is_control:raise AppException(422,'account_not_postable','Inactive and control accounts cannot receive postings')
                line.account_id=account.id;line.account_code=account.account_code;line.account_name=account.name
                delta=Decimal(line.credit_amount or 0)-Decimal(line.debit_amount or 0)
                if account.normal_balance!='credit':delta=-delta
                accounts[account.id]=account;deltas[account.id]=deltas.get(account.id,Decimal(0))+delta
            for identity,account in accounts.items():
                cached=Decimal(account.current_balance or 0)
                snapshot=entry.policy_snapshot or {}
                if snapshot.get('settings'):
                    signed=self.db.scalar(select(func.coalesce(func.sum(JournalEntryLine.debit_amount-JournalEntryLine.credit_amount),0)).join(JournalEntry,JournalEntry.id==JournalEntryLine.journal_entry_id).where(JournalEntryLine.account_id==account.id,JournalEntry.posting_applied_at.is_not(None))) or Decimal(0)
                    prior_book=-signed if account.normal_balance=='credit' else signed
                    if entry.voucher_type=='opening':
                        entry.policy_snapshot={**snapshot,'opening_reconciliation':{**snapshot.get('opening_reconciliation',{}),account.account_code:{'previous_cached_balance':str(cached),'prior_gl_balance':str(prior_book),'opening_delta':str(deltas[identity])}}}
                        cached=prior_book
                    elif cached!=prior_book:raise AppException(409,'accounting_cutover_reconciliation','Reconcile legacy opening balance for account '+account.account_code+' using a reviewed opening voucher before posting new transactions')
                new_balance=cached+deltas[identity]
                settings=(entry.policy_snapshot or {}).get('settings',{})
                channels=set(settings.get('collection_accounts',{}).values())|set(settings.get('cash_accounts',['1001','1011','1012','1013','1020']))|{'1031','1032','1033','1034'}
                if settings and new_balance<0 and account.account_code in channels and account.account_code not in settings.get('allow_negative_accounts',[]):raise AppException(409,'accounting_insufficient_recorded_funds','Insufficient recorded funds in account '+account.account_code+'; reconcile funding or use an explicitly approved overdraft policy')
                if abs(new_balance)>Decimal('999999999999.99'):raise AppException(422,'account_balance_limit','Account balance exceeds supported ledger precision')
                account.current_balance=new_balance
                account.updated_by=actor.id
            from sqlalchemy import inspect
            if inspect(entry).persistent:self.db.flush(entry.lines)
            entry.posting_applied_at=datetime.now(UTC)
            entry.status='posted'
            entry.posted_at=entry.posted_at or entry.posting_applied_at
            self.db.flush()

    def _create_auto_entry(self, actor: User, source_module: str, source_reference: str, journal_date: date, narration: str, lines: list[tuple], cost_center: str | None = None, source_snapshot: dict | None = None) -> JournalEntry:
        lines=[line for line in lines if Decimal(line[2] or 0)!=0 or Decimal(line[3] or 0)!=0]
        total_debit = sum(Decimal(line[2] or 0) for line in lines)
        total_credit = sum(Decimal(line[3] or 0) for line in lines)
        if total_debit != total_credit:
            raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, "unbalanced_auto_entry", f"Auto entry for {source_reference} is not balanced.")
        entry = JournalEntry(
            branch_id=actor.branch_id,
            policy_snapshot={'source':source_snapshot} if source_snapshot else None,
            journal_number=f"JE-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex.upper()}",
            journal_date=journal_date,
            source_module=source_module,
            source_reference=source_reference,
            narration=narration,
            status="posted",
            total_debit=total_debit,
            total_credit=total_credit,
            posted_at=datetime.now(UTC),
            approved_by_user_id=None,
            created_by=actor.id,
            updated_by=actor.id,
        )
        for values in lines:
            account_code,account_name,debit,credit=values[:4]
            center=values[4] if len(values)>4 and values[4] is not None else cost_center
            entry.lines.append(
                JournalEntryLine(
                    account_code=account_code,
                    cost_center=center,
                    account_name=account_name,
                    debit_amount=Decimal(debit or 0),
                    credit_amount=Decimal(credit or 0),
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )
        self.db.add(entry)
        self._apply_posting(entry, actor)
        return entry

    def _sum(self, column, *conditions) -> Decimal:
        stmt = select(func.coalesce(func.sum(column), 0))
        for condition in conditions:
            if condition is not None:
                stmt = stmt.where(condition)
        return Decimal(self.db.scalar(stmt) or 0)

    def _department_revenue(self, branch_id) -> list[AccountingChartPoint]:
        totals={}
        for invoice in self.db.scalars(select(BillingInvoice).where(BillingInvoice.branch_id==branch_id,BillingInvoice.status=='posted',BillingInvoice.is_active.is_(True))):
            for item in invoice.items:
                department=item.billing_department or invoice.billing_department or item.source_module or 'billing'
                credit=sum((Decimal(line.get('return_amount',0)) for refund in invoice.refunds if refund.refund_type=='return' for line in refund.return_items or [] if line.get('invoice_item_id')==str(item.id)),Decimal(0))
                totals[department]=totals.get(department,Decimal(0))+max(Decimal(0),item.net_amount-credit)
        return [AccountingChartPoint(label=key,value=value) for key,value in sorted(totals.items())]

    def _payment_methods(self, branch_id, month_start: date) -> list[AccountingChartPoint]:
        stmt = select(BillingPayment.payment_method, func.coalesce(func.sum(BillingPayment.amount), 0)).where(BillingPayment.branch_id == branch_id, BillingPayment.received_at >= month_start).group_by(BillingPayment.payment_method)
        return [AccountingChartPoint(label=row[0], value=Decimal(row[1] or 0)) for row in self.db.execute(stmt).all()]

    def _expense_breakdown(self, branch_id, month_start: date) -> list[AccountingChartPoint]:
        stmt = select(func.coalesce(Expense.department_name, Expense.payment_method), func.coalesce(func.sum(Expense.amount), 0)).where(Expense.branch_id == branch_id, Expense.expense_date >= month_start).group_by(Expense.department_name, Expense.payment_method)
        return [AccountingChartPoint(label=row[0] or "Expense", value=Decimal(row[1] or 0)) for row in self.db.execute(stmt).all()]

    def _cash_flow(self, branch_id) -> list[AccountingChartPoint]:
        points = []
        for offset in range(6, -1, -1):
            day = today_local() - timedelta(days=offset)
            start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
            end = start + timedelta(days=1)
            inflow = self._sum(BillingPayment.amount, BillingPayment.branch_id == branch_id, BillingPayment.received_at >= start, BillingPayment.received_at < end)
            outflow = self._sum(Expense.amount, Expense.branch_id == branch_id, Expense.expense_date == day)
            points.append(AccountingChartPoint(label=day.strftime("%d %b"), value=inflow - outflow))
        return points

    def _aging_points(self, amount_column, date_column, *conditions) -> list[AccountingChartPoint]:
        buckets = {"0-7": (0, 7), "8-30": (8, 30), "31-60": (31, 60), "60+": (61, 3650)}
        points = []
        today = today_local()
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
        import json
        self.db.add(AccountingAuditLog(branch_id=actor.branch_id, actor_user_id=actor.id, action=action, entity_type=entity_type, entity_id=entity_id, new_value=json.dumps(detail or {},default=str,ensure_ascii=False), ip_address=context.get("ip_address"), user_agent=context.get("user_agent"), created_by=actor.id, updated_by=actor.id))
