"""Review stock counts, historical return evidence and disposal; repair reception scope."""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '20261101_0068'
down_revision = '20261101_0067'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('pharmacy_stock_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('branches.id')),
        sa.Column('kind', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('submitted_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reviewed_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('review_note', sa.Text()), sa.Column('reviewed_at', sa.String(40)),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)), sa.Column('updated_by', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index('ix_pharmacy_stock_reviews_branch_id','pharmacy_stock_reviews',['branch_id'])
    connection = op.get_bind()
    permission_id = uuid4()
    connection.execute(sa.text("INSERT INTO permissions (id,code,module,action,description,is_active,created_at,updated_at) VALUES (:id,'pharmacy.stock.approve','pharmacy','stock.approve','Approve stock reconciliation and disposal evidence',true,now(),now()) ON CONFLICT (code) DO NOTHING"), {'id':permission_id})
    connection.execute(sa.text("INSERT INTO role_permissions (role_id,permission_id) SELECT r.id,p.id FROM roles r CROSS JOIN permissions p WHERE r.code IN ('SUPER_ADMIN','ADMIN') AND p.code='pharmacy.stock.approve' ON CONFLICT DO NOTHING"))
    connection.execute(sa.text("INSERT INTO role_permissions (role_id,permission_id) SELECT r.id,p.id FROM roles r CROSS JOIN permissions p WHERE r.code='RECEPTIONIST' AND p.code='opd.view.doctor_wise' ON CONFLICT DO NOTHING"))


def downgrade():
    op.drop_index('ix_pharmacy_stock_reviews_branch_id',table_name='pharmacy_stock_reviews')
    op.drop_table('pharmacy_stock_reviews')
    # Keep assigned permissions: revoking independently administered access is unsafe.
