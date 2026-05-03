"""Backfill lab and radiology domain tables from existing opd_visit_orders.

Usage:
    cd backend
    .venv/bin/python -m app.scripts.backfill_lab_radiology
"""

import logging
import os
import sys
from datetime import UTC, datetime

from sqlalchemy.orm import joinedload

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.models.billing import BillingInvoiceItem
from app.models.billing_links import BillingItemLink
from app.models.encounter import OPDVisitOrder
from app.models.laboratory import LabOrder, LabOrderItem, LabResult, LabResultItem
from app.models.radiology import RadiologyOrder, RadiologyReport, RadiologyReportSection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_lab_radiology")


def backfill() -> None:
    session = SessionLocal()
    try:
        # Lab orders
        lab_orders = (
            session.query(OPDVisitOrder)
            .options(joinedload(OPDVisitOrder.visit))
            .filter(
                OPDVisitOrder.order_type == "investigation",
                OPDVisitOrder.service_area == "laboratory",
                OPDVisitOrder.lab_order_id.is_(None),
            )
            .all()
        )
        logger.info(f"Found {len(lab_orders)} laboratory orders to backfill")
        for visit_order in lab_orders:
            lab_order = LabOrder(
                branch_id=visit_order.visit.branch_id if visit_order.visit else None,
                patient_id=visit_order.visit.patient_id if visit_order.visit else None,
                visit_id=visit_order.visit_id,
                order_number=f"LAB-BF-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{str(visit_order.id)[:8]}",
                status=visit_order.status or "pending",
                collected_at=visit_order.sample_collected_at,
                completed_at=visit_order.completed_at,
                verified_at=visit_order.verified_at,
                note=visit_order.sample_note,
                created_by=visit_order.created_by,
                updated_by=visit_order.updated_by,
                created_at=visit_order.created_at,
                updated_at=visit_order.updated_at,
            )
            session.add(lab_order)
            session.flush()

            lab_item = LabOrderItem(
                order_id=lab_order.id,
                test_name=visit_order.item_name,
                quantity=visit_order.quantity,
                created_by=visit_order.created_by,
                updated_by=visit_order.updated_by,
                created_at=visit_order.created_at,
                updated_at=visit_order.updated_at,
            )
            session.add(lab_item)

            if visit_order.result_text:
                lab_result = LabResult(
                    order_id=lab_order.id,
                    report_number=f"LR-BF-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{str(visit_order.id)[:8]}",
                    status="preliminary",
                    overall_interpretation=visit_order.result_text,
                    created_by=visit_order.created_by,
                    updated_by=visit_order.updated_by,
                    created_at=visit_order.updated_at or visit_order.created_at,
                    updated_at=visit_order.updated_at or visit_order.created_at,
                )
                session.add(lab_result)
                session.flush()
                result_item = LabResultItem(
                    result_id=lab_result.id,
                    analyte_name=visit_order.item_name,
                    value=visit_order.result_text,
                    created_by=visit_order.created_by,
                    updated_by=visit_order.updated_by,
                    created_at=visit_order.updated_at or visit_order.created_at,
                    updated_at=visit_order.updated_at or visit_order.created_at,
                )
                session.add(result_item)

            visit_order.lab_order_id = lab_order.id
            logger.info(f"Backfilled lab order for OPDVisitOrder {visit_order.id}")

        # Radiology orders
        rad_orders = (
            session.query(OPDVisitOrder)
            .options(joinedload(OPDVisitOrder.visit))
            .filter(
                OPDVisitOrder.order_type == "investigation",
                OPDVisitOrder.service_area == "radiology",
                OPDVisitOrder.radiology_order_id.is_(None),
            )
            .all()
        )
        logger.info(f"Found {len(rad_orders)} radiology orders to backfill")
        for visit_order in rad_orders:
            rad_order = RadiologyOrder(
                branch_id=visit_order.visit.branch_id if visit_order.visit else None,
                patient_id=visit_order.visit.patient_id if visit_order.visit else None,
                visit_id=visit_order.visit_id,
                order_number=f"RAD-BF-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{str(visit_order.id)[:8]}",
                study_description=visit_order.item_name,
                status=visit_order.status or "pending",
                completed_at=visit_order.completed_at,
                verified_at=visit_order.verified_at,
                note=visit_order.sample_note,
                created_by=visit_order.created_by,
                updated_by=visit_order.updated_by,
                created_at=visit_order.created_at,
                updated_at=visit_order.updated_at,
            )
            session.add(rad_order)
            session.flush()

            if visit_order.result_text:
                rad_report = RadiologyReport(
                    order_id=rad_order.id,
                    report_number=f"RR-BF-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{str(visit_order.id)[:8]}",
                    status="draft",
                    overall_findings=visit_order.result_text,
                    created_by=visit_order.created_by,
                    updated_by=visit_order.updated_by,
                    created_at=visit_order.updated_at or visit_order.created_at,
                    updated_at=visit_order.updated_at or visit_order.created_at,
                )
                session.add(rad_report)
                session.flush()
                section = RadiologyReportSection(
                    report_id=rad_report.id,
                    section_name="Findings",
                    content=visit_order.result_text,
                    display_order=0,
                    created_by=visit_order.created_by,
                    updated_by=visit_order.updated_by,
                    created_at=visit_order.updated_at or visit_order.created_at,
                    updated_at=visit_order.updated_at or visit_order.created_at,
                )
                session.add(section)

            visit_order.radiology_order_id = rad_order.id
            logger.info(f"Backfilled radiology order for OPDVisitOrder {visit_order.id}")

        # Billing links backfill
        for visit_order in lab_orders + rad_orders:
            invoice_items = (
                session.query(BillingInvoiceItem)
                .filter(BillingInvoiceItem.source_opd_visit_order_id == visit_order.id)
                .all()
            )
            for inv_item in invoice_items:
                if visit_order.lab_order_id:
                    existing = (
                        session.query(BillingItemLink)
                        .filter(
                            BillingItemLink.invoice_item_id == inv_item.id,
                            BillingItemLink.source_entity_id == visit_order.lab_order_id,
                        )
                        .first()
                    )
                    if not existing:
                        link = BillingItemLink(
                            invoice_item_id=inv_item.id,
                            branch_id=inv_item.invoice.branch_id if inv_item.invoice else None,
                            source_module="lab",
                            source_entity_type="lab_order_item",
                            source_entity_id=visit_order.lab_order_id,
                            meta={"invoice_number": inv_item.invoice.invoice_number if inv_item.invoice else None},
                        )
                        session.add(link)
                        logger.info(f"Created billing link for lab order {visit_order.lab_order_id}")
                elif visit_order.radiology_order_id:
                    existing = (
                        session.query(BillingItemLink)
                        .filter(
                            BillingItemLink.invoice_item_id == inv_item.id,
                            BillingItemLink.source_entity_id == visit_order.radiology_order_id,
                        )
                        .first()
                    )
                    if not existing:
                        link = BillingItemLink(
                            invoice_item_id=inv_item.id,
                            branch_id=inv_item.invoice.branch_id if inv_item.invoice else None,
                            source_module="radiology",
                            source_entity_type="radiology_order",
                            source_entity_id=visit_order.radiology_order_id,
                            meta={"invoice_number": inv_item.invoice.invoice_number if inv_item.invoice else None},
                        )
                        session.add(link)
                        logger.info(f"Created billing link for radiology order {visit_order.radiology_order_id}")

        session.commit()
        logger.info("Backfill completed successfully")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    backfill()
