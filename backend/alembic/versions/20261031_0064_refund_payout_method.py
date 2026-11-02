"""Persist the actual refund payout method for cashier reconciliation."""
from alembic import op
import sqlalchemy as sa
revision='20261031_0064'
down_revision='20261031_0063'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('billing_refunds',sa.Column('payment_method',sa.String(30),nullable=False,server_default='cash'))
    op.execute('UPDATE billing_refunds r SET payment_method=p.payment_method FROM billing_payments p WHERE r.payment_id=p.id')

def downgrade():
    op.drop_column('billing_refunds','payment_method')
