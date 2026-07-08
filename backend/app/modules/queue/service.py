from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.blood_bank import BloodRequest
from app.models.encounter import OPDVisit
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.queue import QueueAuditLog, QueueCounter, QueueSetting, QueueToken
from app.models.scanner import ScanCode
from app.models.telemedicine import TelemedicineAppointment
from app.models.user import User
from app.modules.access_scope.service import AccessScopeService
from app.modules.auth.service import AuthService
from app.schemas.queue import QueueCounterCreate, QueueSettingRead, QueueSettingUpsert, QueueTokenCreate, QueueTokenRead


PRIORITY_RANK = {
    "emergency": 0,
    "urgent": 1,
    "pregnant": 2,
    "disabled": 2,
    "elderly": 3,
    "vip": 4,
    "follow_up": 5,
    "normal": 9,
}

TOKEN_TRANSITIONS = {
    "registered": {"waiting", "called", "cancelled", "no_show"},
    "waiting": {"called", "in_progress", "skipped", "cancelled", "no_show"},
    "called": {"in_progress", "skipped", "recalled", "no_show", "cancelled"},
    "recalled": {"called", "in_progress", "skipped", "no_show", "cancelled"},
    "in_progress": {"completed", "referred", "sent_to_billing", "sent_to_lab", "sent_to_radiology", "sent_to_pharmacy", "cancelled"},
    "skipped": {"recalled", "called", "no_show", "cancelled"},
}

SCOPE_VIEW_PERMISSIONS = {
    "opd": ("opd.queue.view", "opd.view"),
    "billing": ("billing.queue.manage", "billing.view"),
    "pharmacy": ("pharmacy.queue.manage", "pharmacy.view"),
    "laboratory": ("lab.queue.manage", "laboratory.view"),
    "radiology": ("radiology.queue.manage", "radiology.view"),
    "blood_bank": ("blood_bank.queue.manage", "blood_bank.view"),
    "er": ("er.view", "emergency.view"),
    "telemedicine": ("telemedicine.waiting_room.view", "telemedicine.queue.view", "telemedicine.view"),
}

SCOPE_ACTION_PERMISSIONS = {
    "opd": ("opd.queue.call",),
    "billing": ("billing.queue.manage",),
    "pharmacy": ("pharmacy.queue.manage",),
    "laboratory": ("lab.queue.manage",),
    "radiology": ("radiology.queue.manage",),
    "blood_bank": ("blood_bank.queue.manage",),
    "er": ("er.view", "emergency.view"),
    "telemedicine": ("telemedicine.consultation.start", "telemedicine.queue.view", "telemedicine.waiting_room.view"),
}


class QueueService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth = AuthService(db)
        self.scopes = AccessScopeService(db)

    def list_counters(self, actor: User, module: str | None = None) -> list[QueueCounter]:
        stmt = select(QueueCounter).where(QueueCounter.is_active.is_(True)).order_by(QueueCounter.module, QueueCounter.code)
        if actor.branch_id:
            stmt = stmt.where(or_(QueueCounter.branch_id == actor.branch_id, QueueCounter.branch_id.is_(None)))
        if module:
            stmt = stmt.where(QueueCounter.module == module)
        if not self.scopes.has_unrestricted_access(actor, module="queue", scope_type="queue_counter"):
            counter_refs = self.scopes.scope_refs(actor, "queue_counter", module="queue")
            scope_values = self.scopes.scope_values(actor, "queue_scope", module="queue")
            clauses = []
            if counter_refs:
                clauses.append(QueueCounter.id.in_(counter_refs))
            if scope_values:
                clauses.append(QueueCounter.module.in_(scope_values))
            if clauses:
                stmt = stmt.where(or_(*clauses))
        return list(self.db.scalars(stmt))

    def create_counter(self, payload: QueueCounterCreate, actor: User) -> QueueCounter:
        item = QueueCounter(branch_id=actor.branch_id, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self.db.flush()
        self._audit(actor, "counter.created", counter=item, detail={"code": item.code, "module": item.module})
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_counter_status(self, counter_id: UUID, status: str, actor: User) -> QueueCounter:
        counter = self._get_counter(counter_id, actor)
        counter.status = status
        if status != "active":
            counter.current_token_id = None
        counter.updated_by = actor.id
        self._audit(actor, f"counter.{status}", counter=counter, detail={"status": status})
        self.db.commit()
        self.db.refresh(counter)
        return counter

    def list_tokens(
        self,
        actor: User,
        *,
        queue_scope: str | None = None,
        status: str | None = None,
        counter_id: UUID | None = None,
        department_name: str | None = None,
        doctor_user_id: UUID | None = None,
        token_date: date | None = None,
        search: str | None = None,
        limit: int = 80,
    ) -> list[QueueTokenRead]:
        clauses = [QueueToken.is_active.is_(True)]
        if actor.branch_id:
            clauses.append(or_(QueueToken.branch_id == actor.branch_id, QueueToken.branch_id.is_(None)))
        if queue_scope:
            self._assert_scope(actor, queue_scope, view_only=True)
            clauses.append(QueueToken.queue_scope == queue_scope)
        if status:
            clauses.append(QueueToken.status == status)
        if counter_id:
            clauses.append(QueueToken.counter_id == counter_id)
            self.scopes.assert_in_scope(actor, module="queue", scope_type="queue_counter", scope_ref_id=counter_id)
        if department_name:
            clauses.append(QueueToken.department_name.ilike(f"%{department_name}%"))
        if doctor_user_id:
            clauses.append(QueueToken.doctor_user_id == doctor_user_id)
        if token_date:
            clauses.append(QueueToken.token_date == token_date)
        else:
            clauses.append(QueueToken.token_date == date.today())
        if search:
            token = f"%{search.strip()}%"
            clauses.append(or_(QueueToken.token_number.ilike(token), QueueToken.patient_label.ilike(token)))
        stmt = (
            select(QueueToken)
            .where(*clauses)
            .order_by(QueueToken.status == "called", QueueToken.created_at.desc())
            .limit(min(max(limit, 1), 200))
        )
        stmt = self._apply_token_scope_filter(stmt, actor)
        items = list(
            self.db.scalars(
                stmt
            )
        )
        return [self._read(item) for item in sorted(items, key=self._sort_key)]

    def ensure_token(self, payload: QueueTokenCreate, actor: User, *, commit: bool = True) -> QueueToken:
        existing = self.db.scalar(select(QueueToken).where(QueueToken.queue_scope == payload.queue_scope, QueueToken.source_type == payload.source_type, QueueToken.source_id == payload.source_id))
        if existing:
            return existing
        today = date.today()
        sequence = self._next_sequence(actor.branch_id, payload.queue_scope, today, payload.doctor_user_id)
        token_number = self._format_token(payload.queue_scope, payload.department_name, payload.service_area, sequence, payload.doctor_user_id, actor.branch_id)
        token_data = payload.model_dump()
        meta = dict(token_data.get("meta") or {})
        if payload.queue_scope == "opd" and payload.due_at:
            scheduled_at = payload.due_at if payload.due_at.tzinfo else payload.due_at.replace(tzinfo=UTC)
            grace_minutes = int(self._setting_value(actor.branch_id, "opd", "late_grace_minutes", 15) or 15)
            late_minutes = max(int((datetime.now(UTC) - scheduled_at).total_seconds() // 60), 0)
            meta.update({"scheduled_at": scheduled_at.isoformat(), "late_arrival": late_minutes > grace_minutes, "late_by_minutes": late_minutes})
        token_data["meta"] = meta
        item = QueueToken(
            branch_id=actor.branch_id,
            token_date=today,
            token_sequence=sequence,
            token_number=token_number,
            status="waiting",
            **token_data,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(item)
        self.db.flush()
        self._sync_source_queue_fields(item, actor)
        self._register_scan_code(item, actor)
        self._audit(actor, "token.generated", token=item, detail={"token_number": token_number, "scope": payload.queue_scope})
        self._notify_queue_assignment(item, actor)
        if commit:
            self.db.commit()
            self.db.refresh(item)
        return item

    def call_next(self, actor: User, *, queue_scope: str, counter_id: UUID | None = None, doctor_user_id: UUID | None = None) -> QueueTokenRead:
        self._assert_scope(actor, queue_scope)
        counter = self._get_counter(counter_id, actor) if counter_id else None
        doctor_user_id = doctor_user_id or (counter.doctor_user_id if counter else None)
        if queue_scope == "opd" and not doctor_user_id:
            raise AppException(422, "opd_queue_doctor_required", "Select a doctor or doctor counter before calling the next OPD patient")
        item = self._call_next_entity(actor, queue_scope=queue_scope, counter=counter, doctor_user_id=doctor_user_id)
        if not item:
            raise AppException(404, "queue_empty", "No waiting token found")
        self.db.commit()
        self.db.refresh(item)
        return self._read(item)

    def _call_next_entity(self, actor: User, *, queue_scope: str, counter: QueueCounter | None, doctor_user_id: UUID | None) -> QueueToken | None:
        self._expire_stale_called(actor, queue_scope=queue_scope, doctor_user_id=doctor_user_id)
        if counter and counter.status != "active":
            raise AppException(409, "queue_counter_paused", f"{counter.name} is {counter.status}")
        active_stmt = select(QueueToken.id).where(
            QueueToken.queue_scope == queue_scope,
            QueueToken.status.in_(["called", "in_progress"]),
            QueueToken.token_date == date.today(),
            QueueToken.is_active.is_(True),
            *([QueueToken.doctor_user_id == doctor_user_id] if doctor_user_id else []),
            *([or_(QueueToken.branch_id == actor.branch_id, QueueToken.branch_id.is_(None))] if actor.branch_id else []),
        )
        if self.db.scalar(active_stmt):
            raise AppException(409, "queue_active_patient_exists", "Complete, skip, or return the current patient before calling another")
        stmt = select(QueueToken).where(
            QueueToken.queue_scope == queue_scope,
            QueueToken.status.in_(["registered", "waiting", "recalled", "requested", "sample_pending", "crossmatch_pending", "ready_to_issue"]),
            QueueToken.token_date == date.today(),
            QueueToken.is_active.is_(True),
            *([or_(QueueToken.branch_id == actor.branch_id, QueueToken.branch_id.is_(None))] if actor.branch_id else []),
            *([QueueToken.doctor_user_id == doctor_user_id] if doctor_user_id else []),
        )
        stmt = self._apply_token_scope_filter(stmt, actor)
        waiting = list(self.db.scalars(stmt.with_for_update(skip_locked=True)))
        if not waiting:
            return None
        item = sorted(waiting, key=self._sort_key)[0]
        now = datetime.now(UTC)
        item.status = "sample_pending" if queue_scope == "blood_bank" and item.status in {"registered", "waiting", "requested", "recalled"} else "called"
        item.called_at = now
        item.counter_id = counter.id if counter else item.counter_id
        item.updated_by = actor.id
        if counter:
            counter.current_token_id = item.id
            counter.updated_by = actor.id
        self._sync_source_queue_fields(item, actor)
        self._audit(actor, "token.called", token=item, counter=counter, detail={"counter": counter.code if counter else None})
        return item

    def update_status(self, token_id: UUID, status: str, actor: User, *, counter_id: UUID | None = None, notes: str | None = None) -> QueueTokenRead:
        item = self._get_token(token_id, actor)
        self._assert_scope(actor, item.queue_scope)
        if status != item.status and status not in TOKEN_TRANSITIONS.get(item.status, set()):
            raise AppException(409, "queue_invalid_transition", f"Cannot change queue token from {item.status.replace('_', ' ')} to {status.replace('_', ' ')}")
        if status in {"called", "in_progress"}:
            active = self.db.scalar(
                select(QueueToken.id).where(
                    QueueToken.id != item.id,
                    QueueToken.queue_scope == item.queue_scope,
                    QueueToken.doctor_user_id == item.doctor_user_id,
                    QueueToken.token_date == item.token_date,
                    QueueToken.status.in_(["called", "in_progress"]),
                    QueueToken.is_active.is_(True),
                )
            )
            if active:
                raise AppException(409, "queue_active_patient_exists", "This doctor already has an active queue patient")
        now = datetime.now(UTC)
        item.status = status
        item.notes = notes or item.notes
        if counter_id:
            item.counter_id = counter_id
        if status == "in_progress":
            item.started_at = item.started_at or now
        elif status == "called":
            item.called_at = now
        elif status == "completed":
            item.completed_at = now
        elif status == "skipped":
            item.skipped_at = now
        elif status == "recalled":
            recall_count = int((item.meta or {}).get("recall_count", 0)) + 1
            recall_limit = int(self._setting_value(actor.branch_id, item.queue_scope, "recall_limit", 2) or 2)
            if recall_count > recall_limit:
                raise AppException(409, "queue_recall_limit", f"Recall limit of {recall_limit} has been reached")
            item.recalled_at = now
            item.meta = {**(item.meta or {}), "recall_count": recall_count}
        elif status in {"no_show", "cancelled"}:
            item.completed_at = now
        item.updated_by = actor.id
        self._sync_source_queue_fields(item, actor)
        self._audit(actor, f"token.{status}", token=item, detail={"notes": notes})
        counter = self.db.get(QueueCounter, item.counter_id) if item.counter_id else None
        if status in {"completed", "skipped", "no_show", "cancelled", "referred"} and counter and counter.current_token_id == item.id:
            counter.current_token_id = None
            counter.updated_by = actor.id
        if status == "completed" and item.queue_scope == "opd" and (not counter or counter.status == "active") and self._setting_value(actor.branch_id, "opd", "auto_call_next", True):
            self.db.flush()
            self._call_next_entity(actor, queue_scope="opd", counter=counter, doctor_user_id=item.doctor_user_id)
        self.db.commit()
        self.db.refresh(item)
        return self._read(item)

    def transfer(self, token_id: UUID, payload, actor: User) -> QueueTokenRead:
        item = self._get_token(token_id, actor)
        self._assert_scope(actor, item.queue_scope)
        self._assert_scope(actor, payload.queue_scope)
        previous_doctor_id = item.doctor_user_id
        previous_token_number = item.token_number
        item.queue_scope = payload.queue_scope
        item.module = payload.module
        item.service_area = payload.service_area
        item.department_name = payload.department_name or item.department_name
        item.doctor_user_id = payload.doctor_user_id
        item.counter_id = payload.counter_id
        item.priority = payload.priority or item.priority
        item.status = "waiting"
        if payload.queue_scope == "opd" and payload.doctor_user_id and payload.doctor_user_id != previous_doctor_id:
            item.token_sequence = self._next_sequence(actor.branch_id, "opd", date.today(), payload.doctor_user_id)
            item.token_number = self._format_token("opd", item.department_name, item.service_area, item.token_sequence, payload.doctor_user_id, actor.branch_id)
            item.meta = {**(item.meta or {}), "transferred_from_token": previous_token_number, "transferred_at": datetime.now(UTC).isoformat()}
        item.notes = payload.notes or item.notes
        item.updated_by = actor.id
        self._sync_source_queue_fields(item, actor)
        self._audit(actor, "token.transferred", token=item, detail={"to_scope": payload.queue_scope, "notes": payload.notes})
        self.db.commit()
        self.db.refresh(item)
        return self._read(item)

    def update_priority(self, token_id: UUID, priority: str, reason: str, actor: User) -> QueueTokenRead:
        item = self._get_token(token_id, actor)
        previous_priority = item.priority
        item.priority = priority
        item.meta = {**(item.meta or {}), "priority_reason": reason, "previous_priority": previous_priority}
        item.updated_by = actor.id
        self._audit(actor, "token.priority_updated", token=item, detail={"from": previous_priority, "to": priority, "reason": reason})
        self.db.commit()
        self.db.refresh(item)
        return self._read(item)

    def summary(self, actor: User, *, queue_scope: str | None = None, doctor_user_id: UUID | None = None) -> dict:
        clauses = [QueueToken.token_date == date.today(), QueueToken.is_active.is_(True)]
        if actor.branch_id:
            clauses.append(or_(QueueToken.branch_id == actor.branch_id, QueueToken.branch_id.is_(None)))
        if queue_scope:
            self._assert_scope(actor, queue_scope, view_only=True)
            clauses.append(QueueToken.queue_scope == queue_scope)
        if doctor_user_id:
            clauses.append(QueueToken.doctor_user_id == doctor_user_id)
        rows = list(self.db.scalars(select(QueueToken).where(*clauses)))
        if not self.scopes.has_unrestricted_access(actor, module="queue", scope_type="queue_scope"):
            allowed_scopes = self.scopes.scope_values(actor, "queue_scope", module="queue")
            allowed_counters = self.scopes.scope_refs(actor, "queue_counter", module="queue")
            if allowed_scopes or allowed_counters:
                rows = [item for item in rows if item.queue_scope.lower() in allowed_scopes or (item.counter_id and item.counter_id in allowed_counters)]
        waits = [self._waiting_minutes(item) for item in rows if item.status in {"waiting", "registered", "called", "recalled"}]
        by_scope: dict[str, int] = {}
        by_counter: dict[str, int] = {}
        for item in rows:
            by_scope[item.queue_scope] = by_scope.get(item.queue_scope, 0) + 1
            if item.counter_id:
                by_counter[str(item.counter_id)] = by_counter.get(str(item.counter_id), 0) + 1
        return {
            "total_waiting": sum(1 for item in rows if item.status in {"waiting", "registered", "recalled"}),
            "total_called": sum(1 for item in rows if item.status == "called"),
            "total_in_progress": sum(1 for item in rows if item.status == "in_progress"),
            "total_completed": sum(1 for item in rows if item.status == "completed"),
            "skipped_count": sum(1 for item in rows if item.status == "skipped"),
            "longest_wait_minutes": max(waits or [0]),
            "average_wait_minutes": int(sum(waits) / len(waits)) if waits else 0,
            "by_scope": by_scope,
            "by_counter": by_counter,
        }

    def display(self, actor: User, scope: str) -> dict:
        self._assert_scope(actor, scope, view_only=True)
        tokens = self.list_tokens(actor, queue_scope=scope, token_date=date.today(), limit=50)
        current = [item for item in tokens if item.status in {"called", "in_progress"}][:6]
        next_tokens = [item for item in tokens if item.status in {"waiting", "registered", "recalled"}][:8]
        return {"scope": scope, "current": current, "next_tokens": next_tokens, "announcements": ["Please keep your token ready."]}

    def list_settings(self, actor: User) -> list[QueueSettingRead]:
        stmt = select(QueueSetting).where(QueueSetting.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(QueueSetting.branch_id == actor.branch_id, QueueSetting.branch_id.is_(None)))
        return list(self.db.scalars(stmt.order_by(QueueSetting.setting_key.asc())))

    def save_setting(self, payload: QueueSettingUpsert, actor: User) -> QueueSetting:
        key = payload.setting_key.strip().lower().replace(" ", "_")
        item = self.db.scalar(select(QueueSetting).where(QueueSetting.branch_id == actor.branch_id, QueueSetting.setting_key == key))
        if item is None:
            item = QueueSetting(branch_id=actor.branch_id, setting_key=key, setting_value=payload.setting_value, created_by=actor.id, updated_by=actor.id)
            self.db.add(item)
        else:
            item.setting_value = payload.setting_value
            item.updated_by = actor.id
        self.db.flush()
        self._audit(actor, "setting.updated", detail={"setting_key": key})
        self.db.commit()
        self.db.refresh(item)
        return item

    def _assert_scope(self, actor: User, scope: str, view_only: bool = False) -> None:
        permissions = set(self.auth.get_effective_permissions(actor))
        allowed = {"queue.view"} if view_only else {"queue.call_next"}
        scope_permissions = SCOPE_VIEW_PERMISSIONS if view_only else SCOPE_ACTION_PERMISSIONS
        allowed.update(scope_permissions.get(scope, ()))
        if not any(code in permissions for code in allowed):
            raise AppException(403, "forbidden", "You do not have permission for this queue")
        self.scopes.assert_in_scope(actor, module="queue", scope_type="queue_scope", scope_value=scope)

    def _next_sequence(self, branch_id: UUID | None, scope: str, token_date: date, doctor_user_id: UUID | None = None) -> int:
        lock_key = f"queue:{branch_id}:{scope}:{token_date}:{doctor_user_id}"
        self.db.execute(select(func.pg_advisory_xact_lock(func.hashtext(lock_key))))
        stmt = select(func.coalesce(func.max(QueueToken.token_sequence), 0)).where(QueueToken.queue_scope == scope, QueueToken.token_date == token_date)
        if branch_id:
            stmt = stmt.where(QueueToken.branch_id == branch_id)
        if scope == "opd" and doctor_user_id:
            stmt = stmt.where(QueueToken.doctor_user_id == doctor_user_id)
        return int(self.db.scalar(stmt) or 0) + 1

    def _format_token(self, scope: str, department: str | None, service_area: str | None, sequence: int, doctor_user_id: UUID | None = None, branch_id: UUID | None = None) -> str:
        prefix = {
            "opd": "O",
            "billing": "B",
            "pharmacy": "P",
            "laboratory": "L",
            "radiology": "R",
            "blood_bank": "BB",
            "er": "E",
        }.get(scope, (scope[:2] or "Q").upper())
        if scope == "opd" and doctor_user_id:
            doctor = self.db.get(User, doctor_user_id)
            configured_codes = self._setting_value(branch_id, "opd", "doctor_codes", {})
            configured_code = configured_codes.get(str(doctor_user_id)) if isinstance(configured_codes, dict) else None
            username_code = "".join(character for character in (doctor.username if doctor else "") if character.isalnum()).upper()
            username_code = username_code.removeprefix("DR")[:8]
            name_code = "".join(part[0] for part in (doctor.full_name if doctor else "Doctor").replace(".", "").split()).upper()[:3]
            prefix = str(configured_code or username_code or name_code or "DR")[:6].upper()
        elif scope == "opd" and department:
            prefix = "".join(part[0] for part in department.split()[:2]).upper()[:2] or prefix
        elif service_area:
            prefix = service_area[:2].upper()
        return f"{prefix}-{sequence:03d}"

    def _setting_value(self, branch_id: UUID | None, setting_key: str, value_key: str, default):
        stmt = select(QueueSetting).where(QueueSetting.setting_key.in_([setting_key, "global"]), QueueSetting.is_active.is_(True))
        if branch_id:
            stmt = stmt.where(or_(QueueSetting.branch_id == branch_id, QueueSetting.branch_id.is_(None)))
        settings = list(self.db.scalars(stmt.order_by(QueueSetting.setting_key == setting_key)))
        value = default
        for setting in settings:
            if value_key in (setting.setting_value or {}):
                value = setting.setting_value[value_key]
        return value

    def _expire_stale_called(self, actor: User, *, queue_scope: str, doctor_user_id: UUID | None) -> None:
        timeout_minutes = int(self._setting_value(actor.branch_id, queue_scope, "auto_skip_minutes", 0) or 0)
        if timeout_minutes <= 0:
            return
        now = datetime.now(UTC)
        stmt = select(QueueToken).where(
            QueueToken.queue_scope == queue_scope,
            QueueToken.status == "called",
            QueueToken.token_date == date.today(),
            *([QueueToken.doctor_user_id == doctor_user_id] if doctor_user_id else []),
        )
        for token in self.db.scalars(stmt.with_for_update(skip_locked=True)):
            if token.called_at and (now - token.called_at).total_seconds() >= timeout_minutes * 60:
                token.status = "skipped"
                token.skipped_at = now
                token.updated_by = actor.id
                self._sync_source_queue_fields(token, actor)
                self._audit(actor, "token.auto_skipped", token=token, detail={"timeout_minutes": timeout_minutes})

    def _sort_key(self, item: QueueToken) -> tuple:
        scheduled_order = item.created_at if (item.meta or {}).get("late_arrival") else (item.due_at or item.created_at)
        return (PRIORITY_RANK.get(item.priority, 9), scheduled_order, item.created_at, item.token_sequence)

    def _waiting_minutes(self, item: QueueToken) -> int:
        return max(int((datetime.now(UTC) - item.created_at).total_seconds() // 60), 0)

    def _read(self, item: QueueToken) -> QueueTokenRead:
        data = QueueTokenRead.model_validate(item, from_attributes=True)
        data.waiting_minutes = self._waiting_minutes(item)
        return data

    def _get_counter(self, counter_id: UUID, actor: User) -> QueueCounter:
        counter = self.db.get(QueueCounter, counter_id)
        if not counter or not counter.is_active or (actor.branch_id and counter.branch_id not in {None, actor.branch_id}):
            raise AppException(404, "counter_not_found", "Queue counter not found")
        self.scopes.assert_in_scope(actor, module="queue", scope_type="queue_counter", scope_ref_id=counter.id)
        return counter

    def _get_token(self, token_id: UUID, actor: User) -> QueueToken:
        token = self.db.get(QueueToken, token_id)
        if not token or not token.is_active or (actor.branch_id and token.branch_id not in {None, actor.branch_id}):
            raise AppException(404, "queue_token_not_found", "Queue token not found")
        self.scopes.assert_in_scope(actor, module="queue", scope_type="queue_scope", scope_value=token.queue_scope)
        if token.counter_id:
            self.scopes.assert_in_scope(actor, module="queue", scope_type="queue_counter", scope_ref_id=token.counter_id)
        return token

    def _apply_token_scope_filter(self, stmt, actor: User):
        if self.scopes.has_unrestricted_access(actor, module="queue", scope_type="queue_scope"):
            return stmt
        allowed_scopes = self.scopes.scope_values(actor, "queue_scope", module="queue")
        allowed_counters = self.scopes.scope_refs(actor, "queue_counter", module="queue")
        clauses = []
        if allowed_scopes:
            clauses.append(func.lower(QueueToken.queue_scope).in_(allowed_scopes))
        if allowed_counters:
            clauses.append(QueueToken.counter_id.in_(allowed_counters))
        if not clauses:
            return stmt
        return stmt.where(or_(*clauses))

    def _sync_source_queue_fields(self, item: QueueToken, actor: User) -> None:
        if item.visit_id:
            visit = self.db.get(OPDVisit, item.visit_id)
            if visit:
                visit.queue_number = item.token_number
                visit.queue_status = item.status
                visit.queue_called_at = item.called_at
                if item.status == "in_progress" and visit.status in {"waiting", "checked_in"}:
                    visit.status = "in_consultation"
                elif item.status == "completed" and visit.status not in {"billed", "cancelled"}:
                    visit.status = "completed"
                visit.updated_by = actor.id
        if item.blood_request_id:
            request = self.db.get(BloodRequest, item.blood_request_id)
            if request:
                request.status = self._blood_request_status(item.status)
                request.updated_by = actor.id
        if item.queue_scope == "telemedicine" and item.source_type == "telemedicine_appointment":
            appointment = self.db.get(TelemedicineAppointment, item.source_id)
            if appointment:
                appointment.queue_number = item.token_number
                appointment.estimated_wait_minutes = self._waiting_minutes(item)
                appointment.status = {
                    "waiting": "waiting",
                    "called": "ready_to_join",
                    "recalled": "ready_to_join",
                    "in_progress": "in_consultation",
                    "completed": "completed",
                    "skipped": "waiting",
                    "no_show": "no_show",
                    "cancelled": "cancelled",
                }.get(item.status, appointment.status)
                appointment.updated_by = actor.id

    def _blood_request_status(self, status: str) -> str:
        if status in {"waiting", "called", "in_progress", "completed", "skipped", "recalled"}:
            return {
                "waiting": "requested",
                "called": "sample_pending",
                "in_progress": "crossmatch_pending",
                "completed": "issued",
                "skipped": "requested",
                "recalled": "sample_pending",
            }[status]
        return status

    def _register_scan_code(self, item: QueueToken, actor: User) -> None:
        code_value = f"QUEUE:{item.token_number}:{item.id}"
        existing = self.db.scalar(select(ScanCode).where(ScanCode.code_value == code_value))
        if existing:
            return
        self.db.add(
            ScanCode(
                branch_id=actor.branch_id,
                code_value=code_value,
                code_type="qr",
                purpose="queue_token",
                record_type="queue_token",
                record_id=item.id,
                display_value=item.token_number,
                meta={"queue_scope": item.queue_scope, "patient_id": str(item.patient_id) if item.patient_id else None},
                created_by=actor.id,
                updated_by=actor.id,
            )
        )

    def _notify_queue_assignment(self, item: QueueToken, actor: User) -> None:
        self.db.add(
            Notification(
                branch_id=actor.branch_id,
                recipient_user_id=actor.id,
                title=f"Queue token {item.token_number} created",
                message=f"{item.patient_label or 'Patient'} entered {item.queue_scope.replace('_', ' ')} queue.",
                category="clinical" if item.queue_scope in {"opd", "laboratory", "radiology", "blood_bank"} else item.queue_scope,
                module=item.module,
                priority="high" if item.priority in {"emergency", "urgent"} else "medium",
                status="unread",
                notification_type="task_assignment",
                source_key=f"queue:{item.id}",
                related_record_type="queue_token",
                related_record_id=item.id,
                related_display=item.token_number,
                route="/queue",
                action_label="Open Queue",
                action_permission="queue.view",
                due_at=item.due_at,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )

    def _audit(self, actor: User, action: str, *, token: QueueToken | None = None, counter: QueueCounter | None = None, detail: dict | None = None) -> None:
        self.db.add(
            QueueAuditLog(
                branch_id=actor.branch_id,
                token_id=token.id if token else None,
                counter_id=counter.id if counter else None,
                user_id=actor.id,
                action=action,
                module=token.module if token else counter.module if counter else "queue",
                detail=detail or {},
                created_by=actor.id,
                updated_by=actor.id,
            )
        )


def patient_label(patient: Patient | None) -> str | None:
    if not patient:
        return None
    return f"{patient.patient_number} - {patient.first_name} {patient.last_name}"
