"""Persist and backfill branch ownership for blood units and requests."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='20261101_0069'
down_revision='20261101_0068'
branch_labels=None
depends_on=None

def upgrade():
    for table in ['blood_units','blood_requests']:
        op.add_column(table,sa.Column('branch_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('branches.id'),nullable=True))
        op.create_index('ix_'+table+'_branch_id',table,['branch_id'])
    op.execute("INSERT INTO role_permissions(role_id,permission_id) SELECT r.id,p.id FROM roles r CROSS JOIN permissions p WHERE r.code='OT_MANAGER' AND p.code='ot.inventory.manage' ON CONFLICT DO NOTHING")
    op.execute('UPDATE blood_units u SET branch_id=d.branch_id FROM blood_donors d WHERE u.donor_id=d.id')
    op.execute('UPDATE blood_units u SET branch_id=a.branch_id FROM users a WHERE u.branch_id IS NULL AND u.created_by=a.id')
    op.execute('UPDATE blood_requests r SET branch_id=p.branch_id FROM patients p WHERE r.patient_id=p.id')

def downgrade():
    for table in ['blood_requests','blood_units']:
        op.drop_index('ix_'+table+'_branch_id',table_name=table)
        op.drop_column(table,'branch_id')
