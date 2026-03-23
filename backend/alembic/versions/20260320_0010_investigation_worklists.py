"""add investigation worklist fields

Revision ID: 20260320_0010
Revises: 20260320_0009
Create Date: 2026-03-20 21:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0010"
down_revision = "20260320_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("opd_visit_orders", sa.Column("service_area", sa.String(length=30), nullable=True))
    op.add_column("opd_visit_orders", sa.Column("result_text", sa.Text(), nullable=True))
    op.add_column("opd_visit_orders", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("opd_visit_orders", sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_opd_visit_orders_completed_by_user_id_users",
        "opd_visit_orders",
        "users",
        ["completed_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_opd_visit_orders_completed_by_user_id_users", "opd_visit_orders", type_="foreignkey")
    op.drop_column("opd_visit_orders", "completed_by_user_id")
    op.drop_column("opd_visit_orders", "completed_at")
    op.drop_column("opd_visit_orders", "result_text")
    op.drop_column("opd_visit_orders", "service_area")
