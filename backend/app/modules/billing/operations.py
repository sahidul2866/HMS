"""Billing classification, immutable history, reconciliation and cashier custody."""
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from app.core.exceptions import AppException
from app.models.billing import (BillingType, BillingInvoice, BillingEvent, BillingCashHandover,
    BillingCashHandoverEntry, BillingPayment, BillingRefund, BillingReportSnapshot)
from app.models.user import User
from app.modules.auth.service import AuthService


def classification(db, type_id, actor):
    if not type_id:
        return None
    item = db.get(BillingType, type_id)
    if not item or not item.is_active or (actor.branch_id and item.branch_id != actor.branch_id):
        raise AppException(404, 'billing_type_not_found', 'Select an active billing type from this branch')
    return item


def snapshot(invoice):
    fields = ('sub_total','item_discount_amount','discount_percentage','invoice_discount_amount',
        'discount_amount','total_amount','credited_amount','net_payable_amount','paid_amount','refunded_amount','due_amount')
    return {**{key:str(getattr(invoice,key) or 0) for key in fields},
        'invoice_number':invoice.invoice_number,'status':invoice.status,'payment_status':invoice.payment_status,
        'billed_by_user_id':str(invoice.billed_by_user_id),'billing_type_name':invoice.billing_type_name,
        'billing_department':invoice.billing_department,'note':invoice.note,'discount_reason':invoice.discount_reason,
        'items':[{'id':str(i.id),'name':i.service_name,'quantity':str(i.quantity),'unit_price':str(i.unit_price),
            'discount_percentage':str(i.discount_percentage),'discount_amount':str(i.discount_amount),
            'line_total':str(i.line_total),'department':i.billing_department,'type':i.billing_type_name} for i in invoice.items]}


def record_event(db, invoice, actor, kind, reason=None, before=None):
    db.flush()
    db.expire(invoice, ["refunds"])
    db.add(BillingEvent(branch_id=invoice.branch_id,invoice_id=invoice.id,actor_id=actor.id,
        kind=kind,reason=reason,snapshot={'actor_name':actor.full_name,'before':before,'after':snapshot(invoice)},created_by=actor.id,updated_by=actor.id))


class BillingOperations:
    def __init__(self, db):
        self.db=db

    def scoped(self, stmt, model, actor):
        return stmt.where(model.branch_id==actor.branch_id) if actor.branch_id else stmt

    def types(self, actor):
        return list(self.db.scalars(self.scoped(select(BillingType).where(BillingType.is_active.is_(True)).order_by(BillingType.name),BillingType,actor)))

    def create_type(self, payload, actor):
        self.db.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'),{'key':'billing-type:'+str(actor.branch_id)})
        if any(i.code.lower()==payload.code.lower() for i in self.types(actor)):
            raise AppException(409,'billing_type_duplicate','This billing type code already exists')
        item=BillingType(branch_id=actor.branch_id,code=payload.code.upper(),name=payload.name.strip(),department=payload.department.strip(),created_by=actor.id,updated_by=actor.id)
        self.db.add(item);self.db.commit();return item

    def amend(self, invoice_id, payload, actor):
        from app.modules.support_posting.service import lock_branch
        lock_branch(self.db,actor)
        from app.modules.billing.service import BillingServiceManager
        service=BillingServiceManager(self.db)
        invoice=service.get_invoice(invoice_id,actor)
        self.db.execute(select(BillingInvoice).where(BillingInvoice.id==invoice_id).with_for_update()).scalar_one()
        self.db.refresh(invoice)
        if invoice.status!='posted':
            raise AppException(409,'billing_edit_closed','Only posted invoices can be edited')
        before=snapshot(invoice)
        kind=classification(self.db,payload.billing_type_id,actor)
        if 'billing_type_id' in payload.model_fields_set:
            invoice.billing_type_id=kind.id if kind else None
            invoice.billing_type_name=kind.name if kind else None
            invoice.billing_department=kind.department if kind else None
        if 'note' in payload.model_fields_set:
            invoice.note=payload.note
        if payload.discount_percentage is not None or payload.discount_amount is not None:
            settings=service._get_settings_by_branch(actor.branch_id)
            amount,percentage=service._discount_of(invoice.sub_total,payload.discount_percentage or 0,payload.discount_amount)
        if (payload.discount_percentage is not None or payload.discount_amount is not None) and amount != invoice.invoice_discount_amount:
            if invoice.refunds:
                raise AppException(409,'billing_edit_refunded','Invoices with returns or refunds retain their original discount; use a separate adjustment invoice')
            if percentage>settings.max_invoice_discount_percentage or (settings.max_invoice_discount_amount is not None and amount>settings.max_invoice_discount_amount):
                raise AppException(422,'billing_discount_limit','The discount exceeds configured invoice limits')
            total=service._money(invoice.sub_total-amount)
            if total<invoice.paid_amount:
                raise AppException(409,'billing_edit_overpaid','Refund the excess collection before reducing this invoice total')
            invoice.discount_percentage=percentage;invoice.invoice_discount_amount=amount
            invoice.discount_amount=invoice.item_discount_amount+amount;invoice.total_amount=total
            invoice.discount_reason=payload.reason
            service._recalculate_invoice_balance(invoice);service._sync_opd_payment(invoice,actor)
        invoice.updated_by=actor.id
        from app.modules.support_posting.service import amend_invoice_posting
        amend_invoice_posting(self.db,actor,invoice,before)
        record_event(self.db,invoice,actor,'amendment',payload.reason,before)
        self.db.commit();return service.get_invoice(invoice.id,actor)

    def history(self, invoice_id, actor):
        from app.modules.billing.service import BillingServiceManager
        BillingServiceManager(self.db).get_invoice(invoice_id,actor)
        return list(self.db.scalars(select(BillingEvent).where(BillingEvent.invoice_id==invoice_id).order_by(BillingEvent.created_at)))

    def cash_entries(self, actor):
        # Lock the collector to serialize submissions and prevent duplicate custody claims.
        self.db.execute(select(User.id).where(User.id==actor.id).with_for_update())
        payment_ids=select(BillingCashHandoverEntry.payment_id).where(BillingCashHandoverEntry.payment_id.is_not(None))
        refund_ids=select(BillingCashHandoverEntry.refund_id).where(BillingCashHandoverEntry.refund_id.is_not(None))
        payments=list(self.db.scalars(self.scoped(select(BillingPayment).where(BillingPayment.collected_by_user_id==actor.id,BillingPayment.payment_method=='cash',BillingPayment.id.notin_(payment_ids)),BillingPayment,actor)))
        # Cash custody follows the actual recorded refund payout method.
        refunds=list(self.db.scalars(self.scoped(select(BillingRefund).where(BillingRefund.refunded_by_user_id==actor.id,BillingRefund.amount>0,BillingRefund.id.notin_(refund_ids)),BillingRefund,actor)))
        refunds=[r for r in refunds if r.payment_method=='cash']
        return payments,refunds

    def cash_balance(self, actor):
        payments,refunds=self.cash_entries(actor)
        result={'receipts':sum((p.amount for p in payments),Decimal(0)), 'refunds':sum((r.amount for r in refunds),Decimal(0)), 'receipt_count':len(payments),'refund_count':len(refunds)}
        result['expected_amount']=result['receipts']-result['refunds']
        return result

    def handovers(self, actor):
        stmt=self.scoped(select(BillingCashHandover),BillingCashHandover,actor)
        if 'billing.service.manage' not in AuthService(self.db).get_effective_permissions(actor):
            stmt=stmt.where((BillingCashHandover.collector_id==actor.id)|(BillingCashHandover.receiver_id==actor.id))
        return list(self.db.scalars(stmt.order_by(BillingCashHandover.created_at.desc()).limit(250)))

    def submit_handover(self, payload, actor):
        receiver=self.db.get(User,payload.receiver_id)
        if not receiver or not receiver.is_active or receiver.id==actor.id or (actor.branch_id and receiver.branch_id!=actor.branch_id):
            raise AppException(422,'billing_handover_receiver','Choose a different active cashier supervisor from this branch')
        if 'billing.service.manage' not in AuthService(self.db).get_effective_permissions(receiver):
            raise AppException(422,'billing_handover_receiver','The receiver needs billing administration permission')
        payments,refunds=self.cash_entries(actor)
        if not payments and not refunds:
            raise AppException(409,'billing_handover_empty','No unsettled cash transactions remain')
        expected=sum((p.amount for p in payments),Decimal(0))-sum((r.amount for r in refunds),Decimal(0))
        item=BillingCashHandover(branch_id=actor.branch_id,number='HO-'+datetime.now(UTC).strftime('%Y%m%d')+'-'+uuid4().hex[:8].upper(),collector_id=actor.id,receiver_id=receiver.id,expected_amount=expected,declared_amount=payload.declared_amount,variance=payload.declared_amount-expected,note=payload.note,created_by=actor.id,updated_by=actor.id)
        self.db.add(item);self.db.flush()
        for payment in payments:self.db.add(BillingCashHandoverEntry(handover_id=item.id,payment_id=payment.id,amount=payment.amount,created_by=actor.id,updated_by=actor.id))
        for refund in refunds:self.db.add(BillingCashHandoverEntry(handover_id=item.id,refund_id=refund.id,amount=-refund.amount,created_by=actor.id,updated_by=actor.id))
        self.db.commit();return item

    def accept_handover(self, handover_id, payload, actor):
        item=self.db.scalar(self.scoped(select(BillingCashHandover).where(BillingCashHandover.id==handover_id).with_for_update(),BillingCashHandover,actor))
        if not item:raise AppException(404,'billing_handover_missing','Cash handover not found')
        if item.receiver_id!=actor.id:raise AppException(403,'billing_handover_receiver','Only the designated receiver can accept this handover')
        if item.status!='submitted':raise AppException(409,'billing_handover_closed','This handover was already accepted')
        item.status='accepted';item.accepted_at=datetime.now(UTC);item.acceptance_note=payload.note;item.updated_by=actor.id
        self.db.commit();return item

    def statistics(self, actor, date_from=None, date_to=None):
        if date_from and date_to and date_from>date_to:raise AppException(422,'billing_report_dates','Start date must be before end date')
        stmt=self.scoped(select(BillingInvoice).options(selectinload(BillingInvoice.items),selectinload(BillingInvoice.payments),selectinload(BillingInvoice.refunds),selectinload(BillingInvoice.billed_by)),BillingInvoice,actor)
        if date_from:stmt=stmt.where(BillingInvoice.created_at>=datetime.combine(date_from,time.min,tzinfo=UTC))
        if date_to:stmt=stmt.where(BillingInvoice.created_at<datetime.combine(date_to+timedelta(days=1),time.min,tzinfo=UTC))
        invoices=list(self.db.scalars(stmt))
        totals={'invoice_count':len(invoices),'posted_count':0,'void_count':0,'gross':Decimal(0),'discount':Decimal(0),'net':Decimal(0),'collected':Decimal(0),'refunded':Decimal(0),'due':Decimal(0),'returned':Decimal(0)}
        departments={};creators={};methods={}
        for invoice in invoices:
            if invoice.status=='void':totals['void_count']+=1;continue
            if invoice.status!='posted':continue
            totals['posted_count']+=1
            returned=sum((r.credit_amount for r in invoice.refunds if r.refund_type=='return'),Decimal(0))
            for target in (totals,creators.setdefault(str(invoice.billed_by_user_id),{'name':invoice.billed_by_name,'gross':Decimal(0),'discount':Decimal(0),'net':Decimal(0),'collected':Decimal(0),'refunded':Decimal(0),'due':Decimal(0),'returned':Decimal(0)})):
                target['gross']+=invoice.sub_total+invoice.item_discount_amount;target['discount']+=invoice.discount_amount;target['net']+=invoice.total_amount-returned;target['returned']+=returned;target['collected']+=sum((p.amount for p in invoice.payments),Decimal(0));target['refunded']+=invoice.refunded_amount;target['due']+=invoice.due_amount
            # Department allocations use frozen item classifications; mixed invoices reconcile to their totals.
            invoice_values={'gross':invoice.sub_total+invoice.item_discount_amount,'discount':invoice.discount_amount,
                'net':invoice.total_amount-returned,'returned':returned,'collected':sum((p.amount for p in invoice.payments),Decimal(0)),
                'refunded':invoice.refunded_amount,'due':invoice.due_amount}
            weights={}
            for line in invoice.items:
                department=line.billing_department or invoice.billing_department or line.source_module or 'General'
                weights[department]=weights.get(department,Decimal(0))+line.quantity*line.unit_price
            total_weight=sum(weights.values(),Decimal(0))
            allocated={key:Decimal(0) for key in invoice_values}
            for index,(department,weight) in enumerate(weights.items()):
                target=departments.setdefault(department,{key:Decimal(0) for key in invoice_values})
                for key,value in invoice_values.items():
                    amount=value-allocated[key] if index==len(weights)-1 else (value*weight/total_weight).quantize(Decimal('.01')) if total_weight else Decimal(0)
                    target[key]+=amount;allocated[key]+=amount
            for payment in invoice.payments:methods[payment.payment_method]=methods.get(payment.payment_method,Decimal(0))+payment.amount
        def serial(value):
            if isinstance(value,Decimal):return str(value)
            if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
            return value
        data=serial({'totals':totals,'departments':departments,'creators':creators,'payment_methods':methods})
        report=BillingReportSnapshot(branch_id=actor.branch_id,actor_id=actor.id,filters={'date_from':str(date_from) if date_from else None,'date_to':str(date_to) if date_to else None,'basis':'invoice_created_utc'},statistics=data,created_by=actor.id,updated_by=actor.id)
        self.db.add(report);self.db.commit();return {'snapshot_id':str(report.id),'generated_at':report.created_at,'filters':report.filters,**data}
