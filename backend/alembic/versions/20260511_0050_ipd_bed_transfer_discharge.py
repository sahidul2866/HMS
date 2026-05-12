"""Add IPD bed transfer metadata for board and discharge workflows.

Revision ID: 20260511_0050
Revises: 20260511_0049
Create Date: 2026-05-11 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260511_0050"
down_revision = "20260511_0049"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_column(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _has_fk(table_name: str, fk_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(fk["name"] == fk_name for fk in inspector.get_foreign_keys(table_name))


def upgrade() -> None:
    for column in [
        sa.Column("transfer_reason", sa.Text(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    ]:
        _add_column("ipd_admission_movements", column)

    if not _has_fk("ipd_admission_movements", "fk_ipd_movements_requested_by"):
        op.create_foreign_key("fk_ipd_movements_requested_by", "ipd_admission_movements", "users", ["requested_by_user_id"], ["id"])
    if not _has_fk("ipd_admission_movements", "fk_ipd_movements_approved_by"):
        op.create_foreign_key("fk_ipd_movements_approved_by", "ipd_admission_movements", "users", ["approved_by_user_id"], ["id"])


def downgrade() -> None:
    for fk_name in ["fk_ipd_movements_approved_by", "fk_ipd_movements_requested_by"]:
        try:
            op.drop_constraint(fk_name, "ipd_admission_movements", type_="foreignkey")
        except Exception:
            pass
    for column_name in ["approved_by_user_id", "requested_by_user_id", "approved_at", "remarks", "transfer_reason"]:
        if _has_column("ipd_admission_movements", column_name):
            op.drop_column("ipd_admission_movements", column_name)
