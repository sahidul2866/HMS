"""Allow the OT billing officer to invoice the service charges their role records."""
from alembic import op
revision='20261101_0072'
down_revision='20261101_0071'
branch_labels=None
depends_on=None

def upgrade():
    op.execute("INSERT INTO role_permissions(role_id,permission_id) SELECT r.id,p.id FROM roles r CROSS JOIN permissions p WHERE r.code='OT_BILLING_OFFICER' AND p.code='billing.item.service' ON CONFLICT DO NOTHING")

def downgrade():
    pass  # Preserve independently administered permission assignments.
