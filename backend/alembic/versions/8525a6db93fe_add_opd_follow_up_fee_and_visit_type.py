"""add_opd_follow_up_fee_and_visit_type

Revision ID: 8525a6db93fe
Revises: 20260411_0020
Create Date: 2026-04-11 14:50:25.031934
"""
from alembic import op
import sqlalchemy as sa

revision = "8525a6db93fe"
down_revision = "20260411_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column("users", sa.Column("opd_follow_up_fee", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("opd_follow_up_days", sa.Integer(), nullable=False, server_default="30"))
    op.add_column("users", sa.Column("opd_prescription_header_name", sa.String(length=180), nullable=True))
    op.add_column("users", sa.Column("opd_prescription_header_degrees", sa.String(length=300), nullable=True))
    op.add_column("users", sa.Column("opd_prescription_header_specialty", sa.String(length=220), nullable=True))
    op.add_column("users", sa.Column("opd_prescription_header_workplace", sa.String(length=220), nullable=True))
    
    # Add visit_type column to opd_visits table
    op.add_column("opd_visits", sa.Column("visit_type", sa.String(20), nullable=False, server_default="new"))


def downgrade() -> None:
    # Remove columns from users table
    op.drop_column("users", "opd_follow_up_fee")
    op.drop_column("users", "opd_follow_up_days")
    op.drop_column("users", "opd_prescription_header_name")
    op.drop_column("users", "opd_prescription_header_degrees")
    op.drop_column("users", "opd_prescription_header_specialty")
    op.drop_column("users", "opd_prescription_header_workplace")
    
    # Remove column from opd_visits table
    op.drop_column("opd_visits", "visit_type")

