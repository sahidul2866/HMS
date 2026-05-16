"""Add assignment-level access scopes.

Revision ID: 20260513_0056
Revises: 20260511_0055
Create Date: 2026-05-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "20260513_0056"
down_revision: str | None = "20260511_0055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    return name in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    for table_name, principal_column, principal_table in (
        ("user_scopes", "user_id", "users"),
        ("role_scopes", "role_id", "roles"),
    ):
        if _has_table(table_name):
            continue
        op.create_table(
            table_name,
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(principal_column, postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("scope_type", sa.String(60), nullable=False),
            sa.Column("scope_value", sa.String(180), nullable=True),
            sa.Column("scope_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("module", sa.String(60), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_temporary", sa.Boolean(), nullable=False, server_default="false") if table_name == "user_scopes" else sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_override", sa.Boolean(), nullable=False, server_default="false") if table_name == "user_scopes" else sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
            *(
                [sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True), sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True)]
                if table_name == "user_scopes"
                else []
            ),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.ForeignKeyConstraint([principal_column], [f"{principal_table}.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(f"ix_{table_name}_principal_scope", table_name, [principal_column, "scope_type", "module", "status"])
        op.create_index(f"ix_{table_name}_ref", table_name, ["scope_type", "scope_ref_id"])
        op.create_index(f"ix_{table_name}_value", table_name, ["scope_type", "scope_value"])


def downgrade() -> None:
    for table_name in ("role_scopes", "user_scopes"):
        if _has_table(table_name):
            op.drop_table(table_name)
