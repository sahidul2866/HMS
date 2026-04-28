"""add doctor opd fee and opd payment fields

Revision ID: 20260411_0020
Revises: 20260320_0019
Create Date: 2026-04-11 11:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260411_0020"
down_revision = "20260320_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("opd_consultation_fee", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("opd_visits", sa.Column("consultation_discount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("opd_visits", sa.Column("consultation_total", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("opd_visits", sa.Column("consultation_payment_status", sa.String(length=30), nullable=False, server_default="unpaid"))
    op.add_column("opd_visits", sa.Column("consultation_paid_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE opd_visits SET consultation_total = consultation_fee WHERE consultation_total = 0")


def downgrade() -> None:
    op.drop_column("opd_visits", "consultation_paid_at")
    op.drop_column("opd_visits", "consultation_payment_status")
    op.drop_column("opd_visits", "consultation_total")
    op.drop_column("opd_visits", "consultation_discount")
    op.drop_column("users", "opd_consultation_fee")
