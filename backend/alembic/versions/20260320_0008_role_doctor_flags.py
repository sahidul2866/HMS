"""add role doctor and referral flags

Revision ID: 20260320_0008
Revises: 20260320_0007
Create Date: 2026-03-20 18:20:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260320_0008"
down_revision = "20260320_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("roles", sa.Column("is_doctor_role", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("roles", sa.Column("is_referral_role", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("roles", "is_referral_role")
    op.drop_column("roles", "is_doctor_role")
