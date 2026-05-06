from datetime import UTC, datetime
from types import SimpleNamespace
from urllib import request
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models.radiology import PACSLink, RadiologyOrder, RadiologyReport, RadiologyReportSection
from app.models.user import User
from app.modules.audit.service import AuditService
from app.modules.opd.repository import OPDRepository
from app.modules.radiology.pacs_service import OrthancPACSService
from app.modules.radiology.repository import RadiologyRepository
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
from app.utils.enums import AuditAction


class RadiologyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.legacy_repository = OPDRepository(db)
        self.repository = RadiologyRepository(db)
        self.settings = get_settings()

    def list_simulator_machines(self) -> list[RadiologySimulatorMachineRead]:
        return [
            RadiologySimulatorMachineRead(
                code="XRAY_DR_01",
                name="Shimadzu DR Room 1",
                modality="CR/DR",
                status="online",
                sample_source="Chest X-Ray demo image",
            ),
            RadiologySimulatorMachineRead(
                code="CT_16SLICE_01",
                name="Siemens CT 16-Slice",
                modality="CT",
                status="online",
                sample_source="CT demo image",
            ),
            RadiologySimulatorMachineRead(
                code="USG_01",
                name="GE Voluson USG",
                modality="US",
                status="online",
                sample_source="Ultrasound demo image",
            ),
        ]

    def list_worklist(self, actor: User) -> list[ClinicalInvestigationWorkItemRead]:
        new_orders = self.repository.list_orders(actor.branch_id)
        legacy_orders = self.legacy_repository.list_investigation_orders("radiology", actor.branch_id)
        # Exclude legacy orders that are already linked to new orders
        linked_legacy_ids = {o.radiology_order_id for o in legacy_orders if o.radiology_order_id}
        legacy_orders = [o for o in legacy_orders if o.id not in linked_legacy_ids]
        new_items = [self._serialize_new(order) for order in new_orders]
        legacy_items = [self._serialize_legacy(order) for order in legacy_orders]
        return sorted(new_items + legacy_items, key=lambda x: (x.visit_date, x.order_id), reverse=True)

    def get_summary(self, actor: User) -> RadiologySummaryRead:
        new_counts = self.repository.get_summary_counts(actor.branch_id)
        legacy_items = self.legacy_repository.list_investigation_orders("radiology", actor.branch_id)
        linked_legacy_ids = {o.radiology_order_id for o in legacy_items if o.radiology_order_id}
        legacy_items = [o for o in legacy_items if o.id not in linked_legacy_ids]
        return RadiologySummaryRead(
            total_orders=new_counts["total_orders"] + len(legacy_items),
            pending_orders=new_counts["pending_orders"] + len([i for i in legacy_items if i.status == "pending"]),
            ready_orders=new_counts["collected_orders"] + len([i for i in legacy_items if i.status == "collected"]),
            in_progress_orders=new_counts["in_progress_orders"] + len([i for i in legacy_items if i.status == "in_progress"]),
            completed_orders=new_counts["completed_orders"] + len([i for i in legacy_items if i.status == "completed"]),
            verified_orders=new_counts["verified_orders"] + len([i for i in legacy_items if i.status == "verified"]),
        )

    def update_result(self, order_id, payload: ClinicalInvestigationResultUpdate, actor: User, context: dict[str, str | None]) -> ClinicalInvestigationWorkItemRead:
        # Try new table first
        rad_order = self.repository.get_order(order_id)
        if rad_order:
            if actor.branch_id and rad_order.branch_id and actor.branch_id != rad_order.branch_id:
                raise AppException(403, "forbidden", "Radiology order belongs to a different branch")
            rad_order.status = payload.status
            if payload.status in {"collected", "in_progress", "completed", "verified"} and not rad_order.performed_at:
                rad_order.performed_at = datetime.now(UTC)
                rad_order.performed_by_user_id = actor.id
            if payload.status in {"completed", "verified"}:
                rad_order.completed_at = rad_order.completed_at or datetime.now(UTC)
                rad_order.completed_by_user_id = actor.id
            else:
                rad_order.completed_at = None
                rad_order.completed_by_user_id = None
            if payload.status == "verified":
                rad_order.verified_at = datetime.now(UTC)
                rad_order.verified_by_user_id = actor.id
            else:
                rad_order.verified_at = None
                rad_order.verified_by_user_id = None
            rad_order.updated_by = actor.id
            AuditService(self.db).log(
                user_id=actor.id,
                action=AuditAction.OPD_INVESTIGATION_RESULT_UPDATE,
                module="radiology",
                entity_type="radiology_order",
                entity_id=str(rad_order.id),
                detail={"service_area": "radiology", "status": payload.status, "order_number": rad_order.order_number},
                context=context,
            )
            self.db.commit()
            self.db.refresh(rad_order)
            return self._serialize_new(rad_order)

        # Fallback to legacy
        order = self.legacy_repository.get_order(order_id)
        if not order or order.order_type != "investigation" or order.service_area != "radiology":
            raise AppException(404, "radiology_order_not_found", "Radiology work item not found")
        if actor.branch_id and order.visit.branch_id and actor.branch_id != order.visit.branch_id:
            raise AppException(403, "forbidden", "Radiology order belongs to a different branch")

        order.status = payload.status
        order.sample_note = payload.sample_note
        order.result_text = payload.result_text
        if payload.status in {"collected", "in_progress", "completed", "verified"} and not order.sample_collected_at:
            order.sample_collected_at = datetime.now(UTC)
            order.sample_collected_by_user_id = actor.id
        if payload.status in {"completed", "verified"}:
            order.completed_at = order.completed_at or datetime.now(UTC)
            order.completed_by_user_id = actor.id
        else:
            order.completed_at = None
            order.completed_by_user_id = None
        if payload.status == "verified":
            order.verified_at = datetime.now(UTC)
            order.verified_by_user_id = actor.id
        else:
            order.verified_at = None
            order.verified_by_user_id = None
        order.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_INVESTIGATION_RESULT_UPDATE,
            module="radiology",
            entity_type="opd_visit_order",
            entity_id=str(order.id),
            detail={"service_area": "radiology", "status": payload.status, "visit_number": order.visit.visit_number},
            context=context,
        )
        self.db.commit()
        self.db.refresh(order)
        return self._serialize_legacy(order)

    def create_order(self, payload: RadiologyOrderCreate, actor: User, context: dict[str, str | None]) -> RadiologyOrderRead:
        order = RadiologyOrder(
            id=uuid4(),
            branch_id=actor.branch_id,
            patient_id=payload.patient_id,
            visit_id=payload.visit_id,
            order_number=f"RAD-{datetime.now(UTC).strftime('%y%m%d%H%M%S')}",
            modality=payload.modality,
            study_description=payload.study_description,
            body_part=payload.body_part,
            status="pending_study",
            priority=payload.priority,
            note=payload.note,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_order(order)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_INVESTIGATION_RESULT_UPDATE,
            module="radiology",
            entity_type="radiology_order",
            entity_id=str(order.id),
            detail={"status": order.status, "order_number": order.order_number},
            context=context,
        )
        self.db.commit()
        return RadiologyOrderRead.model_validate(order)

    def link_pacs_study(self, payload: PACSLinkCreate, actor: User | None, context: dict[str, str | None]) -> PACSUploadResponse:
        resolved_actor = actor or self._resolve_machine_actor()
        order = self.repository.get_order(payload.order_id)
        if not order:
            raise AppException(404, "radiology_order_not_found", "Radiology order not found")
        viewer_url = payload.viewer_url or self._build_viewer_url(payload.study_uid, payload.orthanc_study_id)
        link = order.pacs_links[0] if order.pacs_links else None
        if link:
            link.study_uid = payload.study_uid
            link.orthanc_study_id = payload.orthanc_study_id
            link.accession_number = payload.accession_number
            link.dicom_patient_id = payload.dicom_patient_id
            link.series_uid = payload.series_uid
            link.viewer_url = viewer_url
            link.status = payload.status
            link.updated_by = resolved_actor.id
        else:
            link = self._new_pacs_link(order.id, payload, viewer_url, resolved_actor.id)
            self.repository.create_pacs_link(link)
        order.status = "study_uploaded"
        order.updated_by = resolved_actor.id
        AuditService(self.db).log(
            user_id=resolved_actor.id,
            action=AuditAction.OPD_INVESTIGATION_RESULT_UPDATE,
            module="radiology",
            entity_type="pacs_link",
            entity_id=str(link.id),
            detail={"order_id": str(order.id), "status": link.status},
            context=context,
        )
        self.db.commit()
        self.db.refresh(link)
        return PACSUploadResponse(order_id=order.id, pacs_link=link)

    def upload_dicom(self, order_id: UUID, content: bytes, actor: User | None, context: dict[str, str | None]) -> PACSUploadResponse:
        order = self.repository.get_order(order_id)
        if not order:
            raise AppException(404, "radiology_order_not_found", "Radiology order not found")
        pacs = OrthancPACSService()
        upload_result = pacs.upload_instance(content)
        orthanc_study_id = upload_result.get("ParentStudy")
        if not orthanc_study_id:
            raise AppException(502, "orthanc_upload_failed", "Orthanc did not return a study id")
        study = pacs.get_study(orthanc_study_id)
        main_tags = study.get("MainDicomTags", {})
        study_uid = main_tags.get("StudyInstanceUID")
        if not study_uid:
            raise AppException(502, "orthanc_missing_study_uid", "StudyInstanceUID is missing from Orthanc response")
        payload = PACSLinkCreate(
            order_id=order.id,
            study_uid=study_uid,
            orthanc_study_id=orthanc_study_id,
            accession_number=main_tags.get("AccessionNumber"),
            dicom_patient_id=main_tags.get("PatientID"),
            status="study_uploaded",
        )
        return self.link_pacs_study(payload, actor, context)

    def add_report(self, payload: RadiologyReportUpsert, actor: User, context: dict[str, str | None]) -> RadiologyOrderRead:
        order = self.repository.get_order(payload.order_id)
        if not order:
            raise AppException(404, "radiology_order_not_found", "Radiology order not found")
        report = order.reports[0] if order.reports else None
        if report is None:
            report = RadiologyReport(
                id=uuid4(),
                order_id=order.id,
                report_number=f"RPT-{datetime.now(UTC).strftime('%y%m%d%H%M%S')}",
                status="draft",
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.repository.create_report(report)
        report.overall_findings = payload.findings
        report.impression = payload.impression
        report.recommendation = payload.recommendation
        report.status = "final"
        report.updated_by = actor.id
        report.reviewed_at = datetime.now(UTC)
        report.reviewed_by_user_id = actor.id
        if report.sections:
            findings_section = report.sections[0]
            findings_section.content = payload.findings
            findings_section.updated_by = actor.id
        else:
            self.repository.create_report_section(
                RadiologyReportSection(
                    id=uuid4(),
                    report_id=report.id,
                    section_name="Findings",
                    content=payload.findings,
                    display_order=1,
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )
        order.status = "report_completed"
        order.completed_at = datetime.now(UTC)
        order.completed_by_user_id = actor.id
        order.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_INVESTIGATION_RESULT_UPDATE,
            module="radiology",
            entity_type="radiology_report",
            entity_id=str(report.id),
            detail={"order_id": str(order.id), "status": order.status},
            context=context,
        )
        self.db.commit()
        self.db.refresh(order)
        return RadiologyOrderRead.model_validate(order)

    def mark_completed(self, order_id: UUID, actor: User, context: dict[str, str | None]) -> RadiologyOrderRead:
        order = self.repository.get_order(order_id)
        if not order:
            raise AppException(404, "radiology_order_not_found", "Radiology order not found")
        order.status = "verified"
        order.verified_at = datetime.now(UTC)
        order.verified_by_user_id = actor.id
        order.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_INVESTIGATION_RESULT_UPDATE,
            module="radiology",
            entity_type="radiology_order",
            entity_id=str(order.id),
            detail={"status": order.status},
            context=context,
        )
        self.db.commit()
        self.db.refresh(order)
        return RadiologyOrderRead.model_validate(order)

    def get_viewer(self, order_id: UUID, actor: User) -> RadiologyViewerRead:
        order = self.repository.get_order(order_id)
        if not order:
            raise AppException(404, "radiology_order_not_found", "Radiology order not found")
        if actor.branch_id and order.branch_id and actor.branch_id != order.branch_id:
            raise AppException(403, "forbidden", "Radiology order belongs to a different branch")
        pacs_link = order.pacs_links[0] if order.pacs_links else None
        if not pacs_link:
            raise AppException(404, "study_not_uploaded", "No PACS study has been linked yet")
        fresh_viewer_url = self._build_viewer_url(pacs_link.study_uid, pacs_link.orthanc_study_id)
        if pacs_link.viewer_url != fresh_viewer_url:
            pacs_link.viewer_url = fresh_viewer_url
            pacs_link.updated_by = actor.id
            self.db.commit()
        return RadiologyViewerRead(
            order_id=order.id,
            study_uid=pacs_link.study_uid,
            viewer_url=fresh_viewer_url,
        )

    def simulate_machine_feed(
        self,
        order_id: UUID,
        payload: RadiologySimulatorFeedRequest,
        actor: User,
        context: dict[str, str | None],
    ) -> RadiologySimulatorFeedResponse:
        order = self.repository.get_order(order_id)
        if not order:
            raise AppException(404, "radiology_order_not_found", "Radiology order not found")
        machines = {machine.code: machine for machine in self.list_simulator_machines()}
        machine = machines.get(payload.machine_code)
        if not machine:
            raise AppException(404, "radiology_machine_not_found", "Simulator machine not found")

        url = self._machine_sample_url(machine.code)
        dicom_bytes = self._download_bytes(url)
        ingest_response = self.ingest_machine_dicom(
            order_id=order_id,
            machine_code=machine.code,
            content=dicom_bytes,
            note=payload.note,
            context=context,
        )

        if payload.note:
            order = self.repository.get_order(order_id)
            if order:
                order.note = payload.note.strip()
                order.updated_by = actor.id
                self.db.commit()

        self.update_result(
            order_id,
            ClinicalInvestigationResultUpdate(
                status="in_progress",
                sample_note=payload.note.strip() if payload.note else None,
                result_text=order.reports[0].overall_findings if order and order.reports else None,
            ),
            actor,
            context,
        )

        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_INVESTIGATION_RESULT_UPDATE,
            module="radiology",
            entity_type="pacs_simulator_feed",
            entity_id=str(order_id),
            detail={"machine_code": machine.code, "study_uid": ingest_response.study_uid},
            context=context,
        )

        return RadiologySimulatorFeedResponse(
            order_id=order_id,
            machine_code=machine.code,
            machine_name=machine.name,
            study_uid=ingest_response.study_uid,
            orthanc_study_id=None,
            viewer_url=ingest_response.viewer_url,
            note=payload.note.strip() if payload.note else None,
        )

    def ingest_machine_dicom(
        self,
        order_id: UUID,
        machine_code: str,
        content: bytes,
        note: str | None,
        context: dict[str, str | None],
    ) -> RadiologyMachineIngestResponse:
        upload_response = self.upload_dicom(order_id, content, actor=None, context=context)
        if note:
            order = self.repository.get_order(order_id)
            if order:
                actor = self._resolve_machine_actor()
                order.note = note.strip()
                order.updated_by = actor.id
                self.db.commit()
        return RadiologyMachineIngestResponse(
            order_id=order_id,
            machine_code=machine_code,
            study_uid=upload_response.pacs_link.study_uid,
            viewer_url=upload_response.pacs_link.viewer_url or self._build_viewer_url(upload_response.pacs_link.study_uid, upload_response.pacs_link.orthanc_study_id),
            note=note.strip() if note else None,
        )

    def _serialize_new(self, order: RadiologyOrder) -> ClinicalInvestigationWorkItemRead:
        visit = order.visit
        patient = order.patient
        report = order.reports[0] if order.reports else None
        pacs_link = order.pacs_links[0] if order.pacs_links else None
        return ClinicalInvestigationWorkItemRead(
            order_id=order.id,
            visit_id=visit.id if visit else order.visit_id,
            visit_number=visit.visit_number if visit else "",
            visit_date=visit.visit_date if visit else datetime.now(UTC).date(),
            patient_id=patient.id if patient else order.patient_id,
            patient_number=patient.patient_number if patient else "",
            patient_name=f"{patient.first_name} {patient.last_name}" if patient else "",
            consulting_doctor_name=visit.consulting_doctor_name if visit else "",
            service_area="radiology",
            item_name=order.study_description,
            room_number=None,
            quantity=1,
            instructions=None,
            chief_complaint=visit.chief_complaint if visit else None,
            diagnosis=(visit.final_diagnosis or visit.provisional_diagnosis) if visit else None,
            status=order.status,
            sample_note=None,
            sample_collected_at=order.performed_at,
            result_text=report.overall_findings if report else None,
            completed_at=order.completed_at,
            verified_at=order.verified_at,
            has_pacs_link=bool(pacs_link and pacs_link.study_uid),
            pacs_study_uid=pacs_link.study_uid if pacs_link else None,
            lab_order_id=None,
            radiology_order_id=order.id,
        )

    def _new_pacs_link(self, order_id: UUID, payload: PACSLinkCreate, viewer_url: str, user_id: UUID) -> PACSLink:
        return PACSLink(
            id=uuid4(),
            order_id=order_id,
            study_uid=payload.study_uid,
            orthanc_study_id=payload.orthanc_study_id,
            accession_number=payload.accession_number,
            dicom_patient_id=payload.dicom_patient_id,
            series_uid=payload.series_uid,
            viewer_url=viewer_url,
            pacs_provider="orthanc",
            status=payload.status,
            created_by=user_id,
            updated_by=user_id,
        )

    def _build_viewer_url(self, study_uid: str, orthanc_study_id: str | None = None) -> str:
        return OrthancPACSService().build_orthanc_viewer_url(orthanc_study_id=orthanc_study_id, study_uid=study_uid)

    @staticmethod
    def _machine_sample_url(machine_code: str) -> str:
        mapping = {
            "XRAY_DR_01": "https://raw.githubusercontent.com/pydicom/pydicom-data/master/data_store/data/SC_rgb.dcm",
            "CT_16SLICE_01": "https://raw.githubusercontent.com/pydicom/pydicom-data/master/data_store/data/emri_small.dcm",
            "USG_01": "https://raw.githubusercontent.com/pydicom/pydicom-data/master/data_store/data/US1_UNCR.dcm",
        }
        return mapping.get(machine_code, mapping["XRAY_DR_01"])

    @staticmethod
    def _download_bytes(url: str) -> bytes:
        with request.urlopen(url, timeout=30) as response:
            return response.read()

    def _resolve_machine_actor(self) -> User:
        user = self.db.execute(select(User).where(User.is_active.is_(True)).order_by(User.created_at.asc())).scalars().first()
        if not user:
            raise AppException(500, "machine_actor_not_found", "No active user found for machine integration")
        return SimpleNamespace(id=user.id, branch_id=None)  # type: ignore[return-value]

    def _serialize_legacy(self, order) -> ClinicalInvestigationWorkItemRead:
        return ClinicalInvestigationWorkItemRead(
            order_id=order.id,
            visit_id=order.visit_id,
            visit_number=order.visit.visit_number,
            visit_date=order.visit.visit_date,
            patient_id=order.visit.patient_id,
            patient_number=order.visit.patient.patient_number,
            patient_name=f"{order.visit.patient.first_name} {order.visit.patient.last_name}",
            consulting_doctor_name=order.visit.consulting_doctor_name,
            service_area=order.service_area or "radiology",
            item_name=order.item_name,
            room_number=order.room_number,
            quantity=order.quantity,
            instructions=order.instructions,
            chief_complaint=order.visit.chief_complaint,
            diagnosis=order.visit.final_diagnosis or order.visit.provisional_diagnosis,
            status=order.status,
            sample_note=order.sample_note,
            sample_collected_at=order.sample_collected_at,
            result_text=order.result_text,
            completed_at=order.completed_at,
            verified_at=order.verified_at,
            has_pacs_link=False,
            pacs_study_uid=None,
            lab_order_id=order.lab_order_id,
            radiology_order_id=order.radiology_order_id,
        )
