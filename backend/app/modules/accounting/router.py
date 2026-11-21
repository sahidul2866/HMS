from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppException
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.accounting.service import AccountingService
from app.schemas.accounting import (
    AccountCreate,
    AccountRead,
    AccountingReportSummary,
    AccountingSyncRead,
    AccountingDashboardRead,
    AccountingJournalCreate,
    AccountingJournalRead,
    AccountingWorkspaceRead,
    FinanceRecordRead,
    GeneralLedgerLineRead,
    JournalEntryActionRead,
    JournalEntryCreate,
    JournalEntryRead,
    SimpleFinanceCreate,
)

router = APIRouter(prefix="/accounting", tags=["Accounting"])


@router.get("/journals", response_model=list[AccountingJournalRead], dependencies=[Depends(require_permissions("accounting.view"))])
def list_journals(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[AccountingJournalRead]:
    return [AccountingJournalRead.model_validate(item, from_attributes=True) for item in AccountingService(db).list_journals(user)]


@router.get("/dashboard", response_model=AccountingDashboardRead, dependencies=[Depends(require_permissions("accounting.view"))])
def dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)) -> AccountingDashboardRead:
    return AccountingService(db).dashboard(user)


@router.get("/workspace", response_model=AccountingWorkspaceRead, dependencies=[Depends(require_permissions("accounting.view"))])
def workspace(user=Depends(get_current_user), db: Session = Depends(get_db)) -> AccountingWorkspaceRead:
    return AccountingService(db).workspace(user)


@router.get("/accounts", response_model=list[AccountRead], dependencies=[Depends(require_permissions("accounting.view"))])
def list_accounts(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[AccountRead]:
    return [AccountRead.model_validate(item, from_attributes=True) for item in AccountingService(db).list_accounts(user)]


@router.post("/accounts", response_model=AccountRead, dependencies=[Depends(require_any_permissions("accounting.chart_of_accounts.manage", "accounting.manage"))])
def create_account(
    payload: AccountCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountRead:
    return AccountRead.model_validate(AccountingService(db).create_account(payload, user, context), from_attributes=True)


@router.get("/journal-entries", response_model=list[JournalEntryRead], dependencies=[Depends(require_permissions("accounting.view"))])
def list_journal_entries(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[JournalEntryRead]:
    return [JournalEntryRead.model_validate(item, from_attributes=True) for item in AccountingService(db).list_journal_entries(user)]


@router.post("/journal-entries", response_model=JournalEntryRead, dependencies=[Depends(require_any_permissions("accounting.voucher.create", "accounting.journal.create", "accounting.journal.post"))])
def create_journal_entry(
    payload: JournalEntryCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JournalEntryRead:
    return JournalEntryRead.model_validate(AccountingService(db).create_journal_entry(payload, user, context), from_attributes=True)


@router.get("/ledger", response_model=list[GeneralLedgerLineRead], dependencies=[Depends(require_any_permissions("accounting.ledger.view", "accounting.view"))])
def general_ledger(
    account_code: str | None = None,
    source_module: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GeneralLedgerLineRead]:
    return AccountingService(db).list_general_ledger(user, account_code, source_module, date_from, date_to)


@router.get("/reports", response_model=AccountingReportSummary, dependencies=[Depends(require_any_permissions("accounting.report.view", "accounting.reports.view", "reporting.financial.view"))])
def reports(user=Depends(get_current_user), db: Session = Depends(get_db)) -> AccountingReportSummary:
    return AccountingService(db).reports(user)


@router.post("/sync-integrations", response_model=AccountingSyncRead, dependencies=[Depends(require_any_permissions("accounting.voucher.post", "accounting.journal.post", "accounting.manage"))])
def sync_integrations(
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountingSyncRead:
    return AccountingSyncRead(**AccountingService(db).sync_source_entries(user, context))


@router.post("/journal-entries/{entry_id}/{action}", response_model=JournalEntryActionRead, dependencies=[Depends(require_any_permissions("accounting.voucher.approve", "accounting.voucher.post", "accounting.voucher.reverse", "accounting.journal.post"))])
def voucher_action(
    entry_id: UUID,
    action: str,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JournalEntryActionRead:
    entry = AccountingService(db).voucher_action(entry_id, action, user, context)
    return JournalEntryActionRead(id=entry.id, journal_number=entry.journal_number, status=entry.status, message=f"Voucher {action} completed.")


@router.post("/finance-records/{kind}/{record_id}/{new_status}", response_model=FinanceRecordRead, dependencies=[Depends(require_any_permissions("accounting.expense.approve", "accounting.approve", "accounting.manage"))])
def update_finance_record_status(
    kind: str,
    record_id: UUID,
    new_status: str,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinanceRecordRead:
    service = AccountingService(db)
    entity = service.update_finance_record_status(kind, record_id, new_status, user, context)
    return service._finance_record(
        entity,
        getattr(entity, "receipt_number", None) or getattr(entity, "refund_number", None) or getattr(entity, "claim_number", None) or getattr(entity, "bill_number", None) or getattr(entity, "invoice_number", None) or getattr(entity, "expense_number", None) or kind,
        getattr(entity, "provider_name", None) or getattr(entity, "company_name", None) or getattr(entity, "supplier_name", None) or getattr(entity, "vendor_name", None) or kind.title(),
        getattr(entity, "amount", None) or getattr(entity, "claim_amount", None) or getattr(entity, "net_amount", None) or getattr(entity, "gross_amount", None) or 0,
        getattr(entity, "status", "created"),
        getattr(entity, "due_amount", 0),
        getattr(entity, "paid_amount", 0),
        getattr(entity, "category", None),
    )


@router.post("/journal/post", response_model=AccountingJournalRead, dependencies=[Depends(require_any_permissions("accounting.voucher.post", "accounting.journal.post"))])
def post_journal(
    payload: AccountingJournalCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountingJournalRead:
    journal = AccountingService(db).post_journal(payload, user, context)
    return AccountingJournalRead(id=journal.id,journal_number=journal.journal_number,description=journal.narration,debit_amount=journal.total_debit,credit_amount=journal.total_credit,status=journal.status)


from app.modules.accounting.management import AccountingManagement
from app.schemas.accounting_standard import PolicyCreate,PeriodCreate,AccountingReason,AccountUpdate
from app.models.accounting_control import AccountingPolicy,FinancialPeriod
from sqlalchemy import select


def control_row(row):
    return {column.name:getattr(row,column.name) for column in row.__table__.columns}


@router.post('/coa-template',dependencies=[Depends(require_permissions('accounting.chart_of_accounts.manage'))])
def install_accounting_template(user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.modules.accounting.coa import install_template
    from app.modules.support_posting.service import lock_branch
    lock_branch(db,user)
    return install_template(db,user)


@router.patch('/accounts/{identity}',response_model=AccountRead,dependencies=[Depends(require_permissions('accounting.chart_of_accounts.manage'))])
def update_account(identity:UUID,payload:AccountUpdate,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return AccountingManagement(db).update_account(identity,payload,user)


@router.get('/policies',dependencies=[Depends(require_permissions('accounting.view'))])
def accounting_policies(user=Depends(get_current_user),db:Session=Depends(get_db)):
    return [control_row(row) for row in db.scalars(select(AccountingPolicy).where(AccountingPolicy.branch_id==user.branch_id).order_by(AccountingPolicy.version.desc()))]


@router.post('/policies',dependencies=[Depends(require_permissions('accounting.manage'))])
def propose_accounting_policy(payload:PolicyCreate,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(AccountingManagement(db).propose_policy(payload,user))


@router.post('/policies/{identity}/approve',dependencies=[Depends(require_permissions('accounting.approve'))])
def approve_accounting_policy(identity:UUID,payload:AccountingReason,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(AccountingManagement(db).approve_policy(identity,user,payload.reason))


@router.get('/periods',dependencies=[Depends(require_permissions('accounting.view'))])
def accounting_periods(user=Depends(get_current_user),db:Session=Depends(get_db)):
    return [control_row(row) for row in db.scalars(select(FinancialPeriod).where(FinancialPeriod.branch_id==user.branch_id).order_by(FinancialPeriod.start_date.desc()))]


@router.post('/periods',dependencies=[Depends(require_permissions('accounting.manage'))])
def create_accounting_period(payload:PeriodCreate,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(AccountingManagement(db).create_period(payload,user))


@router.post('/periods/{identity}/{action}',dependencies=[Depends(require_permissions('accounting.approve'))])
def accounting_period_action(identity:UUID,action:str,payload:AccountingReason,user=Depends(get_current_user),db:Session=Depends(get_db)):
    if action=='year-end-close':return control_row(AccountingManagement(db).year_end(identity,user,payload.reason))
    return control_row(AccountingManagement(db).period_action(identity,action,user,payload.reason))


@router.get('/statements',dependencies=[Depends(require_permissions('accounting.report.view'))])
def accounting_statements(date_from:date|None=None,date_to:date|None=None,cost_center:str|None=None,source_module:str|None=None,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return AccountingManagement(db).statements(user,date_from,date_to,cost_center,source_module)


from app.modules.accounting.cash_management import CashManagement
from app.schemas.accounting_standard import ShiftOpen,ShiftClose,CashTransfer
from app.models.accounting import CashClosing


@router.get('/cash-shifts',dependencies=[Depends(require_permissions('accounting.view'))])
def cash_shifts(user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.modules.auth.service import AuthService
    query=select(CashClosing).where(CashClosing.branch_id==user.branch_id)
    if 'accounting.approve' not in AuthService(db).get_effective_permissions(user):query=query.where(CashClosing.cashier_user_id==user.id)
    return [control_row(row) for row in db.scalars(query.order_by(CashClosing.created_at.desc()).limit(100))]


@router.post('/cash-shifts',dependencies=[Depends(require_permissions('accounting.cash_bank.manage'))])
def open_cash_shift(payload:ShiftOpen,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(CashManagement(db).open_shift(payload,user))


@router.post('/cash-shifts/{identity}/close',dependencies=[Depends(require_permissions('accounting.cash_bank.manage'))])
def close_cash_shift(identity:UUID,payload:ShiftClose,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(CashManagement(db).close_shift(identity,payload,user))


@router.post('/cash-shifts/{identity}/approve',dependencies=[Depends(require_permissions('accounting.approve'))])
def approve_cash_shift(identity:UUID,payload:AccountingReason,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(CashManagement(db).approve_shift(identity,user,payload.reason))


@router.post('/cash-transfers',response_model=JournalEntryRead,dependencies=[Depends(require_permissions('accounting.cash_bank.manage'))])
def cash_transfer(payload:CashTransfer,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return CashManagement(db).transfer(payload,user)


from app.modules.accounting.payables import Payables
from app.schemas.accounting_standard import FinancePayment


@router.post('/supplier-invoices/{identity}/payments',dependencies=[Depends(require_permissions('accounting.supplier_payment.create'))])
def supplier_payment(identity:UUID,payload:FinancePayment,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(Payables(db).supplier_payment(identity,payload,user))


from app.schemas.accounting_standard import TaxVoucher


@router.post('/tax-vouchers',dependencies=[Depends(require_permissions('accounting.journal.create'))])
def create_tax_voucher(payload:TaxVoucher,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.modules.accounting.tax import statutory_voucher
    return statutory_voucher(db,payload,user)


from app.models.accounting_control import FixedAsset
from app.modules.accounting.assets import Assets
from app.schemas.accounting_standard import AssetCreate,AssetDepreciation,AssetDisposal


@router.get('/assets',dependencies=[Depends(require_permissions('accounting.view'))])
def fixed_assets(user=Depends(get_current_user),db:Session=Depends(get_db)):
    return [control_row(row) for row in db.scalars(select(FixedAsset).where(FixedAsset.branch_id==user.branch_id).order_by(FixedAsset.asset_code))]


@router.post('/assets',dependencies=[Depends(require_permissions('accounting.manage'))])
def register_asset(payload:AssetCreate,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(Assets(db).register(payload,user))


@router.post('/assets/{identity}/depreciation',dependencies=[Depends(require_permissions('accounting.journal.post'))])
def depreciate_asset(identity:UUID,payload:AssetDepreciation,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(Assets(db).depreciate(identity,payload,user))


@router.post('/assets/{identity}/disposal',dependencies=[Depends(require_permissions('accounting.approve'))])
def dispose_asset(identity:UUID,payload:AssetDisposal,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(Assets(db).dispose(identity,payload,user))


@router.post('/periods/{identity}/year-end-close',dependencies=[Depends(require_permissions('accounting.approve'))])
def year_end_close(identity:UUID,payload:AccountingReason,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(AccountingManagement(db).year_end(identity,user,payload.reason))


from app.modules.accounting.reconciliation import Reconciliation
from app.schemas.accounting_standard import BankStatementImport,BankStatementMatch


@router.get('/bank-statements',dependencies=[Depends(require_permissions('accounting.view'))])
def bank_statement_rows(user=Depends(get_current_user),db:Session=Depends(get_db)):
    return Reconciliation(db).rows(user)


@router.post('/bank-statements',dependencies=[Depends(require_permissions('accounting.cash_bank.manage'))])
def import_bank_statement(payload:BankStatementImport,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return Reconciliation(db).import_rows(payload,user)


@router.post('/bank-statements/{identity}/match',dependencies=[Depends(require_permissions('accounting.cash_bank.manage'))])
def match_bank_statement(identity:UUID,payload:BankStatementMatch,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(Reconciliation(db).match(identity,payload,user))


@router.get('/statements.xlsx',dependencies=[Depends(require_permissions('accounting.report.export'))])
def export_statements(date_from:date|None=None,date_to:date|None=None,cost_center:str|None=None,source_module:str|None=None,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from fastapi.responses import Response
    from app.modules.accounting.exports import statements_xlsx
    content=statements_xlsx(AccountingManagement(db).statements(user,date_from,date_to,cost_center,source_module))
    return Response(content,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="hospital-financial-statements.xlsx"'})


from fastapi import UploadFile,File,Form


@router.post('/bank-statements/import-csv',dependencies=[Depends(require_permissions('accounting.cash_bank.manage'))])
async def import_statement_csv(file:UploadFile=File(...),ledger_account_code:str=Form(...),user=Depends(get_current_user),db:Session=Depends(get_db)):
    import csv,io
    from app.schemas.accounting_standard import BankStatementRow
    raw=await file.read(250001)
    if len(raw)>250000:raise AppException(422,'statement_file_size','CSV statement exceeds 250 KB')
    try:
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if not {'external_id','transaction_date','signed_amount','reference'}.issubset(set(reader.fieldnames or [])):raise ValueError('Missing columns')
        rows=[]
        for index,row in enumerate(reader):
            if index>=500:raise ValueError('More than 500 rows')
            rows.append(BankStatementRow.model_validate({key:row[key] for key in ['external_id','transaction_date','signed_amount','reference']}))
        payload=BankStatementImport(ledger_account_code=ledger_account_code,rows=rows)
    except (ValueError,UnicodeError):raise AppException(422,'statement_csv','Use UTF-8 CSV columns external_id, transaction_date (YYYY-MM-DD), signed_amount, reference; maximum 500 valid rows')
    return Reconciliation(db).import_rows(payload,user)


from app.schemas.accounting_standard import PharmacyOpeningValue


@router.get('/pharmacy-refunds',dependencies=[Depends(require_permissions('accounting.view'))])
def pharmacy_refunds(user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.models.pharmacy import PharmacySaleReturn
    from app.models.accounting import JournalEntry
    paid=set(db.scalars(select(JournalEntry.source_reference).where(JournalEntry.branch_id==user.branch_id,JournalEntry.source_module=='pharmacy_refund_payment')))
    entries=list(db.scalars(select(JournalEntry).where(JournalEntry.branch_id==user.branch_id,JournalEntry.source_module=='pharmacy_return',JournalEntry.status=='posted')))
    liability={entry.source_reference:sum((line.credit_amount-line.debit_amount for line in entry.lines if line.account_code=='2220'),0) for entry in entries}
    return [{**control_row(row),'refund_amount':str(liability[row.return_number])} for row in db.scalars(select(PharmacySaleReturn).where(PharmacySaleReturn.branch_id==user.branch_id)) if str(row.id) not in paid and liability.get(row.return_number,0)>0]


@router.post('/pharmacy-returns/{identity}/payment',dependencies=[Depends(require_permissions('accounting.approve'))])
def pharmacy_refund_payment(identity:UUID,payload:FinancePayment,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.modules.accounting.pharmacy_posting import pay_return
    return control_row(pay_return(db,identity,payload,user))


@router.post('/pharmacy/{identity}/opening-value',dependencies=[Depends(require_permissions('accounting.approve'))])
def pharmacy_opening_value(identity:UUID,payload:PharmacyOpeningValue,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.modules.accounting.pharmacy_posting import set_opening_value
    return set_opening_value(db,identity,payload,user)


from fastapi import Query


@router.get('/bank-statements/{identity}/suggestions',dependencies=[Depends(require_permissions('accounting.view'))])
def bank_statement_suggestions(identity:UUID,days:int=Query(default=3,ge=0,le=30),user=Depends(get_current_user),db:Session=Depends(get_db)):
    return Reconciliation(db).suggestions(identity,user,days)


from app.modules.accounting.reporting import AccountingReports


@router.get('/aging/{kind}',dependencies=[Depends(require_permissions('accounting.report.view'))])
def aging_report(kind:str,as_of:date|None=None,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return AccountingReports(db).aging(user,kind,as_of)


@router.get('/analysis/{kind}',dependencies=[Depends(require_permissions('accounting.report.view'))])
def accounting_analysis(kind:str,date_from:date|None=None,date_to:date|None=None,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return AccountingReports(db).analysis(user,kind,date_from,date_to)


@router.get('/analysis-export/{kind}',dependencies=[Depends(require_permissions('accounting.report.export'))])
def export_analysis(kind:str,date_from:date|None=None,date_to:date|None=None,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from fastapi.responses import Response
    from app.modules.accounting.exports import analysis_xlsx
    report=AccountingReports(db).analysis(user,kind,date_from,date_to)
    return Response(analysis_xlsx(report,kind),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="hospital-analysis.xlsx"'})


@router.get('/aging-export/{kind}',dependencies=[Depends(require_permissions('accounting.report.export'))])
def export_aging(kind:str,as_of:date|None=None,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from fastapi.responses import Response
    from app.modules.accounting.exports import analysis_xlsx
    report=AccountingReports(db).aging(user,kind,as_of)
    return Response(analysis_xlsx(report,kind+' aging'),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':'attachment; filename="hospital-aging.xlsx"'})


@router.get('/audit',dependencies=[Depends(require_permissions('accounting.view'))])
def accounting_audit(limit:int=Query(default=100,ge=1,le=500),user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.models.accounting import AccountingAuditLog
    return [control_row(row) for row in db.scalars(select(AccountingAuditLog).where(AccountingAuditLog.branch_id==user.branch_id).order_by(AccountingAuditLog.created_at.desc()).limit(limit))]


@router.get('/pharmacy-valuation',dependencies=[Depends(require_permissions('accounting.view'))])
def pharmacy_valuation(user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.models.pharmacy import PharmacyMedicine
    from app.models.inventory import InventoryItem
    from app.models.accounting import JournalEntry,JournalEntryLine
    from sqlalchemy import func
    medicines=list(db.scalars(select(PharmacyMedicine).where(PharmacyMedicine.branch_id==user.branch_id,PharmacyMedicine.is_active.is_(True))))
    valued=sum((row.inventory_value or 0 for row in medicines),0)
    posted=db.scalar(select(func.coalesce(func.sum(JournalEntryLine.debit_amount-JournalEntryLine.credit_amount),0)).join(JournalEntry,JournalEntry.id==JournalEntryLine.journal_entry_id).where(JournalEntry.branch_id==user.branch_id,JournalEntry.posting_applied_at.is_not(None),JournalEntryLine.account_code=='1310'))
    return {'inventory_value':str(valued),'gl_inventory_value':str(posted),'difference':str(valued-posted),'medicines':[{'id':row.id,'name':row.name,'quantity':str(row.stock_quantity),'inventory_value':str(row.inventory_value) if row.inventory_value is not None else None} for row in medicines],'basis':'Pharmacy catalog weighted-average valuation; unvalued legacy stock needs reviewed opening allocation. Warehouse inventory is separately controlled in account 1300.'}


from app.schemas.accounting_standard import PaymentAdjustmentCreate
from app.modules.accounting.payment_adjustments import PaymentAdjustments
from app.models.accounting_control import AccountingPaymentAdjustment


@router.get('/payment-adjustments',dependencies=[Depends(require_permissions('accounting.view'))])
def payment_adjustments(user=Depends(get_current_user),db:Session=Depends(get_db)):
    return [control_row(row) for row in db.scalars(select(AccountingPaymentAdjustment).where(AccountingPaymentAdjustment.branch_id==user.branch_id).order_by(AccountingPaymentAdjustment.created_at.desc()).limit(200))]


@router.post('/payment-adjustments',dependencies=[Depends(require_any_permissions('billing.payment.collect','accounting.approve'))])
def create_payment_adjustment(payload:PaymentAdjustmentCreate,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return control_row(PaymentAdjustments(db).record(payload,user))


@router.get('/integrity',dependencies=[Depends(require_permissions('accounting.view'))])
def accounting_integrity(user=Depends(get_current_user),db:Session=Depends(get_db)):
    return AccountingManagement(db).integrity(user)


from app.schemas.accounting_standard import LegacyJournalResolution


@router.get('/legacy-summary-journals',dependencies=[Depends(require_permissions('accounting.view'))])
def legacy_summary_journals(user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.models.accounting import AccountingJournal,AccountingAuditLog
    mapped=set(db.scalars(select(AccountingAuditLog.entity_id).where(AccountingAuditLog.branch_id==user.branch_id,AccountingAuditLog.action=='accounting.legacy_journal.resolve')))
    return [{**control_row(row),'resolved':str(row.id) in mapped} for row in db.scalars(select(AccountingJournal).where(AccountingJournal.branch_id==user.branch_id).order_by(AccountingJournal.created_at))]


@router.post('/legacy-summary-journals/{identity}/resolve',dependencies=[Depends(require_permissions('accounting.approve'))])
def resolve_legacy_summary(identity:UUID,payload:LegacyJournalResolution,user=Depends(get_current_user),db:Session=Depends(get_db)):
    return AccountingManagement(db).resolve_legacy_journal(identity,payload,user)


@router.get('/employee-advances',dependencies=[Depends(require_permissions('accounting.view'))])
def employee_advances(user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.models.hr import HREmployeeLoan,HREmployee
    return [{**control_row(row),'employee_name':employee.full_name} for row,employee in db.execute(select(HREmployeeLoan,HREmployee).join(HREmployee,HREmployee.id==HREmployeeLoan.employee_id).where(HREmployeeLoan.branch_id==user.branch_id).order_by(HREmployeeLoan.created_at.desc()))]


@router.post('/employee-advances/{identity}/disburse',dependencies=[Depends(require_permissions('accounting.approve'))])
def disburse_employee_advance(identity:UUID,payload:FinancePayment,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.modules.accounting.employee_advances import EmployeeAdvances
    return control_row(EmployeeAdvances(db).disburse(identity,payload,user))


@router.get('/inventory-adjustments',dependencies=[Depends(require_permissions('accounting.view'))])
def pending_stock_adjustments(user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.models.inventory import StockAdjustment,InventoryItem
    return [{**control_row(row),'item_name':item.name} for row,item in db.execute(select(StockAdjustment,InventoryItem).join(InventoryItem,InventoryItem.id==StockAdjustment.item_id).where(InventoryItem.branch_id==user.branch_id,StockAdjustment.status.in_(['draft','pending'])).order_by(StockAdjustment.created_at))]


@router.post('/inventory-adjustments/{identity}/approve',dependencies=[Depends(require_permissions('accounting.approve')),Depends(require_any_permissions('inventory.adjust','inventory.stock.adjust'))])
def approve_inventory_adjustment(identity:UUID,payload:AccountingReason,user=Depends(get_current_user),db:Session=Depends(get_db)):
    from app.modules.accounting.inventory_posting import approve_adjustment
    return control_row(approve_adjustment(db,identity,user,payload.reason))


@router.post("/{kind}", response_model=FinanceRecordRead, dependencies=[Depends(require_any_permissions("accounting.expense.create", "accounting.supplier_payment.create", "accounting.manage"))])
def create_finance_record(
    kind: str,
    payload: SimpleFinanceCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinanceRecordRead:
    entity = AccountingService(db).create_simple(kind, payload, user, context)
    return AccountingService(db)._finance_record(
        entity,
        getattr(entity, "receipt_number", None) or getattr(entity, "refund_number", None) or getattr(entity, "claim_number", None) or getattr(entity, "bill_number", None) or getattr(entity, "invoice_number", None) or getattr(entity, "expense_number", None) or kind,
        getattr(entity, "provider_name", None) or getattr(entity, "company_name", None) or getattr(entity, "supplier_name", None) or getattr(entity, "vendor_name", None) or kind.title(),
        getattr(entity, "amount", None) or getattr(entity, "claim_amount", None) or getattr(entity, "net_amount", None) or getattr(entity, "gross_amount", None) or 0,
        getattr(entity, "status", "created"),
        getattr(entity, "due_amount", 0),
        getattr(entity, "paid_amount", 0),
        getattr(entity, "category", None),
    )
