"""add configuration profiles

Revision ID: 20260430_0036
Revises: 20260429_0035
Create Date: 2026-04-30 00:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260430_0036"
down_revision = "20260429_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuration_profiles",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("profile_type", sa.String(length=80), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.String(length=60), nullable=False, server_default="hospital"),
        sa.Column("target_type", sa.String(length=80), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], name=op.f("fk_configuration_profiles_branch_id_branches")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_configuration_profiles")),
        sa.UniqueConstraint("branch_id", "profile_type", "code", name="uq_configuration_profiles_branch_type_code"),
    )
    op.create_index("ix_configuration_profiles_profile_type", "configuration_profiles", ["profile_type"])


def downgrade() -> None:
    op.drop_index("ix_configuration_profiles_profile_type", table_name="configuration_profiles")
    op.drop_table("configuration_profiles")
