"""Seed realistic lab and radiology demo data.

Usage:
    cd backend
    .venv/bin/python -m app.scripts.seed_lab_radiology_demo
"""

import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.encounter import OPDVisit, OPDVisitOrder
from app.models.laboratory import LabAttachment, LabOrder, LabOrderItem, LabResult, LabResultItem
from app.models.patient import Patient
from app.models.radiology import RadiologyAttachment, RadiologyOrder, RadiologyReport, RadiologyReportSection
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_lab_radiology_demo")


def _get_demo_context(session):
    branch = session.query(Branch).first()
    patient = session.query(Patient).first()
    user = session.query(User).filter(User.is_active.is_(True)).first()
    visit = session.query(OPDVisit).first()
    if not all([branch, patient, user, visit]):
        raise RuntimeError("Missing prerequisite demo data (branch, patient, user, visit)")
    return {
        "branch_id": branch.id,
        "patient_id": patient.id,
        "user_id": user.id,
        "visit_id": visit.id,
    }


def seed() -> None:
    session = SessionLocal()
    try:
        ctx = _get_demo_context(session)
        now = datetime.now(UTC)

        # --- Lab Orders ---
        lab_scenarios = [
            {
                "order_number": "LAB-DEMO-001",
                "status": "verified",
                "tests": [
                    {"name": "CBC", "items": [
                        ("WBC", "7.2", "x10^9/L", Decimal("4.0"), Decimal("11.0"), "normal"),
                        ("RBC", "4.8", "x10^12/L", Decimal("4.5"), Decimal("5.5"), "normal"),
                        ("Hemoglobin", "13.5", "g/dL", Decimal("12.0"), Decimal("16.0"), "normal"),
                        ("Platelets", "250", "x10^9/L", Decimal("150"), Decimal("450"), "normal"),
                    ]},
                ],
                "result_status": "final",
            },
            {
                "order_number": "LAB-DEMO-002",
                "status": "completed",
                "tests": [
                    {"name": "BMP", "items": [
                        ("Glucose", "110", "mg/dL", Decimal("70"), Decimal("100"), "high"),
                        ("Sodium", "138", "mEq/L", Decimal("135"), Decimal("145"), "normal"),
                        ("Potassium", "4.2", "mEq/L", Decimal("3.5"), Decimal("5.0"), "normal"),
                        ("Creatinine", "1.0", "mg/dL", Decimal("0.7"), Decimal("1.3"), "normal"),
                    ]},
                ],
                "result_status": "preliminary",
            },
            {
                "order_number": "LAB-DEMO-003",
                "status": "pending",
                "tests": [
                    {"name": "Lipid Panel", "items": []},
                ],
                "result_status": None,
            },
            {
                "order_number": "LAB-DEMO-004",
                "status": "collected",
                "tests": [
                    {"name": "HbA1c", "items": []},
                ],
                "result_status": None,
            },
        ]

        for scenario in lab_scenarios:
            lab_order = LabOrder(
                id=uuid4(),
                branch_id=ctx["branch_id"],
                patient_id=ctx["patient_id"],
                visit_id=ctx["visit_id"],
                order_number=scenario["order_number"],
                status=scenario["status"],
                priority="routine",
                collected_at=now - timedelta(hours=4) if scenario["status"] in {"collected", "in_progress", "completed", "verified"} else None,
                completed_at=now - timedelta(hours=2) if scenario["status"] in {"completed", "verified"} else None,
                verified_at=now - timedelta(hours=1) if scenario["status"] == "verified" else None,
                created_by=ctx["user_id"],
                updated_by=ctx["user_id"],
            )
            session.add(lab_order)
            session.flush()

            for test in scenario["tests"]:
                lab_item = LabOrderItem(
                    id=uuid4(),
                    order_id=lab_order.id,
                    test_name=test["name"],
                    quantity=1,
                    created_by=ctx["user_id"],
                    updated_by=ctx["user_id"],
                )
                session.add(lab_item)
                session.flush()

            if scenario["result_status"]:
                lab_result = LabResult(
                    id=uuid4(),
                    order_id=lab_order.id,
                    report_number=f"LR-{scenario['order_number']}",
                    status=scenario["result_status"],
                    created_by=ctx["user_id"],
                    updated_by=ctx["user_id"],
                )
                session.add(lab_result)
                session.flush()

                for test in scenario["tests"]:
                    for analyte in test["items"]:
                        result_item = LabResultItem(
                            id=uuid4(),
                            result_id=lab_result.id,
                            analyte_name=analyte[0],
                            value=analyte[1],
                            unit=analyte[2],
                            reference_range_low=analyte[3],
                            reference_range_high=analyte[4],
                            flag=analyte[5],
                            created_by=ctx["user_id"],
                            updated_by=ctx["user_id"],
                        )
                        session.add(result_item)

            # Attachment placeholder
            if scenario["status"] in {"completed", "verified"}:
                att = LabAttachment(
                    id=uuid4(),
                    order_id=lab_order.id,
                    file_name=f"{scenario['order_number']}_report.pdf",
                    mime_type="application/pdf",
                    url=f"/uploads/lab/{scenario['order_number']}_report.pdf",
                    file_size_bytes=12400,
                    created_by_user_id=ctx["user_id"],
                    updated_by=ctx["user_id"],
                )
                session.add(att)

            # Create linked OPD visit order for dashboard compat
            opd_order = OPDVisitOrder(
                id=uuid4(),
                visit_id=ctx["visit_id"],
                order_type="investigation",
                service_area="laboratory",
                item_name=scenario["tests"][0]["name"],
                quantity=1,
                status=scenario["status"],
                lab_order_id=lab_order.id,
                created_by=ctx["user_id"],
                updated_by=ctx["user_id"],
            )
            session.add(opd_order)
            logger.info(f"Created lab demo order {scenario['order_number']}")

        # --- Radiology Orders ---
        rad_scenarios = [
            {
                "order_number": "RAD-DEMO-001",
                "modality": "X-Ray",
                "study": "Chest X-Ray PA",
                "body_part": "Chest",
                "status": "report_completed",
                "sections": [
                    ("Clinical History", "Patient presented with cough and mild fever."),
                    ("Technique", "PA and lateral chest radiographs obtained."),
                    ("Findings", "Lungs are clear. Cardiomediastinal silhouette is normal. No pleural effusion."),
                    ("Impression", "Normal chest X-ray."),
                ],
            },
            {
                "order_number": "RAD-DEMO-002",
                "modality": "CT",
                "study": "CT Brain Plain",
                "body_part": "Brain",
                "status": "ready_for_review",
                "sections": [
                    ("Clinical History", "Headache for 3 days."),
                    ("Technique", "Non-contrast axial CT brain."),
                    ("Findings", "No acute intracranial hemorrhage. No mass effect. Ventricles are normal in size."),
                    ("Impression", "Normal CT brain."),
                ],
            },
            {
                "order_number": "RAD-DEMO-003",
                "modality": "MRI",
                "study": "MRI Lumbar Spine",
                "body_part": "Lumbar Spine",
                "status": "pending_study",
                "sections": [],
            },
            {
                "order_number": "RAD-DEMO-004",
                "modality": "Ultrasound",
                "study": "Ultrasound Whole Abdomen",
                "body_part": "Abdomen",
                "status": "study_uploaded",
                "sections": [],
            },
        ]

        for scenario in rad_scenarios:
            rad_order = RadiologyOrder(
                id=uuid4(),
                branch_id=ctx["branch_id"],
                patient_id=ctx["patient_id"],
                visit_id=ctx["visit_id"],
                order_number=scenario["order_number"],
                modality=scenario["modality"],
                study_description=scenario["study"],
                body_part=scenario["body_part"],
                status=scenario["status"],
                priority="routine",
                performed_at=now - timedelta(hours=3) if scenario["status"] in {"study_uploaded", "ready_for_review", "report_completed", "verified"} else None,
                completed_at=now - timedelta(hours=2) if scenario["status"] in {"report_completed", "verified"} else None,
                verified_at=now - timedelta(hours=1) if scenario["status"] == "verified" else None,
                created_by=ctx["user_id"],
                updated_by=ctx["user_id"],
            )
            session.add(rad_order)
            session.flush()

            if scenario["sections"]:
                rad_report = RadiologyReport(
                    id=uuid4(),
                    order_id=rad_order.id,
                    report_number=f"RR-{scenario['order_number']}",
                    status="final" if scenario["status"] in {"report_completed", "verified"} else "preliminary",
                    overall_findings=next((s[1] for s in scenario["sections"] if s[0] == "Findings"), None),
                    impression=next((s[1] for s in scenario["sections"] if s[0] == "Impression"), None),
                    created_by=ctx["user_id"],
                    updated_by=ctx["user_id"],
                )
                session.add(rad_report)
                session.flush()

                for idx, (name, content) in enumerate(scenario["sections"]):
                    section = RadiologyReportSection(
                        id=uuid4(),
                        report_id=rad_report.id,
                        section_name=name,
                        content=content,
                        display_order=idx,
                        created_by=ctx["user_id"],
                        updated_by=ctx["user_id"],
                    )
                    session.add(section)

            if scenario["status"] in {"study_uploaded", "ready_for_review", "report_completed", "verified"}:
                att = RadiologyAttachment(
                    id=uuid4(),
                    order_id=rad_order.id,
                    file_name=f"{scenario['order_number']}_image.dcm",
                    mime_type="application/dicom",
                    url=f"/uploads/rad/{scenario['order_number']}_image.dcm",
                    file_size_bytes=256000,
                    created_by_user_id=ctx["user_id"],
                    updated_by=ctx["user_id"],
                )
                session.add(att)

            # Create linked OPD visit order for dashboard compat
            opd_order = OPDVisitOrder(
                id=uuid4(),
                visit_id=ctx["visit_id"],
                order_type="investigation",
                service_area="radiology",
                item_name=scenario["study"],
                quantity=1,
                status=scenario["status"],
                radiology_order_id=rad_order.id,
                created_by=ctx["user_id"],
                updated_by=ctx["user_id"],
            )
            session.add(opd_order)
            logger.info(f"Created radiology demo order {scenario['order_number']}")

        session.commit()
        logger.info("Lab and radiology demo seed completed")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
