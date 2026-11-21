from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.encounter import DoctorOPDSchedule, DoctorSlotBooking, OPDVisit, OPDVisitOrder
from app.models.laboratory import LabOrder, LabOrderItem
from app.models.radiology import RadiologyOrder
from app.models.queue import QueueToken
from app.models.user import User
from app.modules.auth.service import AuthService
from app.modules.audit.service import AuditService
from app.modules.ipd.service import IPDService
from app.modules.opd.repository import OPDRepository
from app.modules.patients.repository import PatientsRepository
from app.modules.queue.service import QueueService, patient_label
from app.modules.users.repository import UsersRepository
from app.schemas.encounter import (
    IPDAdmissionCreate,
    OPDConvertToIPD,
    OPDSummary,
    OPDVisitConsultationUpdate,
    OPDVisitCreate,
    OPDVisitPaymentUpdate,
    OPDVisitOrderCreate,
    OPDVisitOrderUpdate,
    OPDVisitUpdate,
)
from app.schemas.queue import QueueTokenCreate, QueueTransferRequest
from app.utils.enums import AuditAction


class OPDService:
    DOCTOR_WISE_VIEW_PERMISSION = "opd.view.doctor_wise"
    TWOPLACES = Decimal("0.01")

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OPDRepository(db)
        self.patients = PatientsRepository(db)
        self.users = UsersRepository(db)
        self.auth = AuthService(db)

    def list_visits(self, actor: User, doctor_user_id=None) -> list[OPDVisit]:
        doctor_scope = self._resolve_doctor_scope(actor, doctor_user_id)
        return self.repository.list_visits(actor.branch_id, doctor_scope)

    def get_visit(self, visit_id, actor: User) -> OPDVisit:
        visit = self.repository.get_visit(visit_id)
        if not visit:
            raise AppException(404, "opd_visit_not_found", "OPD visit not found")
        return self._validate_visit_access(visit, actor)

    def get_summary(self, actor: User, doctor_user_id=None, visit_date=None) -> OPDSummary:
        from app.modules.opd.dashboard import build_summary

        return build_summary(self.db, actor.branch_id, self._resolve_doctor_scope(actor, doctor_user_id), visit_date)

    def create_visit(self, payload: OPDVisitCreate, actor: User, context: dict[str, str | None], source_appointment_id=None, *, commit: bool = True) -> OPDVisit:
        patient = self.patients.get_patient(payload.patient_id)
        if not patient:
            raise AppException(404, "patient_not_found", "Patient not found")
        if actor.branch_id and patient.branch_id and actor.branch_id != patient.branch_id:
            raise AppException(403, "forbidden", "Patient belongs to a different branch")

        # Auto-fill consultation fee based on doctor and visit type
        consultation_fee = Decimal("0")
        if payload.doctor_user_id:
            doctor = self._get_doctor(payload.doctor_user_id, actor)
            if doctor:
                if payload.visit_type == "follow_up":
                    # Check if follow-up is allowed
                    last_visit = self.db.query(OPDVisit).filter(
                        OPDVisit.patient_id == payload.patient_id,
                        OPDVisit.consulting_doctor_user_id == payload.doctor_user_id,
                        OPDVisit.status.in_(['completed', 'prescribed']),
                        OPDVisit.visit_date <= payload.visit_date,
                    ).order_by(OPDVisit.visit_date.desc()).first()
                    if last_visit:
                        days_since_last_visit = (payload.visit_date - last_visit.visit_date).days
                        if days_since_last_visit > doctor.opd_follow_up_days:
                            raise AppException(400, "follow_up_not_allowed", f"Follow-up not allowed. Last visit was {days_since_last_visit} days ago, but follow-up period is {doctor.opd_follow_up_days} days.")
                    else:
                        raise AppException(400, "no_previous_visit", "No previous visit found for follow-up.")
                    consultation_fee = doctor.opd_follow_up_fee
                else:
                    consultation_fee = doctor.opd_consultation_fee

        visit_number = f"OPD-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8].upper()}"
        slot_start_at = payload.slot_start_at
        if slot_start_at and not slot_start_at.tzinfo:
            slot_start_at = slot_start_at.replace(tzinfo=UTC)

        if payload.doctor_user_id and slot_start_at:
            self._assert_slot_within_schedule(payload.doctor_user_id, slot_start_at)

        consulting_doctor = self._get_doctor(payload.doctor_user_id, actor) if payload.doctor_user_id else None
        visit = OPDVisit(
            **payload.model_dump(exclude={"doctor_user_id", "consultation_fee", "slot_start_at"}),
            visit_number=visit_number,
            branch_id=patient.branch_id or actor.branch_id,
            source_appointment_id=source_appointment_id,
            consulting_doctor_user_id=consulting_doctor.id if consulting_doctor else None,
            slot_start_at=slot_start_at,
            consultation_fee=consultation_fee,
            consultation_total=self._money(consultation_fee),
            registered_by_user_id=actor.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_visit(visit)
        from app.modules.opd.prescriptions import audit
        audit(self.db,visit,actor,'created',{'source':'opd_registration'})
        self.db.flush()
        QueueService(self.db).ensure_token(
            QueueTokenCreate(
                queue_scope="opd",
                module="opd",
                service_area="consultation",
                department_name=visit.department_name,
                doctor_user_id=visit.consulting_doctor_user_id,
                patient_id=visit.patient_id,
                patient_label=patient_label(patient),
                priority="follow_up" if payload.visit_type.value == "follow_up" else "normal",
                source_type="opd_visit",
                source_id=visit.id,
                visit_id=visit.id,
                appointment_id=source_appointment_id,
                due_at=slot_start_at,
                meta={"visit_type": payload.visit_type.value, "visit_number": visit.visit_number, "entry_type": "appointment" if source_appointment_id else "walk_in"},
            ),
            actor,
            commit=False,
        )
        if consulting_doctor and slot_start_at:
            self._create_slot_booking_for_visit(
                visit=visit,
                doctor_user_id=consulting_doctor.id,
                slot_start_at=slot_start_at,
                actor=actor,
            )
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_CREATE,
            module="opd",
            entity_type="opd_visit",
            entity_id=str(visit.id),
            detail={"visit_number": visit.visit_number, "patient_id": str(visit.patient_id), "visit_type": payload.visit_type.value},
            context=context,
        )
        if commit:
            self.db.commit()
            self.db.refresh(visit)
        return self.repository.get_visit(visit.id) or visit

    def update_visit(self, visit_id, payload: OPDVisitUpdate, actor: User, context: dict[str, str | None]) -> OPDVisit:
        visit = self.get_visit(visit_id, actor)
        if visit.prescription_status in {'finalized','voided'} and (payload.chief_complaint!=visit.chief_complaint or payload.doctor_user_id!=visit.consulting_doctor_user_id):
            raise AppException(409,'prescription_signed','Signed clinical identity and complaints require a controlled prescription amendment or a new consultation')

        if visit.status not in {"waiting", "billed"}:
            raise AppException(409, "opd_visit_active", "Only a waiting visit can be reassigned or rescheduled")
        previous_doctor_id = visit.consulting_doctor_user_id
        consulting_doctor = self._get_doctor(payload.doctor_user_id, actor) if payload.doctor_user_id else None
        new_slot_start = payload.slot_start_at or visit.slot_start_at
        if new_slot_start and not new_slot_start.tzinfo:
            new_slot_start = new_slot_start.replace(tzinfo=UTC)
        if consulting_doctor:
            if not new_slot_start:
                raise AppException(400, "slot_required", "Slot time is required when doctor is selected")
            self._assert_slot_within_schedule(consulting_doctor.id, new_slot_start)

        visit.visit_date = payload.visit_date
        visit.slot_start_at = new_slot_start
        visit.department_name = payload.department_name
        visit.consulting_doctor_user_id = consulting_doctor.id if consulting_doctor else None
        visit.consulting_doctor_name = payload.consulting_doctor_name
        visit.chief_complaint = payload.chief_complaint
        visit.consultation_fee = payload.consultation_fee
        visit.consultation_total = self._money(max(payload.consultation_fee - (visit.consultation_discount or Decimal("0")), Decimal("0")))
        visit.note = payload.note
        visit.updated_by = actor.id
        if consulting_doctor and new_slot_start:
            self._upsert_slot_booking_for_visit(
                visit=visit,
                doctor_user_id=consulting_doctor.id,
                slot_start_at=new_slot_start,
                actor=actor,
            )
        elif not consulting_doctor:
            booking = self.db.scalar(select(DoctorSlotBooking).where(DoctorSlotBooking.opd_visit_id == visit.id))
            if booking:
                self.db.delete(booking)
                self.db.flush()
        token = self.db.scalar(select(QueueToken).where(QueueToken.visit_id == visit.id, QueueToken.queue_scope == "opd"))
        if token and previous_doctor_id != visit.consulting_doctor_user_id:
            self.db.flush()
            QueueService(self.db).transfer(token.id, QueueTransferRequest(
                queue_scope="opd", module="opd", service_area="consultation",
                doctor_user_id=visit.consulting_doctor_user_id, department_name=visit.department_name,
            ), actor, commit=False, internal=True)
        if token:
            token.due_at = new_slot_start
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_STATUS_UPDATE,
            module="opd",
            entity_type="opd_visit",
            entity_id=str(visit.id),
            detail={"visit_number": visit.visit_number, "visit_updated": True},
            context=context,
        )
        self.db.commit()
        self.db.refresh(visit)
        return visit

    def update_payment(self, visit_id, payload: OPDVisitPaymentUpdate, actor: User, context: dict[str, str | None]) -> OPDVisit:
        # Hospital collections must use the same receipt/ledger path as the billing desk.
        from app.modules.billing.service import BillingServiceManager
        from app.schemas.billing import BillingInvoiceCreate, BillingInvoiceItemCreate, BillingPaymentCreate
        billing=BillingServiceManager(self.db)
        visit=self.get_visit(visit_id,actor)
        billing.list_services(actor)
        invoice=billing.repository.get_invoice_by_source(source_opd_visit_id=visit.id,billing_stage='opd')
        if not invoice:
            config=billing._consultation_service_for_visit(visit,actor)
            if not config:raise AppException(422,'consultation_catalog','Configure the doctor consultation fee first')
            if payload.amount!=config.unit_price:raise AppException(422,'consultation_fee_mismatch','Use an approved billing fee override to change the consultation fee')
            invoice=billing.create_invoice(BillingInvoiceCreate(patient_id=visit.patient_id,source_opd_visit_id=visit.id,source_module='opd',billing_stage='opd',discount_reason='Authorized OPD consultation concession' if payload.discount else None,items=[BillingInvoiceItemCreate(billing_service_id=config.id,quantity=1,discount_amount=payload.discount)]),actor,context,commit=False)
        if invoice.paid_amount>0:raise AppException(409,'consultation_collection_exists','Use the billing desk to collect the remaining balance without duplicating receipts')
        if invoice.total_amount != payload.amount-payload.discount:raise AppException(422,'consultation_invoice_mismatch','The consultation invoice changed; collect its recorded balance from billing')
        if invoice.due_amount>0:billing.create_payment(invoice.id,BillingPaymentCreate(amount=invoice.due_amount,payment_method='cash'),actor,context)
        visit=self.get_visit(visit_id,actor);visit.consultation_payment_source='hospital';self.db.commit()
        return visit

    def update_status(self, visit_id, status: str, actor: User, context: dict[str, str | None]) -> OPDVisit:
        visit = self.get_visit(visit_id, actor)
        transitions = {
            "waiting": {"in_consultation", "cancelled"},
            "billed": {"in_consultation", "cancelled"},
            "in_consultation": {"prescribed", "completed", "waiting", "cancelled"},
            "prescribed": {"completed"},
            "completed": set(), "cancelled": set(),
        }
        if status != visit.status and status not in transitions.get(visit.status, set()):
            raise AppException(409, "opd_invalid_transition", f"Cannot change visit from {visit.status} to {status}")
        visit.status = status
        visit.updated_by = actor.id
        queue_token = self.db.scalar(select(QueueToken).where(QueueToken.visit_id == visit.id, QueueToken.queue_scope == "opd", QueueToken.is_active.is_(True)))
        if queue_token and status in {"in_consultation", "prescribed", "completed", "cancelled"}:
            target_queue_status = {"in_consultation": "in_progress", "prescribed": "completed", "completed": "completed", "cancelled": "cancelled"}[status]
            if target_queue_status != queue_token.status:
                QueueService(self.db).update_status(queue_token.id, target_queue_status, actor, notes=f"Synchronized from OPD visit {visit.visit_number}", commit=False, internal=True)
        if status == "prescribed":
            prescription_orders = [order for order in visit.orders if order.order_type == "prescription" and order.status != "cancelled"]
            if prescription_orders:
                QueueService(self.db).ensure_token(
                    QueueTokenCreate(
                        queue_scope="pharmacy",
                        module="pharmacy",
                        service_area="dispense",
                        department_name=visit.department_name,
                        patient_id=visit.patient_id,
                        patient_label=patient_label(visit.patient),
                        source_type="opd_prescription",
                        source_id=visit.id,
                        visit_id=visit.id,
                        meta={"visit_number": visit.visit_number, "items": len(prescription_orders)},
                    ),
                    actor,
                    commit=False,
                )
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_STATUS_UPDATE,
            module="opd",
            entity_type="opd_visit",
            entity_id=str(visit.id),
            detail={"visit_number": visit.visit_number, "status": status},
            context=context,
        )
        self.db.commit()
        self.db.refresh(visit)
        return visit

    def update_consultation(self, visit_id, payload: OPDVisitConsultationUpdate, actor: User, context: dict[str, str | None], *, commit: bool = True) -> OPDVisit:
        visit = self.get_visit(visit_id, actor)
        from app.modules.opd.prescriptions import lock_visit, assert_draft, audit
        lock_visit(self.db,visit);assert_draft(visit)
        if payload.expected_version is not None and payload.expected_version != visit.clinical_version:
            raise AppException(409,'prescription_conflict','The draft changed in another session; reload before saving')
        before={key:getattr(visit,key) for key in ['chief_complaint','history_of_present_illness','past_history','vital_signs','examination_note','provisional_diagnosis','final_diagnosis','follow_up_note']}
        before['prescription_data']=visit.prescription_data
        values=payload.model_dump(exclude_unset=True,exclude={'expected_version'})
        if payload.prescription_data is not None:
            import json
            try:encoded=json.dumps(payload.prescription_data,allow_nan=False)
            except (ValueError,TypeError):raise AppException(422,'prescription_data','Clinical data must contain finite, JSON-compatible values')
            if len(encoded)>500000:raise AppException(422,'prescription_content_size','Prescription exceeds the supported draft size')
            from app.modules.opd.prescriptions import CLINICAL_FIELDS
            canonical={key:value for key,value in payload.prescription_data.items() if key in CLINICAL_FIELDS}
            if canonical:
                try:validated=OPDVisitConsultationUpdate.model_validate(canonical)
                except ValueError:raise AppException(422,'prescription_data','A configured field contains invalid clinical data')
                values.update(validated.model_dump(exclude_unset=True))
        for field, value in values.items():
            setattr(visit, field, value)
        visit.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_STATUS_UPDATE,
            module="opd",
            entity_type="opd_visit",
            entity_id=str(visit.id),
            detail={"visit_number": visit.visit_number, "consultation_updated": True},
            context=context,
        )
        visit.clinical_version += 1
        audit(self.db,visit,actor,'draft_saved',{'clinical_version':visit.clinical_version,'before':before})
        if commit:
            self.db.commit()
            self.db.refresh(visit)
        return visit

    def finalize_prescription(self, visit_id, payload: OPDVisitConsultationUpdate, actor: User, context: dict[str, str | None]) -> OPDVisit:
        visit = self.get_visit(visit_id, actor)
        token = self.db.scalar(select(QueueToken).where(QueueToken.visit_id == visit.id, QueueToken.queue_scope == "opd"))
        if token:
            QueueService(self.db)._lock_queue(token.branch_id, "opd", token.token_date, token.doctor_user_id)
        self.db.refresh(visit, with_for_update={"of": OPDVisit})
        from app.modules.opd.prescriptions import assert_signer, sign
        assert_signer(visit,actor)
        if visit.prescription_status == "voided":raise AppException(409,"prescription_voided","A voided prescription cannot be signed again")
        if visit.prescription_status == "finalized":
            return visit  # A retried finalization must not call another serial.
        if visit.status != "in_consultation" and visit.prescription_status != "amended":
            raise AppException(409, "opd_consultation_required", "Start the consultation before finalizing a prescription")
        self.update_consultation(visit.id, payload, actor, context, commit=False)
        self.db.expire(visit,["orders"])
        sign(self.db,visit,actor)
        if visit.status in {"prescribed","completed"}:
            self.db.commit();self.db.refresh(visit);return visit
        return self.update_status(visit.id, "prescribed", actor, context)

    def create_order(self, visit_id, payload: OPDVisitOrderCreate, actor: User, context: dict[str, str | None], *, commit: bool = True) -> OPDVisit:
        visit = self.get_visit(visit_id, actor)

        from app.modules.opd.prescriptions import assert_draft, lock_visit
        lock_visit(self.db,visit);assert_draft(visit)
        if payload.request_key:
            prior = self.db.scalar(select(OPDVisitOrder).where(OPDVisitOrder.visit_id==visit.id,OPDVisitOrder.request_key==payload.request_key))
            if prior:
                if prior.order_type != payload.order_type or prior.item_name != payload.item_name or prior.instructions != payload.instructions or prior.quantity != payload.quantity:
                    raise AppException(409,'prescription_order_conflict','Order request key was used with different content')
                return visit
        if payload.order_type=='investigation' and any(o.order_type=='investigation' and o.service_area==payload.service_area and o.item_name.casefold().strip()==payload.item_name.casefold().strip() and o.status!='cancelled' for o in visit.orders):
            return visit
        if payload.order_type=='prescription' and (payload.prescription_detail or {}).get('catalog_id'):
            from app.models.pharmacy import PharmacyMedicine
            from uuid import UUID
            try:catalog_id=UUID(payload.prescription_detail['catalog_id'])
            except (ValueError,TypeError):raise AppException(422,'prescription_catalog','Invalid catalog medicine')
            medicine=self.db.get(PharmacyMedicine,catalog_id)
            if not medicine or not medicine.is_active or medicine.branch_id not in {None,visit.branch_id}:
                raise AppException(422,'prescription_catalog','Medicine is not available in this approved catalog')
            expected=' '.join(value for value in [medicine.name,medicine.strength] if value)
            if payload.item_name!=expected or not payload.prescription_detail.get('confirmed_by_doctor'):
                raise AppException(422,'prescription_selection','Explicitly confirm the selected brand and strength; substitutions are not automatic')
            payload.prescription_detail={**payload.prescription_detail,'catalog_snapshot':{'name':medicine.name,'generic':medicine.generic.name,'strength':medicine.strength,'dosage_form':medicine.dosage_form,'manufacturer':medicine.company.name}}
        order = OPDVisitOrder(
            visit_id=visit.id,
            **payload.model_dump(),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.repository.create_order(order)

        # Create linked domain records for investigation orders
        if order.order_type == "investigation":
            if order.service_area == "laboratory":
                lab_order = LabOrder(
                    branch_id=visit.branch_id,
                    patient_id=visit.patient_id,
                    visit_id=visit.id,
                    order_number=f"LAB-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8].upper()}",
                    status="pending",
                    created_by=actor.id,
                    updated_by=actor.id,
                )
                self.db.add(lab_order)
                self.db.flush()
                lab_item = LabOrderItem(
                    order_id=lab_order.id,
                    test_name=order.item_name,
                    quantity=order.quantity,
                    created_by=actor.id,
                    updated_by=actor.id,
                )
                self.db.add(lab_item)
                order.lab_order_id = lab_order.id
                QueueService(self.db).ensure_token(
                    QueueTokenCreate(
                        queue_scope="laboratory",
                        module="laboratory",
                        service_area="sample_collection",
                        department_name=visit.department_name,
                        patient_id=visit.patient_id,
                        patient_label=patient_label(visit.patient),
                        source_type="lab_order",
                        source_id=lab_order.id,
                        visit_id=visit.id,
                        order_id=lab_order.id,
                        meta={"visit_number": visit.visit_number, "test": order.item_name},
                    ),
                    actor,
                    commit=False,
                )
            elif order.service_area == "radiology":
                rad_order = RadiologyOrder(
                    branch_id=visit.branch_id,
                    patient_id=visit.patient_id,
                    visit_id=visit.id,
                    order_number=f"RAD-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8].upper()}",
                    study_description=order.item_name,
                    status="pending",
                    created_by=actor.id,
                    updated_by=actor.id,
                )
                self.db.add(rad_order)
                self.db.flush()
                order.radiology_order_id = rad_order.id
                QueueService(self.db).ensure_token(
                    QueueTokenCreate(
                        queue_scope="radiology",
                        module="radiology",
                        service_area="imaging",
                        department_name=visit.department_name,
                        patient_id=visit.patient_id,
                        patient_label=patient_label(visit.patient),
                        source_type="radiology_order",
                        source_id=rad_order.id,
                        visit_id=visit.id,
                        order_id=rad_order.id,
                        meta={"visit_number": visit.visit_number, "study": order.item_name},
                    ),
                    actor,
                    commit=False,
                )

        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_ORDER_CREATE,
            module="opd",
            entity_type="opd_visit_order",
            entity_id=str(order.id),
            detail={"visit_number": visit.visit_number, "order_type": order.order_type, "item_name": order.item_name},
            context=context,
        )
        if commit:self.db.commit()
        else:self.db.flush()
        return self.repository.get_visit(visit.id) or visit

    def update_order(self, visit_id, order_id, payload: OPDVisitOrderUpdate, actor: User, context: dict[str, str | None]) -> OPDVisit:
        visit = self.get_visit(visit_id, actor)
        from app.modules.opd.prescriptions import assert_draft, lock_visit
        lock_visit(self.db,visit)
        if payload.model_fields_set.intersection({'item_name','instructions','quantity','service_area'}):assert_draft(visit)

        order = self.repository.get_order(order_id)
        if not order or order.visit_id != visit.id:
            raise AppException(404, "opd_order_not_found", "OPD order not found")
        self.db.refresh(order,with_for_update={'of':OPDVisitOrder})
        if payload.expected_version is not None and payload.expected_version!=order.version:raise AppException(409,'prescription_order_conflict','This order changed in another session; reload it before editing')
        if order.status in {'completed','verified'} and payload.model_fields_set.intersection({'item_name','instructions','quantity','service_area'}):raise AppException(409,'prescription_order_fulfilled','Completed clinical orders cannot have their original intent rewritten')
        order.version+=1


        if payload.item_name is not None:
            order.item_name = payload.item_name
        if payload.instructions is not None:
            order.instructions = payload.instructions
        if payload.quantity is not None:
            order.quantity = payload.quantity
        if payload.room_number is not None:
            order.room_number = payload.room_number
        if payload.sample_note is not None:
            order.sample_note = payload.sample_note
        if payload.result_text is not None:
            order.result_text = payload.result_text
        if payload.service_area is not None:
            if order.order_type == "investigation" and payload.service_area == "pharmacy":
                raise AppException(400, "invalid_service_area", "Investigation orders require laboratory or radiology service area")
            order.service_area = "pharmacy" if order.order_type == "prescription" else payload.service_area
        elif order.order_type == "prescription":
            order.service_area = "pharmacy"

        if payload.status is not None:
            order.status = payload.status
        if order.status == "completed":
            order.completed_at = datetime.now(UTC)
            order.completed_by_user_id = actor.id
        elif payload.status is not None:
            order.completed_at = None
            order.completed_by_user_id = None
        order.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_ORDER_UPDATE,
            module="opd",
            entity_type="opd_visit_order",
            entity_id=str(order.id),
            detail={"visit_number": visit.visit_number, "order_type": order.order_type, "status": payload.status},
            context=context,
        )
        self.db.commit()
        return self.repository.get_visit(visit.id) or visit

    def delete_order(self, visit_id, order_id, actor: User, context: dict[str, str | None]) -> OPDVisit:
        visit = self.get_visit(visit_id, actor)
        from app.modules.opd.prescriptions import assert_draft, lock_visit
        lock_visit(self.db,visit);assert_draft(visit)
        order = self.repository.get_order(order_id)
        if not order or order.visit_id != visit.id:
            raise AppException(404, "opd_order_not_found", "OPD order not found")
        if order.status in {"completed", "verified"}:
            if visit.prescription_status!='amended':raise AppException(400,"opd_order_locked","Completed orders require a prescription amendment for logical withdrawal")
            from app.modules.opd.prescriptions import assert_signer,audit
            assert_signer(visit,actor)
            order.prescription_detail={**(order.prescription_detail or {}),'_withdrawn_from_rx':True,'withdrawn_at':datetime.now(UTC).isoformat(),'withdrawal_reason':(visit.prescription_data or {}).get('_amendment_reason'),'withdrawn_by':str(actor.id)}
            order.version+=1
            audit(self.db,visit,actor,'order_withdrawn',{'order_id':str(order.id),'completed_care_preserved':True})
            self.db.commit();return self.get_visit(visit.id,actor)

        order.status = "cancelled"
        order.updated_by = actor.id
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.OPD_VISIT_ORDER_UPDATE,
            module="opd",
            entity_type="opd_visit_order",
            entity_id=str(order.id),
            detail={"visit_number": visit.visit_number, "order_type": order.order_type, "status": "cancelled", "removed_from_prescription": True},
            context=context,
        )
        self.db.commit()
        return self.repository.get_visit(visit.id) or visit

    def convert_to_ipd(self, visit_id, payload: OPDConvertToIPD, actor: User, context: dict[str, str | None]):
        visit = self.get_visit(visit_id, actor)
        current_token = self.db.scalar(select(QueueToken).where(QueueToken.visit_id == visit.id, QueueToken.queue_scope == "opd"))
        if current_token:
            QueueService(self.db)._lock_queue(current_token.branch_id, "opd", current_token.token_date, current_token.doctor_user_id)
        self.db.refresh(visit, with_for_update={"of": OPDVisit})
        if visit.status == "cancelled":
            raise AppException(409, "opd_cancelled", "A cancelled visit cannot be admitted to IPD")
        if visit.converted_ipd_admission_id:
            raise AppException(409, "opd_already_converted", "OPD visit already converted to IPD")

        ipd_payload = IPDAdmissionCreate(
            patient_id=visit.patient_id,
            bed_id=payload.bed_id,
            admitted_at=payload.admitted_at,
            admission_type=payload.admission_type,
            admission_source="OPD",
            department_name=payload.department_name or visit.department_name,
            patient_condition=payload.patient_condition,
            ward_name=payload.ward_name,
            bed_number=payload.bed_number,
            doctor_user_id=payload.doctor_user_id or visit.consulting_doctor_user_id,
            attending_doctor_name=payload.attending_doctor_name or visit.consulting_doctor_name,
            diagnosis=payload.diagnosis or visit.final_diagnosis or visit.provisional_diagnosis or visit.chief_complaint,
            daily_charge=payload.daily_charge,
            advance_amount=payload.advance_amount,
            expected_discharge_date=payload.expected_discharge_date,
        )
        admission = IPDService(self.db).create_admission(ipd_payload, actor, context, commit=False)
        visit.converted_ipd_admission_id = admission.id
        visit.status = "completed"
        visit.updated_by = actor.id
        queue_token = self.db.scalar(select(QueueToken).where(QueueToken.visit_id == visit.id, QueueToken.queue_scope == "opd", QueueToken.is_active.is_(True)))
        if queue_token and queue_token.status not in {"completed", "cancelled", "no_show"}:
            if queue_token.status != "in_progress":
                queue_token.status = "in_progress"
            QueueService(self.db).update_status(queue_token.id, "completed", actor, notes=f"OPD visit converted to {admission.admission_number}", commit=False, internal=True)
        AuditService(self.db).log(
            user_id=actor.id,
            action=AuditAction.IPD_ADMISSION_CREATE,
            module="opd",
            entity_type="opd_visit",
            entity_id=str(visit.id),
            detail={"visit_number": visit.visit_number, "admission_number": admission.admission_number},
            context=context,
        )
        self.db.commit()
        return admission

    def _get_doctor(self, user_id, actor: User) -> User:
        doctor = self.users.get_user(user_id)
        if not doctor or not doctor.is_active:
            raise AppException(404, "doctor_not_found", "Doctor user not found")
        if actor.branch_id and doctor.branch_id and actor.branch_id != doctor.branch_id:
            raise AppException(403, "forbidden", "Doctor belongs to a different branch")
        if not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(400, "invalid_doctor_user", "Selected user is not configured as a doctor")
        return doctor

    def _validate_visit_access(self, visit: OPDVisit, actor: User) -> OPDVisit:
        if actor.branch_id and visit.branch_id and actor.branch_id != visit.branch_id:
            raise AppException(403, "forbidden", "OPD visit belongs to a different branch")

        if self._can_view_all_doctors(actor):
            return visit

        if self._is_doctor(actor) and visit.consulting_doctor_user_id == actor.id:
            return visit

        raise AppException(403, "forbidden", "You do not have access to this OPD visit")

    def _resolve_doctor_scope(self, actor: User, doctor_user_id):
        if doctor_user_id:
            doctor = self._get_doctor(doctor_user_id, actor)
            if self._can_view_all_doctors(actor):
                return doctor.id
            if self._is_doctor(actor) and doctor.id == actor.id:
                return actor.id
            raise AppException(403, "forbidden", "You do not have access to another doctor's OPD queue")

        if self._can_view_all_doctors(actor):
            return None

        if self._is_doctor(actor):
            return actor.id

        raise AppException(403, "forbidden", "Doctor-wise OPD access must be granted from administration")

    def _can_view_all_doctors(self, actor: User) -> bool:
        return self.DOCTOR_WISE_VIEW_PERMISSION in self.auth.get_effective_permissions(actor)

    @staticmethod
    def _is_doctor(actor: User) -> bool:
        return any(role.is_doctor_role for role in actor.roles)

    def _money(self, value: Decimal) -> Decimal:
        return Decimal(str(value)).quantize(self.TWOPLACES)

    def _assert_slot_within_schedule(self, doctor_user_id, slot_start_at: datetime) -> None:
        schedule = self.db.scalar(
            select(DoctorOPDSchedule).where(
                DoctorOPDSchedule.doctor_user_id == doctor_user_id,
                DoctorOPDSchedule.weekday == slot_start_at.date().weekday(),
            )
        )
        if not schedule:
            raise AppException(400, "schedule_not_configured", "Doctor schedule is not configured for this day")

        start_hour, start_minute = [int(part) for part in schedule.start_time.split(":")]
        end_hour, end_minute = [int(part) for part in schedule.end_time.split(":")]
        start_dt = datetime.combine(slot_start_at.date(), time(start_hour, start_minute), tzinfo=UTC)
        end_dt = datetime.combine(slot_start_at.date(), time(end_hour, end_minute), tzinfo=UTC)
        step = timedelta(minutes=schedule.slot_duration_minutes + schedule.buffer_minutes)
        slot_size = timedelta(minutes=schedule.slot_duration_minutes)

        current = start_dt
        while current + slot_size <= end_dt:
            if current == slot_start_at:
                return
            current += step
        raise AppException(400, "slot_not_in_schedule", "Selected slot is outside configured schedule")

    def _create_slot_booking_for_visit(self, *, visit: OPDVisit, doctor_user_id, slot_start_at: datetime, actor: User) -> None:
        schedule = self.db.scalar(
            select(DoctorOPDSchedule).where(
                DoctorOPDSchedule.doctor_user_id == doctor_user_id,
                DoctorOPDSchedule.weekday == slot_start_at.date().weekday(),
            )
        )
        if not schedule:
            raise AppException(400, "schedule_not_configured", "Doctor schedule is not configured for this day")

        slot_end_at = slot_start_at + timedelta(minutes=schedule.slot_duration_minutes)
        existing_booking = None
        if visit.source_appointment_id:
            existing_booking = self.db.scalar(
                select(DoctorSlotBooking).where(
                    DoctorSlotBooking.appointment_id == visit.source_appointment_id,
                    DoctorSlotBooking.doctor_user_id == doctor_user_id,
                    DoctorSlotBooking.slot_start_at == slot_start_at,
                )
            )
        if existing_booking:
            existing_booking.opd_visit_id = visit.id
            existing_booking.source_type = "visit"
            existing_booking.updated_by = actor.id
            return

        booking = DoctorSlotBooking(
            branch_id=visit.branch_id,
            doctor_user_id=doctor_user_id,
            patient_id=visit.patient_id,
            slot_start_at=slot_start_at,
            slot_end_at=slot_end_at,
            source_type="visit",
            appointment_id=visit.source_appointment_id,
            opd_visit_id=visit.id,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(booking)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(409, "slot_conflict", "Selected slot is already booked") from exc

    def _upsert_slot_booking_for_visit(self, *, visit: OPDVisit, doctor_user_id, slot_start_at: datetime, actor: User) -> None:
        booking = self.db.scalar(select(DoctorSlotBooking).where(DoctorSlotBooking.opd_visit_id == visit.id))
        if not booking:
            self._create_slot_booking_for_visit(visit=visit, doctor_user_id=doctor_user_id, slot_start_at=slot_start_at, actor=actor)
            return
        if booking.doctor_user_id == doctor_user_id and booking.slot_start_at == slot_start_at:
            return

        schedule = self.db.scalar(
            select(DoctorOPDSchedule).where(
                DoctorOPDSchedule.doctor_user_id == doctor_user_id,
                DoctorOPDSchedule.weekday == slot_start_at.date().weekday(),
            )
        )
        if not schedule:
            raise AppException(400, "schedule_not_configured", "Doctor schedule is not configured for this day")

        booking.doctor_user_id = doctor_user_id
        booking.slot_start_at = slot_start_at
        booking.slot_end_at = slot_start_at + timedelta(minutes=schedule.slot_duration_minutes)
        booking.updated_by = actor.id
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppException(409, "slot_conflict", "Selected slot is already booked") from exc
