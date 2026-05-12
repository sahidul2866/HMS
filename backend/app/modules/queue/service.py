from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.blood_bank import BloodRequest
from app.models.encounter import OPDVisit
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.queue import QueueAuditLog, QueueCounter, QueueSetting, QueueToken
from app.models.scanner import ScanCode
from app.models.user import User
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

SCOPE_VIEW_PERMISSIONS = {
    "opd": ("opd.queue.view", "opd.view"),
    "billing": ("billing.queue.manage", "billing.view"),
    "pharmacy": ("pharmacy.queue.manage", "pharmacy.view"),
    "laboratory": ("lab.queue.manage", "laboratory.view"),
    "radiology": ("radiology.queue.manage", "radiology.view"),
    "blood_bank": ("blood_bank.queue.manage", "blood_bank.view"),
    "er": ("er.view", "emergency.view"),
}

SCOPE_ACTION_PERMISSIONS = {
    "opd": ("opd.queue.call",),
    "billing": ("billing.queue.manage",),
    "pharmacy": ("pharmacy.queue.manage",),
    "laboratory": ("lab.queue.manage",),
    "radiology": ("radiology.queue.manage",),
    "blood_bank": ("blood_bank.queue.manage",),
    "er": ("er.view", "emergency.view"),
}


class QueueService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.auth = AuthService(db)

    def list_counters(self, actor: User, module: str | None = None) -> list[QueueCounter]:
        stmt = select(QueueCounter).where(QueueCounter.is_active.is_(True)).order_by(QueueCounter.module, QueueCounter.code)
        if actor.branch_id:
            stmt = stmt.where(or_(QueueCounter.branch_id == actor.branch_id, QueueCounter.branch_id.is_(None)))
        if module:
            stmt = stmt.where(QueueCounter.module == module)
        return list(self.db.scalars(stmt))

    def create_counter(self, payload: QueueCounterCreate, actor: User) -> QueueCounter:
        item = QueueCounter(branch_id=actor.branch_id, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self.db.flush()
        self._audit(actor, "counter.created", counter=item, detail={"code": item.code, "module": item.module})
        self.db.commit()
        self.db.refresh(item)
        return item

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
        items = list(
            self.db.scalars(
                select(QueueToken)
                .where(*clauses)
                .order_by(QueueToken.status == "called", QueueToken.created_at.desc())
                .limit(min(max(limit, 1), 200))
            )
        )
        return [self._read(item) for item in sorted(items, key=self._sort_key)]

    def ensure_token(self, payload: QueueTokenCreate, actor: User, *, commit: bool = True) -> QueueToken:
        existing = self.db.scalar(select(QueueToken).where(QueueToken.queue_scope == payload.queue_scope, QueueToken.source_type == payload.source_type, QueueToken.source_id == payload.source_id))
        if existing:
            return existing
        today = date.today()
        sequence = self._next_sequence(actor.branch_id, payload.queue_scope, today)
        token_number = self._format_token(payload.queue_scope, payload.department_name, payload.service_area, sequence)
        item = QueueToken(
            branch_id=actor.branch_id,
            token_date=today,
            token_sequence=sequence,
            token_number=token_number,
            status="waiting",
            **payload.model_dump(),
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
        waiting = [
            item
            for item in self.db.scalars(
                select(QueueToken).where(
                    QueueToken.queue_scope == queue_scope,
                    QueueToken.status.in_(["registered", "waiting", "recalled", "requested", "sample_pending", "crossmatch_pending", "ready_to_issue"]),
                    QueueToken.token_date == date.today(),
                    QueueToken.is_active.is_(True),
                    *([or_(QueueToken.branch_id == actor.branch_id, QueueToken.branch_id.is_(None))] if actor.branch_id else []),
                    *([QueueToken.doctor_user_id == doctor_user_id] if doctor_user_id else []),
                )
            )
        ]
        if not waiting:
            raise AppException(404, "queue_empty", "No waiting token found")
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
        self.db.commit()
        self.db.refresh(item)
        return self._read(item)

    def update_status(self, token_id: UUID, status: str, actor: User, *, counter_id: UUID | None = None, notes: str | None = None) -> QueueTokenRead:
        item = self._get_token(token_id, actor)
        self._assert_scope(actor, item.queue_scope)
        now = datetime.now(UTC)
        item.status = status
        item.notes = notes or item.notes
        if counter_id:
            item.counter_id = counter_id
        if status == "in_progress":
            item.started_at = item.started_at or now
        elif status == "completed":
            item.completed_at = now
        elif status == "skipped":
            item.skipped_at = now
        elif status == "recalled":
            item.recalled_at = now
        item.updated_by = actor.id
        self._sync_source_queue_fields(item, actor)
        self._audit(actor, f"token.{status}", token=item, detail={"notes": notes})
        self.db.commit()
        self.db.refresh(item)
        return self._read(item)

    def transfer(self, token_id: UUID, payload, actor: User) -> QueueTokenRead:
        item = self._get_token(token_id, actor)
        self._assert_scope(actor, item.queue_scope)
        self._assert_scope(actor, payload.queue_scope)
        item.queue_scope = payload.queue_scope
        item.module = payload.module
        item.service_area = payload.service_area
        item.department_name = payload.department_name or item.department_name
        item.doctor_user_id = payload.doctor_user_id
        item.counter_id = payload.counter_id
        item.priority = payload.priority or item.priority
        item.status = "waiting"
        item.notes = payload.notes or item.notes
        item.updated_by = actor.id
        self._sync_source_queue_fields(item, actor)
        self._audit(actor, "token.transferred", token=item, detail={"to_scope": payload.queue_scope, "notes": payload.notes})
        self.db.commit()
        self.db.refresh(item)
        return self._read(item)

    def summary(self, actor: User) -> dict:
        clauses = [QueueToken.token_date == date.today(), QueueToken.is_active.is_(True)]
        if actor.branch_id:
            clauses.append(or_(QueueToken.branch_id == actor.branch_id, QueueToken.branch_id.is_(None)))
        rows = list(self.db.scalars(select(QueueToken).where(*clauses)))
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

    def _next_sequence(self, branch_id: UUID | None, scope: str, token_date: date) -> int:
        stmt = select(func.coalesce(func.max(QueueToken.token_sequence), 0)).where(QueueToken.queue_scope == scope, QueueToken.token_date == token_date)
        if branch_id:
            stmt = stmt.where(QueueToken.branch_id == branch_id)
        return int(self.db.scalar(stmt) or 0) + 1

    def _format_token(self, scope: str, department: str | None, service_area: str | None, sequence: int) -> str:
        prefix = {
            "opd": "O",
            "billing": "B",
            "pharmacy": "P",
            "laboratory": "L",
            "radiology": "R",
            "blood_bank": "BB",
            "er": "E",
        }.get(scope, (scope[:2] or "Q").upper())
        if scope == "opd" and department:
            prefix = "".join(part[0] for part in department.split()[:2]).upper()[:2] or prefix
        elif service_area:
            prefix = service_area[:2].upper()
        return f"{prefix}-{sequence:03d}"

    def _sort_key(self, item: QueueToken) -> tuple:
        return (PRIORITY_RANK.get(item.priority, 9), item.due_at or item.created_at, item.token_sequence)

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
        return counter

    def _get_token(self, token_id: UUID, actor: User) -> QueueToken:
        token = self.db.get(QueueToken, token_id)
        if not token or not token.is_active or (actor.branch_id and token.branch_id not in {None, actor.branch_id}):
            raise AppException(404, "queue_token_not_found", "Queue token not found")
        return token

    def _sync_source_queue_fields(self, item: QueueToken, actor: User) -> None:
        if item.visit_id:
            visit = self.db.get(OPDVisit, item.visit_id)
            if visit:
                visit.queue_number = item.token_number
                visit.queue_status = item.status
                visit.queue_called_at = item.called_at
                visit.updated_by = actor.id
        if item.blood_request_id:
            request = self.db.get(BloodRequest, item.blood_request_id)
            if request:
                request.status = self._blood_request_status(item.status)
                request.updated_by = actor.id

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
