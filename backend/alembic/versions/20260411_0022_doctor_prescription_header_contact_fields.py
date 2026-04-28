"""add doctor prescription header contact fields

Revision ID: 20260411_0022
Revises: 20260411_0021
Create Date: 2026-04-11 18:05:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260411_0022"
down_revision = "20260411_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("opd_prescription_header_chamber", sa.String(length=220), nullable=True))
    op.add_column("users", sa.Column("opd_prescription_header_phone", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("opd_prescription_header_address", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "opd_prescription_header_address")
    op.drop_column("users", "opd_prescription_header_phone")
    op.drop_column("users", "opd_prescription_header_chamber")
