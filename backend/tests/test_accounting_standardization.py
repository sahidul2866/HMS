"""Real PostgreSQL accounting integrity and control regressions."""
from datetime import date,timedelta
from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session
from pydantic import ValidationError
from test_opd_workflow_integration import database,db,seed
from app.core.exceptions import AppException
from app.models.accounting import Account,JournalEntry,JournalEntryLine
from app.models.accounting_control import AccountingPolicy,AccountingPostingKey,FinancialPeriod
from app.models.user import User
from app.modules.accounting.service import AccountingService
from app.modules.accounting.management import AccountingManagement
from app.modules.accounting.coa import install_template
from app.schemas.accounting import AccountCreate,JournalEntryCreate,JournalEntryLineCreate
from app.schemas.accounting_standard import PeriodCreate,PolicyCreate,AccountingSettings,AccountUpdate


def voucher(amount=100,**kwargs):
    return JournalEntryCreate(journal_date=date.today(),narration='Synthetic balanced voucher',lines=[JournalEntryLineCreate(account_code='1001',account_name='Cash',debit_amount=amount),JournalEntryLineCreate(account_code='4000',account_name='Revenue',credit_amount=amount)],**kwargs)


def setup(db):
    admin,_,_,_=seed(db)
    return admin,AccountingService(db),AccountingManagement(db)


def test_coa_template_is_hierarchical_idempotent_and_preserves_existing_names(db):
    admin,service,management=setup(db)
    install_template(db,admin);count=db.scalar(select(func.count(Account.id)))
    assert count>65
    account=db.scalar(select(Account).where(Account.account_code=='1001'));account.name='Approved local cash name';db.commit()
    install_template(db,admin)
    assert db.scalar(select(func.count(Account.id)))==count and account.name=='Approved local cash name'
    assert account.parent_id and db.get(Account,account.parent_id).is_control
    assert db.scalar(select(Account).where(Account.account_code=='4000')).category=='income'


@pytest.mark.parametrize('debit,credit',[(100,90),(-100,-100),(0,0),('1.001','1.001')])
def test_invalid_journal_amounts_are_rejected(debit,credit):
    with pytest.raises(ValidationError):
        JournalEntryCreate(journal_date=date.today(),narration='Reject unsafe amounts',lines=[JournalEntryLineCreate(account_code='1001',account_name='Cash',debit_amount=debit),JournalEntryLineCreate(account_code='4000',account_name='Revenue',credit_amount=credit)])


def test_line_with_both_debit_and_credit_is_rejected():
    with pytest.raises(ValidationError):JournalEntryCreate(journal_date=date.today(),narration='Two-sided line',lines=[JournalEntryLineCreate(account_code='1001',account_name='Cash',debit_amount=100,credit_amount=20),JournalEntryLineCreate(account_code='4000',account_name='Revenue',credit_amount=80)])


def test_posting_reversal_and_statements_keep_original_and_reversal(db):
    admin,service,management=setup(db)
    entry=service.create_journal_entry(voucher(),admin,{})
    first=management.statements(admin)
    assert first['profit_and_loss']['net_profit']=='100.00' and first['balance_sheet']['equation_difference']=='0.00'
    reversal=service.voucher_action(entry.id,'reverse',admin,{})
    statement=management.statements(admin)
    assert statement['profit_and_loss']['net_profit']=='0.00' and statement['balance_sheet']['assets']=='0.00'
    assert len(service.list_general_ledger(admin))==4
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1001'))==0
    with pytest.raises(AppException):service.voucher_action(entry.id,'reverse',admin,{})


def test_repeated_request_is_idempotent_and_conflicting_content_is_rejected(db):
    admin,service,_=setup(db)
    payload=voucher(request_key='accounting-test-key')
    first=service.create_journal_entry(payload,admin,{})
    assert service.create_journal_entry(payload,admin,{}).id==first.id
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1001'))==100
    with pytest.raises(AppException):service.create_journal_entry(voucher(200,request_key='accounting-test-key'),admin,{})


def test_reversed_source_cannot_be_reposted_as_new_earnings(db):
    admin,service,_=setup(db)
    first=service.create_journal_entry(voucher(source_module='test_source',source_reference='source-001'),admin,{})
    service.voucher_action(first.id,'reverse',admin,{})
    with pytest.raises(AppException):service.create_journal_entry(voucher(source_module='test_source',source_reference='source-001'),admin,{})


def test_accounts_cannot_create_money_or_accept_control_postings(db):
    admin,service,management=setup(db)
    with pytest.raises(AppException):service.create_account(AccountCreate(account_code='TEST',name='Opening bypass',category='assets',opening_balance=100),admin,{})
    install_template(db,admin)
    payload=voucher();payload.lines[0].account_code='1000'
    with pytest.raises(AppException):service.create_journal_entry(payload,admin,{})
    db.rollback()


def test_period_lock_overlap_and_authorized_adjustment_date(db):
    admin,service,management=setup(db)
    today=date.today();period=management.create_period(PeriodCreate(name='Current month',start_date=today,end_date=today),admin)
    with pytest.raises(AppException):management.create_period(PeriodCreate(name='Overlap',start_date=today,end_date=today),admin)
    service.create_journal_entry(voucher(),admin,{})
    management.period_action(period.id,'close',admin,'Books reconciled')
    with pytest.raises(AppException,match='locked period'):service.create_journal_entry(voucher(),admin,{})
    db.rollback()
    management.period_action(period.id,'reopen',admin,'Approved correction')
    assert service.create_journal_entry(voucher(),admin,{}).posting_applied_at


def test_policy_approval_and_manual_maker_checker_are_independent(db):
    admin,service,management=setup(db)
    reviewer=User(branch_id=admin.branch_id,username='finance-reviewer',email='finance@example.test',full_name='Finance reviewer',hashed_password='unused',direct_permissions=admin.direct_permissions);db.add(reviewer);db.commit()
    policy=management.propose_policy(PolicyCreate(effective_from=date.today(),settings=AccountingSettings(cutover_date=date.today(),legal_name='Synthetic hospital',period_required=False)),admin)
    with pytest.raises(AppException):management.approve_policy(policy.id,admin,'Self approval prohibited')
    management.approve_policy(policy.id,reviewer,'Reviewed accounting policy')
    with pytest.raises(AppException):service.create_journal_entry(voucher(),admin,{})
    draft=service.create_journal_entry(voucher(status='draft'),admin,{})
    with pytest.raises(AppException):service.voucher_action(draft.id,'approve',admin,{})
    service.voucher_action(draft.id,'approve',reviewer,{})
    service.voucher_action(draft.id,'post',reviewer,{})
    assert draft.policy_snapshot['version']==1


def test_posting_validates_actual_lines_not_only_header_totals(db):
    admin,service,_=setup(db)
    entry=JournalEntry(branch_id=admin.branch_id,journal_number='BAD-'+uuid4().hex,journal_date=date.today(),narration='Header mismatch',status='draft',total_debit=100,total_credit=100,lines=[JournalEntryLine(account_code='1001',account_name='Cash',debit_amount=500,credit_amount=0),JournalEntryLine(account_code='4000',account_name='Revenue',debit_amount=0,credit_amount=100)])
    with pytest.raises(AppException):service._apply_posting(entry,admin)
    assert db.scalar(select(func.count(Account.id)))==0


def test_accounting_migration_preserves_history_and_enforces_database_immutability(database):
    import importlib.util
    from pathlib import Path
    from sqlalchemy.exc import DBAPIError
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.models.base import Base
    schema='accounting_migration_'+uuid4().hex
    with database.engine.begin() as conn:conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine=database.engine.execution_options(schema_translate_map={None:schema})
    Base.metadata.create_all(engine)
    try:
        with Session(engine,expire_on_commit=False) as session:
            actor,_,_,_=seed(session);service=AccountingService(session)
            entry=service.create_journal_entry(voucher(source_module='legacy_test',source_reference='legacy-preserved'),actor,{})
            identity=entry.id;actor_id=actor.id
        spec=importlib.util.spec_from_file_location('accounting_migration',Path(__file__).parents[1]/'alembic/versions/20261119_0078_accounting_controls.py');migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
        with engine.begin() as conn:
            conn.execute(text(f'SET LOCAL search_path TO {schema}'))
            for name in ['posting_applied_at','policy_snapshot','period_id','voucher_type']:conn.execute(text(f'ALTER TABLE journal_entries DROP COLUMN {name}'))
            for name in ['is_control','reporting_group','parent_id']:conn.execute(text(f'ALTER TABLE accounts DROP COLUMN {name}'))
            for name in ['inventory_value','valuation_opening_value','valuation_opening_journal_id']:conn.execute(text(f'ALTER TABLE pharmacy_medicines DROP COLUMN {name}'))
            for name in ['paid_amount','payment_method','payment_provider']:conn.execute(text(f'ALTER TABLE pharmacy_sales DROP COLUMN {name}'))
            conn.execute(text('ALTER TABLE pharmacy_sale_items DROP COLUMN cost_amount'))
            for name in ['unit_cost','cost_amount']:conn.execute(text(f'ALTER TABLE inventory_stock_transactions DROP COLUMN {name}'))
            conn.execute(text('ALTER TABLE billing_payments DROP COLUMN advance_payment_id'))
            for name in ['ledger_account_code','statement_key','matched_journal_id']:conn.execute(text(f'ALTER TABLE bank_transactions DROP COLUMN {name}'))
            conn.execute(text('ALTER TABLE supplier_invoices DROP COLUMN receiving_id'))
            conn.execute(text('ALTER TABLE supplier_invoices DROP COLUMN purchase_account_code'))
            conn.execute(text('ALTER TABLE supplier_invoices DROP COLUMN pharmacy_purchase_id'))
            for name in ['expense_account_code','cost_center']:conn.execute(text(f'ALTER TABLE expenses DROP COLUMN {name}'))
            for name in ['cash_account_code','counter_name','opened_at','closed_at']:conn.execute(text(f'ALTER TABLE cash_closing DROP COLUMN {name}'))
            for table in ['accounting_payment_adjustments','fixed_assets','accounting_posting_keys','financial_periods','accounting_policies']:conn.execute(text(f'DROP TABLE {table}'))
            with Operations.context(MigrationContext.configure(conn)):migration.upgrade()
            assert conn.scalar(text('SELECT count(*) FROM journal_entries'))==1
            assert conn.scalar(text('SELECT count(*) FROM accounting_posting_keys'))==1
            for statement in ["UPDATE journal_entries SET total_debit=200", "DELETE FROM journal_entries", "UPDATE journal_entry_lines SET debit_amount=200 WHERE debit_amount>0", "DELETE FROM journal_entry_lines"]:
                savepoint=conn.begin_nested()
                with pytest.raises(DBAPIError,match='immutable'):conn.execute(text(statement))
                savepoint.rollback()
            session=Session(conn,expire_on_commit=False,join_transaction_mode='create_savepoint')
            actor=session.get(User,actor_id)
            reversal=AccountingService(session).voucher_action(identity,'reverse',actor,{})
            conn.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
            assert reversal.total_debit==100
            session.close()
            conn.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
            with Operations.context(MigrationContext.configure(conn)):migration.downgrade()
            assert conn.scalar(text('SELECT count(*) FROM journal_entries'))==2
    finally:
        with database.engine.begin() as conn:conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))


@pytest.mark.parametrize('method,provider,code',[('cash',None,'1001'),('bank_transfer',None,'1020'),('card',None,'1034'),('mobile_banking','bkash','1031'),('mobile_banking','nagad','1032'),('mobile_banking','rocket','1033')])
def test_payment_channels_use_distinct_clearing_accounts(db,method,provider,code):
    from app.modules.accounting.channels import collection_account
    actor,_,_=setup(db)
    assert collection_account(db,actor,method,provider)==code


def test_cashier_counts_discrepancy_without_creating_cash_and_requires_supervisor(db):
    from app.modules.accounting.cash_management import CashManagement
    from app.schemas.accounting_standard import ShiftOpen,ShiftClose
    actor,service,_=setup(db);cash=CashManagement(db)
    shift=cash.open_shift(ShiftOpen(counter_name='Reception',opening_balance=5000),actor)
    service.create_journal_entry(voucher(25000),actor,{})
    close=cash.close_shift(shift.id,ShiftClose(counted_cash=29900,note='Physical count shortage'),actor)
    assert close.expected_cash==30000 and close.difference_amount==-100
    with pytest.raises(AppException):cash.approve_shift(shift.id,actor,'Cannot self approve')
    reviewer=User(branch_id=actor.branch_id,username='cash-supervisor',email='cash-supervisor@example.test',full_name='Supervisor',hashed_password='unused',direct_permissions=actor.direct_permissions);db.add(reviewer);db.commit()
    cash.approve_shift(shift.id,reviewer,'Shortage reviewed; adjustment separately authorized')
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1001'))==25000
    assert db.scalar(select(func.count(JournalEntry.id)))==1


def test_gateway_settlement_posts_net_bank_and_explicit_charges_once(db):
    from app.modules.accounting.cash_management import CashManagement
    from app.schemas.accounting_standard import CashTransfer
    actor,service,management=setup(db);install_template(db,actor)
    receipt=voucher(1000);receipt.lines[0].account_code='1031';service.create_journal_entry(receipt,actor,{})
    payload=CashTransfer(transaction_date=date.today(),from_account='1031',to_account='1020',amount=1000,processing_charge=15,reference='Verified bKash settlement',request_key='gateway-settlement-001')
    cash=CashManagement(db);first=cash.transfer(payload,actor);assert cash.transfer(payload,actor).id==first.id
    balances={row.account_code:row.current_balance for row in service.list_accounts(actor)}
    assert balances['1031']==0 and balances['1020']==985 and balances['5160']==15
    assert management.statements(actor)['profit_and_loss']['net_profit']=='985.00'


def test_supplier_liability_partial_and_final_payment_reconcile_without_duplicate_payment(db):
    from app.schemas.accounting import SimpleFinanceCreate
    from app.schemas.accounting_standard import FinancePayment
    from app.modules.accounting.payables import Payables
    actor,service,management=setup(db)
    invoice=service.create_simple('supplier',SimpleFinanceCreate(reference='SUP-TEST-001',name='Approved test supplier',amount=1000),actor,{})
    with pytest.raises(AppException):service.create_simple('supplier',SimpleFinanceCreate(reference='SUP-TEST-001',name='Approved test supplier',amount=1000),actor,{})
    service.update_finance_record_status('supplier',invoice.id,'approved',actor,{})
    payments=Payables(db)
    payload=FinancePayment(amount=300,payment_method='bank_transfer',reference='Supplier receipt 1',request_key='supplier-payment-1')
    first=payments.supplier_payment(invoice.id,payload,actor)
    assert payments.supplier_payment(invoice.id,payload,actor).id==first.id and invoice.due_amount==700
    payments.supplier_payment(invoice.id,FinancePayment(amount=700,payment_method='bank_transfer',reference='Supplier receipt 2',request_key='supplier-payment-2'),actor)
    assert invoice.status=='paid' and invoice.due_amount==0
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='2100'))==0
    assert management.statements(actor)['balance_sheet']['equation_difference']=='0.00'


def test_expense_approval_accrues_and_payment_clears_liability_once(db):
    from app.schemas.accounting import SimpleFinanceCreate
    actor,service,management=setup(db)
    expense=service.create_simple('expense',SimpleFinanceCreate(name='Utility provider',amount=200,expense_account_code='5120',note='Test electricity bill'),actor,{})
    service.update_finance_record_status('expense',expense.id,'approved',actor,{})
    assert management.statements(actor)['profit_and_loss']['expenses']=='200.00'
    service.update_finance_record_status('expense',expense.id,'paid',actor,{})
    service.update_finance_record_status('expense',expense.id,'paid',actor,{})
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='2500'))==0
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1001'))==-200
    assert db.scalar(select(func.count(JournalEntry.id)))==2


@pytest.mark.parametrize('kind,rate,exempt,inclusive,base,tax,gross',[('output_vat','10',False,False,'100.00','10.00','110.00'),('output_vat','10',False,True,'90.91','9.09','100.00'),('input_vat','10',False,False,'100.00','10.00','110.00'),('output_vat','0',True,False,'100.00','0.00','100.00'),('withholding','5',False,False,'100.00','5.00','100.00')])
def test_only_reviewed_effective_category_tax_rules_are_used(db,kind,rate,exempt,inclusive,base,tax,gross):
    from app.modules.accounting.tax import statutory_voucher
    from app.schemas.accounting_standard import TaxVoucher
    actor,_,_=setup(db)
    # Synthetic tax rates only; these are not Bangladesh statutory defaults.
    policy=AccountingPolicy(branch_id=actor.branch_id,version=1,effective_from=date.today(),approved_by=actor.id,settings={'cutover_date':date.today().isoformat(),'maker_checker':False,'tax_rules':[{'code':'TEST','kind':kind,'rate':rate,'exempt':exempt,'inclusive':inclusive,'service_category':'synthetic','effective_from':date.today().isoformat(),'ledger_account':'2250' if kind=='withholding' else '2240','official_reference':'https://nbr.gov.bd/','review_note':'Synthetic test-only rule'}]});db.add(policy);db.commit()
    opening=voucher(1000,voucher_type='opening');opening.lines[1].account_code='3100';AccountingService(db).create_journal_entry(opening,actor,{})
    payload=TaxVoucher(transaction_date=date.today(),tax_code='TEST',service_category='synthetic',basis_amount=100,base_account='2100' if kind=='withholding' else '4000',counterpart_account='1001',document_reference='SYNTHETIC-TAX-001',request_key='synthetic-tax-request')
    result=statutory_voucher(db,payload,actor)
    assert result['base']==base and result['tax']==tax and result['gross']==gross
    assert result['policy_version']==1
    assert statutory_voucher(db,payload,actor)['journal_id']==result['journal_id']
    with pytest.raises(AppException):statutory_voucher(db,payload.model_copy(update={'service_category':'unconfigured'}),actor)


def test_asset_register_depreciation_residual_and_disposal_are_balanced(db):
    from app.modules.accounting.assets import Assets
    from app.schemas.accounting_standard import AssetCreate,AssetDepreciation,AssetDisposal
    actor,service,management=setup(db)
    acquisition=voucher(1200);acquisition.lines[0].account_code='1500';acquisition.lines[1].account_code='1020'
    booked=service.create_journal_entry(acquisition,actor,{})
    assets=Assets(db)
    asset=assets.register(AssetCreate(asset_code='ASSET-TEST',name='Synthetic equipment',category='Laboratory equipment',cost=1200,residual_value=120,useful_life_months=12,acquisition_date=date.today(),depreciation_start=date.today(),acquisition_journal_id=booked.id),actor)
    month=date.today().strftime('%Y-%m');assets.depreciate(asset.id,AssetDepreciation(month=month),actor);assets.depreciate(asset.id,AssetDepreciation(month=month),actor)
    assert asset.accumulated_depreciation==90
    assets.dispose(asset.id,AssetDisposal(disposal_date=date.today(),proceeds=1000,reason='Authorized test disposal'),actor)
    assert asset.status=='disposed' and management.statements(actor)['balance_sheet']['equation_difference']=='0.00'
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1500'))==0


def test_year_end_moves_earnings_once_and_perpetual_assets_carry_forward(db):
    actor,service,management=setup(db)
    today=date.today();period=management.create_period(PeriodCreate(name='Synthetic fiscal year',start_date=today.replace(month=1,day=1),end_date=today),actor)
    service.create_journal_entry(voucher(1000),actor,{})
    expense=voucher(200);expense.lines[0].account_code='5180';expense.lines[1].account_code='1001';service.create_journal_entry(expense,actor,{})
    management.year_end(period.id,actor,'Fiscal-year reconciliation approved')
    count=db.scalar(select(func.count(JournalEntry.id)));management.year_end(period.id,actor,'Idempotent retry')
    assert db.scalar(select(func.count(JournalEntry.id)))==count
    assert management.statements(actor)['profit_and_loss']['net_profit']=='800.00'
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='3200'))==800
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1001'))==800
    assert management.statements(actor)['balance_sheet']['equation_difference']=='0.00'


def test_statement_import_match_duplicate_and_reversal_preserve_original_evidence(db):
    from app.modules.accounting.reconciliation import Reconciliation
    from app.schemas.accounting_standard import BankStatementImport,BankStatementRow,BankStatementMatch
    from app.models.accounting import BankTransaction
    actor,service,_=setup(db)
    payload=voucher(500);payload.lines[0].account_code='1020';entry=service.create_journal_entry(payload,actor,{})
    recon=Reconciliation(db);statement=BankStatementImport(ledger_account_code='1020',rows=[BankStatementRow(external_id='BANK-ROW-1',transaction_date=date.today(),signed_amount=500,reference='Bank verified reference')])
    assert recon.import_rows(statement,actor)['inserted']==1
    assert recon.import_rows(statement,actor)['duplicates']==1
    row=db.scalar(select(BankTransaction))
    recon.match(row.id,BankStatementMatch(journal_id=entry.id,reason='Exact receipt verified'),actor)
    assert recon.rows(actor)[0]['current_reconciliation_status']=='matched'
    service.voucher_action(entry.id,'reverse',actor,{})
    assert recon.rows(actor)[0]['current_reconciliation_status']=='reversal_review'
    assert row.amount==500 and db.scalar(select(func.count(BankTransaction.id)))==1


@pytest.mark.parametrize('role,expected_revenue,expected_expense',[('principal','500.00','350.00'),('agent','150.00','0')])
def test_verified_doctor_direct_collection_posts_receivable_not_hospital_cash(db,role,expected_revenue,expected_expense):
    from app.modules.accounting.doctor_collections import post_verified_doctor_collection
    from app.models.prescription import OPDExternalPayment
    from test_prescription_workflow import scenario
    actor,doctors,_,visit,_=scenario(db)
    db.add(AccountingPolicy(branch_id=actor.branch_id,version=1,effective_from=date.today(),approved_by=actor.id,settings={'cutover_date':date.today().isoformat(),'consultation_role':role,'maker_checker':False}));db.commit()
    claim=OPDExternalPayment(visit_id=visit.id,kind='doctor_direct',amount=500,request_key='doctor-receivable-test',reason='Verified synthetic receipt',settlement_snapshot={'doctor_share':'350.00','hospital_share_due':'150.00'});db.add(claim);db.flush()
    post_verified_doctor_collection(db,claim,visit,actor);db.commit()
    book=AccountingManagement(db).statements(actor)
    assert book['profit_and_loss']['income']==expected_revenue
    assert Decimal(book['profit_and_loss']['expenses'])==Decimal(expected_expense)
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1160'))==150
    assert not db.scalar(select(Account.id).where(Account.account_code=='1001'))


def test_patient_advance_is_liability_then_allocated_without_new_cash(db):
    from app.schemas.accounting import SimpleFinanceCreate
    from test_opd_workflow_integration import visit
    from app.modules.billing.service import BillingServiceManager
    from app.schemas.billing import BillingPaymentCreate
    from app.schemas.encounter import OPDVisitPaymentUpdate
    from app.modules.opd.service import OPDService
    from app.models.billing import BillingInvoice
    actor,doctors,patient,slot=seed(db);service=AccountingService(db)
    advance=service.create_simple('advance',SimpleFinanceCreate(patient_id=patient.id,amount=500,note='Actual patient advance received'),actor,{})
    assert service.reports(actor).profit_and_loss[0].value==0
    current=visit(db,actor,doctors[0],patient,slot)
    billing=BillingServiceManager(db);billing.list_services(actor)
    config=billing._consultation_service_for_visit(current,actor)
    from app.schemas.billing import BillingInvoiceCreate,BillingInvoiceItemCreate
    invoice=billing.create_invoice(BillingInvoiceCreate(patient_id=patient.id,source_opd_visit_id=current.id,source_module='opd',billing_stage='opd',items=[BillingInvoiceItemCreate(billing_service_id=config.id,quantity=1)]),actor,{})
    payload=BillingPaymentCreate(amount=500,payment_method='patient_advance',advance_payment_id=advance.id,request_key='patient-advance-apply')
    billing.create_payment(invoice.id,payload,actor,{});billing.create_payment(invoice.id,payload,actor,{})
    assert advance.balance_amount==0 and advance.adjusted_amount==500
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1001'))==500
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='2210'))==0
    assert invoice.due_amount==0


def test_pharmacy_weighted_cost_credit_sale_and_discounted_return_reconcile(db):
    from app.models.pharmacy import PharmacyMedicine,PharmacyMedicineType,PharmacyGeneric,PharmacyCompany
    from app.modules.pharmacy.service import PharmacyService
    from app.schemas.pharmacy import PharmacyPurchaseCreate,PharmacySaleCreate,PharmacySaleItemWrite,PharmacySaleReturnCreate
    actor,_,patient,_=seed(db)
    db.add(AccountingPolicy(branch_id=actor.branch_id,version=1,effective_from=date.today(),approved_by=actor.id,settings={'cutover_date':date.today().isoformat(),'maker_checker':False,'pharmacy_accounting_enabled':True}));db.commit()
    form=PharmacyMedicineType(name='Synthetic form');generic=PharmacyGeneric(name='Synthetic generic');company=PharmacyCompany(name='Synthetic manufacturer');db.add_all([form,generic,company]);db.flush()
    medicine=PharmacyMedicine(branch_id=actor.branch_id,medicine_type_id=form.id,generic_id=generic.id,company_id=company.id,name='Synthetic approved accounting item',stock_quantity=0,purchase_price=10,sale_price=20);db.add(medicine);db.commit()
    pharmacy=PharmacyService(db)
    purchase=pharmacy.create_purchase(PharmacyPurchaseCreate(medicine_id=medicine.id,purchase_date=date.today(),supplier_name='Synthetic supplier',quantity=10,unit_cost=10),actor,{})
    assert medicine.inventory_value==100
    sale=pharmacy.create_sale(PharmacySaleCreate(patient_id=patient.id,sale_date=date.today(),paid_amount=0,discount_amount=20,items=[PharmacySaleItemWrite(medicine_id=medicine.id,quantity=5,unit_price=20)]),actor,{})
    assert medicine.inventory_value==50
    book=AccountingManagement(db).statements(actor)
    assert book['profit_and_loss']['income']=='80.00' and book['profit_and_loss']['expenses']=='50.00'
    returned=pharmacy.create_return(PharmacySaleReturnCreate(sale_id=sale.id,sale_item_id=sale.items[0].id,returned_at=date.today(),quantity=2),actor,{})
    assert returned.total_amount==32 and medicine.inventory_value==70
    balances={row.account_code:row.current_balance for row in AccountingService(db).list_accounts(actor)}
    assert balances['1100']==48 and balances['1310']==70 and balances['5030']==30
    assert AccountingManagement(db).statements(actor)['balance_sheet']['equation_difference']=='0.00'
    with pytest.raises(AppException):pharmacy.delete_sale(sale.id,actor,{})


def test_doctor_funded_800_100_concession_direct_retention_cannot_be_paid_twice(db):
    from datetime import datetime,UTC
    from test_opd_workflow_integration import visit
    from app.modules.billing.service import BillingServiceManager
    from app.modules.billing.policies import FinancialPolicies
    from app.schemas.billing_policy import PolicyCreate as BillingPolicyCreate,FinancialRules,SettlementCreate
    from app.schemas.billing import BillingInvoiceCreate,BillingInvoiceItemCreate
    from app.modules.opd.prescriptions import PrescriptionWorkflow
    from app.schemas.prescription import DirectConsultationPayment,ExternalPaymentReview
    actor,doctors,patient,slot=seed(db);doctors[0].opd_consultation_fee=800;db.commit()
    current=visit(db,actor,doctors[0],patient,slot)
    db.add(AccountingPolicy(branch_id=actor.branch_id,version=1,effective_from=date.today(),approved_by=actor.id,settings={'cutover_date':date.today().isoformat(),'maker_checker':False,'consultation_role':'principal','revenue_accounts':{'opd':'4010'}}));db.commit()
    financial=FinancialPolicies(db)
    financial.create(BillingPolicyCreate(scope='hospital',selector='*',effective_from=datetime.now(UTC)-timedelta(days=1),reason='Approved doctor-funded concession',rules=FinancialRules(doctor_key='doctor',doctor_revenue_percentage=70,discount_sharing={'doctor':100})),actor)
    billing=BillingServiceManager(db);billing.list_services(actor);config=billing._consultation_service_for_visit(current,actor)
    invoice=billing.create_invoice(BillingInvoiceCreate(patient_id=patient.id,source_opd_visit_id=current.id,source_module='opd',billing_stage='opd',discount_reason='Doctor-funded concession',items=[BillingInvoiceItemCreate(billing_service_id=config.id,quantity=1,discount_amount=100)]),actor,{})
    assert invoice.total_amount==700
    workflow=PrescriptionWorkflow(db)
    workflow.external_payment(current.id,DirectConsultationPayment(kind='doctor_direct',amount=700,reason='Doctor collected actual cash',request_key='doctor-direct-800'),doctors[0])
    from app.models.prescription import OPDExternalPayment
    claim=db.scalar(select(OPDExternalPayment).where(OPDExternalPayment.visit_id==current.id))
    workflow.review_external_payment(current.id,claim.id,ExternalPaymentReview(decision='verified',evidence='Independent doctor receipt verification',request_key='doctor-direct-800-review'),actor)
    book=AccountingManagement(db).statements(actor)
    assert book['profit_and_loss']['income']=='700.00'
    assert book['profit_and_loss']['expenses']=='460.00'
    assert book['profit_and_loss']['net_profit']=='240.00'
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1160'))==240
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='2110'))==0
    assert not db.scalar(select(Account.id).where(Account.account_code=='1001'))
    with pytest.raises(AppException):financial.settle(SettlementCreate(participant_key='doctor',amount=1,reason='Duplicate retained earnings prohibited',request_key='duplicate-retained-payout'),actor)


def test_concurrent_journal_retries_post_once_and_distinct_entries_preserve_balances(database):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.models.base import Base
    schema='accounting_race_'+uuid4().hex
    with database.engine.begin() as conn:conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine=database.engine.execution_options(schema_translate_map={None:schema});Base.metadata.create_all(engine)
    try:
        with Session(engine,expire_on_commit=False) as session:
            actor,_,_,_=seed(session);actor_id=actor.id
            AccountingService(session).create_journal_entry(voucher(100,request_key='race-opening'),actor,{})
        for same_key in [True,False]:
            barrier=Barrier(2)
            def post(index):
                with Session(engine,expire_on_commit=False) as session:
                    actor=session.get(User,actor_id)
                    # Warm the identity map before the branch lock to exercise stale-cache protection.
                    session.scalar(select(Account).where(Account.account_code=='1001'))
                    barrier.wait(timeout=10)
                    key='race-repeat' if same_key else 'race-distinct-'+str(index)
                    return AccountingService(session).create_journal_entry(voucher(100,request_key=key),actor,{}).id
            with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(post,range(2)))
            assert (ids[0]==ids[1]) is same_key
        with Session(engine) as session:
            assert session.scalar(select(Account.current_balance).where(Account.account_code=='1001'))==400
            assert session.scalar(select(func.count(JournalEntry.id)))==4
    finally:
        with database.engine.begin() as conn:conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))


def test_failed_post_rolls_back_accounts_journal_keys_and_cash(db):
    actor,service,_=setup(db)
    payload=voucher(source_module='rollback_test',source_reference='rollback-001');payload.lines[1].account_code='UNCONFIGURED'
    with pytest.raises(AppException):service.create_journal_entry(payload,actor,{})
    db.rollback()
    assert db.scalar(select(func.count(JournalEntry.id)))==0
    assert db.scalar(select(func.count(AccountingPostingKey.id)))==0
    assert db.scalar(select(func.count(Account.id)))==0


@pytest.mark.parametrize('amount',['999999999999.99','0.01','100000000.33'])
def test_supported_large_amounts_and_smallest_paisa_remain_exact(db,amount):
    actor,service,management=setup(db)
    service.create_journal_entry(voucher(Decimal(amount)),actor,{})
    statement=management.statements(actor)
    assert Decimal(statement['total_debit'])==Decimal(amount)==Decimal(statement['total_credit'])
    assert Decimal(statement['balance_sheet']['equation_difference'])==0


def test_failed_attempt_has_no_cash_and_chargeback_reopens_receivable_once(db):
    from test_billing_policies import setup_invoice
    from app.models.accounting_control import AccountingPaymentAdjustment
    from app.modules.accounting.payment_adjustments import PaymentAdjustments
    from app.schemas.accounting_standard import PaymentAdjustmentCreate
    actor,billing,_,invoice,_,_=setup_invoice(db,paid=1800)
    adjustments=PaymentAdjustments(db);before=db.scalar(select(func.count(JournalEntry.id)))
    adjustments.record(PaymentAdjustmentCreate(invoice_id=invoice.id,kind='failed',amount=10,request_key='failed-attempt-1',reason='Verified failed provider attempt'),actor)
    assert db.scalar(select(func.count(JournalEntry.id)))==before
    original=invoice.payments[0]
    payload=PaymentAdjustmentCreate(invoice_id=invoice.id,payment_id=original.id,kind='chargeback',amount=500,request_key='chargeback-example-1',reason='Verified actual provider debit')
    first=adjustments.record(payload,actor);assert adjustments.record(payload,actor).id==first.id
    assert invoice.paid_amount==1300 and invoice.due_amount==500
    assert original.amount==1800
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1001'))==1300
    with pytest.raises(AppException):adjustments.record(payload.model_copy(update={'amount':Decimal(1800),'request_key':'chargeback-too-large'}),actor)


def test_cutover_reconciles_legacy_cached_opening_without_doubling_cash(db):
    actor,service,management=setup(db)
    db.add_all([Account(branch_id=actor.branch_id,account_code='1001',name='Legacy cash',category='assets',normal_balance='debit',current_balance=200,opening_balance=200),Account(branch_id=actor.branch_id,account_code='3100',name='Legacy capital',category='equity',normal_balance='credit',current_balance=200,opening_balance=200)])
    db.add(AccountingPolicy(branch_id=actor.branch_id,version=1,effective_from=date.today(),approved_by=actor.id,settings={'cutover_date':date.today().isoformat(),'maker_checker':False}));db.commit()
    with pytest.raises(AppException,match='opening balance'):service.create_journal_entry(voucher(100),actor,{})
    db.rollback()
    opening=voucher(200,voucher_type='opening');opening.lines[1].account_code='3100'
    journal=service.create_journal_entry(opening,actor,{})
    assert journal.policy_snapshot['opening_reconciliation']['1001']['previous_cached_balance']=='200.00'
    service.create_journal_entry(voucher(100),actor,{})
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1001'))==300
    assert management.statements(actor)['balance_sheet']['equation_difference']=='0.00'


def test_trial_balance_reports_ending_balances_not_gross_journal_turnover(db):
    actor,service,management=setup(db)
    service.create_journal_entry(voucher(100),actor,{})
    transfer=voucher(50);transfer.lines[0].account_code='1100';transfer.lines[1].account_code='1001';service.create_journal_entry(transfer,actor,{})
    book=management.statements(actor);accounts={row['code']:row for row in book['trial_balance']}
    assert accounts['1001']['debit']=='50.00' and accounts['1001']['credit']=='0'
    assert accounts['1001']['gross_debit_movements']=='100.00'
    assert Decimal(book['total_debit'])==100==Decimal(book['total_credit'])


def test_legacy_summary_resolution_links_opening_without_reposting_cash(db):
    from app.models.accounting import AccountingJournal
    from app.schemas.accounting_standard import LegacyJournalResolution
    actor,service,management=setup(db)
    legacy=AccountingJournal(branch_id=actor.branch_id,journal_number='OLD-'+uuid4().hex,description='Original legacy summary retained',debit_amount=100,credit_amount=100,status='posted',posted_by_user_id=actor.id,created_by=actor.id,updated_by=actor.id);db.add(legacy);db.commit()
    assert management.integrity(actor)['can_close'] is False
    opening=voucher(100,voucher_type='opening');opening.lines[1].account_code='3100';journal=service.create_journal_entry(opening,actor,{})
    result=management.resolve_legacy_journal(legacy.id,LegacyJournalResolution(journal_id=journal.id,treatment='included_in_opening',reason='Original paper records reconciled to approved opening voucher'),actor)
    assert result['cash_created']=='0.00' and management.integrity(actor)['can_close'] is True
    assert db.scalar(select(func.count(JournalEntry.id)))==1 and legacy.debit_amount==100


def test_employee_advance_payroll_recovery_and_insufficient_funds_rollback(db):
    from test_operational_posting import payroll_setup
    from app.modules.accounting.employee_advances import EmployeeAdvances
    from app.schemas.accounting_standard import FinancePayment
    from app.schemas.hr import HRLoanCreate,HRPayrollRunCreate
    actor,reviewer,hr,employee=payroll_setup(db);service=AccountingService(db)
    opening=voucher(10000,voucher_type='opening');opening.lines[0].account_code='1020';opening.lines[1].account_code='3100';service.create_journal_entry(opening,actor,{})
    db.add(AccountingPolicy(branch_id=actor.branch_id,version=1,effective_from=date.today(),approved_by=reviewer.id,settings={'cutover_date':date.today().isoformat(),'maker_checker':True,'payroll_payment_account':'1020'}));db.commit()
    loan=hr.create_loan(HRLoanCreate(employee_id=employee.id,approved_amount=500,monthly_installment=500,deduction_start_month=date.today().strftime('%Y-%m')),actor)
    assert loan.status=='pending'
    request=FinancePayment(amount=500,payment_method='bank_transfer',reference='Verified advance transfer',request_key='employee-advance-test')
    advances=EmployeeAdvances(db)
    with pytest.raises(AppException):advances.disburse(loan.id,request,actor)
    advances.disburse(loan.id,request,reviewer);advances.disburse(loan.id,request,reviewer)
    assert loan.status=='active' and db.scalar(select(Account.current_balance).where(Account.account_code=='1150'))==500
    run=hr.process_payroll(HRPayrollRunCreate(payroll_month=date.today().strftime('%Y-%m')),actor)
    hr.approve_payroll(run.id,reviewer,status='approved')
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1150'))==0
    with pytest.raises(AppException,match='Insufficient recorded funds'):hr.approve_payroll(run.id,reviewer,status='paid')
    db.rollback();db.refresh(run);db.refresh(loan)
    assert run.status=='approved' and loan.remaining_balance==500
    funding=voucher(20000,status='draft',voucher_type='opening');funding.lines[0].account_code='1020';funding.lines[1].account_code='3100';entry=service.create_journal_entry(funding,actor,{})
    service.voucher_action(entry.id,'approve',reviewer,{});service.voucher_action(entry.id,'post',reviewer,{})
    hr.approve_payroll(run.id,reviewer,status='paid')
    assert loan.remaining_balance==0 and db.scalar(select(Account.current_balance).where(Account.account_code=='2200'))==0
    assert db.scalar(select(Account.current_balance).where(Account.account_code=='1020'))==4000
    assert AccountingManagement(db).statements(actor)['balance_sheet']['equation_difference']=='0.00'


def test_reports_reconcile_ten_thousand_balanced_journals_with_measured_latency(db):
    import json,time
    from pathlib import Path
    from datetime import datetime,UTC
    from sqlalchemy import insert
    actor,_,management=setup(db);cash_id=uuid4();income_id=uuid4();count=10000;now=datetime.now(UTC)
    db.execute(insert(Account),[{'id':cash_id,'branch_id':actor.branch_id,'account_code':'1001','name':'Synthetic cash','category':'assets','normal_balance':'debit','current_balance':count,'opening_balance':0},{'id':income_id,'branch_id':actor.branch_id,'account_code':'4000','name':'Synthetic revenue','category':'income','normal_balance':'credit','current_balance':count,'opening_balance':0}])
    headers=[];lines=[]
    for index in range(count):
        identity=uuid4();headers.append({'id':identity,'branch_id':actor.branch_id,'journal_number':'PERF-'+str(index)+'-'+identity.hex,'journal_date':date.today(),'source_module':'synthetic_performance','source_reference':str(index),'narration':'Synthetic balanced performance record','status':'posted','total_debit':1,'total_credit':1,'posted_at':now,'posting_applied_at':now})
        lines.extend([{'id':uuid4(),'journal_entry_id':identity,'account_id':cash_id,'account_code':'1001','account_name':'Synthetic cash','debit_amount':1,'credit_amount':0,'cost_center':'Medicine'},{'id':uuid4(),'journal_entry_id':identity,'account_id':income_id,'account_code':'4000','account_name':'Synthetic revenue','debit_amount':0,'credit_amount':1,'cost_center':'Medicine'}])
    db.execute(insert(JournalEntry),headers);db.execute(insert(JournalEntryLine),lines);db.flush()
    start=time.perf_counter();book=management.statements(actor,date.today(),date.today());elapsed=round((time.perf_counter()-start)*1000,2)
    assert Decimal(book['total_debit'])==count==Decimal(book['total_credit'])
    assert Decimal(book['profit_and_loss']['net_profit'])==count
    assert book['balance_sheet']['equation_difference']=='0.00'
    Path('/tmp/hms-accounting-performance.json').write_text(json.dumps({'journals':count,'lines':len(lines),'statement_service_ms':elapsed,'scope':'Local PostgreSQL complete statements, cash-flow aggregation and hydration; synthetic balanced ledger, not production latency'},indent=2))
    assert elapsed<5000


def test_source_review_never_manufactures_unverified_historical_payroll(db):
    from app.models.accounting import PayrollAccounting
    actor,service,_=setup(db)
    db.add(AccountingPolicy(branch_id=actor.branch_id,version=1,effective_from=date.today(),approved_by=actor.id,settings={'cutover_date':date.today().isoformat(),'maker_checker':False}))
    db.add(PayrollAccounting(branch_id=actor.branch_id,payroll_month=date.today().strftime('%Y-%m'),gross_salary=1000,net_salary_payable=900,status='pending',created_by=actor.id,updated_by=actor.id))
    db.commit()
    before=db.scalar(select(func.count(JournalEntry.id)))
    result=service.sync_source_entries(actor,{})
    assert result['created_entries']==0 and result['skipped_entries']==1
    assert db.scalar(select(func.count(JournalEntry.id)))==before


def test_pharmacy_paid_return_disbursement_is_verified_and_exactly_once(db):
    from app.models.pharmacy import PharmacyMedicine,PharmacyMedicineType,PharmacyGeneric,PharmacyCompany
    from app.modules.pharmacy.service import PharmacyService
    from app.schemas.pharmacy import PharmacyPurchaseCreate,PharmacySaleCreate,PharmacySaleItemWrite,PharmacySaleReturnCreate
    actor,_,patient,_=seed(db)
    db.add(AccountingPolicy(branch_id=actor.branch_id,version=1,effective_from=date.today(),approved_by=actor.id,settings={'cutover_date':date.today().isoformat(),'maker_checker':False,'pharmacy_accounting_enabled':True}));db.commit()
    form=PharmacyMedicineType(name='Synthetic form');generic=PharmacyGeneric(name='Synthetic generic');company=PharmacyCompany(name='Synthetic manufacturer');db.add_all([form,generic,company]);db.flush()
    medicine=PharmacyMedicine(branch_id=actor.branch_id,medicine_type_id=form.id,generic_id=generic.id,company_id=company.id,name='Synthetic approved accounting item',stock_quantity=0,purchase_price=10,sale_price=20);db.add(medicine);db.commit()
    pharmacy=PharmacyService(db)
    purchase=pharmacy.create_purchase(PharmacyPurchaseCreate(medicine_id=medicine.id,purchase_date=date.today(),supplier_name='Synthetic supplier',quantity=10,unit_cost=10),actor,{})
    assert medicine.inventory_value==100
    sale=pharmacy.create_sale(PharmacySaleCreate(patient_id=patient.id,sale_date=date.today(),paid_amount=80,discount_amount=20,items=[PharmacySaleItemWrite(medicine_id=medicine.id,quantity=5,unit_price=20)]),actor,{})
    assert medicine.inventory_value==50
    book=AccountingManagement(db).statements(actor)
    assert book['profit_and_loss']['income']=='80.00' and book['profit_and_loss']['expenses']=='50.00'
    returned=pharmacy.create_return(PharmacySaleReturnCreate(sale_id=sale.id,sale_item_id=sale.items[0].id,returned_at=date.today(),quantity=2),actor,{})
    assert returned.total_amount==32 and medicine.inventory_value==70
    balances={row.account_code:row.current_balance for row in AccountingService(db).list_accounts(actor)}
    assert balances['2220']==32 and balances['1310']==70 and balances['5030']==30
    assert AccountingManagement(db).statements(actor)['balance_sheet']['equation_difference']=='0.00'
    with pytest.raises(AppException):pharmacy.delete_sale(sale.id,actor,{})

    from app.modules.accounting.pharmacy_posting import pay_return
    from app.schemas.accounting_standard import FinancePayment
    with pytest.raises(AppException):pay_return(db,returned.id,FinancePayment(amount=33,reference='verified-refund',request_key='refund-request-001'),actor)
    payload=FinancePayment(amount=32,payment_method='cash',reference='verified-refund',request_key='refund-request-001')
    paid=pay_return(db,returned.id,payload,actor)
    assert pay_return(db,returned.id,payload,actor).id==paid.id
    balances={row.account_code:row.current_balance for row in AccountingService(db).list_accounts(actor)}
    assert balances['2220']==0 and balances['1001']==48
    assert AccountingManagement(db).statements(actor)['balance_sheet']['equation_difference']=='0.00'

