"""Add IPD order execution, medication, nursing task, and vitals fields.

Revision ID: 20260511_0049
Revises: 20260511_0048
Create Date: 2026-05-11 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260511_0049"
down_revision = "20260511_0048"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_column(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    ]


def upgrade() -> None:
    _add_column("ipd_nursing_notes", sa.Column("glucose", sa.Numeric(8, 2), nullable=True))

    for column in [
        sa.Column("order_set_code", sa.String(120), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frequency", sa.String(80), nullable=True),
        sa.Column("duration", sa.String(80), nullable=True),
        sa.Column("dose", sa.String(80), nullable=True),
        sa.Column("route", sa.String(80), nullable=True),
        sa.Column("lab_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("radiology_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("discontinued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discontinued_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    ]:
        _add_column("ipd_orders", column)

    _add_column("ipd_medication_administrations", sa.Column("remarks", sa.Text(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("ipd_orders")}
    for name, target, column in [
        ("fk_ipd_orders_lab_order", "lab_orders", "lab_order_id"),
        ("fk_ipd_orders_radiology_order", "radiology_orders", "radiology_order_id"),
        ("fk_ipd_orders_discontinued_by", "users", "discontinued_by_user_id"),
        ("fk_ipd_orders_cancelled_by", "users", "cancelled_by_user_id"),
    ]:
        if name not in existing_fks and _has_column("ipd_orders", column):
            op.create_foreign_key(name, "ipd_orders", target, [column], ["id"])

    if not _has_table("ipd_nursing_tasks"):
        op.create_table(
            "ipd_nursing_tasks",
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("assigned_nurse_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("task_type", sa.String(60), nullable=False),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("instructions", sa.Text(), nullable=True),
            sa.Column("ward_name", sa.String(120), nullable=True),
            sa.Column("bed_number", sa.String(60), nullable=True),
            sa.Column("shift_name", sa.String(80), nullable=True),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("completion_note", sa.Text(), nullable=True),
            *_audit_columns(),
            sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["order_id"], ["ipd_orders.id"]),
            sa.ForeignKeyConstraint(["assigned_nurse_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    if _has_table("ipd_nursing_tasks"):
        op.drop_table("ipd_nursing_tasks")
    for name in ["fk_ipd_orders_cancelled_by", "fk_ipd_orders_discontinued_by", "fk_ipd_orders_radiology_order", "fk_ipd_orders_lab_order"]:
        try:
            op.drop_constraint(name, "ipd_orders", type_="foreignkey")
        except Exception:
            pass
    for column in [
        "remarks",
    ]:
        if _has_column("ipd_medication_administrations", column):
            op.drop_column("ipd_medication_administrations", column)
    for column in [
        "cancelled_by_user_id",
        "cancelled_at",
        "discontinued_by_user_id",
        "discontinued_at",
        "radiology_order_id",
        "lab_order_id",
        "route",
        "dose",
        "duration",
        "frequency",
        "scheduled_at",
        "order_set_code",
    ]:
        if _has_column("ipd_orders", column):
            op.drop_column("ipd_orders", column)
    if _has_column("ipd_nursing_notes", "glucose"):
        op.drop_column("ipd_nursing_notes", "glucose")
