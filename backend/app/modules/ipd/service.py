from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.configuration import ConfigurationProfile
from app.models.encounter import (
    IPDAdmission,
    IPDAdmissionMovement,
    IPDBed,
    IPDClinicalNote,
    IPDHandover,
    IPDMedicationAdministration,
    IPDNursingNote,
    IPDNursingTask,
    IPDOrder,
    IPDStaffAssignment,
    IPDTimelineEvent,
)
from app.models.hr import HREmployee, HRDutyRoster, HRLeaveRequest
from app.models.laboratory import LabOrder, LabOrderItem
from app.models.radiology import RadiologyOrder
from app.models.role import Role
from app.models.user import User
from app.modules.access_scope.service import AccessScopeService
from app.modules.audit.service import AuditService
from app.modules.auth.service import AuthService
from app.modules.ipd.repository import IPDRepository
from app.modules.patients.repository import PatientsRepository
from app.modules.users.repository import UsersRepository
from app.schemas.encounter import (
    IPDAdmissionCreate,
    IPDAdmissionRead,
    IPDBedBoardRow,
    IPDBedCreate,
    IPDClinicalNoteCreate,
    IPDDischarge,
    IPDHandoverCreate,
    IPDMedicationAdministrationCreate,
    IPDNursingNoteCreate,
    IPDNursingTaskCreate,
    IPDNursingTaskUpdate,
    IPDOrderCreate,
    IPDOrderGroupRead,
    IPDOrderStatusUpdate,
    IPDPatientWorkspace,
    IPDReportSummary,
    IPDDischargeReadiness,
    IPDSettingsRead,
    IPDSettingsUpdate,
    IPDShiftCoverageRead,
    IPDStaffAssignmentCreate,
    IPDStaffAvailabilityRead,
    IPDTransfer,
    IPDSummary,
    IPDVitalsTrendRead,
)
from app.utils.enums import AuditAction


class IPDService:
    DOCTOR_ASSIGNMENT_TYPES = {"admitting_doctor", "primary_consultant", "duty_doctor", "specialist_consultant", "on_call_doctor"}
    NURSE_ASSIGNMENT_TYPES = {"primary_nurse", "duty_nurse"}
    SETTINGS_PROFILE_TYPE = "ipd_settings"
    SETTINGS_CODE = "default"

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = IPDRepository(db)
        self.patients = PatientsRepository(db)
        self.users = UsersRepository(db)
        self.scopes = AccessScopeService(db)

    def list_admissions(self, actor: User) -> list[IPDAdmission]:
        return [admission for admission in self.repository.list_admissions(actor.branch_id) if self._admission_in_scope(actor, admission)]

    def list_beds(self, actor: User) -> list[IPDBed]:
        beds = self.repository.list_beds(actor.branch_id)
        if self.scopes.has_unrestricted_access(actor, module="ipd", scope_type="ward"):
            return beds
        wards = self.scopes.scope_values(actor, "ward", module="ipd")
        if not wards:
            return beds
        return [bed for bed in beds if bed.ward_name.lower() in wards]

    def bed_board(
        self,
        actor: User,
        *,
        ward_name: str | None = None,
        room_type: str | None = None,
        bed_type: str | None = None,
        department_name: str | None = None,
        status: str | None = None,
    ) -> list[IPDBedBoardRow]:
        admissions = [item for item in self.repository.list_admissions(actor.branch_id) if item.status != "discharged" and self._admission_in_scope(actor, item)]
        admission_by_bed = {item.bed_id: item for item in admissions if item.bed_id}
        rows: list[IPDBedBoardRow] = []
        now = datetime.now(UTC)
        for bed in self.list_beds(actor):
            admission = admission_by_bed.get(bed.id)
            board_status = bed.status
            if admission and admission.discharge_status in {"requested", "planned", "summary_drafted", "ready"}:
                board_status = "discharge_pending"
            elif admission:
                board_status = "occupied"
            doctor = admission.attending_doctor_name if admission else None
            nurse = admission.assigned_nurse.full_name if admission and admission.assigned_nurse else None
            row = IPDBedBoardRow(
                bed_id=bed.id,
                ward_name=bed.ward_name,
                room_type=bed.bed_type,
                bed_number=bed.bed_number,
                bed_type=bed.bed_type,
                daily_rate=bed.daily_rate,
                bed_status=bed.status,
                board_status=board_status,
                patient_id=admission.patient_id if admission else None,
                patient_name=f"{admission.patient.first_name} {admission.patient.last_name}".strip() if admission and admission.patient else None,
                patient_number=admission.patient.patient_number if admission and admission.patient else None,
                admission_id=admission.id if admission else None,
                admission_number=admission.admission_number if admission else None,
                department_name=admission.department_name if admission else None,
                doctor_name=doctor,
                nurse_name=nurse,
                admitted_at=admission.admitted_at if admission else None,
                discharge_status=admission.discharge_status if admission else None,
                billing_status=admission.billing_status if admission else None,
                occupancy_hours=Decimal(str(round(((now - admission.admitted_at).total_seconds() / 3600), 2))) if admission else Decimal("0"),
            )
            if ward_name and row.ward_name != ward_name:
                continue
            if room_type and row.room_type != room_type:
                continue
            if bed_type and row.bed_type != bed_type:
                continue
            if department_name and row.department_name != department_name:
                continue
            if status and row.board_status != status and row.bed_status != status:
                continue
            rows.append(row)
        return rows

    def get_settings(self, actor: User) -> IPDSettingsRead:
        profile = self._get_or_create_settings_profile(actor)
        return IPDSettingsRead(id=profile.id, updated_at=profile.updated_at, **self._settings_payload(profile))

    def update_settings(self, payload: IPDSettingsUpdate, actor: User, context: dict[str, str | None]) -> IPDSettingsRead:
        profile = self._get_or_create_settings_profile(actor)
        profile.payload = payload.model_dump(mode="json")
        profile.name = "Default IPD Settings"
        profile.description = "Branch-level IPD workflow, bed, assignment, handover, documentation, and discharge configuration."
        profile.updated_by = actor.id
        self.db.commit()
        self.db.refresh(profile)
        return IPDSettingsRead(id=profile.id, updated_at=profile.updated_at, **self._settings_payload(profile))

    def get_admission(self, admission_id, actor: User) -> IPDAdmission:
        admission = self.repository.get_admission(admission_id)
        if not admission:
            raise AppException(404, "ipd_admission_not_found", "IPD admission not found")
        if actor.branch_id and admission.branch_id and actor.branch_id != admission.branch_id:
            raise AppException(403, "forbidden", "IPD admission belongs to a different branch")
        self._assert_admission_scope(actor, admission)
        return admission

    def get_summary(self, actor: User) -> IPDSummary:
        admissions = self.list_admissions(actor)
        return IPDSummary(
            total_admissions=len(admissions),
            active_admissions=sum(1 for admission in admissions if admission.status == "admitted"),
            discharged_admissions=sum(1 for admission in admissions if admission.status == "discharged"),
            occupied_beds=sum(1 for admission in admissions if admission.status == "admitted"),
            pending_orders=sum(1 for admission in admissions for order in admission.orders if order.status not in {"completed", "verified", "cancelled"}),
            pending_handovers=sum(1 for admission in admissions for handover in admission.handovers if handover.status == "pending_ack"),
            discharge_planned=sum(1 for admission in admissions if admission.discharge_status in {"requested", "planned", "summary_drafted", "ready"}),
        )

    def create_admission(self, payload: IPDAdmissionCreate, actor: User, context: dict[str, str | None]) -> IPDAdmission:
        settings = self._settings(actor)
        self._validate_required_fields(payload.model_dump(), settings.required_admission_fields, "admission")
        patient = self.patients.get_patient(payload.patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")
        active_existing = self.db.scalar(
            select(IPDAdmission.id).where(
                IPDAdmission.patient_id == patient.id,
                IPDAdmission.status != "discharged",
                IPDAdmission.is_active.is_(True),
            )
        )
        if active_existing:
            raise AppException(409, "ipd_active_admission_exists", "Patient already has an active IPD admission")

        bed = None
        if payload.bed_id:
            bed = self.repository.get_bed(payload.bed_id)
            if not bed:
                raise AppException(404, "ipd_bed_not_found", "IPD bed not found")
            if actor.branch_id and bed.branch_id and actor.branch_id != bed.branch_id:
                raise AppException(403, "forbidden", "IPD bed belongs to a different branch")
            if bed.status != "available":
                raise AppException(409, "ipd_bed_unavailable", "Selected bed is not available")

        admission_data = payload.model_dump()
        attending_doctor = self._get_doctor(payload.doctor_user_id, actor) if payload.doctor_user_id else None
        admission_data["ward_name"] = bed.ward_name if bed else payload.ward_name
        admission_data["bed_number"] = bed.bed_number if bed else payload.bed_number
        admission_data["daily_charge"] = bed.daily_rate if bed and payload.daily_charge == 0 else payload.daily_charge
        admission_data.pop("doctor_user_id", None)

        admission = IPDAdmission(
            **admission_data,
            admission_number=self._generate_admission_number(actor.branch_id, settings.admission_number_format),
            branch_id=patient.branch_id or actor.branch_id,
            attending_doctor_user_id=attending_doctor.id if attending_doctor else None,
            admitted_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        if bed:
            bed.status = "occupied"
            bed.updated_by = actor.id
        self.repository.create_admission(admission)
        self.repository.create_movement(
            IPDAdmissionMovement(
                admission_id=admission.id,
                movement_type="admission",
                moved_at=admission.admitted_at,
                to_ward_name=admission.ward_name,
                to_bed_number=admission.bed_number,
                note=f"Admitted as {admission.admission_type}",
                moved_by_user_id=actor.id,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
        self._timeline(admission, actor, "admission", "Patient admitted", f"{admission.ward_name} / {admission.bed_number}", "ipd_admission", admission.id)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.IPD_ADMISSION_CREATE,
            module="ipd",
            entity_type="ipd_admission",
            entity_id=str(admission.id),
            detail={"admission_number": admission.admission_number, "patient_id": str(admission.patient_id)},
            context=context,
        )
        self.db.commit()
        self.db.refresh(admission)
        return self.repository.get_admission(admission.id) or admission

    def transfer(self, admission_id, payload: IPDTransfer, actor: User, context: dict[str, str | None]) -> IPDAdmission:
        admission = self.repository.get_admission(admission_id)
        if not admission:
            raise AppException(404, "ipd_admission_not_found", "IPD admission not found")
        if admission.status == "discharged":
            raise AppException(409, "ipd_already_discharged", "Discharged admissions cannot be transferred")
        if actor.branch_id and admission.branch_id and actor.branch_id != admission.branch_id:
            raise AppException(403, "forbidden", "IPD admission belongs to a different branch")

        previous_ward = admission.ward_name
        previous_bed_number = admission.bed_number
        new_bed = None
        if payload.bed_id:
            new_bed = self.repository.get_bed(payload.bed_id)
            if not new_bed:
                raise AppException(404, "ipd_bed_not_found", "IPD bed not found")
            if actor.branch_id and new_bed.branch_id and actor.branch_id != new_bed.branch_id:
                raise AppException(403, "forbidden", "IPD bed belongs to a different branch")
            if new_bed.status != "available":
                raise AppException(409, "ipd_bed_unavailable", "Selected bed is not available")
            admission.ward_name = new_bed.ward_name
            admission.bed_number = new_bed.bed_number
            admission.bed_id = new_bed.id
            if admission.bed:
                admission.bed.status = "cleaning"
                admission.bed.updated_by = actor.id
            new_bed.status = "occupied"
            new_bed.updated_by = actor.id
        else:
            admission.ward_name = payload.ward_name
            admission.bed_number = payload.bed_number
            admission.bed_id = None
            if admission.bed:
                admission.bed.status = "cleaning"
                admission.bed.updated_by = actor.id

        admission.updated_by = actor.id
        self.repository.create_movement(
            IPDAdmissionMovement(
                admission_id=admission.id,
                movement_type="transfer",
                moved_at=payload.transfer_time or datetime.now(UTC),
                from_ward_name=previous_ward,
                from_bed_number=previous_bed_number,
                to_ward_name=admission.ward_name,
                to_bed_number=admission.bed_number,
                transfer_reason=payload.transfer_reason,
                remarks=payload.remarks,
                requested_by_user_id=actor.id,
                approved_by_user_id=payload.approved_by_user_id or actor.id,
                approved_at=datetime.now(UTC),
                note=payload.note or payload.remarks or payload.transfer_reason,
                moved_by_user_id=actor.id,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
        self._timeline(admission, actor, "bed_transfer", "Bed transfer", f"{previous_ward} / {previous_bed_number} to {admission.ward_name} / {admission.bed_number}", "ipd_movement", admission.id)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.IPD_ADMISSION_TRANSFER,
            module="ipd",
            entity_type="ipd_admission",
            entity_id=str(admission.id),
            detail={"admission_number": admission.admission_number, "from_bed": previous_bed_number, "to_bed": admission.bed_number},
            context=context,
        )
        self.db.commit()
        self.db.refresh(admission)
        return self.repository.get_admission(admission.id) or admission

    def discharge(self, admission_id, payload: IPDDischarge, actor: User, context: dict[str, str | None]) -> IPDAdmission:
        admission = self.get_admission(admission_id, actor)
        if admission.status == "discharged":
            raise AppException(409, "ipd_already_discharged", "Patient already discharged")
        readiness = self.discharge_readiness(admission_id, actor, discharge_payload=payload)
        if not readiness.ready and not payload.allow_override:
            raise AppException(409, "ipd_discharge_not_ready", "Discharge is blocked: " + "; ".join(readiness.blockers))
        if payload.allow_override and not payload.override_reason:
            raise AppException(422, "ipd_discharge_override_reason_required", "Override reason is required for final discharge")

        admission.status = "discharged"
        admission.discharge_status = "completed"
        admission.discharge_condition = payload.discharge_condition
        admission.discharge_diagnosis = payload.discharge_diagnosis
        admission.discharge_summary = payload.discharge_summary
        admission.discharge_note = payload.discharge_note
        admission.discharged_at = datetime.now(UTC)
        admission.discharged_by_user_id = actor.id
        admission.updated_by = actor.id
        if admission.bed:
            admission.bed.status = "cleaning"
            admission.bed.updated_by = actor.id
        self.repository.create_movement(
            IPDAdmissionMovement(
                admission_id=admission.id,
                movement_type="discharge",
                moved_at=admission.discharged_at,
                from_ward_name=admission.ward_name,
                from_bed_number=admission.bed_number,
                remarks=payload.override_reason if payload.allow_override else None,
                note=payload.discharge_note or payload.discharge_summary,
                moved_by_user_id=actor.id,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
        self._timeline(admission, actor, "discharge", "Final discharge completed", payload.discharge_summary or payload.discharge_note, "ipd_admission", admission.id)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.IPD_ADMISSION_DISCHARGE,
            module="ipd",
            entity_type="ipd_admission",
            entity_id=str(admission.id),
            detail={"admission_number": admission.admission_number},
            context=context,
        )
        self.db.commit()
        self.db.refresh(admission)
        return admission

    def workspace(self, admission_id, actor: User) -> IPDPatientWorkspace:
        admission = self.get_admission(admission_id, actor)
        from app.schemas.encounter import IPDAdmissionRead

        return IPDPatientWorkspace(
            admission=IPDAdmissionRead.model_validate(self._admission_payload(admission)),
            assignments=admission.staff_assignments,
            clinical_notes=sorted(admission.clinical_notes, key=lambda item: item.authored_at, reverse=True),
            nursing_notes=sorted(admission.nursing_notes, key=lambda item: item.recorded_at, reverse=True),
            orders=sorted(admission.orders, key=lambda item: item.ordered_at, reverse=True),
            medications=sorted(admission.medication_administrations, key=lambda item: item.scheduled_at or item.created_at, reverse=True),
            nursing_tasks=sorted(admission.nursing_tasks, key=lambda item: item.due_at or item.created_at, reverse=True),
            handovers=sorted(admission.handovers, key=lambda item: item.handed_over_at, reverse=True),
            timeline=sorted(admission.timeline_events, key=lambda item: item.occurred_at, reverse=True),
        )

    def assign_staff(self, admission_id, payload: IPDStaffAssignmentCreate, actor: User, context: dict[str, str | None]) -> IPDStaffAssignment:
        admission = self.get_admission(admission_id, actor)
        self._validate_assignment_type(payload, actor)
        self._require_assignment_permission(payload.role_type, actor)
        staff = self.users.get_user(payload.staff_user_id)
        if not staff or not staff.is_active:
            raise AppException(404, "staff_not_found", "Staff user not found")
        if actor.branch_id and staff.branch_id and actor.branch_id != staff.branch_id:
            raise AppException(403, "forbidden", "Staff belongs to a different branch")
        availability = self._staff_availability(staff, payload.role_type, actor, ward_name=admission.ward_name, department_name=admission.department_name, shift_name=payload.shift_name)
        if not availability.can_assign and not payload.allow_override:
            raise AppException(409, "ipd_staff_not_available", "; ".join(availability.warnings) or "Selected staff is not available for this assignment")
        if payload.allow_override and not payload.override_reason:
            raise AppException(422, "ipd_assignment_override_reason_required", "Override reason is required when assigning unavailable or overloaded staff")

        now = datetime.now(UTC)
        for assignment in admission.staff_assignments:
            if assignment.role_type == payload.role_type and assignment.assignment_type == payload.assignment_type and not assignment.ended_at:
                assignment.ended_at = now
                assignment.changed_at = now
                assignment.changed_by_user_id = actor.id
                assignment.updated_by = actor.id
        assignment = IPDStaffAssignment(
            admission_id=admission.id,
            staff_user_id=staff.id,
            staff_name=staff.full_name,
            role_type=payload.role_type,
            assignment_type=payload.assignment_type,
            shift_name=payload.shift_name,
            ward_name=admission.ward_name,
            bed_number=admission.bed_number,
            department_name=admission.department_name,
            assigned_at=now,
            reason=payload.reason,
            override_reason=payload.override_reason if payload.allow_override else None,
            schedule_status="override" if payload.allow_override else ("on_duty" if availability.is_on_duty and not availability.is_on_leave else "unverified"),
            assigned_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        if payload.role_type == "doctor" and payload.assignment_type in {"admitting_doctor", "primary_consultant", "duty_doctor"}:
            admission.attending_doctor_user_id = staff.id
            admission.attending_doctor_name = staff.full_name
        elif payload.role_type == "nurse" and payload.assignment_type in {"primary_nurse", "duty_nurse"}:
            admission.assigned_nurse_user_id = staff.id
        admission.updated_by = actor.id
        self.repository.create(assignment)
        detail = f"{staff.full_name} as {payload.assignment_type}"
        if payload.shift_name:
            detail = f"{detail} ({payload.shift_name})"
        self._timeline(admission, actor, f"{payload.role_type}_assignment", f"{payload.role_type.title()} assigned", detail, "ipd_staff_assignment", assignment.id)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def list_staff_availability(
        self,
        actor: User,
        *,
        role_type: str,
        ward_name: str | None = None,
        department_name: str | None = None,
        shift_name: str | None = None,
        q: str | None = None,
    ) -> list[IPDStaffAvailabilityRead]:
        if role_type not in {"doctor", "nurse"}:
            raise AppException(422, "ipd_invalid_staff_role", "Staff role must be doctor or nurse")
        users = self._candidate_staff(actor, role_type, q=q)
        return [
            self._staff_availability(staff, role_type, actor, ward_name=ward_name, department_name=department_name, shift_name=shift_name)
            for staff in users
        ]

    def shift_coverage(self, actor: User, *, ward_name: str | None = None, shift_name: str | None = None) -> IPDShiftCoverageRead:
        current_shift = shift_name or self._current_shift_name()
        doctors = self.list_staff_availability(actor, role_type="doctor", ward_name=ward_name, shift_name=current_shift)
        nurses = self.list_staff_availability(actor, role_type="nurse", ward_name=ward_name, shift_name=current_shift)
        doctors_on_duty = len([item for item in doctors if item.is_on_duty and item.can_assign])
        nurses_on_duty = len([item for item in nurses if item.is_on_duty and item.can_assign])
        warnings = []
        if doctors and doctors_on_duty == 0:
            warnings.append("No available doctor coverage found for this shift")
        if nurses and nurses_on_duty == 0:
            warnings.append("No available nurse coverage found for this shift")
        return IPDShiftCoverageRead(
            shift_name=current_shift,
            ward_name=ward_name,
            doctors_on_duty=doctors_on_duty,
            nurses_on_duty=nurses_on_duty,
            doctor_gap=bool(doctors) and doctors_on_duty == 0,
            nurse_gap=bool(nurses) and nurses_on_duty == 0,
            warnings=warnings,
        )

    def create_clinical_note(self, admission_id, payload: IPDClinicalNoteCreate, actor: User, context: dict[str, str | None]) -> IPDClinicalNote:
        admission = self.get_admission(admission_id, actor)
        note = IPDClinicalNote(admission_id=admission.id, **payload.model_dump(), authored_by_user_id=actor.id, authored_at=datetime.now(UTC), created_by=actor.id, updated_by=actor.id)
        self.repository.create(note)
        if payload.diagnosis:
            admission.diagnosis = payload.diagnosis
        self._timeline(admission, actor, "clinical_note", payload.title or payload.note_type, payload.note, "ipd_clinical_note", note.id)
        self.db.commit()
        self.db.refresh(note)
        return note

    def create_nursing_note(self, admission_id, payload: IPDNursingNoteCreate, actor: User, context: dict[str, str | None]) -> IPDNursingNote:
        admission = self.get_admission(admission_id, actor)
        abnormal = self._abnormal_vitals(payload)
        note = IPDNursingNote(admission_id=admission.id, **payload.model_dump(), abnormal_alert=abnormal, recorded_by_user_id=actor.id, recorded_at=datetime.now(UTC), created_by=actor.id, updated_by=actor.id)
        self.repository.create(note)
        self._timeline(admission, actor, "nursing_note", "Nursing note / vitals", payload.note, "ipd_nursing_note", note.id)
        self.db.commit()
        self.db.refresh(note)
        return note

    def create_order(self, admission_id, payload: IPDOrderCreate, actor: User, context: dict[str, str | None]) -> IPDOrder:
        admission = self.get_admission(admission_id, actor)
        service_area = payload.service_area or self._service_area_for_order(payload.order_type)
        order_data = payload.model_dump()
        order_data["service_area"] = service_area
        order = IPDOrder(admission_id=admission.id, **order_data, status="active", ordered_by_user_id=actor.id, ordered_at=datetime.now(UTC), created_by=actor.id, updated_by=actor.id)
        self.repository.create(order)
        self._sync_downstream_order(admission, order, actor)
        self._generate_execution_items(admission, order, actor)
        self._timeline(admission, actor, f"{payload.order_type}_order", f"{payload.order_type.title()} order", payload.item_name, "ipd_order", order.id)
        self.db.commit()
        self.db.refresh(order)
        return order

    def update_order_status(self, admission_id, order_id, payload: IPDOrderStatusUpdate, actor: User, context: dict[str, str | None]) -> IPDOrder:
        admission = self.get_admission(admission_id, actor)
        order = next((item for item in admission.orders if item.id == order_id), None)
        if not order:
            raise AppException(404, "ipd_order_not_found", "IPD order not found")
        now = datetime.now(UTC)
        order.status = payload.status
        order.updated_by = actor.id
        if payload.status == "cancelled":
            order.cancelled_at = now
            order.cancelled_by_user_id = actor.id
        if payload.status == "discontinued":
            order.discontinued_at = now
            order.discontinued_by_user_id = actor.id
        self._timeline(admission, actor, "order_status", f"Order {payload.status}", payload.reason or order.item_name, "ipd_order", order.id)
        self.db.commit()
        self.db.refresh(order)
        return order

    def grouped_orders(self, admission_id, actor: User) -> list[IPDOrderGroupRead]:
        admission = self.get_admission(admission_id, actor)
        groups: dict[tuple[str, str], list[IPDOrder]] = {}
        for order in sorted(admission.orders, key=lambda item: item.ordered_at, reverse=True):
            groups.setdefault((order.order_type, order.status), []).append(order)
        return [IPDOrderGroupRead(order_type=key[0], status=key[1], orders=value) for key, value in sorted(groups.items())]

    def administer_medication(self, admission_id, payload: IPDMedicationAdministrationCreate, actor: User, context: dict[str, str | None]) -> IPDMedicationAdministration:
        admission = self.get_admission(admission_id, actor)
        if payload.status == "administered" and not payload.allow_duplicate:
            duplicate = self.db.scalar(
                select(IPDMedicationAdministration.id).where(
                    IPDMedicationAdministration.admission_id == admission.id,
                    IPDMedicationAdministration.order_id == payload.order_id,
                    IPDMedicationAdministration.medicine_name == payload.medicine_name,
                    IPDMedicationAdministration.scheduled_at == payload.scheduled_at,
                    IPDMedicationAdministration.status == "administered",
                    IPDMedicationAdministration.is_active.is_(True),
                )
            )
            if duplicate:
                raise AppException(409, "ipd_medication_duplicate", "This scheduled medicine has already been administered")
        administered_at = payload.administered_at or (datetime.now(UTC) if payload.status == "administered" else None)
        med = IPDMedicationAdministration(
            admission_id=admission.id,
            **payload.model_dump(exclude={"administered_at", "allow_duplicate"}),
            administered_at=administered_at,
            administered_by_user_id=actor.id if payload.status in {"administered", "skipped", "held", "delayed", "refused"} else None,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create(med)
        self._timeline(admission, actor, "medication", f"Medication {payload.status}", payload.medicine_name, "ipd_medication_administration", med.id)
        self.db.commit()
        self.db.refresh(med)
        return med

    def list_medication_schedule(self, actor: User, *, ward_name: str | None = None, nurse_user_id: UUID | None = None, shift_name: str | None = None, status: str | None = None) -> list[IPDMedicationAdministration]:
        stmt = select(IPDMedicationAdministration).join(IPDMedicationAdministration.admission).where(IPDAdmission.is_active.is_(True)).order_by(IPDMedicationAdministration.scheduled_at.asc().nulls_last())
        if actor.branch_id:
            stmt = stmt.where(IPDAdmission.branch_id == actor.branch_id)
        stmt = self._apply_admission_scope_filter(stmt, actor)
        if ward_name:
            stmt = stmt.where(IPDAdmission.ward_name == ward_name)
        if status:
            stmt = stmt.where(IPDMedicationAdministration.status == status)
        if nurse_user_id:
            stmt = stmt.where(IPDAdmission.assigned_nurse_user_id == nurse_user_id)
        items = list(self.db.scalars(stmt.limit(300)))
        if shift_name and shift_name != "unscheduled":
            items = [item for item in items if item.scheduled_at and self._shift_for_datetime(item.scheduled_at) == shift_name]
        elif shift_name == "unscheduled":
            items = [item for item in items if not item.scheduled_at]
        return items[:200]

    def create_nursing_task(self, admission_id, payload: IPDNursingTaskCreate, actor: User, context: dict[str, str | None]) -> IPDNursingTask:
        admission = self.get_admission(admission_id, actor)
        task = IPDNursingTask(admission_id=admission.id, ward_name=admission.ward_name, bed_number=admission.bed_number, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.repository.create(task)
        self._timeline(admission, actor, "nursing_task", "Nursing task created", task.title, "ipd_nursing_task", task.id)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_nursing_task(self, task_id, payload: IPDNursingTaskUpdate, actor: User, context: dict[str, str | None]) -> IPDNursingTask:
        task = self.db.get(IPDNursingTask, task_id)
        if not task:
            raise AppException(404, "ipd_nursing_task_not_found", "Nursing task not found")
        admission = self.get_admission(task.admission_id, actor)
        task.status = payload.status
        task.completion_note = payload.completion_note
        task.updated_by = actor.id
        if payload.status == "completed":
            task.completed_at = datetime.now(UTC)
            task.completed_by_user_id = actor.id
        self._timeline(admission, actor, "nursing_task_status", f"Nursing task {payload.status}", task.completion_note or task.title, "ipd_nursing_task", task.id)
        self.db.commit()
        self.db.refresh(task)
        return task

    def list_nursing_tasks(self, actor: User, *, ward_name: str | None = None, nurse_user_id: UUID | None = None, shift_name: str | None = None, status: str | None = None) -> list[IPDNursingTask]:
        stmt = select(IPDNursingTask).join(IPDNursingTask.admission).where(IPDAdmission.is_active.is_(True)).order_by(IPDNursingTask.due_at.asc().nulls_last(), IPDNursingTask.created_at.desc())
        if actor.branch_id:
            stmt = stmt.where(IPDAdmission.branch_id == actor.branch_id)
        stmt = self._apply_nursing_task_scope_filter(stmt, actor)
        if ward_name:
            stmt = stmt.where(IPDNursingTask.ward_name == ward_name)
        if nurse_user_id:
            stmt = stmt.where(IPDNursingTask.assigned_nurse_user_id == nurse_user_id)
        if shift_name:
            stmt = stmt.where(IPDNursingTask.shift_name == shift_name)
        if status:
            stmt = stmt.where(IPDNursingTask.status == status)
        return list(self.db.scalars(stmt.limit(200)))

    def vitals_trends(self, admission_id, actor: User) -> list[IPDVitalsTrendRead]:
        admission = self.get_admission(admission_id, actor)
        notes = sorted(admission.nursing_notes, key=lambda item: item.recorded_at)
        return [
            IPDVitalsTrendRead(
                recorded_at=item.recorded_at,
                temperature=item.temperature,
                pulse=item.pulse,
                respiratory_rate=item.respiratory_rate,
                systolic_bp=item.systolic_bp,
                diastolic_bp=item.diastolic_bp,
                spo2=item.spo2,
                pain_score=item.pain_score,
                glucose=item.glucose,
                abnormal_alert=item.abnormal_alert,
            )
            for item in notes
        ]

    def create_handover(self, admission_id, payload: IPDHandoverCreate, actor: User, context: dict[str, str | None]) -> IPDHandover:
        admission = self.get_admission(admission_id, actor)
        settings = self._settings(actor)
        self._validate_required_fields(payload.model_dump(), settings.required_handover_fields, "handover")
        handover = IPDHandover(admission_id=admission.id, **payload.model_dump(), sender_user_id=actor.id, handed_over_at=datetime.now(UTC), created_by=actor.id, updated_by=actor.id)
        self.repository.create(handover)
        self._timeline(admission, actor, "handover", "Duty handover", payload.summary, "ipd_handover", handover.id)
        self.db.commit()
        self.db.refresh(handover)
        return handover

    def list_handovers(self, actor: User, *, status: str | None = None, ward_name: str | None = None, q: str | None = None) -> list[IPDHandover]:
        stmt = (
            select(IPDHandover)
            .join(IPDHandover.admission)
            .options(selectinload(IPDHandover.admission).selectinload(IPDAdmission.patient))
            .where(IPDAdmission.is_active.is_(True))
            .order_by(IPDHandover.handed_over_at.desc())
        )
        if actor.branch_id:
            stmt = stmt.where(IPDAdmission.branch_id == actor.branch_id)
        stmt = self._apply_handover_scope_filter(stmt, actor)
        if status:
            stmt = stmt.where(IPDHandover.status == status)
        if ward_name:
            stmt = stmt.where(IPDAdmission.ward_name == ward_name)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(or_(IPDAdmission.admission_number.ilike(pattern), IPDHandover.summary.ilike(pattern), IPDHandover.pending_items.ilike(pattern)))
        return list(self.db.scalars(stmt.limit(100)))

    def acknowledge_handover(self, handover_id, actor: User, context: dict[str, str | None]) -> IPDHandover:
        handover = self.db.get(IPDHandover, handover_id)
        if not handover:
            raise AppException(404, "ipd_handover_not_found", "Handover not found")
        admission = self.get_admission(handover.admission_id, actor)
        handover.status = "acknowledged"
        handover.acknowledged_at = datetime.now(UTC)
        handover.receiver_user_id = handover.receiver_user_id or actor.id
        handover.updated_by = actor.id
        self._timeline(admission, actor, "handover_ack", "Handover acknowledged", handover.summary, "ipd_handover", handover.id)
        self.db.commit()
        self.db.refresh(handover)
        return handover

    def plan_discharge(self, admission_id, actor: User, context: dict[str, str | None], status: str = "requested") -> IPDAdmission:
        admission = self.get_admission(admission_id, actor)
        admission.discharge_status = status
        admission.status = "discharge_planned" if status in {"requested", "planned"} else admission.status
        admission.updated_by = actor.id
        self._timeline(admission, actor, "discharge_plan", f"Discharge {status}", None, "ipd_admission", admission.id)
        self.db.commit()
        self.db.refresh(admission)
        return admission

    def discharge_readiness(self, admission_id, actor: User, discharge_payload: IPDDischarge | None = None) -> IPDDischargeReadiness:
        admission = self.get_admission(admission_id, actor)
        settings = self._settings(actor)
        pending_lab = len([order for order in admission.orders if order.order_type == "lab" and order.status not in {"completed", "cancelled", "discontinued"}])
        pending_radiology = len([order for order in admission.orders if order.order_type == "radiology" and order.status not in {"completed", "cancelled", "discontinued"}])
        summary_text = discharge_payload.discharge_summary if discharge_payload else admission.discharge_summary
        payload_values = discharge_payload.model_dump() if discharge_payload else {
            "discharge_summary": admission.discharge_summary,
            "discharge_diagnosis": admission.discharge_diagnosis,
            "discharge_condition": admission.discharge_condition,
        }
        summary_missing = [field for field in settings.required_discharge_summary_fields if payload_values.get(field) in (None, "", [])]
        checks = [
            {"key": "doctor_approval", "label": "Doctor approval", "done": admission.discharge_status in {"approved", "ready", "completed"} or bool(summary_text)},
            {"key": "summary", "label": "Discharge summary", "done": not summary_missing},
            {"key": "billing", "label": "Billing clearance", "done": not settings.clearance_requirements.get("billing") or admission.billing_status == "cleared"},
            {"key": "pharmacy", "label": "Pharmacy clearance", "done": not settings.clearance_requirements.get("pharmacy") or admission.pharmacy_clearance_status == "cleared"},
            {"key": "lab", "label": "Lab clearance", "done": (not settings.clearance_requirements.get("lab") or admission.lab_clearance_status == "cleared") and pending_lab == 0},
            {"key": "radiology", "label": "Radiology clearance", "done": (not settings.clearance_requirements.get("radiology") or admission.radiology_clearance_status == "cleared") and pending_radiology == 0},
        ]
        blockers = [item["label"] for item in checks if not item["done"]]
        return IPDDischargeReadiness(
            admission_id=admission.id,
            admission_number=admission.admission_number,
            status=admission.discharge_status,
            ready=not blockers,
            checks=checks,
            blockers=blockers,
            discharge_summary_ready=not summary_missing,
            final_bill_url=f"/billing/create?patientId={admission.patient_id}&ipdAdmissionId={admission.id}&billingStage=final",
        )

    def report_summary(self, actor: User) -> IPDReportSummary:
        admissions = self.repository.list_admissions(actor.branch_id)
        beds = self.repository.list_beds(actor.branch_id)
        active = [item for item in admissions if item.status != "discharged"]
        discharged = [item for item in admissions if item.status == "discharged" and item.discharged_at]
        ward_counts: dict[str, int] = {}
        discharge_counts: dict[str, int] = {}
        department_flow: dict[str, dict[str, int]] = {}
        for admission in admissions:
            ward_counts[admission.ward_name] = ward_counts.get(admission.ward_name, 0) + (0 if admission.status == "discharged" else 1)
            discharge_counts[admission.discharge_status] = discharge_counts.get(admission.discharge_status, 0) + 1
            department = admission.department_name or "Unassigned"
            department_flow.setdefault(department, {"department": department, "admissions": 0, "discharges": 0})
            department_flow[department]["admissions"] += 1
            if admission.status == "discharged":
                department_flow[department]["discharges"] += 1
        los_days = Decimal("0")
        if discharged:
            total_days = sum((item.discharged_at - item.admitted_at).total_seconds() / 86400 for item in discharged)
            los_days = Decimal(str(round(total_days / len(discharged), 2)))
        transfers = [movement for admission in admissions for movement in admission.movements if movement.movement_type == "transfer"]
        return IPDReportSummary(
            bed_occupancy={"total_beds": len(beds), "occupied": len(active), "available": len([bed for bed in beds if bed.status == "available"]), "occupancy_percent": round((len(active) / len(beds)) * 100, 2) if beds else 0},
            ward_census=[{"ward": ward, "active": count} for ward, count in sorted(ward_counts.items())],
            transfer_history=sorted(transfers, key=lambda item: item.moved_at, reverse=True)[:100],
            average_length_of_stay_days=los_days,
            discharge_status=discharge_counts,
            pending_discharge=[IPDAdmissionRead.model_validate(self._admission_payload(item)) for item in active if item.discharge_status in {"requested", "planned", "summary_drafted", "ready"}],
            department_flow=list(department_flow.values()),
        )

    def create_bed(self, payload: IPDBedCreate, actor: User, context: dict[str, str | None]) -> IPDBed:
        settings = self._settings(actor)
        if settings.bed_types and payload.bed_type not in settings.bed_types:
            raise AppException(422, "ipd_invalid_bed_type", "Bed type is not enabled in IPD settings")
        existing = self.repository.get_bed_by_number(actor.branch_id, payload.ward_name, payload.bed_number)
        if existing:
            raise AppException(409, "ipd_bed_exists", "Ward and bed number already exist")

        bed = IPDBed(
            **payload.model_dump(),
            branch_id=actor.branch_id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_bed(bed)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.IPD_BED_CREATE,
            module="ipd",
            entity_type="ipd_bed",
            entity_id=str(bed.id),
            detail={"ward_name": bed.ward_name, "bed_number": bed.bed_number},
            context=context,
        )
        self.db.commit()
        self.db.refresh(bed)
        return bed

    def _timeline(self, admission: IPDAdmission, actor: User, event_type: str, title: str, detail: str | None, source_type: str | None, source_id) -> None:
        self.repository.create(
            IPDTimelineEvent(
                admission_id=admission.id,
                event_type=event_type,
                title=title,
                detail=detail,
                source_type=source_type,
                source_id=source_id,
                occurred_at=datetime.now(UTC),
                actor_user_id=actor.id,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )

    def _abnormal_vitals(self, payload: IPDNursingNoteCreate) -> bool:
        settings = self._default_settings_payload().get("vitals_config", {})
        temperature = settings.get("temperature", {})
        pulse = settings.get("pulse", {})
        spo2 = settings.get("spo2", {})
        return any(
            [
                payload.temperature is not None and (payload.temperature < Decimal(str(temperature.get("min", 35))) or payload.temperature > Decimal(str(temperature.get("max", 38)))),
                payload.pulse is not None and (payload.pulse < int(pulse.get("min", 50)) or payload.pulse > int(pulse.get("max", 120))),
                payload.respiratory_rate is not None and (payload.respiratory_rate < 10 or payload.respiratory_rate > 28),
                payload.systolic_bp is not None and (payload.systolic_bp < 90 or payload.systolic_bp > 180),
                payload.diastolic_bp is not None and (payload.diastolic_bp < 50 or payload.diastolic_bp > 110),
                payload.spo2 is not None and payload.spo2 < int(spo2.get("min", 92)),
                payload.pain_score is not None and payload.pain_score >= 7,
                payload.glucose is not None and (payload.glucose < Decimal("3.9") or payload.glucose > Decimal("11.1")),
            ]
        )

    def _service_area_for_order(self, order_type: str) -> str | None:
        if order_type == "medicine":
            return "pharmacy"
        if order_type == "lab":
            return "laboratory"
        if order_type == "radiology":
            return "radiology"
        return None

    def _sync_downstream_order(self, admission: IPDAdmission, order: IPDOrder, actor: User) -> None:
        if order.order_type == "lab":
            lab_order = LabOrder(
                id=uuid4(),
                branch_id=admission.branch_id or actor.branch_id,
                patient_id=admission.patient_id,
                admission_id=admission.id,
                order_number=f"LAB-IPD-{datetime.now(UTC).strftime('%y%m%d%H%M%S')}",
                status="pending",
                priority=order.priority,
                note=order.instructions,
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.repository.create(lab_order)
            self.repository.create(
                LabOrderItem(
                    order_id=lab_order.id,
                    test_name=order.item_name,
                    quantity=order.quantity,
                    status="ordered",
                    note=order.instructions,
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )
            order.lab_order_id = lab_order.id
        elif order.order_type == "radiology":
            radiology_order = RadiologyOrder(
                id=uuid4(),
                branch_id=admission.branch_id or actor.branch_id,
                patient_id=admission.patient_id,
                admission_id=admission.id,
                order_number=f"RAD-IPD-{datetime.now(UTC).strftime('%y%m%d%H%M%S')}",
                study_description=order.item_name,
                status="pending_study",
                priority=order.priority,
                scheduled_at=order.scheduled_at,
                note=order.instructions,
                created_by=actor.id,
                updated_by=actor.id,
            )
            self.repository.create(radiology_order)
            order.radiology_order_id = radiology_order.id

    def _generate_execution_items(self, admission: IPDAdmission, order: IPDOrder, actor: User) -> None:
        if order.order_type == "medicine":
            self.repository.create(
                IPDMedicationAdministration(
                    admission_id=admission.id,
                    order_id=order.id,
                    medicine_name=order.item_name,
                    dose=order.dose,
                    route=order.route,
                    frequency=order.frequency,
                    scheduled_at=order.scheduled_at,
                    status="due",
                    reason=order.instructions,
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )
            self._create_task_from_order(admission, order, actor, task_type="medication", title=f"Administer {order.item_name}")
        elif order.order_type in {"nursing", "monitoring", "procedure"}:
            task_type = "vitals_monitoring" if order.order_type == "monitoring" else order.order_type
            self._create_task_from_order(admission, order, actor, task_type=task_type, title=order.item_name)
        elif order.order_type == "lab":
            self._create_task_from_order(admission, order, actor, task_type="sample_collection", title=f"Collect sample: {order.item_name}")
        elif order.order_type == "diet":
            self._create_task_from_order(admission, order, actor, task_type="diet", title=f"Diet instruction: {order.item_name}")

    def _create_task_from_order(self, admission: IPDAdmission, order: IPDOrder, actor: User, *, task_type: str, title: str) -> None:
        self.repository.create(
            IPDNursingTask(
                admission_id=admission.id,
                order_id=order.id,
                assigned_nurse_user_id=admission.assigned_nurse_user_id,
                task_type=task_type,
                title=title,
                instructions=order.instructions,
                ward_name=admission.ward_name,
                bed_number=admission.bed_number,
                shift_name=self._current_shift_name(),
                due_at=order.scheduled_at,
                status="pending",
                created_by=actor.id,
                updated_by=actor.id,
            )
        )

    def _admission_payload(self, admission: IPDAdmission) -> dict:
        data = {column.name: getattr(admission, column.name) for column in admission.__table__.columns}
        data["patient"] = admission.patient
        data["doctor_user_id"] = admission.attending_doctor_user_id
        data["movements"] = admission.movements
        active_assignments = [assignment for assignment in admission.staff_assignments if not assignment.ended_at]
        data["active_doctors"] = [assignment for assignment in active_assignments if assignment.role_type == "doctor"]
        data["active_nurses"] = [assignment for assignment in active_assignments if assignment.role_type == "nurse"]
        data["current_shift"] = self._current_shift_name()
        data["handover_status"] = "pending_ack" if any(handover.status == "pending_ack" for handover in admission.handovers) else "clear"
        data["pending_orders"] = len([order for order in admission.orders if order.status not in {"completed", "verified", "cancelled"}])
        data["pending_handovers"] = len([handover for handover in admission.handovers if handover.status == "pending_ack"])
        data["due_medications"] = len([med for med in admission.medication_administrations if med.status == "due"])
        return data

    def handover_board_payload(self, handover: IPDHandover) -> dict:
        data = {column.name: getattr(handover, column.name) for column in handover.__table__.columns}
        admission = handover.admission
        data["admission_number"] = admission.admission_number if admission else None
        data["patient_name"] = f"{admission.patient.first_name} {admission.patient.last_name}".strip() if admission and admission.patient else None
        data["ward_name"] = admission.ward_name if admission else None
        data["bed_number"] = admission.bed_number if admission else None
        return data

    def _get_doctor(self, user_id, actor: User) -> User:
        doctor = self.users.get_user(user_id)
        if not doctor or not doctor.is_active:
            raise AppException(404, "doctor_not_found", "Doctor user not found")
        if actor.branch_id and doctor.branch_id and actor.branch_id != doctor.branch_id:
            raise AppException(403, "forbidden", "Doctor belongs to a different branch")
        if not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(400, "invalid_doctor_user", "Selected user is not configured as a doctor")
        return doctor

    def _validate_assignment_type(self, payload: IPDStaffAssignmentCreate, actor: User) -> None:
        settings = self._settings(actor)
        configured = settings.doctor_assignment_types if payload.role_type == "doctor" else settings.nurse_assignment_types
        allowed = set(configured) if configured else (self.DOCTOR_ASSIGNMENT_TYPES if payload.role_type == "doctor" else self.NURSE_ASSIGNMENT_TYPES)
        if payload.assignment_type not in allowed:
            raise AppException(422, "ipd_invalid_assignment_type", f"{payload.role_type.title()} assignment must be one of: {', '.join(sorted(allowed))}")

    def _require_assignment_permission(self, role_type: str, actor: User) -> None:
        permission = "ipd.assign_doctor" if role_type == "doctor" else "ipd.assign_nurse"
        if permission not in set(AuthService(self.db).get_effective_permissions(actor)):
            raise AppException(403, "forbidden", f"Missing permission: {permission}")

    def _candidate_staff(self, actor: User, role_type: str, *, q: str | None = None) -> list[User]:
        pattern = f"%{q}%" if q else None
        if role_type == "doctor":
            stmt = select(User).join(User.roles).where(User.is_active.is_(True), Role.is_doctor_role.is_(True))
        else:
            stmt = (
                select(User)
                .outerjoin(User.roles)
                .outerjoin(HREmployee, HREmployee.user_id == User.id)
                .where(
                    User.is_active.is_(True),
                    or_(
                        Role.code.ilike("%nurse%"),
                        Role.name.ilike("%nurse%"),
                        HREmployee.employee_category.ilike("%nurse%"),
                        HREmployee.specialization.ilike("%nurse%"),
                    ),
                )
            )
        if actor.branch_id:
            stmt = stmt.where(or_(User.branch_id == actor.branch_id, User.branch_id.is_(None)))
        if pattern:
            stmt = stmt.where(or_(User.full_name.ilike(pattern), User.username.ilike(pattern), User.email.ilike(pattern)))
        return list(self.db.scalars(stmt.options(selectinload(User.roles)).order_by(User.full_name.asc()).limit(100)).unique())

    def _staff_availability(self, staff: User, role_type: str, actor: User, *, ward_name: str | None, department_name: str | None, shift_name: str | None) -> IPDStaffAvailabilityRead:
        today = date.today()
        current_shift = shift_name or self._current_shift_name()
        employee = self.db.scalar(
            select(HREmployee)
            .options(selectinload(HREmployee.department))
            .where(HREmployee.user_id == staff.id, HREmployee.is_active.is_(True))
        )
        roster = None
        is_on_leave = False
        warnings: list[str] = []
        if employee:
            roster_stmt = (
                select(HRDutyRoster)
                .options(selectinload(HRDutyRoster.shift))
                .where(HRDutyRoster.employee_id == employee.id, HRDutyRoster.roster_date == today, HRDutyRoster.status.in_(["assigned", "approved", "completed"]))
            )
            rosters = list(self.db.scalars(roster_stmt))
            roster = next((item for item in rosters if item.shift and item.shift.shift_type == current_shift), None) or next((item for item in rosters if item.shift and item.shift.name.lower() == current_shift.lower()), None) or (rosters[0] if rosters else None)
            is_on_leave = bool(
                self.db.scalar(
                    select(HRLeaveRequest.id).where(
                        HRLeaveRequest.employee_id == employee.id,
                        HRLeaveRequest.status == "approved",
                        HRLeaveRequest.start_date <= today,
                        HRLeaveRequest.end_date >= today,
                    )
                )
            )
        active_load = self.db.scalar(
            select(func.count(IPDStaffAssignment.id)).where(
                IPDStaffAssignment.staff_user_id == staff.id,
                IPDStaffAssignment.role_type == role_type,
                IPDStaffAssignment.ended_at.is_(None),
                IPDStaffAssignment.is_active.is_(True),
            )
        ) or 0
        settings = self._settings(actor)
        max_load = settings.max_patient_load_doctor if role_type == "doctor" else settings.max_patient_load_nurse
        is_overloaded = active_load >= max_load
        is_on_duty = True
        roster_status = roster.status if roster else None
        duty_area = roster.duty_area if roster else None
        if employee and not roster:
            is_on_duty = False
            warnings.append("No approved roster found for this shift")
        if roster and roster.duty_area and ward_name and roster.duty_area.lower() not in {ward_name.lower(), "ipd", "all wards", "all"}:
            is_on_duty = False
            warnings.append(f"Rostered for {roster.duty_area}, not {ward_name}")
        if is_on_leave:
            warnings.append("Staff is on approved leave")
        if is_overloaded:
            warnings.append("Staff is already at configured IPD patient load")
        if not employee:
            warnings.append("No HR employee profile linked; roster could not be verified")
        can_assign = not is_on_leave and not is_overloaded and (is_on_duty or not employee)
        department_label = employee.department.name if employee and employee.department else department_name
        return IPDStaffAvailabilityRead(
            staff_user_id=staff.id,
            staff_name=staff.full_name,
            role_type=role_type,
            employee_id=employee.id if employee else None,
            employee_status=employee.employment_status if employee else None,
            department_name=department_label,
            current_shift=current_shift,
            duty_area=duty_area,
            roster_status=roster_status,
            is_on_duty=is_on_duty,
            is_on_leave=is_on_leave,
            active_ipd_assignments=active_load,
            max_patient_load=max_load,
            is_overloaded=is_overloaded,
            can_assign=can_assign,
            warnings=warnings,
        )

    def _settings(self, actor: User) -> IPDSettingsRead:
        profile = self._get_or_create_settings_profile(actor)
        return IPDSettingsRead(id=profile.id, updated_at=profile.updated_at, **self._settings_payload(profile))

    def _get_or_create_settings_profile(self, actor: User) -> ConfigurationProfile:
        return self._get_or_create_settings_profile_for_branch(actor.branch_id, actor.id)

    def _get_or_create_settings_profile_for_branch(self, branch_id, actor_id=None) -> ConfigurationProfile:
        profile = self.db.scalar(
            select(ConfigurationProfile).where(
                ConfigurationProfile.branch_id == branch_id,
                ConfigurationProfile.profile_type == self.SETTINGS_PROFILE_TYPE,
                ConfigurationProfile.code == self.SETTINGS_CODE,
                ConfigurationProfile.is_active.is_(True),
            )
        )
        if profile:
            return profile
        profile = ConfigurationProfile(
            branch_id=branch_id,
            profile_type=self.SETTINGS_PROFILE_TYPE,
            code=self.SETTINGS_CODE,
            name="Default IPD Settings",
            description="Safe default IPD workflow configuration.",
            scope="hospital",
            payload=self._default_settings_payload(),
            is_default=True,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.db.add(profile)
        self.db.flush()
        return profile

    def _settings_payload(self, profile: ConfigurationProfile) -> dict:
        defaults = self._default_settings_payload()
        payload = profile.payload or {}
        merged = {**defaults, **payload}
        for key in [
            "department_admission_rules",
            "payment_type_rules",
            "insurance_corporate_rules",
            "department_staff_rules",
            "shift_assignment_rules",
            "on_call_assignment_rules",
            "vitals_config",
            "intake_output_settings",
            "clearance_requirements",
            "billing_clearance_rules",
            "pharmacy_clearance_rules",
            "lab_radiology_pending_order_rules",
            "follow_up_requirements",
            "role_permission_notes",
            "default_bed_charges",
            "shift_handover_timings",
        ]:
            merged[key] = {**defaults.get(key, {}), **(payload.get(key) or {})}
        return merged

    def _default_settings_payload(self) -> dict:
        return {
            "ward_types": ["General Ward", "Cabin", "ICU", "CCU", "NICU", "Isolation", "Surgery Ward", "Maternity Ward"],
            "room_types": ["General", "Semi-private", "Private", "Cabin", "Isolation", "ICU", "NICU", "CCU"],
            "bed_types": ["General", "Semi-private", "Private", "Cabin", "ICU", "CCU", "NICU", "Isolation"],
            "bed_statuses": ["available", "occupied", "reserved", "cleaning", "maintenance", "blocked"],
            "cleaning_statuses": ["cleaning", "disinfection", "ready", "maintenance"],
            "critical_care_categories": ["ICU", "CCU", "NICU", "HDU", "Isolation"],
            "default_bed_charges": {"General": "0", "Semi-private": "0", "Private": "0", "Cabin": "0", "ICU": "0", "CCU": "0", "NICU": "0", "Isolation": "0"},
            "admission_sources": ["OPD", "Emergency", "Direct", "Referral", "Transfer"],
            "admission_types": ["General", "Emergency", "Surgery", "ICU", "Maternity", "Pediatric", "Corporate", "Insurance"],
            "required_admission_fields": ["patient_id", "admitted_at", "ward_name", "bed_number", "attending_doctor_name"],
            "admission_number_format": "IPD-{YYYY}{MM}{DD}-{SEQ4}",
            "department_admission_rules": {},
            "payment_type_rules": {"allowed": ["cash", "card", "insurance", "corporate", "exempted"]},
            "insurance_corporate_rules": {"require_policy_reference": False, "require_approval_before_admission": False},
            "doctor_assignment_types": sorted(self.DOCTOR_ASSIGNMENT_TYPES),
            "nurse_assignment_types": sorted(self.NURSE_ASSIGNMENT_TYPES),
            "max_patient_load_doctor": 20,
            "max_patient_load_nurse": 8,
            "department_staff_rules": {},
            "shift_assignment_rules": {"shifts": ["morning", "evening", "night", "on_call"]},
            "on_call_assignment_rules": {"allow_on_call_without_roster": True},
            "handover_templates": [
                {"name": "Nursing Shift Handover", "type": "nursing"},
                {"name": "Doctor Duty Handover", "type": "doctor"},
            ],
            "required_handover_fields": ["summary"],
            "shift_handover_timings": {"morning": "06:00", "evening": "14:00", "night": "22:00"},
            "require_handover_acknowledgment": True,
            "handover_escalation_minutes": 30,
            "doctor_note_templates": [{"name": "Progress Note", "type": "progress_note"}, {"name": "Consultation Note", "type": "consultation_note"}],
            "nursing_note_templates": [{"name": "Nursing Note", "type": "nursing_note"}, {"name": "Vitals", "type": "vitals"}],
            "vitals_config": {"temperature": {"min": 35, "max": 38}, "pulse": {"min": 50, "max": 120}, "spo2": {"min": 92}},
            "intake_output_settings": {"enabled": True, "shift_total_required": False},
            "care_plan_templates": [{"name": "General Care Plan"}, {"name": "Fall Risk Care Plan"}],
            "procedure_note_templates": [{"name": "Bedside Procedure Note"}, {"name": "Minor Procedure Note"}],
            "discharge_approval_levels": ["doctor", "billing"],
            "required_discharge_summary_fields": ["discharge_summary"],
            "clearance_requirements": {"billing": False, "pharmacy": False, "lab": False, "radiology": False},
            "billing_clearance_rules": {"require_before_final_discharge": False},
            "pharmacy_clearance_rules": {"require_return_review": False},
            "lab_radiology_pending_order_rules": {"allow_discharge_with_pending_results": True},
            "follow_up_requirements": {"require_follow_up_date": False},
            "role_permission_notes": {
                "admit": ["ipd.admit"],
                "transfer": ["ipd.transfer", "ipd.bed_transfer"],
                "assign_staff": ["ipd.assign_doctor", "ipd.assign_nurse"],
                "handover": ["ipd.handover.create", "ipd.handover.acknowledge"],
                "discharge": ["ipd.discharge.request", "ipd.discharge.approve", "ipd.discharge.finalize"],
            },
        }

    def _validate_required_fields(self, values: dict, required_fields: list[str], label: str) -> None:
        missing = [field for field in required_fields if values.get(field) in (None, "", [])]
        if missing:
            raise AppException(422, f"ipd_{label.replace(' ', '_')}_required_fields", f"Missing required {label} fields: {', '.join(missing)}")

    def _admission_in_scope(self, actor: User, admission: IPDAdmission) -> bool:
        if self.scopes.has_unrestricted_access(actor, module="ipd", scope_type="ward"):
            return True
        has_scopes = self.scopes.has_scope_assignments(actor, "ward", "doctor_profile", "nurse_station", "shift", module="ipd")
        if not has_scopes:
            return True
        wards = self.scopes.scope_values(actor, "ward", module="ipd")
        doctor_refs = self.scopes.scope_refs(actor, "doctor_profile", module="ipd")
        nurse_refs = self.scopes.scope_refs(actor, "nurse_station", module="ipd")
        shifts = self.scopes.scope_values(actor, "shift", module="ipd")
        if admission.ward_name and admission.ward_name.lower() in wards:
            return True
        if admission.attending_doctor_user_id and admission.attending_doctor_user_id in doctor_refs:
            return True
        if admission.assigned_nurse_user_id and admission.assigned_nurse_user_id in nurse_refs:
            return True
        if admission.attending_doctor_user_id == actor.id or admission.assigned_nurse_user_id == actor.id:
            return True
        if shifts:
            active = [assignment for assignment in admission.staff_assignments if assignment.staff_user_id == actor.id and not assignment.ended_at]
            if any((assignment.shift_name or "").lower() in shifts for assignment in active):
                return True
        return False

    def _assert_admission_scope(self, actor: User, admission: IPDAdmission) -> None:
        if not self._admission_in_scope(actor, admission):
            self.scopes.assert_in_scope(actor, module="ipd", scope_type="ward", scope_value=admission.ward_name)

    def _apply_admission_scope_filter(self, stmt, actor: User):
        if self.scopes.has_unrestricted_access(actor, module="ipd", scope_type="ward"):
            return stmt
        if not self.scopes.has_scope_assignments(actor, "ward", "doctor_profile", "nurse_station", module="ipd"):
            return stmt
        clauses = []
        wards = self.scopes.scope_values(actor, "ward", module="ipd")
        doctor_refs = self.scopes.scope_refs(actor, "doctor_profile", module="ipd")
        nurse_refs = self.scopes.scope_refs(actor, "nurse_station", module="ipd")
        if wards:
            clauses.append(func.lower(IPDAdmission.ward_name).in_(wards))
        if doctor_refs:
            clauses.append(IPDAdmission.attending_doctor_user_id.in_(doctor_refs))
        if nurse_refs:
            clauses.append(IPDAdmission.assigned_nurse_user_id.in_(nurse_refs))
        clauses.extend([IPDAdmission.attending_doctor_user_id == actor.id, IPDAdmission.assigned_nurse_user_id == actor.id])
        return stmt.where(or_(*clauses))

    def _apply_nursing_task_scope_filter(self, stmt, actor: User):
        if self.scopes.has_unrestricted_access(actor, module="ipd", scope_type="ward"):
            return stmt
        if not self.scopes.has_scope_assignments(actor, "ward", "nurse_station", "shift", module="ipd"):
            return stmt
        clauses = [IPDNursingTask.assigned_nurse_user_id == actor.id]
        wards = self.scopes.scope_values(actor, "ward", module="ipd")
        nurse_refs = self.scopes.scope_refs(actor, "nurse_station", module="ipd")
        shifts = self.scopes.scope_values(actor, "shift", module="ipd")
        if wards:
            clauses.append(func.lower(IPDNursingTask.ward_name).in_(wards))
        if nurse_refs:
            clauses.append(IPDNursingTask.assigned_nurse_user_id.in_(nurse_refs))
        if shifts:
            clauses.append(func.lower(IPDNursingTask.shift_name).in_(shifts))
        return stmt.where(or_(*clauses))

    def _apply_handover_scope_filter(self, stmt, actor: User):
        if self.scopes.has_unrestricted_access(actor, module="ipd", scope_type="ward"):
            return stmt
        if not self.scopes.has_scope_assignments(actor, "ward", "shift", module="ipd"):
            return stmt
        clauses = [IPDHandover.sender_user_id == actor.id, IPDHandover.receiver_user_id == actor.id]
        wards = self.scopes.scope_values(actor, "ward", module="ipd")
        shifts = self.scopes.scope_values(actor, "shift", module="ipd")
        if wards:
            clauses.append(func.lower(IPDAdmission.ward_name).in_(wards))
        if shifts:
            clauses.append(func.lower(IPDHandover.shift_name).in_(shifts))
        return stmt.where(or_(*clauses))

    def _generate_admission_number(self, branch_id, number_format: str) -> str:
        now = datetime.now(UTC)
        day_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
        count = self.db.scalar(select(func.count(IPDAdmission.id)).where(IPDAdmission.created_at >= day_start)) or 0
        if branch_id:
            count = self.db.scalar(select(func.count(IPDAdmission.id)).where(IPDAdmission.branch_id == branch_id, IPDAdmission.created_at >= day_start)) or 0
        sequence = int(count) + 1
        return (
            number_format.replace("{YYYY}", now.strftime("%Y"))
            .replace("{YY}", now.strftime("%y"))
            .replace("{MM}", now.strftime("%m"))
            .replace("{DD}", now.strftime("%d"))
            .replace("{SEQ4}", f"{sequence:04d}")
            .replace("{SEQ5}", f"{sequence:05d}")
            .replace("{TS}", now.strftime("%H%M%S"))
        )

    def _current_shift_name(self) -> str:
        hour = datetime.now().hour
        return self._shift_for_hour(hour)

    def _shift_for_datetime(self, value: datetime) -> str:
        return self._shift_for_hour(value.hour)

    def _shift_for_hour(self, hour: int) -> str:
        if 6 <= hour < 14:
            return "morning"
        if 14 <= hour < 22:
            return "evening"
        return "night"
