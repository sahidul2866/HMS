"""Record the mobile-banking provider and transaction reference on payments."""
from alembic import op
import sqlalchemy as sa

revision = '20261101_0075'
down_revision = '20261101_0074'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('billing_payments', sa.Column('payment_provider', sa.String(30), nullable=True))
    op.add_column('billing_payments', sa.Column('reference_number', sa.String(80), nullable=True))
    # One transaction reference can settle one receipt only, per provider and method.
    op.create_index('uq_billing_payments_reference', 'billing_payments', ['payment_method', sa.text("coalesce(payment_provider, '')"), 'reference_number'], unique=True, postgresql_where=sa.text('reference_number IS NOT NULL'))


def downgrade():
    op.drop_index('uq_billing_payments_reference', table_name='billing_payments')
    op.drop_column('billing_payments', 'reference_number')
    op.drop_column('billing_payments', 'payment_provider')
