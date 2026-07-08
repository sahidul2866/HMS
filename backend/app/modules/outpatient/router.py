from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.outpatient.service import OutpatientService
from app.schemas.outpatient import OutpatientDashboardRead, OutpatientQueueAction, OutpatientReportRead, UnifiedOutpatientQueueItem

router = APIRouter(prefix="/outpatient", tags=["Outpatient"])


@router.get("/dashboard", response_model=OutpatientDashboardRead, dependencies=[Depends(require_any_permissions("opd.view", "telemedicine.view", "outpatient.report.view"))])
def dashboard(visit_mode: str | None = None, doctor_id: UUID | None = None, status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    filters = {k: v for k, v in {"visit_mode": visit_mode, "doctor_id": doctor_id, "status": status}.items() if v is not None}
    return OutpatientService(db).dashboard(user, filters)


@router.get("/queue", response_model=list[UnifiedOutpatientQueueItem], dependencies=[Depends(require_any_permissions("opd.queue.manage", "opd.queue.view", "telemedicine.waiting_room.view", "telemedicine.queue.view"))])
def queue(visit_mode: str | None = None, doctor_id: UUID | None = None, status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    filters = {k: v for k, v in {"visit_mode": visit_mode, "doctor_id": doctor_id, "status": status}.items() if v is not None}
    return OutpatientService(db).queue_items(user, filters)


@router.post("/queue/{token_id}/action", response_model=UnifiedOutpatientQueueItem, dependencies=[Depends(require_any_permissions("opd.queue.manage", "opd.consultation.start", "opd.consultation.complete", "telemedicine.consultation.start", "telemedicine.consultation.complete"))])
def queue_action(token_id: UUID, payload: OutpatientQueueAction, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return OutpatientService(db).action(token_id, payload, user, context)


@router.get("/reports", response_model=OutpatientReportRead, dependencies=[Depends(require_permissions("outpatient.report.view"))])
def reports(report_type: str = Query("queue_waiting_time"), visit_mode: str | None = None, doctor_id: UUID | None = None, status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    filters = {k: v for k, v in {"visit_mode": visit_mode, "doctor_id": doctor_id, "status": status}.items() if v is not None}
    return OutpatientService(db).reports(user, report_type, filters)
