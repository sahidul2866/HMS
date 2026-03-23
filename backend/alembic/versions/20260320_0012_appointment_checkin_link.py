"""link appointments to opd visits

Revision ID: 20260320_0012
Revises: 20260320_0011
Create Date: 2026-03-20 23:40:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260320_0012"
down_revision = "20260320_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("opd_visits", sa.Column("source_appointment_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_opd_visits_source_appointment_id_appointments",
        "opd_visits",
        "appointments",
        ["source_appointment_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_opd_visits_source_appointment_id_appointments", "opd_visits", type_="foreignkey")
    op.drop_column("opd_visits", "source_appointment_id")
