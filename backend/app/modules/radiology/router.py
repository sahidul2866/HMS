from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.integration import verify_machine_integration_key
from app.dependencies.permissions import require_any_permissions
from app.modules.radiology.service import RadiologyService
from app.schemas.encounter import ClinicalInvestigationResultUpdate, ClinicalInvestigationWorkItemRead
from app.schemas.radiology import (
    PACSLinkCreate,
    PACSUploadResponse,
    RadiologyOrderCreate,
    RadiologyOrderRead,
    RadiologyReportUpsert,
    RadiologyMachineIngestResponse,
    RadiologySimulatorFeedRequest,
    RadiologySimulatorFeedResponse,
    RadiologySimulatorMachineRead,
    RadiologySummaryRead,
    RadiologyViewerRead,
)

router = APIRouter(prefix="/radiology", tags=["Radiology"])


@router.get(
    "/summary",
    response_model=RadiologySummaryRead,
    dependencies=[Depends(require_any_permissions("radiology.view", "radiology.manage"))],
)
def get_radiology_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> RadiologySummaryRead:
    return RadiologyService(db).get_summary(user)


@router.get(
    "/worklist",
    response_model=list[ClinicalInvestigationWorkItemRead],
    dependencies=[Depends(require_any_permissions("radiology.view", "radiology.manage"))],
)
def list_radiology_worklist(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[ClinicalInvestigationWorkItemRead]:
    return RadiologyService(db).list_worklist(user)


@router.put(
    "/worklist/{order_id}",
    response_model=ClinicalInvestigationWorkItemRead,
    dependencies=[Depends(require_any_permissions("radiology.upload_report", "radiology.verify_result"))],
)
def update_radiology_result(
    order_id: UUID,
    payload: ClinicalInvestigationResultUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClinicalInvestigationWorkItemRead:
    return RadiologyService(db).update_result(order_id, payload, user, context)


@router.post(
    "/orders",
    response_model=RadiologyOrderRead,
    dependencies=[Depends(require_any_permissions("radiology.order.create", "opd.prescribe", "diagnostics.order.manage"))],
)
def create_radiology_order(
    payload: RadiologyOrderCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RadiologyOrderRead:
    return RadiologyService(db).create_order(payload, user, context)


@router.post(
    "/pacs/link",
    response_model=PACSUploadResponse,
    dependencies=[Depends(require_any_permissions("radiology.upload_image", "settings.configuration.manage"))],
)
def link_pacs_study(
    payload: PACSLinkCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PACSUploadResponse:
    return RadiologyService(db).link_pacs_study(payload, user, context)


@router.post(
    "/orders/{order_id}/upload-dicom",
    response_model=PACSUploadResponse,
    dependencies=[Depends(require_any_permissions("radiology.upload_image", "settings.configuration.manage"))],
)
async def upload_dicom(
    order_id: UUID,
    dicom_file: UploadFile = File(...),
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PACSUploadResponse:
    content = await dicom_file.read()
    return RadiologyService(db).upload_dicom(order_id, content, user, context)


@router.get(
    "/orders/{order_id}/viewer",
    response_model=RadiologyViewerRead,
    dependencies=[Depends(require_any_permissions("radiology.view", "radiology.manage"))],
)
def get_viewer_url(
    order_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RadiologyViewerRead:
    return RadiologyService(db).get_viewer(order_id, user)


@router.post(
    "/report",
    response_model=RadiologyOrderRead,
    dependencies=[Depends(require_any_permissions("radiology.upload_report", "radiology.verify_result"))],
)
def upsert_report(
    payload: RadiologyReportUpsert,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RadiologyOrderRead:
    return RadiologyService(db).add_report(payload, user, context)


@router.post(
    "/orders/{order_id}/complete",
    response_model=RadiologyOrderRead,
    dependencies=[Depends(require_any_permissions("radiology.verify_result"))],
)
def mark_completed(
    order_id: UUID,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RadiologyOrderRead:
    return RadiologyService(db).mark_completed(order_id, user, context)


@router.get(
    "/simulator/machines",
    response_model=list[RadiologySimulatorMachineRead],
    dependencies=[Depends(require_any_permissions("radiology.view", "radiology.manage"))],
)
def list_simulator_machines(db: Session = Depends(get_db)) -> list[RadiologySimulatorMachineRead]:
    return RadiologyService(db).list_simulator_machines()


@router.post(
    "/orders/{order_id}/simulate-machine",
    response_model=RadiologySimulatorFeedResponse,
    dependencies=[Depends(require_any_permissions("radiology.upload_image", "settings.configuration.manage"))],
)
def simulate_machine_feed(
    order_id: UUID,
    payload: RadiologySimulatorFeedRequest,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RadiologySimulatorFeedResponse:
    return RadiologyService(db).simulate_machine_feed(order_id, payload, user, context)


@router.post(
    "/integration/orders/{order_id}/dicom",
    response_model=RadiologyMachineIngestResponse,
    dependencies=[Depends(verify_machine_integration_key)],
)
async def ingest_machine_dicom(
    order_id: UUID,
    machine_code: str = Form(...),
    note: str | None = Form(default=None),
    dicom_file: UploadFile = File(...),
    context=Depends(get_request_context),
    db: Session = Depends(get_db),
) -> RadiologyMachineIngestResponse:
    content = await dicom_file.read()
    return RadiologyService(db).ingest_machine_dicom(order_id, machine_code, content, note, context)
