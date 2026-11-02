"""The queue page offers only the queues a user can read, so it never opens on a refused scope."""
from uuid import uuid4

from test_opd_workflow_integration import database, db, seed  # noqa: F401
from app.models.permission import Permission
from app.models.scope import UserScope
from app.models.user import User
from app.modules.queue.service import QueueService, SCOPE_VIEW_PERMISSIONS
from sqlalchemy import select


def clerk(db, actor, codes):
    suffix = uuid4().hex[:8]
    permissions = list(db.scalars(select(Permission).where(Permission.code.in_(codes))))
    user = User(branch_id=actor.branch_id, username="clerk_" + suffix, email=suffix + "@example.test", full_name="Queue Clerk", hashed_password="unused", direct_permissions=permissions)
    db.add(user)
    db.flush()
    return user


def test_assigned_queue_scope_limits_what_the_page_offers(db):
    actor, *_ = seed(db)
    user = clerk(db, actor, ["queue.view"])
    assert QueueService(db).viewable_scopes(user) == list(SCOPE_VIEW_PERMISSIONS)
    db.add(UserScope(branch_id=actor.branch_id, user_id=user.id, scope_type="queue_scope", scope_value="billing", module="queue"))
    db.flush()
    assert QueueService(db).viewable_scopes(user) == ["billing"]


def test_probing_scopes_leaves_no_denial_audit_rows(db):
    from app.models.audit_log import AuditLog
    actor, *_ = seed(db)
    user = clerk(db, actor, ["queue.view"])
    db.add(UserScope(branch_id=actor.branch_id, user_id=user.id, scope_type="queue_scope", scope_value="billing", module="queue"))
    db.flush()
    before = len(list(db.scalars(select(AuditLog))))
    QueueService(db).viewable_scopes(user)
    assert len(list(db.scalars(select(AuditLog)))) == before


def test_permission_without_queue_view_hides_other_queues(db):
    actor, *_ = seed(db)
    user = clerk(db, actor, ["billing.view"])
    assert QueueService(db).viewable_scopes(user) == ["billing"]
