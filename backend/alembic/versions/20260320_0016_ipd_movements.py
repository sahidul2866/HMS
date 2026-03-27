"""add ipd admission movements

Revision ID: 20260320_0016
Revises: 20260320_0015
Create Date: 2026-03-26 04:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0016"
down_revision = "20260320_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ipd_admission_movements",
        sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.String(length=30), nullable=False),
        sa.Column("moved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("from_ward_name", sa.String(length=120), nullable=True),
        sa.Column("from_bed_number", sa.String(length=60), nullable=True),
        sa.Column("to_ward_name", sa.String(length=120), nullable=True),
        sa.Column("to_bed_number", sa.String(length=60), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("moved_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"], name=op.f("fk_ipd_admission_movements_admission_id_ipd_admissions")),
        sa.ForeignKeyConstraint(["moved_by_user_id"], ["users.id"], name=op.f("fk_ipd_admission_movements_moved_by_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ipd_admission_movements")),
    )


def downgrade() -> None:
    op.drop_table("ipd_admission_movements")
