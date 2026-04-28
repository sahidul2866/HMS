"""add doctor prescription header settings

Revision ID: 20260411_0021
Revises: 8525a6db93fe
Create Date: 2026-04-11 17:25:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260411_0021"
down_revision = "8525a6db93fe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These columns are already added in the previous migration
    pass


def downgrade() -> None:
    # These columns are handled in the previous migration
    pass
