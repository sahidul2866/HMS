"""Relink radiology PACS links to viewable (non-SEG) Orthanc studies.

Usage:
    cd backend
    .venv/bin/python -m app.scripts.relink_radiology_viewable_studies
"""

from __future__ import annotations

from app.core.database import SessionLocal
from app.models.radiology import PACSLink, RadiologyOrder
from app.modules.radiology.pacs_service import OrthancPACSService

EXCLUDED_STUDY_UIDS = {
    "1.2.392.200103.20080913.113635.0.2009.6.22.21.43.10.22941.1",  # SEG demo object
}


def main() -> None:
    session = SessionLocal()
    pacs = OrthancPACSService()
    try:
        orthanc_study_ids = pacs.list_studies()
        viewable: list[dict] = []
        for orthanc_study_id in orthanc_study_ids:
            study = pacs.get_study(orthanc_study_id)
            try:
                import json
                raw_instances = pacs._call("GET", f"/studies/{orthanc_study_id}/instances")
                instances = json.loads(raw_instances.decode("utf-8")) if raw_instances else []
            except Exception:
                instances = []
            if not instances:
                continue
            first_instance = instances[0]
            instance_id = first_instance.get("ID") if isinstance(first_instance, dict) else first_instance
            if not instance_id:
                continue
            tags = study.get("MainDicomTags", {})
            study_uid = tags.get("StudyInstanceUID")
            if not study_uid:
                continue
            if study_uid in EXCLUDED_STUDY_UIDS:
                continue
            try:
                pacs._call("GET", f"/instances/{instance_id}/preview")
            except Exception:
                continue
            viewable.append({"orthanc_study_id": orthanc_study_id, "study_uid": study_uid})

        if not viewable:
            print("No viewable Orthanc studies found. Upload non-SEG studies first.")
            return

        orders = (
            session.query(RadiologyOrder)
            .filter(RadiologyOrder.is_active.is_(True))
            .order_by(RadiologyOrder.created_at.asc())
            .all()
        )
        if not orders:
            print("No radiology orders found.")
            return

        updated = 0
        for index, order in enumerate(orders):
            target = viewable[index % len(viewable)]
            link = order.pacs_links[0] if order.pacs_links else None
            if link is None:
                link = PACSLink(order_id=order.id, created_by=order.updated_by, updated_by=order.updated_by)
                session.add(link)
            link.study_uid = target["study_uid"]
            link.orthanc_study_id = target["orthanc_study_id"]
            link.viewer_url = pacs.build_orthanc_viewer_url(
                orthanc_study_id=target["orthanc_study_id"],
                study_uid=target["study_uid"],
            )
            link.status = "study_uploaded"
            link.pacs_provider = "orthanc"
            link.updated_by = order.updated_by
            if order.status in {"pending", "pending_study"}:
                order.status = "study_uploaded"
            updated += 1

        session.commit()
        print(f"Relinked {updated} radiology orders to {len(viewable)} viewable Orthanc studies.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
