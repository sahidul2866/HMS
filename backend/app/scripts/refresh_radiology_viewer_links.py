"""Refresh stored radiology PACS viewer links using current viewer settings.

Usage:
    cd backend
    .venv/bin/python -m app.scripts.refresh_radiology_viewer_links
"""

from app.core.database import SessionLocal
from app.models.radiology import PACSLink
from app.modules.radiology.pacs_service import OrthancPACSService


def main() -> None:
    session = SessionLocal()
    pacs = OrthancPACSService()
    try:
        links = session.query(PACSLink).filter(PACSLink.study_uid.isnot(None)).all()
        for link in links:
            link.viewer_url = pacs.build_orthanc_viewer_url(
                orthanc_study_id=link.orthanc_study_id,
                study_uid=link.study_uid,
            )
        session.commit()
        print(f"Updated {len(links)} PACS viewer links.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
