"""Freeze bed stay rates and retain calendar dates on billed bed charges."""
from alembic import op
import sqlalchemy as sa
revision='20261031_0065'
down_revision='20261031_0064'
branch_labels=None
depends_on=None

def upgrade():
    op.execute('\nCREATE TABLE ipd_bed_stays (\n\tadmission_id UUID NOT NULL, \n\tbed_id UUID, \n\tward_name VARCHAR(120) NOT NULL, \n\tbed_number VARCHAR(60) NOT NULL, \n\tdaily_rate NUMERIC(12, 2) NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tended_at TIMESTAMP WITH TIME ZONE, \n\testimated BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcreated_by UUID, \n\tupdated_by UUID, \n\tCONSTRAINT pk_ipd_bed_stays PRIMARY KEY (id), \n\tCONSTRAINT fk_ipd_bed_stays_admission_id_ipd_admissions FOREIGN KEY(admission_id) REFERENCES ipd_admissions (id), \n\tCONSTRAINT fk_ipd_bed_stays_bed_id_ipd_beds FOREIGN KEY(bed_id) REFERENCES ipd_beds (id)\n)\n\n')
    op.execute('CREATE INDEX ix_ipd_bed_stays_admission_id ON ipd_bed_stays (admission_id)')
    op.add_column('billing_invoice_items',sa.Column('bed_charge_date',sa.Date()))
    op.execute("INSERT INTO ipd_bed_stays (id,admission_id,bed_id,ward_name,bed_number,daily_rate,started_at,ended_at,estimated,is_active,created_at,updated_at) SELECT id,id,bed_id,ward_name,bed_number,daily_charge,admitted_at,discharged_at,true,true,now(),now() FROM ipd_admissions")

def downgrade():
    op.drop_column('billing_invoice_items','bed_charge_date')
    op.drop_table('ipd_bed_stays')
