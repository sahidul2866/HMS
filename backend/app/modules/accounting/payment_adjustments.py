"""Failed attempts have no GL. Approved chargebacks reopen AR without editing receipts."""
import hashlib
from decimal import Decimal
from sqlalchemy import select,func
from app.core.exceptions import AppException
from app.models.accounting_control import AccountingPaymentAdjustment
from app.models.billing import BillingInvoice,BillingPayment
from app.modules.accounting.controls import policy_for
from app.modules.accounting.service import AccountingService
from app.modules.accounting.management import AccountingManagement
from app.modules.support_posting.service import lock_branch
from app.utils.accounting_time import today_local


class PaymentAdjustments:
    def __init__(self,db):self.db=db
    def record(self,payload,actor):
        from app.modules.auth.service import AuthService
        permissions=set(AuthService(self.db).get_effective_permissions(actor))
        if payload.kind!='failed' and not {'accounting.approve','billing.payment.refund'}.issubset(permissions):raise AppException(403,'payment_adjustment_permission','Finance approval and payment reversal permission are required')
        if payload.kind=='failed' and not permissions.intersection({'billing.payment.collect','accounting.approve'}):raise AppException(403,'payment_attempt_permission','Collection access is required')
        lock_branch(self.db,actor)
        digest=hashlib.sha256(payload.model_dump_json(exclude={'request_key'}).encode()).hexdigest()
        prior=self.db.scalar(select(AccountingPaymentAdjustment).where(AccountingPaymentAdjustment.branch_id==actor.branch_id,AccountingPaymentAdjustment.request_key==payload.request_key))
        if prior:
            if prior.fingerprint!=digest:raise AppException(409,'payment_adjustment_conflict','Request key was used for another financial adjustment')
            return prior
        invoice=self.db.scalar(select(BillingInvoice).where(BillingInvoice.id==payload.invoice_id,BillingInvoice.branch_id==actor.branch_id).with_for_update())
        if not invoice:raise AppException(404,'invoice_not_found','Invoice not found in this branch')
        row=AccountingPaymentAdjustment(branch_id=actor.branch_id,invoice_id=invoice.id,payment_id=payload.payment_id,kind=payload.kind,amount=payload.amount,request_key=payload.request_key,fingerprint=digest,reason=payload.reason,created_by=actor.id,updated_by=actor.id)
        if payload.kind!='failed':
            payment=self.db.scalar(select(BillingPayment).where(BillingPayment.id==payload.payment_id,BillingPayment.invoice_id==invoice.id,BillingPayment.branch_id==actor.branch_id).with_for_update())
            if not payment:raise AppException(422,'adjustment_payment','Choose the original successful receipt')
            policy=policy_for(self.db,actor.branch_id,today_local())
            if policy and policy.settings.get('maker_checker') and payment.created_by==actor.id:raise AppException(403,'payment_adjustment_maker_checker','An independent approver must reverse this collection')
            if invoice.refunds or invoice.status!='posted':raise AppException(409,'payment_adjustment_review','Refunded/cancelled invoices require a reviewed financial adjustment, not an automatic chargeback')
            adjusted=self.db.scalar(select(func.coalesce(func.sum(AccountingPaymentAdjustment.amount),0)).where(AccountingPaymentAdjustment.payment_id==payment.id,AccountingPaymentAdjustment.kind!='failed')) or Decimal(0)
            if payload.amount>payment.amount-adjusted or payload.amount>invoice.paid_amount:raise AppException(422,'payment_adjustment_excess','Adjustment exceeds the unadjusted original receipt')
            from app.modules.accounting.channels import collection_account
            channel=payload.deduction_account or collection_account(self.db,actor,payment.payment_method,payment.payment_provider)
            allowed={'1001','1011','1012','1013','1020','1031','1032','1033','1034'}
            if policy:allowed.update(policy.settings.get('collection_accounts',{}).values())
            if payment.payment_method=='patient_advance':
                from app.models.accounting import AdvancePayment
                deposit=self.db.get(AdvancePayment,payment.advance_payment_id)
                if not deposit:raise AppException(409,'advance_adjustment_review','Original advance allocation cannot be reconciled')
                channel='2210';deposit.balance_amount+=payload.amount;deposit.adjusted_amount-=payload.amount
            elif channel not in allowed:raise AppException(422,'chargeback_channel','Choose an actual configured collection/settlement account')
            entry=AccountingService(self.db)._create_auto_entry(actor,'payment_adjustment',str(row.id or payload.request_key),today_local(),payload.kind+' of '+payment.receipt_number+': '+payload.reason,[('1100','Reopened patient receivable',payload.amount,0),(channel,'Actual reversed collection / restored deposit',0,payload.amount)])
            self.db.flush();row.journal_id=entry.id
            invoice.paid_amount-=payload.amount
            from app.modules.billing.service import BillingServiceManager
            billing=BillingServiceManager(self.db);billing._recalculate_invoice_balance(invoice);billing._sync_opd_payment(invoice,actor)
        elif payload.payment_id:raise AppException(422,'failed_payment_receipt','A failed attempt must not reference a successful receipt')
        self.db.add(row);self.db.flush();AccountingManagement(self.db).audit(actor,'payment.'+payload.kind,row.id,{'invoice_id':str(invoice.id),'amount':str(payload.amount),'reason':payload.reason,'cash_posted':payload.kind!='failed'});self.db.commit();return row
