"""OPD draft concurrency, signed revisions, versioned templates and direct payment claims."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision='20261119_0077'
down_revision='20261119_0076'
branch_labels=None
depends_on=None


def base():
    return [sa.Column('id',UUID(as_uuid=True),primary_key=True),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('created_by',UUID(as_uuid=True)),sa.Column('updated_by',UUID(as_uuid=True)),sa.Column('is_active',sa.Boolean(),nullable=False,server_default=sa.true())]


def upgrade():
    op.create_index('ix_opd_doctor_worklist','opd_visits',['branch_id','consulting_doctor_user_id','visit_date','status'],if_not_exists=True)
    op.create_index('ix_medicine_prescribing_scope','pharmacy_medicines',['branch_id','is_active','name'],if_not_exists=True)
    op.create_index('ix_prescription_template_assignment','configuration_profiles',['profile_type','branch_id','is_active','target_id'],if_not_exists=True)
    op.add_column('users',sa.Column('opd_bmdc_registration',sa.String(80)))
    op.add_column('users',sa.Column('opd_signature_image',sa.Text()))
    op.add_column('pharmacy_medicines',sa.Column('search_aliases',sa.JSON()))
    for column in [sa.Column('prescription_data',sa.JSON()),sa.Column('prescription_template_id',UUID(as_uuid=True),sa.ForeignKey('configuration_profiles.id')),sa.Column('clinical_version',sa.Integer(),nullable=False,server_default='0'),sa.Column('prescription_status',sa.String(20),nullable=False,server_default='draft'),sa.Column('consultation_payment_source',sa.String(30),nullable=False,server_default='pending')]:op.add_column('opd_visits',column)
    op.add_column('opd_visit_orders',sa.Column('version',sa.Integer(),nullable=False,server_default='0'))
    op.add_column('opd_visit_orders',sa.Column('prescription_detail',sa.JSON()))
    op.add_column('opd_visit_orders',sa.Column('request_key',sa.String(100)))
    op.create_unique_constraint('uq_opd_visit_order_request','opd_visit_orders',['visit_id','request_key'])
    op.add_column('configuration_profiles',sa.Column('version',sa.Integer(),nullable=False,server_default='1'))
    op.create_table('prescription_revisions',*base(),sa.Column('visit_id',UUID(as_uuid=True),sa.ForeignKey('opd_visits.id'),nullable=False,index=True),sa.Column('version',sa.Integer(),nullable=False),sa.Column('status',sa.String(20),nullable=False),sa.Column('doctor_id',UUID(as_uuid=True),sa.ForeignKey('users.id')),sa.Column('reason',sa.Text()),sa.Column('snapshot',sa.JSON(),nullable=False),sa.Column('signed_at',sa.DateTime(timezone=True)),sa.UniqueConstraint('visit_id','version',name='uq_prescription_visit_version'))
    op.create_table('configuration_profile_versions',*base(),sa.Column('profile_id',UUID(as_uuid=True),sa.ForeignKey('configuration_profiles.id'),nullable=False,index=True),sa.Column('version',sa.Integer(),nullable=False),sa.Column('snapshot',sa.JSON(),nullable=False),sa.UniqueConstraint('profile_id','version',name='uq_configuration_profile_version'))
    op.create_table('opd_external_payments',*base(),sa.Column('visit_id',UUID(as_uuid=True),sa.ForeignKey('opd_visits.id'),nullable=False,index=True),sa.Column('kind',sa.String(30),nullable=False),sa.Column('amount',sa.Numeric(12,2),nullable=False),sa.Column('request_key',sa.String(100),nullable=False),sa.Column('reason',sa.Text(),nullable=False),sa.Column('settlement_snapshot',sa.JSON(),nullable=False),sa.UniqueConstraint('visit_id','request_key',name='uq_opd_external_payment_request'))
    op.create_table('prescription_events',*base(),sa.Column('visit_id',UUID(as_uuid=True),sa.ForeignKey('opd_visits.id'),nullable=False,index=True),sa.Column('actor_id',UUID(as_uuid=True),sa.ForeignKey('users.id'),nullable=False),sa.Column('kind',sa.String(40),nullable=False),sa.Column('detail',sa.JSON(),nullable=False))
    op.create_table('prescription_shortcuts',*base(),sa.Column('owner_id',UUID(as_uuid=True),sa.ForeignKey('users.id'),nullable=False,index=True),sa.Column('branch_id',UUID(as_uuid=True),sa.ForeignKey('branches.id')),sa.Column('kind',sa.String(30),nullable=False),sa.Column('name',sa.String(150),nullable=False),sa.Column('content',sa.JSON(),nullable=False))
    # Preserve already completed legacy clinical records without inventing a signing time.
    op.execute("""INSERT INTO prescription_revisions(id,visit_id,version,status,doctor_id,snapshot,signed_at,created_by,updated_by)
        SELECT v.id,v.id,1,'finalized',v.consulting_doctor_user_id,
        to_jsonb(v) || jsonb_build_object('legacy_import',true,'signed_at',NULL,
          'patient',jsonb_build_object('first_name',p.first_name,'last_name',p.last_name,'patient_number',p.patient_number,'date_of_birth',p.date_of_birth,'gender',p.gender,'phone',p.phone),
          'doctor',jsonb_build_object('full_name',v.consulting_doctor_name),'template_payload','{}'::jsonb,
          'orders',COALESCE((SELECT jsonb_agg(to_jsonb(o)) FROM opd_visit_orders o WHERE o.visit_id=v.id AND o.status<>'cancelled'),'[]'::jsonb)),
        NULL,v.registered_by_user_id,v.registered_by_user_id
        FROM opd_visits v JOIN patients p ON p.id=v.patient_id WHERE v.status IN ('prescribed','completed')""")
    op.execute("UPDATE opd_visits SET prescription_status='finalized' WHERE status IN ('prescribed','completed')")
    op.execute("""CREATE FUNCTION prescription_history_immutable() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'Clinical history is append-only'; END; $$ LANGUAGE plpgsql""")
    for table in ['prescription_revisions','configuration_profile_versions','opd_external_payments','prescription_events']:
        op.execute(f'CREATE TRIGGER clinical_history_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION prescription_history_immutable()')
    op.execute("""INSERT INTO configuration_profile_versions (id,profile_id,version,snapshot,created_by,updated_by) SELECT id,id,version,json_build_object('name',name,'scope',scope,'target_type',target_type,'target_id',target_id,'payload',payload),created_by,updated_by FROM configuration_profiles""")


def downgrade():
    op.drop_index('ix_opd_doctor_worklist',table_name='opd_visits')
    op.drop_index('ix_medicine_prescribing_scope',table_name='pharmacy_medicines')
    op.drop_index('ix_prescription_template_assignment',table_name='configuration_profiles')
    op.drop_column('users','opd_signature_image');op.drop_column('users','opd_bmdc_registration')
    op.drop_column('pharmacy_medicines','search_aliases')
    for table in ['prescription_revisions','configuration_profile_versions','opd_external_payments','prescription_events']:op.execute(f'DROP TRIGGER clinical_history_immutable ON {table}')
    op.execute('DROP FUNCTION prescription_history_immutable()')
    for table in ['prescription_events','prescription_shortcuts','opd_external_payments','configuration_profile_versions','prescription_revisions']:op.drop_table(table)
    op.drop_column('configuration_profiles','version')
    op.drop_constraint('uq_opd_visit_order_request','opd_visit_orders',type_='unique')
    op.drop_column('opd_visit_orders','version')
    op.drop_column('opd_visit_orders','request_key');op.drop_column('opd_visit_orders','prescription_detail')
    for name in ['consultation_payment_source','prescription_status','clinical_version','prescription_template_id','prescription_data']:op.drop_column('opd_visits',name)
