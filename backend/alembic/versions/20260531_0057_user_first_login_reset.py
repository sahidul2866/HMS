"""Add first-login password reset flag to users."""

from alembic import op
import sqlalchemy as sa


revision = "20260531_0057"
down_revision = "20260513_0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("must_reset_password", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("users", "must_reset_password", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "must_reset_password")
