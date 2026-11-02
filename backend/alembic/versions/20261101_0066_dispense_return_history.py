"""Track inspected physical returns against original issues."""
from alembic import op
import sqlalchemy as sa
revision='20261101_0066'
down_revision='20261031_0065'
branch_labels=None
depends_on=None
def upgrade():
    op.add_column('pharmacy_dispenses',sa.Column('return_history',sa.JSON(),nullable=True))
def downgrade():
    op.drop_column('pharmacy_dispenses','return_history')
