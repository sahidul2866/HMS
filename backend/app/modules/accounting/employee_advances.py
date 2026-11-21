"""Disburse approved HR advance requests before allowing payroll recovery."""
from sqlalchemy import select
from app.models.hr import HREmployeeLoan,HREmployee
from app.models.accounting import JournalEntry
from app.modules.support_posting.service import lock_branch
from app.modules.accounting.service import AccountingService
from app.modules.accounting.controls import policy_for
from app.modules.accounting.channels import collection_account
from app.modules.accounting.management import AccountingManagement
from app.utils.accounting_time import today_local
from app.core.exceptions import AppException


class EmployeeAdvances:
    def __init__(self,db):self.db=db
    def disburse(self,identity,payload,actor):
        lock_branch(self.db,actor)
        loan=self.db.scalar(select(HREmployeeLoan).where(HREmployeeLoan.id==identity,HREmployeeLoan.branch_id==actor.branch_id).with_for_update())
        if not loan:raise AppException(404,'employee_advance_not_found','Staff advance request not found')
        snapshot=payload.model_dump(mode='json')
        previous=self.db.scalar(select(JournalEntry).where(JournalEntry.branch_id==actor.branch_id,JournalEntry.source_module=='employee_advance_disbursement',JournalEntry.source_reference==str(loan.id)))
        if previous:
            if (previous.policy_snapshot or {}).get('source')!=snapshot:raise AppException(409,'employee_advance_conflict','Advance was already disbursed with different receipt information')
            return loan
        policy=policy_for(self.db,actor.branch_id,today_local())
        if not policy:raise AppException(422,'employee_advance_policy','Approve an accounting cutover policy first')
        employee=self.db.get(HREmployee,loan.employee_id)
        if policy.settings.get('maker_checker') and (loan.created_by==actor.id or employee.user_id==actor.id):raise AppException(403,'employee_advance_self_approval','Another authorized manager must approve and disburse this advance')
        if loan.status!='pending' or payload.amount!=loan.approved_amount:raise AppException(409,'employee_advance_state','Pay the pending approved request amount; reconcile legacy active loans through opening balances')
        channel=collection_account(self.db,actor,payload.payment_method,payload.payment_provider)
        AccountingService(self.db)._create_auto_entry(actor,'employee_advance_disbursement',str(loan.id),today_local(),'Employee advance '+employee.full_name+' / '+payload.reference,[('1150','Employee Advance Receivable',payload.amount,0),(channel,'Actual advance disbursement',0,payload.amount)],source_snapshot=snapshot)
        loan.status='active';loan.updated_by=actor.id;AccountingManagement(self.db).audit(actor,'employee.advance.disburse',loan.id,{'employee_id':str(employee.id),'amount':str(payload.amount),'reference':payload.reference});self.db.commit();return loan
