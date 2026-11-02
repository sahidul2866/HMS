"""Source-linked operational posting, payroll corrections and salary revisions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision='20261101_0074'
down_revision='20261101_0073'
branch_labels=None
depends_on=None

def uid(name, target=None, nullable=True):
    return sa.Column(name,UUID(as_uuid=True),*( [sa.ForeignKey(target)] if target else []),nullable=nullable)
def base():
    return [sa.Column('id',UUID(as_uuid=True),primary_key=True),sa.Column('is_active',sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),uid('created_by'),uid('updated_by')]
def upgrade():
    op.create_table('operational_postings',*base(),uid('branch_id','branches.id',False),sa.Column('source_type',sa.String(60),nullable=False),uid('source_id',nullable=False),sa.Column('event',sa.String(60),nullable=False),sa.Column('amount',sa.Numeric(14,2),nullable=False,server_default='0'),uid('invoice_id','billing_invoices.id'),uid('journal_id','journal_entries.id'),sa.Column('details',sa.JSON()),sa.UniqueConstraint('source_type','source_id','event',name='uq_operational_posting_source_event'))
    op.create_index('ix_operational_postings_branch_id','operational_postings',['branch_id'])
    op.create_table('hr_salary_revisions',*base(),uid('employee_id','hr_employees.id',False),uid('branch_id','branches.id',False),sa.Column('effective_from',sa.Date(),nullable=False),sa.Column('components',sa.JSON(),nullable=False),sa.UniqueConstraint('employee_id','effective_from',name='uq_hr_salary_revision_date'))
    op.create_table('hr_payroll_adjustments',*base(),uid('employee_id','hr_employees.id',False),uid('branch_id','branches.id',False),uid('source_payroll_item_id','hr_payroll_items.id'),uid('payroll_item_id','hr_payroll_items.id'),sa.Column('target_month',sa.String(7),nullable=False),sa.Column('kind',sa.String(30),nullable=False),sa.Column('amount',sa.Numeric(12,2),nullable=False),sa.Column('reason',sa.Text(),nullable=False),sa.Column('status',sa.String(30),nullable=False,server_default='pending'),uid('approved_by_user_id','users.id'))
    for table,column,target in [('catering_meal_plans','inventory_store_id','inventory_stores.id'),('catering_inventory_usage','inventory_store_id','inventory_stores.id'),('catering_inventory_usage','stock_transaction_id','inventory_stock_transactions.id'),('catering_staff_meal_orders','payroll_item_id','hr_payroll_items.id')]:
        op.add_column(table,uid(column,target))
    for table in ['catering_meal_tasks','transport_trips']:
        op.add_column(table,sa.Column('posting_policy',sa.String(30),nullable=False,server_default='manual_review'))
    op.add_column('catering_staff_meal_orders',sa.Column('deduction_state',sa.String(30),nullable=False,server_default='manual_review'))
    for column in ['staff_meal_deduction','adjustment_earnings','adjustment_deductions']:
        op.add_column('hr_payroll_items',sa.Column(column,sa.Numeric(12,2),nullable=False,server_default='0'))
    # No historic stock, charges or meal deductions are inferred or posted.
    for role in ['KITCHEN_STAFF','CATERING_MANAGER','TRANSPORT_DRIVER','TRANSPORT_MANAGER']:
        op.execute(sa.text("INSERT INTO role_permissions(role_id,permission_id) SELECT r.id,p.id FROM roles r CROSS JOIN permissions p WHERE r.code=:role AND p.code='billing.item.service' ON CONFLICT DO NOTHING").bindparams(role=role))

def downgrade():
    raise RuntimeError('Posting history must be retained; restore through a reviewed forward migration')
