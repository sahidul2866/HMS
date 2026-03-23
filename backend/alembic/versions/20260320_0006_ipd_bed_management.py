"""add ipd bed management

Revision ID: 20260320_0006
Revises: 20260320_0005
Create Date: 2026-03-20 17:15:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0006"
down_revision = "20260320_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ipd_beds",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ward_name", sa.String(length=120), nullable=False),
        sa.Column("bed_number", sa.String(length=60), nullable=False),
        sa.Column("bed_type", sa.String(length=40), nullable=False, server_default="general"),
        sa.Column("daily_rate", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="available"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ipd_beds_bed_number"), "ipd_beds", ["bed_number"], unique=False)
    op.add_column("ipd_admissions", sa.Column("bed_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_ipd_admissions_bed_id_ipd_beds"),
        "ipd_admissions",
        "ipd_beds",
        ["bed_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_ipd_admissions_bed_id_ipd_beds"), "ipd_admissions", type_="foreignkey")
    op.drop_column("ipd_admissions", "bed_id")
    op.drop_index(op.f("ix_ipd_beds_bed_number"), table_name="ipd_beds")
    op.drop_table("ipd_beds")
