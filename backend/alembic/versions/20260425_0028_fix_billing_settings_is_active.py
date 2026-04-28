"""fix billing settings common active column

Revision ID: 20260425_0028
Revises: 20260420_0027
Create Date: 2026-04-25 15:40:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260425_0028"
down_revision = "20260420_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE billing_settings ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true NOT NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE billing_settings DROP COLUMN IF EXISTS is_active")
