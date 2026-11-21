"""Accounts payable payments use the existing supplier records and shared posting engine."""
from datetime import UTC,datetime,date
from app.utils.accounting_time import today_local
from decimal import Decimal
from uuid import uuid5,NAMESPACE_URL
from sqlalchemy import select
from app.core.exceptions import AppException
from app.models.accounting import SupplierInvoice,SupplierPayment,JournalEntry
from app.modules.support_posting.service import lock_branch
from app.modules.accounting.channels import collection_account
from app.modules.accounting.service import AccountingService
from app.modules.accounting.management import AccountingManagement


class Payables:
    def __init__(self,db):self.db=db

    def supplier_payment(self,identity,payload,actor):
        lock_branch(self.db,actor)
        invoice=self.db.scalar(select(SupplierInvoice).where(SupplierInvoice.id==identity,SupplierInvoice.branch_id==actor.branch_id).with_for_update())
        if not invoice:raise AppException(404,'supplier_invoice_not_found','Supplier invoice not found')
        number='SP-'+uuid5(NAMESPACE_URL,str(identity)+':'+payload.request_key).hex.upper()
        prior=self.db.scalar(select(SupplierPayment).where(SupplierPayment.payment_number==number))
        if prior:
            if prior.amount!=payload.amount or prior.payment_method!=payload.payment_method:raise AppException(409,'supplier_payment_conflict','Request key used for another payment')
            return prior
        from app.modules.accounting.controls import policy_for
        policy=policy_for(self.db,actor.branch_id,today_local())
        if policy and policy.settings.get('maker_checker') and invoice.created_by==actor.id:raise AppException(403,'supplier_payment_maker_checker','An independent authorized payer must execute this supplier invoice payment')
        if invoice.status not in {'approved','partial','paid'}:raise AppException(409,'supplier_invoice_not_approved','Approve the supplier liability before paying it')
        if payload.amount>invoice.due_amount:raise AppException(422,'supplier_payment_excess','Payment exceeds supplier outstanding amount')
        service=AccountingService(self.db)
        if not service._source_entry_exists(actor.branch_id,'supplier_invoice',str(invoice.id)) and not service._source_entry_exists(actor.branch_id,'supplier_invoice',invoice.invoice_number):
            raise AppException(409,'supplier_opening_required','Reconcile or post the supplier liability before recording a payment')
        channel=collection_account(self.db,actor,payload.payment_method,payload.payment_provider)
        payment=SupplierPayment(branch_id=actor.branch_id,supplier_invoice_id=invoice.id,payment_number=number,amount=payload.amount,payment_method=payload.payment_method,paid_at=datetime.now(UTC),approved_by_user_id=actor.id,created_by=actor.id,updated_by=actor.id)
        self.db.add(payment)
        service._create_auto_entry(actor,'supplier_payment',number,today_local(),'Supplier payment '+invoice.invoice_number+' / '+payload.reference,[('2100','Accounts Payable',payload.amount,0),(channel,'Collection / bank channel',0,payload.amount)])
        invoice.paid_amount=Decimal(invoice.paid_amount)+payload.amount;invoice.due_amount=Decimal(invoice.gross_amount)-invoice.paid_amount
        invoice.status='paid' if invoice.due_amount==0 else 'partial';invoice.updated_by=actor.id
        self.db.flush();AccountingManagement(self.db).audit(actor,'supplier.payment',payment.id,{'invoice_id':str(invoice.id),'amount':str(payload.amount),'reference':payload.reference});self.db.commit();return payment
