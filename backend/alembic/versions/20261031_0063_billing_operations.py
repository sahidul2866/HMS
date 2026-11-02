"""Billing classification, immutable snapshots and cash custody."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision='20261031_0063'
down_revision='20260707_0062'
branch_labels=None
depends_on=None


def upgrade():
    op.execute('\nCREATE TABLE billing_types (\n\tbranch_id UUID, \n\tcode VARCHAR(40) NOT NULL, \n\tname VARCHAR(120) NOT NULL, \n\tdepartment VARCHAR(120) NOT NULL, \n\tid UUID NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcreated_by UUID, \n\tupdated_by UUID, \n\tCONSTRAINT pk_billing_types PRIMARY KEY (id), \n\tCONSTRAINT uq_billing_types_branch_code UNIQUE (branch_id, code), \n\tCONSTRAINT fk_billing_types_branch_id_branches FOREIGN KEY(branch_id) REFERENCES branches (id)\n)\n\n')
    op.execute('\nCREATE TABLE billing_events (\n\tbranch_id UUID, \n\tinvoice_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\tkind VARCHAR(40) NOT NULL, \n\treason TEXT, \n\tsnapshot JSON NOT NULL, \n\tid UUID NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcreated_by UUID, \n\tupdated_by UUID, \n\tCONSTRAINT pk_billing_events PRIMARY KEY (id), \n\tCONSTRAINT fk_billing_events_branch_id_branches FOREIGN KEY(branch_id) REFERENCES branches (id), \n\tCONSTRAINT fk_billing_events_invoice_id_billing_invoices FOREIGN KEY(invoice_id) REFERENCES billing_invoices (id), \n\tCONSTRAINT fk_billing_events_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_billing_events_invoice_id ON billing_events (invoice_id)')
    op.execute('\nCREATE TABLE billing_cash_handovers (\n\tbranch_id UUID, \n\tnumber VARCHAR(60) NOT NULL, \n\tcollector_id UUID NOT NULL, \n\treceiver_id UUID NOT NULL, \n\texpected_amount NUMERIC(12, 2) NOT NULL, \n\tdeclared_amount NUMERIC(12, 2) NOT NULL, \n\tvariance NUMERIC(12, 2) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tnote TEXT NOT NULL, \n\taccepted_at TIMESTAMP WITH TIME ZONE, \n\tacceptance_note TEXT, \n\tid UUID NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcreated_by UUID, \n\tupdated_by UUID, \n\tCONSTRAINT pk_billing_cash_handovers PRIMARY KEY (id), \n\tCONSTRAINT fk_billing_cash_handovers_branch_id_branches FOREIGN KEY(branch_id) REFERENCES branches (id), \n\tCONSTRAINT uq_billing_cash_handovers_number UNIQUE (number), \n\tCONSTRAINT fk_billing_cash_handovers_collector_id_users FOREIGN KEY(collector_id) REFERENCES users (id), \n\tCONSTRAINT fk_billing_cash_handovers_receiver_id_users FOREIGN KEY(receiver_id) REFERENCES users (id)\n)\n\n')
    op.execute('\nCREATE TABLE billing_cash_handover_entries (\n\thandover_id UUID NOT NULL, \n\tpayment_id UUID, \n\trefund_id UUID, \n\tamount NUMERIC(12, 2) NOT NULL, \n\tid UUID NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcreated_by UUID, \n\tupdated_by UUID, \n\tCONSTRAINT pk_billing_cash_handover_entries PRIMARY KEY (id), \n\tCONSTRAINT fk_billing_cash_handover_entries_handover_id_billing_ca_5669 FOREIGN KEY(handover_id) REFERENCES billing_cash_handovers (id), \n\tCONSTRAINT uq_billing_cash_handover_entries_payment_id UNIQUE (payment_id), \n\tCONSTRAINT fk_billing_cash_handover_entries_payment_id_billing_payments FOREIGN KEY(payment_id) REFERENCES billing_payments (id), \n\tCONSTRAINT uq_billing_cash_handover_entries_refund_id UNIQUE (refund_id), \n\tCONSTRAINT fk_billing_cash_handover_entries_refund_id_billing_refunds FOREIGN KEY(refund_id) REFERENCES billing_refunds (id)\n)\n\n')
    op.execute('\nCREATE TABLE billing_report_snapshots (\n\tbranch_id UUID, \n\tactor_id UUID NOT NULL, \n\tfilters JSON NOT NULL, \n\tstatistics JSON NOT NULL, \n\tid UUID NOT NULL, \n\tis_active BOOLEAN NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tcreated_by UUID, \n\tupdated_by UUID, \n\tCONSTRAINT pk_billing_report_snapshots PRIMARY KEY (id), \n\tCONSTRAINT fk_billing_report_snapshots_branch_id_branches FOREIGN KEY(branch_id) REFERENCES branches (id), \n\tCONSTRAINT fk_billing_report_snapshots_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n')
    op.add_column('billing_item_configs',sa.Column('billing_type_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('billing_types.id')))
    op.add_column('billing_invoices',sa.Column('billing_type_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('billing_types.id')))
    for table in ('billing_invoices','billing_invoice_items'):
        op.add_column(table,sa.Column('billing_type_name',sa.String(120)))
        op.add_column(table,sa.Column('billing_department',sa.String(120)))
    op.add_column('billing_invoices',sa.Column('discount_reason',sa.Text()))


def downgrade():
    op.drop_column('billing_invoices','discount_reason')
    for table in ('billing_invoices','billing_invoice_items'):
        op.drop_column(table,'billing_department');op.drop_column(table,'billing_type_name')
    op.drop_column('billing_invoices','billing_type_id');op.drop_column('billing_item_configs','billing_type_id')
    for table in ('billing_report_snapshots','billing_cash_handover_entries','billing_cash_handovers','billing_events','billing_types'):
        op.drop_table(table)
