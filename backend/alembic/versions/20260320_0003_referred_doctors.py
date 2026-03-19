"""add referred doctors

Revision ID: 20260320_0003
Revises: 20260320_0002
Create Date: 2026-03-20 00:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0003"
down_revision = "20260320_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referred_doctors",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("doctor_code", sa.String(length=50), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("specialty", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], name=op.f("fk_referred_doctors_branch_id_branches")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_referred_doctors")),
    )
    op.create_index(op.f("ix_referred_doctors_doctor_code"), "referred_doctors", ["doctor_code"], unique=False)

    op.add_column("billing_invoices", sa.Column("referred_doctor_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_billing_invoices_referred_doctor_id_referred_doctors"),
        "billing_invoices",
        "referred_doctors",
        ["referred_doctor_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_billing_invoices_referred_doctor_id_referred_doctors"), "billing_invoices", type_="foreignkey")
    op.drop_column("billing_invoices", "referred_doctor_id")
    op.drop_index(op.f("ix_referred_doctors_doctor_code"), table_name="referred_doctors")
    op.drop_table("referred_doctors")
