from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.billing import BillingInvoice
from app.models.blood_bank import BloodRequest, BloodUnit
from app.models.encounter import ERVisit, IPDAdmission, IPDMedicationAdministration, IPDNursingNote, IPDNursingTask, OPDVisit, Appointment
from app.models.inventory import InventoryItem
from app.models.laboratory import LabOrder
from app.models.notification import Notification, NotificationAuditLog, NotificationSetting
from app.models.pharmacy import PharmacyMedicine
from app.models.radiology import RadiologyOrder
from app.models.user import User
from app.modules.auth.service import AuthService
from app.schemas.notification import NotificationRead, NotificationSettingRead, NotificationSettingUpsert, NotificationSummary


ACTIVE_STATUSES = {"unread", "action_required", "in_progress", "escalated"}
TERMINAL_STATUSES = {"completed", "dismissed", "expired"}


class NotificationsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth = AuthService(db)

    def summary(self, actor: User) -> NotificationSummary:
        self.sync_for_user(actor)
        base = self._base_query(actor)
        unread = int(self.db.scalar(select(func.count(Notification.id)).where(*base, Notification.status == "unread")) or 0)
        action_required = int(self.db.scalar(select(func.count(Notification.id)).where(*base, Notification.status.in_(["action_required", "escalated"]))) or 0)
        critical = int(self.db.scalar(select(func.count(Notification.id)).where(*base, Notification.priority == "critical", Notification.status.in_(list(ACTIVE_STATUSES)))) or 0)
        latest = list(
            self.db.scalars(
                select(Notification)
                .where(*base, Notification.status.notin_(list(TERMINAL_STATUSES)))
                .order_by((Notification.priority == "critical").desc(), Notification.created_at.desc())
                .limit(8)
            )
        )
        return NotificationSummary(
            unread_count=unread,
            action_required_count=action_required,
            critical_count=critical,
            latest=[self._read(item, actor) for item in latest],
        )

    def list_notifications(
        self,
        actor: User,
        *,
        status: str | None = None,
        priority: str | None = None,
        module: str | None = None,
        category: str | None = None,
        assigned_to_me: bool = False,
        due_today: bool = False,
        overdue: bool = False,
        search: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> tuple[list[NotificationRead], int, int, int, int]:
        self.sync_for_user(actor)
        clauses = list(self._base_query(actor))
        if status:
            clauses.append(Notification.status == status)
        if priority:
            clauses.append(Notification.priority == priority)
        if module:
            clauses.append(Notification.module == module)
        if category:
            clauses.append(Notification.category == category)
        if assigned_to_me:
            clauses.append(Notification.recipient_user_id == actor.id)
        today = date.today()
        if due_today:
            start = datetime(today.year, today.month, today.day, tzinfo=UTC)
            clauses.append(Notification.due_at >= start)
            clauses.append(Notification.due_at < start + timedelta(days=1))
        if overdue:
            clauses.append(Notification.due_at < datetime.now(UTC))
            clauses.append(Notification.status.in_(list(ACTIVE_STATUSES)))
        if search:
            token = f"%{search.strip()}%"
            clauses.append(or_(Notification.title.ilike(token), Notification.message.ilike(token), Notification.related_display.ilike(token)))

        total = int(self.db.scalar(select(func.count(Notification.id)).where(*clauses)) or 0)
        items = list(
            self.db.scalars(
                select(Notification)
                .where(*clauses)
                .order_by((Notification.priority == "critical").desc(), Notification.due_at.asc().nullslast(), Notification.created_at.desc())
                .offset(offset)
                .limit(min(max(limit, 1), 100))
            )
        )
        base = self._base_query(actor)
        unread = int(self.db.scalar(select(func.count(Notification.id)).where(*base, Notification.status == "unread")) or 0)
        action_required = int(self.db.scalar(select(func.count(Notification.id)).where(*base, Notification.status.in_(["action_required", "escalated"]))) or 0)
        critical = int(self.db.scalar(select(func.count(Notification.id)).where(*base, Notification.priority == "critical", Notification.status.in_(list(ACTIVE_STATUSES)))) or 0)
        return [self._read(item, actor) for item in items], total, unread, action_required, critical

    def update_status(self, notification_id: UUID, status: str, actor: User) -> NotificationRead:
        item = self._get_owned(notification_id, actor)
        now = datetime.now(UTC)
        if status == "read":
            item.status = "read" if item.status == "unread" else item.status
            item.read_at = item.read_at or now
        elif status == "dismissed":
            item.status = "dismissed"
            item.dismissed_at = now
            item.read_at = item.read_at or now
        elif status == "completed":
            item.status = "completed"
            item.completed_at = now
            item.read_at = item.read_at or now
        elif status == "in_progress":
            item.status = "in_progress"
            item.read_at = item.read_at or now
        item.updated_by = actor.id
        self._audit(actor, item, f"notification.{status}", {"title": item.title})
        self.db.commit()
        self.db.refresh(item)
        return self._read(item, actor)

    def mark_all_read(self, actor: User) -> int:
        items = list(self.db.scalars(select(Notification).where(*self._base_query(actor), Notification.status == "unread")))
        now = datetime.now(UTC)
        for item in items:
            item.status = "read"
            item.read_at = now
            item.updated_by = actor.id
            self._audit(actor, item, "notification.read", {"bulk": True})
        self.db.commit()
        return len(items)

    def list_settings(self, actor: User) -> list[NotificationSettingRead]:
        stmt = select(NotificationSetting).where(NotificationSetting.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(NotificationSetting.branch_id == actor.branch_id, NotificationSetting.branch_id.is_(None)))
        return list(self.db.scalars(stmt.order_by(NotificationSetting.setting_key.asc())))

    def save_setting(self, payload: NotificationSettingUpsert, actor: User) -> NotificationSettingRead:
        key = payload.setting_key.strip().lower().replace(" ", "_")
        item = self.db.scalar(select(NotificationSetting).where(NotificationSetting.branch_id == actor.branch_id, NotificationSetting.setting_key == key))
        if item is None:
            item = NotificationSetting(branch_id=actor.branch_id, setting_key=key, setting_value=payload.setting_value, created_by=actor.id, updated_by=actor.id)
            self.db.add(item)
        else:
            item.setting_value = payload.setting_value
            item.updated_by = actor.id
        self.db.flush()
        self.db.add(NotificationAuditLog(branch_id=actor.branch_id, user_id=actor.id, action="notification.setting.update", module="settings", detail={"setting_key": key}, created_by=actor.id, updated_by=actor.id))
        self.db.commit()
        self.db.refresh(item)
        return item

    def sync_for_user(self, actor: User) -> None:
        permissions = set(self.auth.get_effective_permissions(actor))
        now = datetime.now(UTC)
        role_codes = {role.code for role in actor.roles if role.is_active}

        def has(*codes: str) -> bool:
            return any(code in permissions for code in codes)

        if has("ipd.view"):
            self._sync_ipd(actor, permissions, role_codes, now)
        if has("opd.view", "appointment.view"):
            self._sync_opd_appointments(actor, permissions)
        if has("er.view", "emergency.view"):
            self._sync_er(actor)
        if has("laboratory.view"):
            self._sync_lab(actor)
        if has("radiology.view"):
            self._sync_radiology(actor)
        if has("pharmacy.view", "pharmacy.dispense"):
            self._sync_pharmacy(actor)
        if has("inventory.view"):
            self._sync_inventory(actor)
        if has("billing.view"):
            self._sync_billing(actor)
        if has("blood_bank.view", "blood_bank.stock.view"):
            self._sync_blood_bank(actor)
        if has("hr.view", "payroll.view"):
            self._sync_hr_payroll(actor, permissions)
        if has("accounting.view", "accounting.manage"):
            self._sync_accounting(actor)
        if has("settings.role.manage", "settings.permission.manage"):
            self._ensure(
                actor,
                source_key="admin:security-review",
                title="Security and permission review",
                message="Review recent role, permission, and configuration changes from Administration.",
                category="security",
                module="admin",
                priority="informational",
                notification_type="system_alert",
                route="/admin/roles",
                action_label="Review Roles",
                action_permission="settings.role.manage",
            )
        self._expire_stale(actor)
        self.db.commit()

    def _sync_ipd(self, actor: User, permissions: set[str], role_codes: set[str], now: datetime) -> None:
        stmt = select(IPDAdmission).where(IPDAdmission.status == "admitted")
        if actor.branch_id:
            stmt = stmt.where(IPDAdmission.branch_id == actor.branch_id)
        if "DOCTOR" in role_codes:
            stmt = stmt.where(IPDAdmission.attending_doctor_user_id == actor.id)
        if any(code in role_codes for code in {"NURSE", "OT_NURSE"}) or "ipd.medication.administer" in permissions:
            stmt = stmt.where(or_(IPDAdmission.assigned_nurse_user_id == actor.id, IPDAdmission.assigned_nurse_user_id.is_(None)))
        for admission in self.db.scalars(stmt.limit(8)):
            if "ipd.medication.administer" in permissions:
                med_stmt = select(IPDMedicationAdministration).where(
                    IPDMedicationAdministration.admission_id == admission.id,
                    IPDMedicationAdministration.status.in_(["scheduled", "due", "overdue"]),
                ).order_by(IPDMedicationAdministration.scheduled_at.asc()).limit(3)
                for med in self.db.scalars(med_stmt):
                    due_at = med.scheduled_at
                    priority = "high" if due_at and due_at < now else "medium"
                    self._ensure(
                        actor,
                        source_key=f"ipd:med:{med.id}",
                        title="Medication administration due",
                        message=f"{admission.ward_name} Bed {admission.bed_number}: {med.medicine_name} {med.dose or ''} {med.route or ''}".strip(),
                        category="medication",
                        module="ipd",
                        priority=priority,
                        status="action_required",
                        notification_type="reminder",
                        related_record_type="ipd_medication",
                        related_record_id=med.id,
                        related_display=f"{admission.admission_number} · {med.medicine_name}",
                        route="/ipd",
                        action_label="Administer Medicine",
                        action_permission="ipd.medication.administer",
                        due_at=due_at,
                    )
            if "ipd.nursing_note.create" in permissions:
                recent_vitals = self.db.scalar(
                    select(IPDNursingNote)
                    .where(IPDNursingNote.admission_id == admission.id)
                    .order_by(IPDNursingNote.recorded_at.desc())
                    .limit(1)
                )
                due = not recent_vitals or recent_vitals.recorded_at < now - timedelta(hours=8)
                if due:
                    self._ensure(
                        actor,
                        source_key=f"ipd:vitals:{admission.id}:{date.today().isoformat()}",
                        title="Vitals monitoring due",
                        message=f"{admission.ward_name} Bed {admission.bed_number}: record vitals for assigned patient.",
                        category="nursing",
                        module="ipd",
                        priority="medium",
                        status="action_required",
                        notification_type="scheduled",
                        related_record_type="ipd_admission",
                        related_record_id=admission.id,
                        related_display=admission.admission_number,
                        route="/ipd",
                        action_label="Add Vitals",
                        action_permission="ipd.nursing_note.create",
                        due_at=now,
                    )
            if "ipd.discharge.approve" in permissions and admission.discharge_status in {"requested", "planned", "pending_approval"}:
                self._ensure(
                    actor,
                    source_key=f"ipd:discharge:{admission.id}",
                    title="Discharge approval pending",
                    message=f"{admission.admission_number}: discharge workflow needs review.",
                    category="clinical",
                    module="ipd",
                    priority="high",
                    status="action_required",
                    notification_type="approval_request",
                    related_record_type="ipd_admission",
                    related_record_id=admission.id,
                    related_display=admission.admission_number,
                    route="/ipd/admissions",
                    action_label="Review Discharge",
                    action_permission="ipd.discharge.approve",
                )
        if "ipd.handover.acknowledge" in permissions:
            tasks = select(IPDNursingTask).where(IPDNursingTask.status.in_(["pending", "assigned", "overdue"]))
            for task in self.db.scalars(tasks.limit(5)):
                self._ensure(
                    actor,
                    source_key=f"ipd:nursing-task:{task.id}",
                    title="Nursing task pending",
                    message=task.title,
                    category="nursing",
                    module="ipd",
                    priority="high" if task.status == "overdue" else "medium",
                    status="action_required",
                    notification_type="task_assignment",
                    related_record_type="ipd_nursing_task",
                    related_record_id=task.id,
                    related_display=task.title,
                    route="/ipd",
                    action_label="Complete Task",
                    action_permission="ipd.nursing_note.create",
                    due_at=task.due_at,
                )

    def _sync_opd_appointments(self, actor: User, permissions: set[str]) -> None:
        today = date.today()
        if "appointment.view" in permissions:
            stmt = select(Appointment).where(func.date(Appointment.appointment_at) == today, Appointment.status.in_(["scheduled", "confirmed"]))
            if actor.branch_id:
                stmt = stmt.where(Appointment.branch_id == actor.branch_id)
            if "opd.prescribe" in permissions:
                stmt = stmt.where(Appointment.doctor_user_id == actor.id)
            count = int(self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
            if count:
                self._ensure(actor, source_key=f"appointment:today:{actor.id}:{today}", title="Appointment queue updated", message=f"{count} appointment(s) scheduled/confirmed today.", category="clinical", module="appointments", priority="medium", notification_type="instant", route="/appointments", action_label="Open Queue", action_permission="appointment.view")
        if "opd.view" in permissions:
            visit_stmt = select(func.count(OPDVisit.id)).where(OPDVisit.visit_date == today, OPDVisit.status.in_(["waiting", "in_consultation"]))
            if actor.branch_id:
                visit_stmt = visit_stmt.where(OPDVisit.branch_id == actor.branch_id)
            waiting = int(self.db.scalar(visit_stmt) or 0)
            if waiting:
                self._ensure(actor, source_key=f"opd:waiting:{today}", title="OPD patients waiting", message=f"{waiting} OPD patient(s) are waiting or in consultation.", category="clinical", module="opd", priority="medium", status="action_required", notification_type="instant", route="/opd/visits", action_label="Open OPD", action_permission="opd.view")

    def _sync_er(self, actor: User) -> None:
        stmt = select(ERVisit).where(ERVisit.status.in_(["waiting", "triaged", "assigned", "in_treatment"]))
        if actor.branch_id:
            stmt = stmt.where(ERVisit.branch_id == actor.branch_id)
        for visit in self.db.scalars(stmt.order_by(ERVisit.triage_level.asc(), ERVisit.arrival_time.asc()).limit(5)):
            priority = "critical" if visit.triage_category in {"red", "critical"} or visit.triage_level <= 1 else "high"
            self._ensure(actor, source_key=f"er:active:{visit.id}", title="Emergency patient needs attention", message=f"{visit.visit_number}: {visit.triage_category} triage, status {visit.status}.", category="clinical", module="er", priority=priority, status="action_required", notification_type="instant", related_record_type="er_visit", related_record_id=visit.id, related_display=visit.visit_number, route="/er", action_label="Open ER", action_permission="er.view", due_at=visit.arrival_time + timedelta(minutes=30))

    def _sync_lab(self, actor: User) -> None:
        rows = self._status_counts(LabOrder, ["pending", "collected", "in_progress"])
        for status, count in rows.items():
            if count:
                self._ensure(actor, source_key=f"lab:{status}", title=f"Lab {status.replace('_', ' ')} workload", message=f"{count} lab order(s) require attention.", category="lab", module="laboratory", priority="high" if status == "collected" else "medium", status="action_required", notification_type="task_assignment", route="/laboratory", action_label="Open Lab", action_permission="laboratory.view")

    def _sync_radiology(self, actor: User) -> None:
        rows = self._status_counts(RadiologyOrder, ["pending", "in_progress", "reported"])
        for status, count in rows.items():
            if count:
                self._ensure(actor, source_key=f"radiology:{status}", title=f"Radiology {status.replace('_', ' ')} workload", message=f"{count} radiology order(s) require attention.", category="radiology", module="radiology", priority="medium", status="action_required", notification_type="task_assignment", route="/radiology", action_label="Open Radiology", action_permission="radiology.view")

    def _sync_pharmacy(self, actor: User) -> None:
        low = self._count_branch(PharmacyMedicine, PharmacyMedicine.stock_quantity <= PharmacyMedicine.reorder_level, actor.branch_id)
        if low:
            self._ensure(actor, source_key="pharmacy:low-stock", title="Pharmacy low stock", message=f"{low} medicine(s) are at or below reorder level.", category="pharmacy", module="pharmacy", priority="high", status="action_required", notification_type="system_alert", route="/pharmacy/medicines", action_label="Review Stock", action_permission="pharmacy.view")

    def _sync_inventory(self, actor: User) -> None:
        low = self._count_branch(InventoryItem, InventoryItem.stock_quantity <= InventoryItem.reorder_level, actor.branch_id)
        if low:
            self._ensure(actor, source_key="inventory:low-stock", title="Inventory low stock", message=f"{low} inventory item(s) are at or below reorder level.", category="inventory", module="inventory", priority="high", status="action_required", notification_type="system_alert", route="/inventory/items", action_label="Review Items", action_permission="inventory.view")

    def _sync_billing(self, actor: User) -> None:
        stmt = select(func.count(BillingInvoice.id)).where(BillingInvoice.status == "posted", BillingInvoice.payment_status.in_(["unpaid", "partial"]))
        if actor.branch_id:
            stmt = stmt.where(BillingInvoice.branch_id == actor.branch_id)
        due = int(self.db.scalar(stmt) or 0)
        if due:
            self._ensure(actor, source_key="billing:pending-dues", title="Pending billing payments", message=f"{due} posted invoice(s) have unpaid or partial payment status.", category="billing", module="billing", priority="medium", status="action_required", notification_type="task_assignment", route="/billing/due-payments", action_label="Process Payment", action_permission="billing.view")

    def _sync_blood_bank(self, actor: User) -> None:
        requests = self._count_branch(BloodRequest, BloodRequest.status.in_(["requested", "under_review", "crossmatch_pending", "ready_to_issue"]), actor.branch_id)
        if requests:
            self._ensure(actor, source_key="blood-bank:pending-requests", title="Blood bank requests pending", message=f"{requests} blood request(s) need review, crossmatch, or issue.", category="blood_bank", module="blood_bank", priority="high", status="action_required", notification_type="task_assignment", route="/blood-bank", action_label="Open Blood Bank", action_permission="blood_bank.view")
        near = int(self.db.scalar(select(func.count(BloodUnit.id)).where(BloodUnit.status == "available", BloodUnit.expiry_date <= date.today() + timedelta(days=7))) or 0)
        if near:
            self._ensure(actor, source_key="blood-bank:near-expiry", title="Blood units near expiry", message=f"{near} available blood unit/component record(s) expire within 7 days.", category="blood_bank", module="blood_bank", priority="high", notification_type="reminder", route="/blood-bank", action_label="Review Stock", action_permission="blood_bank.stock.view")

    def _sync_hr_payroll(self, actor: User, permissions: set[str]) -> None:
        if "hr.leave.manage" in permissions:
            self._ensure(actor, source_key="hr:leave-review", title="HR leave and attendance review", message="Review pending leave, attendance correction, and document tasks.", category="hr", module="hr", priority="informational", notification_type="task_assignment", route="/hr/leave", action_label="Open Leave", action_permission="hr.leave.manage")
        if "payroll.view" in permissions:
            self._ensure(actor, source_key="payroll:exceptions", title="Payroll exception review", message="Review payroll exceptions, approval status, and payslip generation before processing.", category="payroll", module="payroll", priority="medium", status="action_required", notification_type="approval_request", route="/hr/payroll", action_label="Review Payroll", action_permission="payroll.view")

    def _sync_accounting(self, actor: User) -> None:
        self._ensure(actor, source_key="accounting:approvals", title="Accounting approvals", message="Review vouchers, expenses, supplier payments, and cash handover queues.", category="accounting", module="accounting", priority="informational", notification_type="approval_request", route="/accounting", action_label="Open Accounting", action_permission="accounting.view")

    def _status_counts(self, model: Any, statuses: list[str]) -> dict[str, int]:
        stmt = select(model.status, func.count(model.id)).where(model.status.in_(statuses)).group_by(model.status)
        return {str(status): int(count or 0) for status, count in self.db.execute(stmt)}

    def _count_branch(self, model: Any, condition: Any, branch_id: UUID | None) -> int:
        stmt = select(func.count(model.id)).where(condition)
        if branch_id and hasattr(model, "branch_id"):
            stmt = stmt.where(model.branch_id == branch_id)
        return int(self.db.scalar(stmt) or 0)

    def _ensure(self, actor: User, *, source_key: str, title: str, message: str, category: str, module: str, priority: str, notification_type: str, status: str = "unread", related_record_type: str | None = None, related_record_id: UUID | None = None, related_display: str | None = None, route: str | None = None, action_label: str | None = None, action_permission: str | None = None, due_at: datetime | None = None, meta: dict[str, Any] | None = None) -> Notification:
        item = self.db.scalar(select(Notification).where(Notification.recipient_user_id == actor.id, Notification.source_key == source_key))
        if item is None:
            item = Notification(branch_id=actor.branch_id, recipient_user_id=actor.id, source_key=source_key, title=title, message=message, category=category, module=module, priority=priority, status=status, notification_type=notification_type, related_record_type=related_record_type, related_record_id=related_record_id, related_display=related_display, route=route, action_label=action_label, action_permission=action_permission, due_at=due_at, meta=meta or {}, created_by=actor.id, updated_by=actor.id)
            self.db.add(item)
            self.db.flush()
            self._audit(actor, item, "notification.created", {"source_key": source_key})
        elif item.status not in TERMINAL_STATUSES:
            item.title = title
            item.message = message
            item.priority = priority
            item.due_at = due_at
            item.updated_by = actor.id
        return item

    def _expire_stale(self, actor: User) -> None:
        cutoff = datetime.now(UTC) - timedelta(days=30)
        for item in self.db.scalars(select(Notification).where(Notification.recipient_user_id == actor.id, Notification.status.in_(["read", "unread"]), Notification.created_at < cutoff)):
            item.status = "expired"
            item.updated_by = actor.id

    def _base_query(self, actor: User) -> tuple[Any, ...]:
        clauses: list[Any] = [Notification.recipient_user_id == actor.id, Notification.is_active.is_(True)]
        if actor.branch_id:
            clauses.append(or_(Notification.branch_id == actor.branch_id, Notification.branch_id.is_(None)))
        return tuple(clauses)

    def _get_owned(self, notification_id: UUID, actor: User) -> Notification:
        item = self.db.scalar(select(Notification).where(Notification.id == notification_id, *self._base_query(actor)))
        if not item:
            raise AppException(404, "notification_not_found", "Notification was not found")
        return item

    def _read(self, item: Notification, actor: User) -> NotificationRead:
        permissions = set(self.auth.get_effective_permissions(actor))
        action_allowed = bool(item.action_permission and item.action_permission in permissions)
        route = item.route if (not item.action_permission or item.action_permission in permissions) else None
        action_label = item.action_label if action_allowed else None
        # Keep details minimal when the action target itself is not permitted.
        message = item.message if (not item.action_permission or item.action_permission in permissions) else "You have a notification, but the linked record requires additional permission."
        return NotificationRead(
            id=item.id,
            title=item.title,
            message=message,
            category=item.category,
            module=item.module,
            priority=item.priority,
            status=item.status,
            notification_type=item.notification_type,
            related_record_type=item.related_record_type if action_allowed else None,
            related_record_id=item.related_record_id if action_allowed else None,
            related_display=item.related_display if action_allowed else None,
            route=route,
            action_label=action_label,
            action_permission=item.action_permission,
            due_at=item.due_at,
            read_at=item.read_at,
            completed_at=item.completed_at,
            dismissed_at=item.dismissed_at,
            escalated_at=item.escalated_at,
            created_at=item.created_at,
            meta=item.meta or {},
            action_allowed=action_allowed,
            overdue=bool(item.due_at and item.due_at < datetime.now(UTC) and item.status in ACTIVE_STATUSES),
        )

    def _audit(self, actor: User, item: Notification | None, action: str, detail: dict[str, Any]) -> None:
        self.db.add(NotificationAuditLog(branch_id=actor.branch_id, notification_id=item.id if item else None, user_id=actor.id, action=action, module=item.module if item else None, detail=detail, created_by=actor.id, updated_by=actor.id))
