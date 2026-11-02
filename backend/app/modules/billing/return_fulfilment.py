"""Preflight unused clinical charges, then cancel work in the return transaction.

Financial returns never invent a physical stock receipt or erase completed care.
Delivered goods use the pharmacy's batch-aware return process; completed services
can receive a separately audited financial refund without cancelling clinical work.
"""
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.exceptions import AppException
from app.models.encounter import IPDOrder, IPDMedicationAdministration, OPDVisitOrder
from app.models.laboratory import LabOrder
from app.models.pharmacy import PharmacyDispense, PharmacySaleItem
from app.models.radiology import RadiologyOrder


def cancellation_plan(db, item, quantity, previously_returned, actor):
    # Cashiers may credit goods already physically received by pharmacy. This
    # does not cancel prescriptions or manufacture another stock movement.
    received = list(db.scalars(select(PharmacyDispense).where(PharmacyDispense.billing_invoice_item_id == item.id, PharmacyDispense.is_active.is_(True)).with_for_update()))
    physical = sum((Decimal(d.returned_quantity or 0) for d in received if d.return_history), Decimal(0))
    if received and physical >= quantity + previously_returned:
        return []
    if any(d.status not in {"pending", "cancelled"} for d in received):
        raise AppException(409, "billing_return_not_received", "Pharmacy must physically receive the requested quantity before the cashier posts its credit")
    changes = []
    visited = set()

    def locked(model, identifier):
        if not identifier:
            return None
        return db.scalar(select(model).where(model.id == identifier).with_for_update().execution_options(populate_existing=True))

    def add(entity):
        if entity is None or (type(entity), entity.id) in visited:
            return
        visited.add((type(entity), entity.id))
        if quantity + previously_returned < item.quantity:
            raise AppException(409, 'billing_return_clinical_quantity', 'Return the entire unused clinical order together. Use the department return workflow for goods already issued.')
        if isinstance(entity, LabOrder):
            unused = entity.status in {'pending', 'ordered', 'cancelled'} and not entity.collected_at and not entity.results
            unused = unused and len([line for line in entity.items if line.is_active]) <= 1
        elif isinstance(entity, RadiologyOrder):
            unused = entity.status in {'pending', 'ordered', 'scheduled', 'cancelled'} and not entity.performed_at and not entity.reports and not entity.pacs_links
        elif isinstance(entity, PharmacyDispense):
            unused = entity.status in {'pending', 'cancelled'}
        elif isinstance(entity, IPDOrder):
            given = db.scalar(select(IPDMedicationAdministration.id).where(IPDMedicationAdministration.order_id == entity.id, IPDMedicationAdministration.status == 'administered').limit(1))
            unused = entity.status in {'ordered', 'pending', 'active', 'cancelled', 'discontinued'} and not given
        else:
            sold = db.scalar(select(PharmacySaleItem.id).where(PharmacySaleItem.source_visit_order_id == entity.id, PharmacySaleItem.is_active.is_(True), PharmacySaleItem.quantity > PharmacySaleItem.returned_quantity).limit(1))
            unused = entity.status in {'pending', 'ordered', 'cancelled'} and not sold
        if not unused:
            raise AppException(409, 'billing_return_fulfilled', 'This order has started or goods have been issued. Complete the department return/review first; request an audited billing adjustment for a price concession without cancelling care.')
        if getattr(entity, 'branch_id', None) and actor.branch_id and entity.branch_id != actor.branch_id:
            raise AppException(403, 'billing_return_branch', 'Linked order belongs to another branch')
        changes.append(entity)

    opd = locked(OPDVisitOrder, item.source_opd_visit_order_id)
    add(opd)
    if opd:
        add(locked(LabOrder, opd.lab_order_id))
        add(locked(RadiologyOrder, opd.radiology_order_id))
        for dispense in db.scalars(select(PharmacyDispense).where(PharmacyDispense.source_visit_order_id == opd.id, PharmacyDispense.is_active.is_(True)).with_for_update()):
            add(dispense)
    for link in item.item_links:
        if link.source_entity_type == 'ipd_order':
            order = locked(IPDOrder, link.source_entity_id)
            add(order)
            if order:
                add(locked(LabOrder, order.lab_order_id))
                add(locked(RadiologyOrder, order.radiology_order_id))
        elif link.source_entity_type == 'pharmacy_dispense':
            add(locked(PharmacyDispense, link.source_entity_id))
        elif link.source_entity_type == 'radiology_order':
            add(locked(RadiologyOrder, link.source_entity_id))
        elif link.source_entity_type == 'lab_order_item':
            # Historical links use the LabOrder id despite this entity-type name.
            add(locked(LabOrder, link.source_entity_id))
    return changes


def cancel_unused(changes, actor):
    for entity in changes:
        entity.status = 'cancelled'
        entity.updated_by = actor.id
        if isinstance(entity, IPDOrder):
            entity.billing_status = 'returned'
            entity.cancelled_at = datetime.now(UTC)
            entity.cancelled_by_user_id = actor.id
            for medication in entity.admission.medication_administrations:
                if medication.order_id == entity.id and medication.status in {'due', 'held', 'delayed'}:
                    medication.status = 'skipped'
                    medication.reason = 'Unused charge returned; linked order cancelled'
                    medication.updated_by = actor.id
            for task in entity.nursing_tasks:
                if task.status in {'pending', 'in_progress', 'overdue'}:
                    task.status = 'cancelled'
                    task.updated_by = actor.id
        if isinstance(entity, LabOrder):
            for line in entity.items:
                line.status = 'cancelled'
                line.updated_by = actor.id
