"""Allow an inspected unused returned unit to retain multiple issue-history entries."""
from alembic import op
revision='20261101_0070'
down_revision='20261101_0069'
branch_labels=None
depends_on=None

def upgrade():
    op.drop_constraint('uq_blood_issues_unit_id','blood_issues',type_='unique')

def downgrade():
    # Refuse to erase valid issue history when a unit has been reissued.
    op.create_unique_constraint('uq_blood_issues_unit_id','blood_issues',['unit_id'])
