"""add pharmacy partial dispense and return fields

Revision ID: 20260320_0019
Revises: 20260320_0018
Create Date: 2026-03-26 19:20:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260320_0019"
down_revision = "20260320_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pharmacy_dispenses", sa.Column("requested_quantity", sa.Numeric(12, 2), nullable=True))
    op.add_column("pharmacy_dispenses", sa.Column("returned_quantity", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("pharmacy_dispenses", sa.Column("status", sa.String(length=30), nullable=False, server_default="dispensed"))
    op.add_column("pharmacy_dispenses", sa.Column("return_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("pharmacy_dispenses", "return_note")
    op.drop_column("pharmacy_dispenses", "status")
    op.drop_column("pharmacy_dispenses", "returned_quantity")
    op.drop_column("pharmacy_dispenses", "requested_quantity")
