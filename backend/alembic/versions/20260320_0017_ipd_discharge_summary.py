"""add ipd discharge summary fields

Revision ID: 20260320_0017
Revises: 20260320_0016
Create Date: 2026-03-26 04:35:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260320_0017"
down_revision = "20260320_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ipd_admissions", sa.Column("discharge_condition", sa.String(length=120), nullable=True))
    op.add_column("ipd_admissions", sa.Column("discharge_diagnosis", sa.Text(), nullable=True))
    op.add_column("ipd_admissions", sa.Column("discharge_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ipd_admissions", "discharge_summary")
    op.drop_column("ipd_admissions", "discharge_diagnosis")
    op.drop_column("ipd_admissions", "discharge_condition")
