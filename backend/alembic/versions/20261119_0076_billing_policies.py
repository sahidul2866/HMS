"""Versioned policies, frozen invoice rules, participant accounts and request deduplication."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '20261119_0076'
down_revision = '20261101_0075'
branch_labels = None
depends_on = None


def base():
    return [sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('created_by', UUID(as_uuid=True)), sa.Column('updated_by', UUID(as_uuid=True)),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true())]


def upgrade():
    op.add_column('referred_doctors', sa.Column('referrer_type', sa.String(30), nullable=False, server_default='external_doctor'))
    op.add_column('billing_invoice_items', sa.Column('financial_snapshot', sa.JSON()))
    op.create_table('billing_policies', *base(),
        sa.Column('branch_id', UUID(as_uuid=True), sa.ForeignKey('branches.id'), index=True),
        sa.Column('scope', sa.String(30), nullable=False), sa.Column('selector', sa.String(150), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False), sa.Column('effective_until', sa.DateTime(timezone=True)),
        sa.Column('reason', sa.Text(), nullable=False), sa.Column('rules', sa.JSON(), nullable=False))
    op.create_table('billing_allocations', *base(),
        sa.Column('branch_id', UUID(as_uuid=True), sa.ForeignKey('branches.id'), index=True),
        sa.Column('invoice_id', UUID(as_uuid=True), sa.ForeignKey('billing_invoices.id'), index=True),
        sa.Column('invoice_item_id', UUID(as_uuid=True), sa.ForeignKey('billing_invoice_items.id')),
        sa.Column('participant_key', sa.String(100), nullable=False, index=True),
        sa.Column('component', sa.String(30), nullable=False), sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('state', sa.String(20), nullable=False), sa.Column('request_key', sa.String(100)), sa.Column('reason', sa.Text(), nullable=False),
        sa.UniqueConstraint('branch_id', 'request_key', name='uq_billing_allocation_request'))
    op.create_table('billing_commands', *base(),
        sa.Column('invoice_id', UUID(as_uuid=True), sa.ForeignKey('billing_invoices.id'), nullable=False),
        sa.Column('request_key', sa.String(100), nullable=False), sa.Column('operation', sa.String(40), nullable=False),
        sa.Column('fingerprint', sa.String(64), nullable=False), sa.UniqueConstraint('invoice_id', 'request_key', name='uq_billing_command_request'))

    op.execute("""CREATE FUNCTION billing_reject_history_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'Financial history is append-only'; END;
        $$ LANGUAGE plpgsql""")
    for table in ('billing_policies', 'billing_allocations', 'billing_commands', 'billing_events'):
        op.execute(f'CREATE TRIGGER immutable_financial_history BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION billing_reject_history_mutation()')


def downgrade():
    for table in ('billing_policies', 'billing_allocations', 'billing_commands', 'billing_events'):
        op.execute(f'DROP TRIGGER immutable_financial_history ON {table}')
    op.execute('DROP FUNCTION billing_reject_history_mutation()')
    op.drop_table('billing_commands')
    op.drop_table('billing_allocations')
    op.drop_table('billing_policies')
    op.drop_column('billing_invoice_items', 'financial_snapshot')
    op.drop_column('referred_doctors', 'referrer_type')
