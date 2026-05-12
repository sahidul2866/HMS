from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.audit_log import AuditLog
from app.models.blood_bank import (
    BloodCollection,
    BloodCrossmatch,
    BloodDiscard,
    BloodDonor,
    BloodDonorScreening,
    BloodIssue,
    BloodRequest,
    BloodReturn,
    BloodStorageLocation,
    BloodTestResult,
    BloodTransfusion,
    BloodUnit,
)
from app.models.encounter import IPDTimelineEvent
from app.models.patient import Patient
from app.models.queue import QueueToken
from app.models.scanner import ScanCode
from app.modules.queue.service import QueueService, patient_label
from app.schemas.blood_bank import (
    BloodBankDashboardRead,
    BloodBankReportRead,
    BloodCollectionCreate,
    BloodDiscardCreate,
    BloodIssueCreate,
    BloodRequestCreate,
    BloodReturnCreate,
    BloodTestResultCreate,
    BloodUnitRead,
    ComponentPrepareCreate,
    CrossmatchCreate,
    DonorScreeningCreate,
    MoveUnitCreate,
    StorageLocationCreate,
    TransfusionCreate,
)
from app.schemas.queue import QueueTokenCreate

ISSUABLE_UNIT_STATUSES = {"available", "crossmatched", "reserved"}
FAILED_TEST_STATUSES = {"reactive", "positive", "rejected", "failed"}
BLOCKED_UNIT_STATUSES = {"expired", "discarded", "quarantined", "issued", "transfused"}
BLOOD_QUEUE_STATUS_LABELS = {
    "requested": "Blood request received",
    "sample_pending": "Sample pending",
    "sample_collected": "Sample collected",
    "crossmatch_pending": "Crossmatch pending",
    "crossmatched": "Crossmatched",
    "ready_to_issue": "Ready to issue",
    "partially_issued": "Partially issued",
    "issued": "Issued",
    "returned": "Returned",
    "cancelled": "Cancelled",
    "rejected": "Rejected",
    "discarded": "Discarded",
}


class BloodBankService:
    def __init__(self, db: Session):
        self.db = db

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _serial(self, prefix: str) -> str:
        return f"{prefix}-{self._now().strftime('%Y%m%d%H%M%S%f')[:-3]}"

    def _audit(self, action: str, entity_type: str, entity_id: UUID | str, user, detail: dict | None = None, context: dict | None = None) -> None:
        self.db.add(
            AuditLog(
                user_id=getattr(user, "id", None),
                action=action,
                module="blood_bank",
                entity_type=entity_type,
                entity_id=str(entity_id),
                detail=detail or {},
                ip_address=(context or {}).get("ip_address"),
                user_agent=(context or {}).get("user_agent"),
                created_at=self._now(),
            )
        )

    def _ipd_timeline(self, request: BloodRequest | None, user, event_type: str, title: str, detail: str | None, source_type: str, source_id: UUID) -> None:
        if not request or not request.admission_id:
            return
        self.db.add(
            IPDTimelineEvent(
                admission_id=request.admission_id,
                event_type=event_type,
                title=title,
                detail=detail,
                source_type=source_type,
                source_id=source_id,
                occurred_at=self._now(),
                actor_user_id=getattr(user, "id", None),
                created_by=getattr(user, "id", None),
                updated_by=getattr(user, "id", None),
            )
        )

    def _get_unit(self, unit_id: UUID) -> BloodUnit:
        unit = self.db.get(BloodUnit, unit_id)
        if not unit:
            raise AppException(status.HTTP_404_NOT_FOUND, "unit_not_found", "Blood unit not found")
        if unit.expiry_date and unit.expiry_date < date.today() and unit.status not in {"expired", "discarded", "transfused"}:
            unit.status = "expired"
        return unit

    def _priority_for_request(self, request: BloodRequest) -> str:
        urgency = (request.urgency or "routine").lower()
        if urgency == "emergency":
            return "emergency"
        if urgency == "urgent":
            return "urgent"
        return "normal"

    def _ensure_request_queue(self, request: BloodRequest, user, *, status_value: str | None = None) -> QueueToken:
        patient = request.patient or self.db.get(Patient, request.patient_id)
        queue_status = status_value or request.status or "requested"
        token = QueueService(self.db).ensure_token(
            QueueTokenCreate(
                queue_scope="blood_bank",
                module="blood_bank",
                service_area=request.component_type,
                department_name=request.department_name,
                doctor_user_id=request.requesting_doctor_id,
                patient_id=request.patient_id,
                patient_label=patient_label(patient),
                priority=self._priority_for_request(request),
                source_type="blood_request",
                source_id=request.id,
                blood_request_id=request.id,
                due_at=request.required_at,
                notes=request.indication or request.remarks,
                meta={
                    "request_number": request.request_number,
                    "blood_group": request.blood_group,
                    "component_type": request.component_type,
                    "quantity_units": request.quantity_units,
                    "urgency": request.urgency,
                    "department": request.department_name,
                    "required_at": request.required_at.isoformat() if request.required_at else None,
                    "doctor_user_id": str(request.requesting_doctor_id) if request.requesting_doctor_id else None,
                },
            ),
            user,
            commit=False,
        )
        token.status = queue_status
        token.priority = self._priority_for_request(request)
        token.due_at = request.required_at
        token.meta = {
            **(token.meta or {}),
            "request_number": request.request_number,
            "blood_group": request.blood_group,
            "component_type": request.component_type,
            "quantity_units": request.quantity_units,
            "urgency": request.urgency,
            "department": request.department_name,
            "required_at": request.required_at.isoformat() if request.required_at else None,
        }
        return token

    def _sync_request_queue(self, request: BloodRequest, user, status_value: str) -> None:
        request.status = status_value
        request.updated_by = user.id
        token = self.db.scalar(select(QueueToken).where(QueueToken.blood_request_id == request.id))
        if token:
            token.status = status_value
            token.priority = self._priority_for_request(request)
            token.due_at = request.required_at
            token.updated_by = user.id
            token.meta = {
                **(token.meta or {}),
                "request_number": request.request_number,
                "blood_group": request.blood_group,
                "component_type": request.component_type,
                "quantity_units": request.quantity_units,
                "urgency": request.urgency,
                "department": request.department_name,
                "required_at": request.required_at.isoformat() if request.required_at else None,
            }
        else:
            self._ensure_request_queue(request, user, status_value=status_value)

    def _register_blood_scan_code(self, code_value: str, purpose: str, record_type: str, record_id: UUID, display_value: str, user, meta: dict | None = None) -> None:
        if self.db.scalar(select(ScanCode.id).where(ScanCode.code_value == code_value)):
            return
        self.db.add(
            ScanCode(
                branch_id=getattr(user, "branch_id", None),
                code_value=code_value,
                code_type="qr",
                purpose=purpose,
                record_type=record_type,
                record_id=record_id,
                display_value=display_value,
                meta=meta or {},
                created_by=user.id,
                updated_by=user.id,
            )
        )

    def _unit_read(self, unit: BloodUnit) -> BloodUnitRead:
        return BloodUnitRead(
            id=unit.id,
            unit_number=unit.unit_number,
            blood_group=unit.blood_group,
            rh_factor=unit.rh_factor,
            component_type=unit.component_type,
            collection_date=unit.collection_date,
            expiry_date=unit.expiry_date,
            volume_ml=unit.volume_ml,
            storage_location_id=unit.storage_location_id,
            storage_location_name=unit.storage_location.name if unit.storage_location else None,
            status=unit.status,
            testing_status=unit.testing_status,
            donor_id=unit.donor_id,
            current_patient_id=unit.current_patient_id,
            remarks=unit.remarks,
        )

    def dashboard(self) -> BloodBankDashboardRead:
        today = date.today()
        near_expiry = today + timedelta(days=7)
        available_rows = self.db.execute(
            select(BloodUnit.blood_group, BloodUnit.component_type, func.count(BloodUnit.id))
            .where(BloodUnit.status == "available")
            .group_by(BloodUnit.blood_group, BloodUnit.component_type)
        ).all()
        by_group: dict[str, int] = {}
        by_component: dict[str, dict[str, int]] = {}
        for group, component, count in available_rows:
            by_group[group] = by_group.get(group, 0) + count
            by_component.setdefault(group, {})[component] = count

        all_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        low_groups = [group for group in all_groups if by_group.get(group, 0) < 2]
        pending_crossmatch = self.db.scalar(
            select(func.count(BloodRequest.id)).where(BloodRequest.status.in_(["requested", "under_review", "sample_required", "crossmatch_pending"]))
        ) or 0
        return BloodBankDashboardRead(
            available_units_by_group=by_group,
            available_components_by_group=by_component,
            low_stock_groups=low_groups,
            near_expiry_units=self.db.scalar(select(func.count(BloodUnit.id)).where(BloodUnit.expiry_date.between(today, near_expiry), BloodUnit.status.in_(["available", "reserved", "crossmatched"]))) or 0,
            expired_units=self.db.scalar(select(func.count(BloodUnit.id)).where(or_(BloodUnit.expiry_date < today, BloodUnit.status == "expired"))) or 0,
            pending_donor_screening=self.db.scalar(select(func.count(BloodDonor.id)).where(BloodDonor.medical_screening_status == "pending")) or 0,
            pending_crossmatch_requests=pending_crossmatch,
            pending_issue_requests=self.db.scalar(select(func.count(BloodRequest.id)).where(BloodRequest.status.in_(["crossmatched", "ready_to_issue"]))) or 0,
            issued_units=self.db.scalar(select(func.count(BloodUnit.id)).where(BloodUnit.status == "issued")) or 0,
            discarded_units=self.db.scalar(select(func.count(BloodUnit.id)).where(BloodUnit.status == "discarded")) or 0,
            emergency_requests=self.db.scalar(select(func.count(BloodRequest.id)).where(BloodRequest.urgency == "emergency", BloodRequest.status.notin_(["cancelled", "rejected", "issued"]))) or 0,
            unsafe_units_blocked=self.db.scalar(select(func.count(BloodUnit.id)).where(or_(BloodUnit.status.in_(list(BLOCKED_UNIT_STATUSES)), BloodUnit.testing_status.in_(list(FAILED_TEST_STATUSES))))) or 0,
        )

    def list_donors(self, q: str | None = None, blood_group: str | None = None, eligibility: str | None = None, page: int = 1, page_size: int = 20):
        query = select(BloodDonor)
        if q:
            like = f"%{q}%"
            query = query.where(or_(BloodDonor.name.ilike(like), BloodDonor.phone.ilike(like), BloodDonor.donor_number.ilike(like)))
        if blood_group:
            query = query.where(BloodDonor.blood_group == blood_group)
        if eligibility:
            query = query.where(BloodDonor.eligibility_status == eligibility)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(query.order_by(BloodDonor.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        for item in items:
            item.donation_count = len(item.collections)
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def create_donor(self, payload, user, context):
        duplicate = None
        if payload.phone:
            duplicate = self.db.scalar(select(BloodDonor).where(BloodDonor.phone == payload.phone, BloodDonor.name.ilike(payload.name)))
        if duplicate:
            raise AppException(status.HTTP_409_CONFLICT, "duplicate_donor", "A donor with the same name and phone already exists")
        donor = BloodDonor(**payload.model_dump(exclude={"donor_number"}), donor_number=payload.donor_number or self._serial("DNR"), created_by=user.id, updated_by=user.id)
        self.db.add(donor)
        self.db.flush()
        self._audit("blood_bank.donor.create", "blood_donor", donor.id, user, {"donor_number": donor.donor_number}, context)
        self.db.commit()
        self.db.refresh(donor)
        donor.donation_count = 0
        return donor

    def screen_donor(self, payload: DonorScreeningCreate, user, context):
        donor = self.db.get(BloodDonor, payload.donor_id)
        if not donor:
            raise AppException(status.HTTP_404_NOT_FOUND, "donor_not_found", "Donor not found")
        screening = BloodDonorScreening(
            **payload.model_dump(exclude={"screened_at", "override_authorized"}),
            screened_at=payload.screened_at or self._now(),
            screening_staff_id=user.id,
            override_authorized_by=user.id if payload.override_authorized else None,
            created_by=user.id,
            updated_by=user.id,
        )
        donor.eligibility_status = payload.eligibility_result
        donor.medical_screening_status = "completed"
        donor.updated_by = user.id
        self.db.add(screening)
        self.db.flush()
        self._audit("blood_bank.donor.screen", "blood_donor_screening", screening.id, user, {"donor_id": str(donor.id), "result": payload.eligibility_result}, context)
        self.db.commit()
        self.db.refresh(screening)
        return screening

    def collect_blood(self, payload: BloodCollectionCreate, user, context):
        donor = self.db.get(BloodDonor, payload.donor_id)
        if not donor:
            raise AppException(status.HTTP_404_NOT_FOUND, "donor_not_found", "Donor not found")
        if donor.eligibility_status != "eligible":
            raise AppException(status.HTTP_400_BAD_REQUEST, "donor_not_eligible", "Blood collection is blocked because donor is not eligible")
        unit_number = payload.unit_number or self._serial("BU")
        if self.db.scalar(select(BloodUnit.id).where(BloodUnit.unit_number == unit_number)):
            raise AppException(status.HTTP_409_CONFLICT, "duplicate_unit", "Blood unit number already exists")
        collected_at = payload.collected_at or self._now()
        collection = BloodCollection(
            **payload.model_dump(exclude={"collected_at", "unit_number"}),
            collection_number=self._serial("COL"),
            unit_number=unit_number,
            collected_at=collected_at,
            collection_staff_id=user.id,
            created_by=user.id,
            updated_by=user.id,
        )
        unit = BloodUnit(
            collection=collection,
            donor_id=donor.id,
            unit_number=unit_number,
            blood_group=payload.blood_group,
            component_type="Whole Blood",
            collection_date=collected_at.date(),
            volume_ml=payload.collection_volume_ml,
            status="testing_pending",
            testing_status="pending",
            created_by=user.id,
            updated_by=user.id,
        )
        donor.last_donation_date = collected_at.date()
        self.db.add_all([collection, unit])
        self.db.flush()
        self._register_blood_scan_code(
            f"BLOODUNIT:{unit.unit_number}:{unit.id}",
            "blood_unit",
            "blood_unit",
            unit.id,
            unit.unit_number,
            user,
            {"blood_group": unit.blood_group, "component_type": unit.component_type, "donor_id": str(donor.id)},
        )
        self._audit("blood_bank.collection.create", "blood_unit", unit.id, user, {"unit_number": unit_number, "donor_id": str(donor.id)}, context)
        self.db.commit()
        self.db.refresh(collection)
        return collection

    def update_test(self, payload: BloodTestResultCreate, user, context):
        unit = self._get_unit(payload.unit_id)
        test = self.db.scalar(select(BloodTestResult).where(BloodTestResult.unit_id == payload.unit_id, BloodTestResult.test_name == payload.test_name))
        data = payload.model_dump(exclude={"performed_at", "verified"})
        if not test:
            test = BloodTestResult(**data, performed_at=payload.performed_at or self._now(), performed_by=user.id, created_by=user.id, updated_by=user.id)
            self.db.add(test)
        else:
            for key, value in data.items():
                setattr(test, key, value)
            test.performed_at = payload.performed_at or test.performed_at or self._now()
            test.performed_by = test.performed_by or user.id
            test.updated_by = user.id
        if payload.verified:
            test.verified_by = user.id
            test.verified_at = self._now()
        if payload.status.lower() in FAILED_TEST_STATUSES or str(payload.result or "").lower() in FAILED_TEST_STATUSES:
            unit.testing_status = payload.status
            unit.status = "quarantined"
        elif payload.status in {"completed", "non_reactive", "negative"}:
            unit.testing_status = "completed"
            if unit.status == "testing_pending":
                unit.status = "available"
        self.db.flush()
        self._audit("blood_bank.testing.update", "blood_test_result", test.id, user, {"unit_id": str(unit.id), "status": payload.status}, context)
        self.db.commit()
        self.db.refresh(test)
        return test

    def prepare_component(self, payload: ComponentPrepareCreate, user, context):
        source = self._get_unit(payload.source_unit_id)
        if source.status not in {"available", "testing_pending"}:
            raise AppException(status.HTTP_400_BAD_REQUEST, "source_unit_not_available", "Source unit cannot be split in its current status")
        unit_number = payload.component_unit_number or self._serial("BC")
        if self.db.scalar(select(BloodUnit.id).where(BloodUnit.unit_number == unit_number)):
            raise AppException(status.HTTP_409_CONFLICT, "duplicate_unit", "Component unit number already exists")
        component = BloodUnit(
            collection_id=source.collection_id,
            donor_id=source.donor_id,
            source_unit_id=source.id,
            unit_number=unit_number,
            blood_group=source.blood_group,
            rh_factor=source.rh_factor,
            component_type=payload.component_type,
            collection_date=source.collection_date,
            prepared_at=payload.prepared_at or self._now(),
            expiry_date=payload.expiry_date,
            volume_ml=payload.volume_ml,
            storage_location_id=payload.storage_location_id,
            status="available" if source.testing_status == "completed" else "testing_pending",
            testing_status=source.testing_status,
            prepared_by=user.id,
            remarks=payload.remarks,
            created_by=user.id,
            updated_by=user.id,
        )
        self.db.add(component)
        self.db.flush()
        self._register_blood_scan_code(
            f"BLOODUNIT:{component.unit_number}:{component.id}",
            "blood_unit",
            "blood_unit",
            component.id,
            component.unit_number,
            user,
            {"blood_group": component.blood_group, "component_type": component.component_type, "source_unit_id": str(source.id)},
        )
        self._audit("blood_bank.component.prepare", "blood_unit", component.id, user, {"source_unit_id": str(source.id), "component_type": payload.component_type}, context)
        self.db.commit()
        self.db.refresh(component)
        return self._unit_read(component)

    def list_units(self, blood_group: str | None, component_type: str | None, status_value: str | None, storage_location_id: UUID | None, page: int, page_size: int):
        query = select(BloodUnit)
        if blood_group:
            query = query.where(BloodUnit.blood_group == blood_group)
        if component_type:
            query = query.where(BloodUnit.component_type == component_type)
        if status_value:
            query = query.where(BloodUnit.status == status_value)
        if storage_location_id:
            query = query.where(BloodUnit.storage_location_id == storage_location_id)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        units = self.db.scalars(query.order_by(BloodUnit.expiry_date.asc().nulls_last(), BloodUnit.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return {"items": [self._unit_read(unit) for unit in units], "total": total, "page": page, "page_size": page_size}

    def create_location(self, payload: StorageLocationCreate, user, context):
        location = BloodStorageLocation(**payload.model_dump(), branch_id=getattr(user, "branch_id", None), created_by=user.id, updated_by=user.id)
        self.db.add(location)
        self.db.flush()
        self._audit("blood_bank.storage.create", "blood_storage_location", location.id, user, {"code": location.code}, context)
        self.db.commit()
        self.db.refresh(location)
        return location

    def list_locations(self):
        return self.db.scalars(select(BloodStorageLocation).order_by(BloodStorageLocation.name)).all()

    def move_unit(self, unit_id: UUID, payload: MoveUnitCreate, user, context):
        unit = self._get_unit(unit_id)
        old = str(unit.storage_location_id) if unit.storage_location_id else None
        unit.storage_location_id = payload.storage_location_id
        unit.updated_by = user.id
        self._audit("blood_bank.stock.location_change", "blood_unit", unit.id, user, {"from": old, "to": str(payload.storage_location_id), "remarks": payload.remarks}, context)
        self.db.commit()
        self.db.refresh(unit)
        return self._unit_read(unit)

    def create_request(self, payload: BloodRequestCreate, user, context):
        request = BloodRequest(**payload.model_dump(), request_number=self._serial("BRQ"), created_by=user.id, updated_by=user.id)
        self.db.add(request)
        self.db.flush()
        self._ensure_request_queue(request, user, status_value="requested")
        self._register_blood_scan_code(
            f"BLOODREQ:{request.request_number}:{request.id}",
            "blood_request",
            "blood_request",
            request.id,
            request.request_number,
            user,
            {"patient_id": str(request.patient_id), "blood_group": request.blood_group, "component_type": request.component_type, "urgency": request.urgency},
        )
        self._audit("blood_bank.request.create", "blood_request", request.id, user, {"patient_id": str(payload.patient_id), "urgency": payload.urgency}, context)
        self._ipd_timeline(request, user, "blood_request", "Blood request created", f"{request.quantity_units} unit(s) {request.blood_group} {request.component_type} requested.", "blood_request", request.id)
        self.db.commit()
        self.db.refresh(request)
        return request

    def list_requests(self, status_value: str | None, urgency: str | None, page: int, page_size: int):
        query = select(BloodRequest)
        if status_value:
            query = query.where(BloodRequest.status == status_value)
        if urgency:
            query = query.where(BloodRequest.urgency == urgency)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.scalars(query.order_by(BloodRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def crossmatch(self, payload: CrossmatchCreate, user, context):
        request = self.db.get(BloodRequest, payload.request_id)
        unit = self._get_unit(payload.unit_id)
        if not request:
            raise AppException(status.HTTP_404_NOT_FOUND, "request_not_found", "Blood request not found")
        if unit.status in BLOCKED_UNIT_STATUSES or unit.testing_status != "completed":
            raise AppException(status.HTTP_400_BAD_REQUEST, "unsafe_unit", "Unsafe, expired, discarded, quarantined, or untested units cannot be crossmatched")
        incompatible = payload.compatibility_status != "compatible"
        if incompatible and not payload.emergency_override:
            raise AppException(status.HTTP_400_BAD_REQUEST, "incompatible_unit", "Incompatible units cannot be approved without emergency override")
        crossmatch = BloodCrossmatch(
            **payload.model_dump(exclude={"tested_at", "emergency_override"}),
            unit_blood_group=unit.blood_group,
            component_type=unit.component_type,
            tested_by=user.id,
            tested_at=payload.tested_at or self._now(),
            emergency_override_by=user.id if payload.emergency_override else None,
            created_by=user.id,
            updated_by=user.id,
        )
        unit.status = "crossmatched" if not incompatible else "reserved"
        unit.current_request_id = request.id
        self._sync_request_queue(request, user, "crossmatched" if not incompatible else "rejected")
        self.db.add(crossmatch)
        self.db.flush()
        self._audit("blood_bank.crossmatch.perform", "blood_crossmatch", crossmatch.id, user, {"request_id": str(request.id), "unit_id": str(unit.id), "compatibility": payload.compatibility_status}, context)
        self.db.commit()
        self.db.refresh(crossmatch)
        return crossmatch

    def issue(self, payload: BloodIssueCreate, user, context):
        request = self.db.get(BloodRequest, payload.request_id)
        unit = self._get_unit(payload.unit_id)
        if not request:
            raise AppException(status.HTTP_404_NOT_FOUND, "request_not_found", "Blood request not found")
        if self.db.scalar(select(BloodIssue.id).where(BloodIssue.unit_id == unit.id)):
            raise AppException(status.HTTP_409_CONFLICT, "duplicate_issue", "This unit has already been issued")
        if unit.status not in ISSUABLE_UNIT_STATUSES or unit.status in BLOCKED_UNIT_STATUSES or unit.testing_status != "completed":
            raise AppException(status.HTTP_400_BAD_REQUEST, "unsafe_unit", "Only tested available or crossmatched units can be issued")
        crossmatch = self.db.get(BloodCrossmatch, payload.crossmatch_id) if payload.crossmatch_id else self.db.scalar(select(BloodCrossmatch).where(BloodCrossmatch.request_id == request.id, BloodCrossmatch.unit_id == unit.id))
        if not crossmatch or crossmatch.compatibility_status != "compatible":
            if not payload.emergency_override:
                raise AppException(status.HTTP_400_BAD_REQUEST, "crossmatch_required", "Compatible crossmatch is required before issue")
            if not payload.override_reason:
                raise AppException(status.HTTP_400_BAD_REQUEST, "override_reason_required", "Emergency override requires a documented reason")
            request.emergency_override_by = user.id
            request.override_reason = payload.override_reason
        issue = BloodIssue(
            issue_number=self._serial("BIS"),
            request_id=request.id,
            patient_id=request.patient_id,
            unit_id=unit.id,
            crossmatch_id=crossmatch.id if crossmatch else None,
            quantity=1,
            issued_by=user.id,
            received_by=payload.received_by,
            issued_at=payload.issued_at or self._now(),
            destination=payload.destination,
            transport_condition=payload.transport_condition,
            remarks=payload.remarks,
            created_by=user.id,
            updated_by=user.id,
        )
        unit.status = "issued"
        unit.current_patient_id = request.patient_id
        self._sync_request_queue(request, user, "issued")
        self.db.add(issue)
        self.db.flush()
        self._audit("blood_bank.issue", "blood_issue", issue.id, user, {"request_id": str(request.id), "unit_id": str(unit.id)}, context)
        self._ipd_timeline(request, user, "blood_issue", "Blood unit issued", f"Unit {unit.unit_number} issued to {issue.destination or 'clinical area'}.", "blood_issue", issue.id)
        self.db.commit()
        self.db.refresh(issue)
        return issue

    def transfusion(self, payload: TransfusionCreate, user, context):
        issue = self.db.get(BloodIssue, payload.issue_id)
        if not issue:
            raise AppException(status.HTTP_404_NOT_FOUND, "issue_not_found", "Blood issue not found")
        existing = self.db.scalar(select(BloodTransfusion).where(BloodTransfusion.issue_id == issue.id))
        if existing:
            transfusion = existing
            for key, value in payload.model_dump(exclude={"started_at", "completed_at"}).items():
                setattr(transfusion, key, value)
            transfusion.completed_at = payload.completed_at or transfusion.completed_at
            transfusion.updated_by = user.id
        else:
            transfusion = BloodTransfusion(
                issue_id=issue.id,
                unit_id=issue.unit_id,
                patient_id=issue.patient_id,
                status=payload.status,
                started_by=user.id,
                started_at=payload.started_at or self._now(),
                completed_at=payload.completed_at,
                completed_by=user.id if payload.status in {"completed", "stopped"} else None,
                vitals=payload.vitals,
                reaction_observed=payload.reaction_observed,
                reaction_details=payload.reaction_details,
                remarks=payload.remarks,
                created_by=user.id,
                updated_by=user.id,
            )
            self.db.add(transfusion)
        unit = self._get_unit(issue.unit_id)
        if payload.status == "completed":
            unit.status = "transfused"
        elif payload.status in {"started", "held", "stopped"}:
            unit.status = "issued"
        self.db.flush()
        self._audit("blood_bank.transfusion.update", "blood_transfusion", transfusion.id, user, {"status": payload.status, "reaction": payload.reaction_observed}, context)
        self._ipd_timeline(issue.request, user, "blood_transfusion", "Blood transfusion updated", f"Unit {issue.unit.unit_number if issue.unit else issue.unit_id} transfusion status: {payload.status}.", "blood_transfusion", transfusion.id)
        self.db.commit()
        self.db.refresh(transfusion)
        return transfusion

    def return_unit(self, payload: BloodReturnCreate, user, context):
        issue = self.db.get(BloodIssue, payload.issue_id)
        if not issue:
            raise AppException(status.HTTP_404_NOT_FOUND, "issue_not_found", "Blood issue not found")
        unit = self._get_unit(issue.unit_id)
        ret = BloodReturn(
            **payload.model_dump(exclude={"returned_at"}),
            unit_id=unit.id,
            returned_at=payload.returned_at or self._now(),
            checked_by=user.id,
            created_by=user.id,
            updated_by=user.id,
        )
        decision = payload.decision.lower()
        unit.status = "available" if decision == "accept" else "quarantined" if decision == "quarantine" else "discarded"
        self._sync_request_queue(issue.request, user, "returned")
        self.db.add(ret)
        self.db.flush()
        self._audit("blood_bank.return", "blood_return", ret.id, user, {"unit_id": str(unit.id), "decision": payload.decision}, context)
        self.db.commit()
        self.db.refresh(ret)
        return ret

    def discard(self, payload: BloodDiscardCreate, user, context):
        unit = self._get_unit(payload.unit_id)
        if unit.status == "transfused":
            raise AppException(status.HTTP_400_BAD_REQUEST, "unit_transfused", "Transfused units cannot be discarded from stock")
        discard = BloodDiscard(
            **payload.model_dump(exclude={"discarded_at"}),
            discarded_at=payload.discarded_at or self._now(),
            discarded_by=user.id,
            created_by=user.id,
            updated_by=user.id,
        )
        unit.status = "discarded"
        if unit.current_request_id:
            request = self.db.get(BloodRequest, unit.current_request_id)
            if request:
                self._sync_request_queue(request, user, "discarded")
        self.db.add(discard)
        self.db.flush()
        self._audit("blood_bank.discard", "blood_discard", discard.id, user, {"unit_id": str(unit.id), "reason": payload.reason}, context)
        self.db.commit()
        self.db.refresh(discard)
        return discard

    def report(self, report_type: str, date_from: date | None, date_to: date | None) -> BloodBankReportRead:
        rows: list[dict] = []
        if report_type in {"stock", "blood_group_stock", "component_stock", "near_expiry", "expired", "discard"}:
            query = select(BloodUnit)
            if report_type == "near_expiry":
                query = query.where(BloodUnit.expiry_date.between(date.today(), date.today() + timedelta(days=7)))
            if report_type == "expired":
                query = query.where(or_(BloodUnit.expiry_date < date.today(), BloodUnit.status == "expired"))
            if report_type == "discard":
                query = query.where(BloodUnit.status == "discarded")
            for unit in self.db.scalars(query.order_by(BloodUnit.blood_group, BloodUnit.component_type)).all():
                rows.append({"unit_number": unit.unit_number, "blood_group": unit.blood_group, "component": unit.component_type, "status": unit.status, "expiry_date": str(unit.expiry_date) if unit.expiry_date else None})
        elif report_type in {"issue", "transfusion", "crossmatch", "emergency_request", "patient_usage"}:
            query = select(BloodRequest)
            if report_type == "emergency_request":
                query = query.where(BloodRequest.urgency == "emergency")
            for request in self.db.scalars(query.order_by(BloodRequest.created_at.desc()).limit(500)).all():
                rows.append({"request_number": request.request_number, "patient_id": str(request.patient_id), "blood_group": request.blood_group, "component": request.component_type, "quantity": request.quantity_units, "status": request.status, "urgency": request.urgency})
        else:
            for donor in self.db.scalars(select(BloodDonor).order_by(BloodDonor.created_at.desc()).limit(500)).all():
                rows.append({"donor_number": donor.donor_number, "name": donor.name, "phone": donor.phone, "blood_group": donor.blood_group, "eligibility": donor.eligibility_status, "last_donation_date": str(donor.last_donation_date) if donor.last_donation_date else None})
        return BloodBankReportRead(report_type=report_type, generated_at=self._now(), rows=rows, totals={"count": len(rows), "date_from": str(date_from) if date_from else None, "date_to": str(date_to) if date_to else None})
