"""Serialize commands before reading balances; successful retries return the persisted invoice."""
from functools import wraps
import hashlib
from sqlalchemy import select
from app.core.exceptions import AppException
from app.models.billing import BillingInvoice
from app.models.billing_policy import BillingCommand


def financial_command(method):
    @wraps(method)
    def wrapped(self, invoice_id, payload, actor, context):
        from app.modules.support_posting.service import lock_branch
        lock_branch(self.db, actor)
        self.db.execute(select(BillingInvoice.id).where(BillingInvoice.id == invoice_id).with_for_update())
        invoice = self.get_invoice(invoice_id, actor)
        self.db.refresh(invoice)
        self.db.expire(invoice, ['refunds', 'payments'])
        key = payload.request_key
        if key:
            fingerprint = hashlib.sha256(payload.model_dump_json(exclude={'request_key'}).encode()).hexdigest()
            previous = self.db.scalar(select(BillingCommand).where(BillingCommand.invoice_id == invoice_id, BillingCommand.request_key == key))
            if previous:
                if previous.operation != method.__name__ or previous.fingerprint != fingerprint:
                    raise AppException(409, 'billing_request_conflict', 'Request key was already used with different financial details')
                return invoice
            self.db.add(BillingCommand(invoice_id=invoice_id, request_key=key, operation=method.__name__, fingerprint=fingerprint, created_by=actor.id, updated_by=actor.id))
        if method.__name__ in {'create_refund', 'create_return', 'cancel_invoice'}:
            from app.modules.auth.service import AuthService
            requires_approval = any((item.financial_snapshot or {}).get('rules', {}).get('refund_approval_required', False) for item in invoice.items)
            if requires_approval and 'billing.service.manage' not in AuthService(self.db).get_effective_permissions(actor):
                raise AppException(403, 'billing_refund_approval', 'This invoice requires billing administrator refund approval')
        return method(self, invoice_id, payload, actor, context)
    return wrapped
