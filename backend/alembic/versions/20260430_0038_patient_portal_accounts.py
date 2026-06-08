"""separate patient portal accounts from staff users

Revision ID: 20260430_0038
Revises: 20260430_0037
Create Date: 2026-04-30 02:05:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260430_0038"
down_revision = "20260430_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_portal_accounts",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_patient_portal_accounts_branch_id"), "patient_portal_accounts", ["branch_id"])
    op.create_index(op.f("ix_patient_portal_accounts_email"), "patient_portal_accounts", ["email"])
    op.create_index(op.f("ix_patient_portal_accounts_patient_id"), "patient_portal_accounts", ["patient_id"])
    op.create_index(op.f("ix_patient_portal_accounts_username"), "patient_portal_accounts", ["username"])

    op.create_table(
        "patient_portal_refresh_tokens",
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("token_jti", sa.String(length=80), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["patient_portal_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_patient_portal_refresh_tokens_account_id"), "patient_portal_refresh_tokens", ["account_id"])
    op.create_index(op.f("ix_patient_portal_refresh_tokens_session_id"), "patient_portal_refresh_tokens", ["session_id"])
    op.create_index(op.f("ix_patient_portal_refresh_tokens_token_hash"), "patient_portal_refresh_tokens", ["token_hash"])

    op.execute(
        """
        INSERT INTO patient_portal_accounts (
            branch_id, patient_id, username, email, full_name, hashed_password, phone,
            last_login_at, created_at, updated_at, created_by, updated_by, id, is_active
        )
        SELECT
            u.branch_id, u.patient_id, u.username, u.email, u.full_name, u.hashed_password, p.phone,
            u.last_login_at, u.created_at, now(), u.created_by, u.updated_by, u.id, u.is_active
        FROM users u
        JOIN patients p ON p.id = u.patient_id
        WHERE u.patient_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM patient_portal_accounts a
            WHERE a.username = u.username OR a.email = u.email
          )
        """
    )

    op.execute(
        """
        UPDATE users u
        SET is_active = false, updated_at = now()
        WHERE u.patient_id IS NOT NULL
          AND EXISTS (
            SELECT 1 FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            WHERE ur.user_id = u.id AND r.code = 'PATIENT'
          )
        """
    )
    op.add_column("appointments", sa.Column("booked_by_patient_account_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.alter_column("appointments", "booked_by_user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.create_foreign_key(
        op.f("fk_appointments_booked_by_patient_account_id_patient_portal_accounts"),
        "appointments",
        "patient_portal_accounts",
        ["booked_by_patient_account_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_appointments_booked_by_patient_account_id_patient_portal_accounts"), "appointments", type_="foreignkey")
    op.drop_column("appointments", "booked_by_patient_account_id")
    op.alter_column("appointments", "booked_by_user_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.execute(
        """
        UPDATE users u
        SET is_active = true, updated_at = now()
        WHERE u.patient_id IS NOT NULL
          AND EXISTS (
            SELECT 1 FROM patient_portal_accounts a
            WHERE a.username = u.username OR a.email = u.email
          )
        """
    )
    op.drop_table("patient_portal_refresh_tokens")
    op.drop_table("patient_portal_accounts")
