"""Frozen line allocation shared by invoice output and return posting."""
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def net_line_amounts(invoice) -> dict:
    """Line values after the invoice-level discount; they always add up to the invoice total.

    The invoice discount is spread by line value and the last line absorbs the rounding remainder,
    so returning every line can never credit more (or less) than the patient was billed.
    """
    lines = sorted((item for item in invoice.items if item.is_active), key=lambda item: str(item.id))
    net: dict[UUID, Decimal] = {}
    value_base = sum((item.line_total for item in lines), Decimal("0"))
    remaining_discount = money(invoice.invoice_discount_amount)
    allocated_net = Decimal("0.00")
    for index, item in enumerate(lines):
        if index == len(lines) - 1:
            amount = money(invoice.total_amount - allocated_net)
        else:
            share = money(invoice.invoice_discount_amount * item.line_total / value_base) if value_base else Decimal("0.00")
            share = min(share, remaining_discount)
            remaining_discount -= share
            amount = money(item.line_total - share)
        net[item.id] = amount
        allocated_net += amount
    return net

