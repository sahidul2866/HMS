"""revoke staff appointment permissions from patient role

Revision ID: 20260621_0060
Revises: 20260604_0059
Create Date: 2026-06-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260621_0060"
down_revision = "20260604_0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id = (SELECT id FROM roles WHERE code = 'PATIENT')
              AND permission_id IN (
                  SELECT id FROM permissions
                  WHERE code IN ('appointment.view', 'appointment.book')
              )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.code = 'PATIENT'
              AND p.code IN ('appointment.view', 'appointment.book')
            ON CONFLICT DO NOTHING
            """
        )
    )
