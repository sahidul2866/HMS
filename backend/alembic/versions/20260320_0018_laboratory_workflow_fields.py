"""add laboratory workflow fields to opd orders

Revision ID: 20260320_0018
Revises: 20260320_0017
Create Date: 2026-03-26 06:20:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0018"
down_revision = "20260320_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("opd_visit_orders", sa.Column("sample_note", sa.Text(), nullable=True))
    op.add_column("opd_visit_orders", sa.Column("sample_collected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("opd_visit_orders", sa.Column("sample_collected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("opd_visit_orders", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("opd_visit_orders", sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_opd_visit_orders_sample_collected_by_user_id",
        "opd_visit_orders",
        "users",
        ["sample_collected_by_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_opd_visit_orders_verified_by_user_id",
        "opd_visit_orders",
        "users",
        ["verified_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_opd_visit_orders_verified_by_user_id", "opd_visit_orders", type_="foreignkey")
    op.drop_constraint("fk_opd_visit_orders_sample_collected_by_user_id", "opd_visit_orders", type_="foreignkey")
    op.drop_column("opd_visit_orders", "verified_by_user_id")
    op.drop_column("opd_visit_orders", "verified_at")
    op.drop_column("opd_visit_orders", "sample_collected_by_user_id")
    op.drop_column("opd_visit_orders", "sample_collected_at")
    op.drop_column("opd_visit_orders", "sample_note")
