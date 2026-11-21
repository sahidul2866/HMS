"""Policy resolution and exact, append-only participant accounting."""
from datetime import UTC, datetime
from decimal import Decimal, ROUND_DOWN
from sqlalchemy import select, func, or_, text
from app.core.exceptions import AppException
from app.models.billing_policy import BillingPolicy, BillingAllocation
from app.schemas.billing_policy import FinancialRules
from app.utils.billing_amounts import money, net_line_amounts


def allocate(amount, weights):
    """Largest remainder allocation, stable ties by account key, exact to one paisa."""
    amount = money(amount)
    total = sum(weights.values(), Decimal(0))
    if amount < 0 or any(w < 0 for w in weights.values()):
        raise ValueError('Allocation requires nonnegative values')
    if not total:
        if amount:
            raise ValueError('Cannot allocate money without a positive weight')
        return {key: Decimal('0.00') for key in weights}
    raw = {key: amount * weight / total for key, weight in weights.items()}
    result = {key: value.quantize(Decimal('.01'), rounding=ROUND_DOWN) for key, value in raw.items()}
    remaining = int((amount - sum(result.values())) * 100)
    for key in sorted(weights, key=lambda k: (-(raw[k] - result[k]), str(k)))[:remaining]:
        result[key] += Decimal('.01')
    return result


def enforce_discount(item, invoice_discount, rules, actor=None, approved=False):
    gross = money(item.unit_price * item.quantity)
    discount = money(item.discount_amount + invoice_discount)
    if discount and not rules.discounts_allowed:
        raise AppException(422, 'billing_discount_prohibited', 'This service does not allow discounts, including invoice discounts')
    roles = {r.code for r in actor.roles if r.is_active} if actor is not None else set()
    override = bool(roles.intersection(rules.override_roles))
    if not override and (discount > money(gross * rules.max_percentage / 100) or (rules.max_amount is not None and discount > rules.max_amount)):
        raise AppException(422, 'billing_policy_discount_limit', 'Combined item and invoice discount exceeds the service policy')
    if item.discount_amount and invoice_discount and not rules.combine:
        raise AppException(422, 'billing_discount_combination', 'This service does not allow combined discounts')
    if discount and actor is not None:
        roles = {r.code for r in actor.roles if r.is_active}
        if rules.allowed_roles and not override and not roles.intersection(rules.allowed_roles):
            raise AppException(403, 'billing_discount_role', 'Your role cannot apply this discount')
        if rules.approval_required and not approved:
            raise AppException(403, 'billing_discount_approval', 'This discount requires billing administrator approval')


def enforce_catalog_discount(item, invoice_discount):
    gross = money(item.unit_price * item.quantity)
    total = money(item.discount_amount + invoice_discount)
    percentage = getattr(item, 'max_discount_percentage', None)
    amount = getattr(item, 'max_discount_amount', None)
    if (percentage is not None and total > money(gross * percentage / 100)) or (amount is not None and total > amount):
        raise AppException(422, 'billing_combined_discount_limit', 'Combined item and invoice discount exceeds the frozen service limit')


def financial_values(item, net, rules):
    gross = money(item.quantity * item.unit_price)
    discount = money(gross - net)
    contributions = allocate(discount, rules.discount_sharing)
    revenue_doctor = (max(Decimal(0), gross - rules.hospital_fixed_deduction)
                      if rules.hospital_fixed_deduction is not None else money(gross * rules.doctor_revenue_percentage / 100)) if rules.doctor_key else Decimal(0)
    commission = Decimal(0)
    if rules.commission_enabled:
        commission = rules.commission_fixed if rules.commission_fixed is not None else money((gross if rules.commission_basis == 'gross' else net) * rules.commission_percentage / 100)
        if rules.commission_limit is not None:
            commission = min(commission, rules.commission_limit)
    if revenue_doctor + commission > gross:
        raise AppException(422, 'billing_allocation_excess', 'Doctor revenue and commission exceed the gross service value')
    values = {('hospital', 'revenue'): money(gross - revenue_doctor - commission)}
    if rules.doctor_key:
        values[(rules.doctor_key, 'revenue')] = money(revenue_doctor)
    if rules.commission_enabled:
        for key, value in allocate(commission, {p.key: p.share for p in rules.participants}).items():
            values[(key, 'commission')] = value
    for key, value in contributions.items():
        values[(key, 'discount')] = -value
    assert sum(values.values()) == net
    return values


class FinancialPolicies:
    def __init__(self, db):
        self.db = db

    def list(self, actor):
        stmt = select(BillingPolicy).order_by(BillingPolicy.created_at.desc(), BillingPolicy.id)
        if actor.branch_id:
            stmt = stmt.where(or_(BillingPolicy.branch_id == actor.branch_id, BillingPolicy.branch_id.is_(None)))
        return list(self.db.scalars(stmt))

    def create(self, payload, actor):
        row = BillingPolicy(branch_id=actor.branch_id, **payload.model_dump(exclude={'rules'}), rules=payload.rules.model_dump(mode='json'), created_by=actor.id, updated_by=actor.id)
        self.db.add(row)
        self.db.flush()
        from app.modules.accounting.participants import post_participant_allocations
        post_participant_allocations(self.db,actor)
        self.db.commit()
        return row

    def resolve(self, actor, config, invoice):
        now = datetime.now(UTC)
        from app.models.encounter import OPDVisit
        visit_id = getattr(invoice, 'source_opd_visit_id', None)
        visit = self.db.get(OPDVisit, visit_id) if visit_id else None
        doctor_id = visit.consulting_doctor_user_id if visit else invoice.internal_referral_user_id
        from app.models.billing import BillingType
        category = self.db.get(BillingType, config.billing_type_id) if config.billing_type_id else None
        department = category.department if category else invoice.billing_department
        matches = {'hospital': '*', 'department': department,
                   'category': str(config.billing_type_id), 'item': str(config.id),
                   'doctor': str(doctor_id), 'referrer': str(invoice.referred_doctor_id)}
        priority = {'hospital': 0, 'department': 1, 'category': 2, 'doctor': 3, 'referrer': 4, 'item': 5}
        branch_id = getattr(invoice, 'branch_id', None) or config.branch_id or actor.branch_id
        rows = [p for p in self.list(actor) if p.branch_id in {None, branch_id} and p.is_active and p.effective_from <= now and (p.effective_until is None or now < p.effective_until) and matches.get(p.scope) == p.selector]
        if not rows:
            return None
        # A more specific policy replaces the complete rule set; branch wins at the same scope.
        rows.sort(key=lambda p: (priority[p.scope], p.branch_id is not None, p.effective_from, p.created_at, str(p.id)))
        row = rows[-1]
        return {'policy_id': str(row.id), 'rules': row.rules}

    def freeze(self, invoice, configs, resolved, actor):
        from app.modules.auth.service import AuthService
        approved = 'billing.service.manage' in AuthService(self.db).get_effective_permissions(actor)
        indexed_shares = allocate(invoice.invoice_discount_amount, {index: item.line_total for index, item in enumerate(invoice.items)})
        shares = {item.id: indexed_shares[index] for index, item in enumerate(invoice.items)}
        nets = {item.id: item.line_total - shares[item.id] for item in invoice.items}
        for item, request in zip(invoice.items, resolved):
            item.financial_snapshot = {'allocation_only': True, 'invoice_discount_amount': str(shares[item.id])}
            if request.carry_forward_item_id:
                continue
            enforce_catalog_discount(item, shares[item.id])
            policy = self.resolve(actor, configs[request.billing_service_id], invoice)
            if policy:
                rules = FinancialRules.model_validate(policy['rules'])
                enforce_discount(item, item.line_total - nets[item.id], rules, actor, approved)
                item.financial_snapshot = {**policy, 'invoice_discount_amount': str(item.line_total - nets[item.id])}
            if request.unit_price_override is not None:
                item.financial_snapshot = {**item.financial_snapshot, 'fee_override': {'unit_price': str(request.unit_price_override), 'reason': request.override_reason}}
        self.db.flush()

    def sync(self, invoice, actor, reason):
        nets = net_line_amounts(invoice)
        previous = list(self.db.scalars(select(BillingAllocation).where(BillingAllocation.invoice_id == invoice.id, BillingAllocation.component != 'settlement')))
        returned = {}
        for refund in invoice.refunds:
            if refund.refund_type == 'return':
                for line in refund.return_items or []:
                    key = line['invoice_item_id']
                    returned[key] = returned.get(key, Decimal(0)) + Decimal(line['quantity'])
        for item in invoice.items:
            if not item.financial_snapshot or item.financial_snapshot.get('allocation_only'):
                continue
            rules = FinancialRules.model_validate(item.financial_snapshot['rules'])
            targets = financial_values(item, nets[item.id], rules)
            ratio = Decimal(0) if invoice.status in {'void', 'consolidated'} else max(Decimal(0), (item.quantity - returned.get(str(item.id), Decimal(0))) / item.quantity)
            # Scale each signed component cumulatively; hospital revenue absorbs rounding.
            scaled = {key: money(value * ratio) for key, value in targets.items()}
            retained_net = nets[item.id] - money(nets[item.id] * (1 - ratio))
            scaled[('hospital', 'revenue')] += retained_net - sum(scaled.values())
            for (key, component), target in scaled.items():
                old = sum((r.amount for r in previous if r.invoice_item_id == item.id and r.participant_key == key and r.component == component), Decimal(0))
                delta = target - old
                if delta:
                    pending = component == 'commission' and rules.commission_approval_required
                    self.db.add(BillingAllocation(branch_id=invoice.branch_id, invoice_id=invoice.id, invoice_item_id=item.id, participant_key=key, component=component, amount=delta, state='pending' if pending else 'approved', reason=reason, created_by=actor.id, updated_by=actor.id))
        self.db.flush()
        managed = [item for item in invoice.items if item.financial_snapshot and not item.financial_snapshot.get('allocation_only')]
        if managed:
            commission = self.db.scalar(select(func.coalesce(func.sum(BillingAllocation.amount), 0)).where(BillingAllocation.invoice_id == invoice.id, BillingAllocation.component == 'commission'))
            legacy = sum((item.doctor_share_amount for item in invoice.items if item not in managed), Decimal(0))
            invoice.referred_doctor_amount = money(commission + legacy)
            self.db.flush()
        from app.modules.accounting.participants import post_participant_allocations
        post_participant_allocations(self.db,actor)

    def entries(self, actor):
        stmt = select(BillingAllocation).order_by(BillingAllocation.created_at, BillingAllocation.id)
        # Hospital-wide users choose explicit branches for settlement; null branch is its own account scope.
        stmt = stmt.where(BillingAllocation.branch_id == actor.branch_id)
        return list(self.db.scalars(stmt))

    def settle(self, payload, actor):
        from app.modules.support_posting.service import lock_branch
        lock_branch(self.db, actor)
        self.db.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'), {'key': 'financial-settle:' + str(actor.branch_id)})
        rows = [r for r in self.entries(actor) if r.participant_key == payload.participant_key]
        duplicate = next((r for r in self.entries(actor) if r.request_key == payload.request_key), None)
        if duplicate:
            if duplicate.participant_key != payload.participant_key or duplicate.amount != -payload.amount:
                raise AppException(409, 'billing_request_conflict', 'This request key was already used for another settlement')
            return duplicate
        if payload.approve_pending:
            # Approval is a separate append-only transfer; original earned entries remain pending.
            pending = sum((r.amount for r in rows if r.state == 'pending'), Decimal(0))
            if pending:
                for state, amount in [('pending', -pending), ('approved', pending)]:
                    row = BillingAllocation(branch_id=actor.branch_id, participant_key=payload.participant_key, component='approval', state=state, amount=amount, reason=payload.reason, created_by=actor.id, updated_by=actor.id)
                    self.db.add(row)
                    rows.append(row)
        balance = sum((r.amount for r in rows if r.state in {'approved', 'settled'}), Decimal(0))
        balance += min(Decimal(0), sum((r.amount for r in rows if r.state == 'pending'), Decimal(0)))
        if payload.participant_key == 'hospital' or payload.amount > balance:
            raise AppException(422, 'billing_settlement_excess', 'Settlement exceeds the approved participant payable balance')
        row = BillingAllocation(branch_id=actor.branch_id, participant_key=payload.participant_key, component='settlement', state='settled', amount=-payload.amount, request_key=payload.request_key, reason=payload.reason, created_by=actor.id, updated_by=actor.id)
        self.db.add(row)
        self.db.flush()
        from app.modules.accounting.participants import post_participant_allocations
        post_participant_allocations(self.db,actor)
        self.db.commit()
        return row
