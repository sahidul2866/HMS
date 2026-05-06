"""Upload demo DICOM images to Orthanc and link seeded radiology orders.

Usage:
    cd backend
    .venv/bin/python -m app.scripts.seed_radiology_pacs_images
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from urllib import request
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.radiology import PACSLink, RadiologyOrder
from app.modules.radiology.pacs_service import OrthancPACSService

logger = logging.getLogger("seed_radiology_pacs_images")
logging.basicConfig(level=logging.INFO)

SAMPLE_DICOM_URLS = [
    "https://raw.githubusercontent.com/pydicom/pydicom-data/master/data_store/data/emri_small.dcm",
    "https://raw.githubusercontent.com/pydicom/pydicom-data/master/data_store/data/SC_rgb.dcm",
    "https://raw.githubusercontent.com/pydicom/pydicom-data/master/data_store/data/US1_UNCR.dcm",
]
UNSUPPORTED_MODALITIES = {"SEG"}


def _download_bytes(url: str) -> bytes:
    with request.urlopen(url, timeout=30) as response:
        return response.read()


def seed() -> None:
    session = SessionLocal()
    pacs = OrthancPACSService()
    try:
        orders = (
            session.query(RadiologyOrder)
            .filter(RadiologyOrder.is_active.is_(True))
            .order_by(RadiologyOrder.created_at.desc())
            .limit(12)
            .all()
        )
        if not orders:
            logger.info("No radiology orders found. Seed radiology demo orders first.")
            return

        for idx, order in enumerate(orders):
            orthanc_study_id = None
            tags: dict[str, str] = {}
            study_uid = None
            for attempt in range(len(SAMPLE_DICOM_URLS)):
                url = SAMPLE_DICOM_URLS[(idx + attempt) % len(SAMPLE_DICOM_URLS)]
                dicom_bytes = _download_bytes(url)
                upload_result = pacs.upload_instance(dicom_bytes)
                candidate_study_id = upload_result.get("ParentStudy")
                if not candidate_study_id:
                    continue
                candidate_study = pacs.get_study(candidate_study_id)
                candidate_tags = candidate_study.get("MainDicomTags", {})
                modality = (candidate_tags.get("ModalitiesInStudy") or "").upper()
                if modality in UNSUPPORTED_MODALITIES:
                    logger.info("Skipping unsupported modality %s for order %s", modality, order.order_number)
                    continue
                orthanc_study_id = candidate_study_id
                tags = candidate_tags
                study_uid = tags.get("StudyInstanceUID")
                break

            if not orthanc_study_id:
                logger.warning("Could not upload a supported study for order %s", order.order_number)
                continue
            if not study_uid:
                logger.warning("Missing StudyInstanceUID for order %s", order.order_number)
                continue

            link = order.pacs_links[0] if order.pacs_links else None
            if link is None:
                link = PACSLink(
                    id=uuid4(),
                    order_id=order.id,
                    created_by=order.updated_by,
                    updated_by=order.updated_by,
                )
                session.add(link)

            link.study_uid = study_uid
            link.orthanc_study_id = orthanc_study_id
            link.series_uid = None
            link.accession_number = tags.get("AccessionNumber")
            link.dicom_patient_id = tags.get("PatientID")
            link.pacs_provider = "orthanc"
            link.status = "study_uploaded"
            link.viewer_url = pacs.build_orthanc_viewer_url(orthanc_study_id=orthanc_study_id, study_uid=study_uid)
            link.updated_by = order.updated_by

            if order.status in {"pending", "pending_study"}:
                order.status = "study_uploaded"
                order.performed_at = order.performed_at or datetime.now(UTC)
                order.updated_by = order.updated_by

            logger.info("Linked order %s to study %s", order.order_number, study_uid)

        session.commit()
        logger.info("Radiology PACS image seed completed.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
