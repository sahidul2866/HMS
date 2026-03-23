"""add integrated clinical and billing user links

Revision ID: 20260320_0009
Revises: 20260320_0008
Create Date: 2026-03-20 20:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0009"
down_revision = "20260320_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "opd_visits",
        sa.Column("consulting_doctor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_opd_visits_consulting_doctor_user_id_users",
        "opd_visits",
        "users",
        ["consulting_doctor_user_id"],
        ["id"],
    )
    op.add_column(
        "opd_visits",
        sa.Column("converted_ipd_admission_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_opd_visits_converted_ipd_admission_id_ipd_admissions",
        "opd_visits",
        "ipd_admissions",
        ["converted_ipd_admission_id"],
        ["id"],
    )
    op.add_column("opd_visit_orders", sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"))
    op.add_column(
        "ipd_admissions",
        sa.Column("attending_doctor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_ipd_admissions_attending_doctor_user_id_users",
        "ipd_admissions",
        "users",
        ["attending_doctor_user_id"],
        ["id"],
    )
    op.add_column(
        "billing_invoices",
        sa.Column("internal_referral_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_billing_invoices_internal_referral_user_id_users",
        "billing_invoices",
        "users",
        ["internal_referral_user_id"],
        ["id"],
    )
    op.add_column(
        "pharmacy_dispenses",
        sa.Column("source_visit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pharmacy_dispenses",
        sa.Column("source_visit_order_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_pharmacy_dispenses_source_visit_id_opd_visits",
        "pharmacy_dispenses",
        "opd_visits",
        ["source_visit_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_pharmacy_dispenses_source_visit_order_id_opd_visit_orders",
        "pharmacy_dispenses",
        "opd_visit_orders",
        ["source_visit_order_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_pharmacy_dispenses_source_visit_order_id_opd_visit_orders", "pharmacy_dispenses", type_="foreignkey")
    op.drop_constraint("fk_pharmacy_dispenses_source_visit_id_opd_visits", "pharmacy_dispenses", type_="foreignkey")
    op.drop_column("pharmacy_dispenses", "source_visit_order_id")
    op.drop_column("pharmacy_dispenses", "source_visit_id")
    op.drop_constraint("fk_billing_invoices_internal_referral_user_id_users", "billing_invoices", type_="foreignkey")
    op.drop_column("billing_invoices", "internal_referral_user_id")
    op.drop_constraint("fk_ipd_admissions_attending_doctor_user_id_users", "ipd_admissions", type_="foreignkey")
    op.drop_column("ipd_admissions", "attending_doctor_user_id")
    op.drop_column("opd_visit_orders", "status")
    op.drop_constraint("fk_opd_visits_converted_ipd_admission_id_ipd_admissions", "opd_visits", type_="foreignkey")
    op.drop_column("opd_visits", "converted_ipd_admission_id")
    op.drop_constraint("fk_opd_visits_consulting_doctor_user_id_users", "opd_visits", type_="foreignkey")
    op.drop_column("opd_visits", "consulting_doctor_user_id")
