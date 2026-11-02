"""Restore provable ownership on donors created before branch stamping was enforced."""
from alembic import op
revision='20261101_0071'
down_revision='20261101_0070'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('UPDATE blood_donors d SET branch_id=u.branch_id FROM users u WHERE d.branch_id IS NULL AND d.created_by=u.id')
    op.execute('UPDATE blood_units b SET branch_id=d.branch_id FROM blood_donors d WHERE b.branch_id IS NULL AND b.donor_id=d.id')

def downgrade():
    pass  # Keep recovered ownership; clearing it would remove isolation evidence.
