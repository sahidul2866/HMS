from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.ipd.service import IPDService
from app.schemas.encounter import (
    IPDAdmissionCreate,
    IPDAdmissionRead,
    IPDBedBoardRow,
    IPDBedCreate,
    IPDBedRead,
    IPDBillingSummary,
    IPDClinicalNoteCreate,
    IPDClinicalNoteRead,
    IPDDischarge,
    IPDDischargeReadiness,
    IPDHandoverCreate,
    IPDHandoverBoardRead,
    IPDHandoverRead,
    IPDMedicationAdministrationCreate,
    IPDMedicationAdministrationRead,
    IPDNursingNoteCreate,
    IPDNursingNoteRead,
    IPDNursingTaskCreate,
    IPDNursingTaskRead,
    IPDNursingTaskUpdate,
    IPDOrderCreate,
    IPDOrderGroupRead,
    IPDOrderRead,
    IPDOrderStatusUpdate,
    IPDPatientWorkspace,
    IPDReportSummary,
    IPDSettingsRead,
    IPDSettingsUpdate,
    IPDShiftCoverageRead,
    IPDStaffAssignmentCreate,
    IPDStaffAssignmentRead,
    IPDStaffAvailabilityRead,
    IPDTransfer,
    IPDSummary,
    IPDVitalsTrendRead,
)

router = APIRouter(prefix="/ipd", tags=["IPD"])


@router.get("/admissions", response_model=list[IPDAdmissionRead], dependencies=[Depends(require_permissions("ipd.view"))])
def list_ipd_admissions(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[IPDAdmissionRead]:
    service = IPDService(db)
    return [IPDAdmissionRead.model_validate(service._admission_payload(item)) for item in service.list_admissions(user)]


@router.get("/admissions/{admission_id}", response_model=IPDAdmissionRead, dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_admission(admission_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDAdmissionRead:
    admission = IPDService(db).get_admission(admission_id, user)
    service = IPDService(db)
    return IPDAdmissionRead.model_validate(service._admission_payload(admission))


@router.get("/admissions/{admission_id}/workspace", response_model=IPDPatientWorkspace, dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_workspace(admission_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDPatientWorkspace:
    return IPDService(db).workspace(admission_id, user)


@router.get("/admissions/{admission_id}/billing-summary", response_model=IPDBillingSummary, dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_billing_summary(admission_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDBillingSummary:
    return IPDService(db).billing_summary(admission_id, user)


@router.get("/summary", response_model=IPDSummary, dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDSummary:
    return IPDService(db).get_summary(user)


@router.get("/bed-board", response_model=list[IPDBedBoardRow], dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_bed_board(
    ward_name: str | None = None,
    room_type: str | None = None,
    bed_type: str | None = None,
    department_name: str | None = None,
    status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[IPDBedBoardRow]:
    return IPDService(db).bed_board(user, ward_name=ward_name, room_type=room_type, bed_type=bed_type, department_name=department_name, status=status)


@router.get("/reports/summary", response_model=IPDReportSummary, dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_report_summary(user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDReportSummary:
    return IPDService(db).report_summary(user)


@router.get("/settings", response_model=IPDSettingsRead, dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_settings(user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDSettingsRead:
    return IPDService(db).get_settings(user)


@router.put("/settings", response_model=IPDSettingsRead, dependencies=[Depends(require_any_permissions("ipd.settings.manage", "ipd.admission.manage"))])
def update_ipd_settings(
    payload: IPDSettingsUpdate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDSettingsRead:
    return IPDService(db).update_settings(payload, user, context)


@router.get("/staff-availability", response_model=list[IPDStaffAvailabilityRead], dependencies=[Depends(require_permissions("ipd.view"))])
def list_ipd_staff_availability(
    role_type: str,
    ward_name: str | None = None,
    department_name: str | None = None,
    shift_name: str | None = None,
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[IPDStaffAvailabilityRead]:
    return IPDService(db).list_staff_availability(user, role_type=role_type, ward_name=ward_name, department_name=department_name, shift_name=shift_name, q=q)


@router.get("/shift-coverage", response_model=IPDShiftCoverageRead, dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_shift_coverage(
    ward_name: str | None = None,
    shift_name: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDShiftCoverageRead:
    return IPDService(db).shift_coverage(user, ward_name=ward_name, shift_name=shift_name)


@router.get("/beds", response_model=list[IPDBedRead], dependencies=[Depends(require_permissions("ipd.view"))])
def list_ipd_beds(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[IPDBedRead]:
    return [IPDBedRead.model_validate(item, from_attributes=True) for item in IPDService(db).list_beds(user)]


@router.post("/beds", response_model=IPDBedRead, dependencies=[Depends(require_permissions("ipd.bed.manage"))])
def create_ipd_bed(
    payload: IPDBedCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDBedRead:
    bed = IPDService(db).create_bed(payload, user, context)
    return IPDBedRead.model_validate(bed, from_attributes=True)


@router.post("/admissions", response_model=IPDAdmissionRead, dependencies=[Depends(require_permissions("ipd.admit"))])
def create_ipd_admission(
    payload: IPDAdmissionCreate,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDAdmissionRead:
    admission = IPDService(db).create_admission(payload, user, context)
    service = IPDService(db)
    return IPDAdmissionRead.model_validate(service._admission_payload(admission))


@router.put(
    "/admissions/{admission_id}/discharge",
    response_model=IPDAdmissionRead,
    dependencies=[Depends(require_any_permissions("ipd.discharge", "ipd.discharge.finalize"))],
)
def discharge_ipd_admission(
    admission_id: UUID,
    payload: IPDDischarge,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDAdmissionRead:
    admission = IPDService(db).discharge(admission_id, payload, user, context)
    service = IPDService(db)
    return IPDAdmissionRead.model_validate(service._admission_payload(admission))


@router.get(
    "/admissions/{admission_id}/discharge-readiness",
    response_model=IPDDischargeReadiness,
    dependencies=[Depends(require_permissions("ipd.view"))],
)
def get_ipd_discharge_readiness(admission_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDDischargeReadiness:
    return IPDService(db).discharge_readiness(admission_id, user)


@router.put(
    "/admissions/{admission_id}/transfer",
    response_model=IPDAdmissionRead,
    dependencies=[Depends(require_permissions("ipd.transfer"))],
)
def transfer_ipd_admission(
    admission_id: UUID,
    payload: IPDTransfer,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IPDAdmissionRead:
    admission = IPDService(db).transfer(admission_id, payload, user, context)
    service = IPDService(db)
    return IPDAdmissionRead.model_validate(service._admission_payload(admission))


@router.post("/admissions/{admission_id}/assignments", response_model=IPDStaffAssignmentRead, dependencies=[Depends(require_any_permissions("ipd.assign_doctor", "ipd.assign_nurse"))])
def assign_ipd_staff(admission_id: UUID, payload: IPDStaffAssignmentCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDStaffAssignmentRead:
    return IPDStaffAssignmentRead.model_validate(IPDService(db).assign_staff(admission_id, payload, user, context), from_attributes=True)


@router.post("/admissions/{admission_id}/clinical-notes", response_model=IPDClinicalNoteRead, dependencies=[Depends(require_permissions("ipd.doctor_note.create"))])
def create_ipd_clinical_note(admission_id: UUID, payload: IPDClinicalNoteCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDClinicalNoteRead:
    return IPDClinicalNoteRead.model_validate(IPDService(db).create_clinical_note(admission_id, payload, user, context), from_attributes=True)


@router.post("/admissions/{admission_id}/nursing-notes", response_model=IPDNursingNoteRead, dependencies=[Depends(require_permissions("ipd.nursing_note.create"))])
def create_ipd_nursing_note(admission_id: UUID, payload: IPDNursingNoteCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDNursingNoteRead:
    return IPDNursingNoteRead.model_validate(IPDService(db).create_nursing_note(admission_id, payload, user, context), from_attributes=True)


@router.post("/admissions/{admission_id}/orders", response_model=IPDOrderRead, dependencies=[Depends(require_permissions("ipd.order.create"))])
def create_ipd_order(admission_id: UUID, payload: IPDOrderCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDOrderRead:
    return IPDOrderRead.model_validate(IPDService(db).create_order(admission_id, payload, user, context), from_attributes=True)


@router.get("/admissions/{admission_id}/orders/grouped", response_model=list[IPDOrderGroupRead], dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_grouped_orders(admission_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[IPDOrderGroupRead]:
    return IPDService(db).grouped_orders(admission_id, user)


@router.patch("/admissions/{admission_id}/orders/{order_id}", response_model=IPDOrderRead, dependencies=[Depends(require_permissions("ipd.order.create"))])
def update_ipd_order_status(admission_id: UUID, order_id: UUID, payload: IPDOrderStatusUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDOrderRead:
    return IPDOrderRead.model_validate(IPDService(db).update_order_status(admission_id, order_id, payload, user, context), from_attributes=True)


@router.post("/admissions/{admission_id}/medications", response_model=IPDMedicationAdministrationRead, dependencies=[Depends(require_permissions("ipd.medication.administer"))])
def administer_ipd_medication(admission_id: UUID, payload: IPDMedicationAdministrationCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDMedicationAdministrationRead:
    return IPDMedicationAdministrationRead.model_validate(IPDService(db).administer_medication(admission_id, payload, user, context), from_attributes=True)


@router.get("/medications/schedule", response_model=list[IPDMedicationAdministrationRead], dependencies=[Depends(require_permissions("ipd.view"))])
def list_ipd_medication_schedule(ward_name: str | None = None, nurse_user_id: UUID | None = None, shift_name: str | None = None, status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[IPDMedicationAdministrationRead]:
    return [IPDMedicationAdministrationRead.model_validate(item, from_attributes=True) for item in IPDService(db).list_medication_schedule(user, ward_name=ward_name, nurse_user_id=nurse_user_id, shift_name=shift_name, status=status)]


@router.get("/nursing-tasks", response_model=list[IPDNursingTaskRead], dependencies=[Depends(require_permissions("ipd.view"))])
def list_ipd_nursing_tasks(ward_name: str | None = None, nurse_user_id: UUID | None = None, shift_name: str | None = None, status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[IPDNursingTaskRead]:
    return [IPDNursingTaskRead.model_validate(item, from_attributes=True) for item in IPDService(db).list_nursing_tasks(user, ward_name=ward_name, nurse_user_id=nurse_user_id, shift_name=shift_name, status=status)]


@router.post("/admissions/{admission_id}/nursing-tasks", response_model=IPDNursingTaskRead, dependencies=[Depends(require_permissions("ipd.nursing_note.create"))])
def create_ipd_nursing_task(admission_id: UUID, payload: IPDNursingTaskCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDNursingTaskRead:
    return IPDNursingTaskRead.model_validate(IPDService(db).create_nursing_task(admission_id, payload, user, context), from_attributes=True)


@router.patch("/nursing-tasks/{task_id}", response_model=IPDNursingTaskRead, dependencies=[Depends(require_permissions("ipd.nursing_note.create"))])
def update_ipd_nursing_task(task_id: UUID, payload: IPDNursingTaskUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDNursingTaskRead:
    return IPDNursingTaskRead.model_validate(IPDService(db).update_nursing_task(task_id, payload, user, context), from_attributes=True)


@router.get("/admissions/{admission_id}/vitals-trends", response_model=list[IPDVitalsTrendRead], dependencies=[Depends(require_permissions("ipd.view"))])
def get_ipd_vitals_trends(admission_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[IPDVitalsTrendRead]:
    return IPDService(db).vitals_trends(admission_id, user)


@router.post("/admissions/{admission_id}/handovers", response_model=IPDHandoverRead, dependencies=[Depends(require_permissions("ipd.handover.create"))])
def create_ipd_handover(admission_id: UUID, payload: IPDHandoverCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDHandoverRead:
    return IPDHandoverRead.model_validate(IPDService(db).create_handover(admission_id, payload, user, context), from_attributes=True)


@router.get("/handovers", response_model=list[IPDHandoverBoardRead], dependencies=[Depends(require_permissions("ipd.view"))])
def list_ipd_handovers(
    status: str | None = None,
    ward_name: str | None = None,
    q: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[IPDHandoverBoardRead]:
    service = IPDService(db)
    return [IPDHandoverBoardRead.model_validate(service.handover_board_payload(item)) for item in service.list_handovers(user, status=status, ward_name=ward_name, q=q)]


@router.post("/handovers/{handover_id}/acknowledge", response_model=IPDHandoverRead, dependencies=[Depends(require_permissions("ipd.handover.acknowledge"))])
def acknowledge_ipd_handover(handover_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDHandoverRead:
    return IPDHandoverRead.model_validate(IPDService(db).acknowledge_handover(handover_id, user, context), from_attributes=True)


@router.post("/admissions/{admission_id}/discharge-plan", response_model=IPDAdmissionRead, dependencies=[Depends(require_permissions("ipd.discharge.request"))])
def plan_ipd_discharge(admission_id: UUID, status: str = "requested", context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)) -> IPDAdmissionRead:
    service = IPDService(db)
    admission = service.plan_discharge(admission_id, user, context, status=status)
    return IPDAdmissionRead.model_validate(service._admission_payload(admission))
