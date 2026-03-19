from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.modules.audit.repository import AuditRepository


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuditRepository(db)

    def list_logs(self) -> list[AuditLog]:
        return self.repository.list_logs()

    def log(
        self,
        user_id,
        action: str,
        module: str,
        entity_type: str | None,
        entity_id: str | None,
        detail: dict | None,
        context: dict[str, str | None],
    ) -> AuditLog:
        return self.repository.create_log(
            AuditLog(
                user_id=user_id,
                action=str(action),
                module=module,
                entity_type=entity_type,
                entity_id=entity_id,
                detail=detail,
                ip_address=context.get("ip_address"),
                user_agent=context.get("user_agent"),
                created_at=datetime.now(UTC),
            )
        )

