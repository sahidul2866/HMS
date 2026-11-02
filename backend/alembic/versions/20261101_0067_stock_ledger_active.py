"""Align legacy stock transaction ledger with the shared active flag."""
from alembic import op
import sqlalchemy as sa
revision='20261101_0067'
down_revision='20261101_0066'
branch_labels=None
depends_on=None
def upgrade():
    op.execute('ALTER TABLE inventory_stock_transactions ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE')
def downgrade():
    op.drop_column('inventory_stock_transactions','is_active')
