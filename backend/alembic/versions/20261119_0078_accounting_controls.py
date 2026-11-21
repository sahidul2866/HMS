"""Central accounting integrity, versioned policy, periods and immutable posted GL."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision='20261119_0078'
down_revision='20261119_0077'
branch_labels=None
depends_on=None


def base():
    return [sa.Column('id',UUID(as_uuid=True),primary_key=True),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.Column('created_by',UUID(as_uuid=True)),sa.Column('updated_by',UUID(as_uuid=True)),sa.Column('is_active',sa.Boolean(),nullable=False,server_default=sa.true())]


def upgrade():
    op.add_column('supplier_invoices',sa.Column('purchase_account_code',sa.String(50),nullable=False,server_default='1300'))
    op.add_column('supplier_invoices',sa.Column('pharmacy_purchase_id',UUID(as_uuid=True),sa.ForeignKey('pharmacy_purchases.id')))
    op.add_column('inventory_stock_transactions',sa.Column('unit_cost',sa.Numeric(14,4)))
    op.add_column('inventory_stock_transactions',sa.Column('cost_amount',sa.Numeric(14,2)))
    for name in ['inventory_value','valuation_opening_value']:op.add_column('pharmacy_medicines',sa.Column(name,sa.Numeric(14,2)))
    op.add_column('pharmacy_medicines',sa.Column('valuation_opening_journal_id',UUID(as_uuid=True),sa.ForeignKey('journal_entries.id')))
    op.add_column('pharmacy_sales',sa.Column('paid_amount',sa.Numeric(14,2)))
    op.add_column('pharmacy_sales',sa.Column('payment_method',sa.String(40)))
    op.add_column('pharmacy_sales',sa.Column('payment_provider',sa.String(30)))
    op.add_column('pharmacy_sale_items',sa.Column('cost_amount',sa.Numeric(14,2)))
    op.add_column('billing_payments',sa.Column('advance_payment_id',UUID(as_uuid=True),sa.ForeignKey('advance_payments.id')))
    op.add_column('bank_transactions',sa.Column('ledger_account_code',sa.String(50)))
    op.add_column('bank_transactions',sa.Column('statement_key',sa.String(64)))
    op.add_column('bank_transactions',sa.Column('matched_journal_id',UUID(as_uuid=True),sa.ForeignKey('journal_entries.id')))
    op.create_index('uq_bank_statement_key','bank_transactions',['branch_id','statement_key'],unique=True)
    op.add_column('supplier_invoices',sa.Column('receiving_id',UUID(as_uuid=True),sa.ForeignKey('stock_receivings.id')))
    op.add_column('expenses',sa.Column('expense_account_code',sa.String(50),nullable=False,server_default='5180'))
    op.add_column('expenses',sa.Column('cost_center',sa.String(120)))
    op.add_column('cash_closing',sa.Column('cash_account_code',sa.String(50),nullable=False,server_default='1001'))
    op.add_column('cash_closing',sa.Column('counter_name',sa.String(100)))
    op.add_column('cash_closing',sa.Column('opened_at',sa.DateTime(timezone=True)))
    op.add_column('cash_closing',sa.Column('closed_at',sa.DateTime(timezone=True)))
    op.add_column('accounts',sa.Column('parent_id',UUID(as_uuid=True),sa.ForeignKey('accounts.id')))
    op.add_column('accounts',sa.Column('reporting_group',sa.String(80)))
    op.add_column('accounts',sa.Column('is_control',sa.Boolean(),nullable=False,server_default=sa.false()))
    op.create_table('accounting_policies',*base(),sa.Column('branch_id',UUID(as_uuid=True),sa.ForeignKey('branches.id'),nullable=False,index=True),sa.Column('version',sa.Integer(),nullable=False),sa.Column('effective_from',sa.Date(),nullable=False),sa.Column('settings',sa.JSON(),nullable=False),sa.Column('approved_by',UUID(as_uuid=True),sa.ForeignKey('users.id')),sa.UniqueConstraint('branch_id','version',name='uq_accounting_policy_version'))
    op.create_table('financial_periods',*base(),sa.Column('branch_id',UUID(as_uuid=True),sa.ForeignKey('branches.id'),nullable=False,index=True),sa.Column('name',sa.String(100),nullable=False),sa.Column('start_date',sa.Date(),nullable=False),sa.Column('end_date',sa.Date(),nullable=False),sa.Column('status',sa.String(20),nullable=False),sa.UniqueConstraint('branch_id','name',name='uq_financial_period_name'))
    op.add_column('journal_entries',sa.Column('voucher_type',sa.String(30),nullable=False,server_default='journal'))
    op.add_column('journal_entries',sa.Column('period_id',UUID(as_uuid=True),sa.ForeignKey('financial_periods.id')))
    op.add_column('journal_entries',sa.Column('policy_snapshot',sa.JSON()))
    op.add_column('journal_entries',sa.Column('posting_applied_at',sa.DateTime(timezone=True)))
    op.execute("UPDATE journal_entries SET posting_applied_at=COALESCE(posted_at,created_at) WHERE status IN ('posted','reversed')")
    op.create_table('accounting_posting_keys',*base(),sa.Column('branch_id',UUID(as_uuid=True),sa.ForeignKey('branches.id'),nullable=False),sa.Column('source_module',sa.String(80),nullable=False),sa.Column('source_reference',sa.String(120),nullable=False),sa.Column('journal_id',UUID(as_uuid=True),sa.ForeignKey('journal_entries.id'),nullable=False),sa.Column('fingerprint',sa.String(64),nullable=False),sa.UniqueConstraint('branch_id','source_module','source_reference',name='uq_accounting_posting_key'))
    # Retain all historical duplicates; reserve each old source once without reposting anything.
    op.execute("""INSERT INTO accounting_posting_keys(id,branch_id,source_module,source_reference,journal_id,fingerprint)
      SELECT DISTINCT ON (branch_id,source_module,source_reference) id,branch_id,source_module,source_reference,id,'legacy-reconciliation-required'
      FROM journal_entries WHERE branch_id IS NOT NULL AND source_module IS NOT NULL AND source_reference IS NOT NULL AND status IN ('posted','reversed')
      ORDER BY branch_id,source_module,source_reference,created_at,id""")
    op.create_table('accounting_payment_adjustments',*base(),sa.Column('branch_id',UUID(as_uuid=True),sa.ForeignKey('branches.id'),nullable=False,index=True),sa.Column('invoice_id',UUID(as_uuid=True),sa.ForeignKey('billing_invoices.id'),nullable=False,index=True),sa.Column('payment_id',UUID(as_uuid=True),sa.ForeignKey('billing_payments.id')),sa.Column('kind',sa.String(30),nullable=False),sa.Column('amount',sa.Numeric(14,2),nullable=False),sa.Column('request_key',sa.String(100),nullable=False),sa.Column('fingerprint',sa.String(64),nullable=False),sa.Column('reason',sa.Text(),nullable=False),sa.Column('journal_id',UUID(as_uuid=True),sa.ForeignKey('journal_entries.id')),sa.UniqueConstraint('branch_id','request_key',name='uq_accounting_payment_adjustment_request'))
    op.create_table('fixed_assets',*base(),sa.Column('branch_id',UUID(as_uuid=True),sa.ForeignKey('branches.id'),nullable=False,index=True),sa.Column('asset_code',sa.String(80),nullable=False),sa.Column('name',sa.String(180),nullable=False),sa.Column('category',sa.String(100),nullable=False),sa.Column('department',sa.String(120)),sa.Column('cost',sa.Numeric(14,2),nullable=False),sa.Column('residual_value',sa.Numeric(14,2),nullable=False),sa.Column('useful_life_months',sa.Integer(),nullable=False),sa.Column('acquisition_date',sa.Date(),nullable=False),sa.Column('depreciation_start',sa.Date(),nullable=False),sa.Column('depreciation_method',sa.String(30),nullable=False),sa.Column('accumulated_depreciation',sa.Numeric(14,2),nullable=False),sa.Column('last_depreciation_month',sa.String(7)),sa.Column('acquisition_journal_id',UUID(as_uuid=True),sa.ForeignKey('journal_entries.id'),nullable=False),sa.Column('status',sa.String(20),nullable=False),sa.UniqueConstraint('branch_id','asset_code',name='uq_fixed_asset_code'))
    op.create_index('ix_accounting_gl_scope_date','journal_entries',['branch_id','journal_date','status'],if_not_exists=True)
    op.create_index('ix_accounting_gl_account','journal_entry_lines',['account_id','journal_entry_id'],if_not_exists=True)
    op.create_index('ix_accounting_audit_source','accounting_audit_logs',['branch_id','action','entity_id'],if_not_exists=True)
    op.execute("""CREATE FUNCTION accounting_header_immutable() RETURNS trigger AS $$
      BEGIN
        IF OLD.posting_applied_at IS NOT NULL THEN
          IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Posted accounting history is immutable'; END IF;
          IF (to_jsonb(NEW)-'status'-'updated_at'-'updated_by') IS DISTINCT FROM (to_jsonb(OLD)-'status'-'updated_at'-'updated_by')
             OR (NEW.status<>OLD.status AND NOT (OLD.status='posted' AND NEW.status='reversed' AND EXISTS(SELECT 1 FROM journal_entries r WHERE r.reversed_entry_id=OLD.id AND r.posting_applied_at IS NOT NULL))) THEN
             RAISE EXCEPTION 'Posted accounting history is immutable'; END IF;
        END IF;
        IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
      END; $$ LANGUAGE plpgsql""")
    op.execute("""CREATE FUNCTION accounting_period_post_guard() RETURNS trigger AS $$ BEGIN
      IF NEW.posting_applied_at IS NOT NULL AND NEW.status NOT IN ('posted','reversed') THEN RAISE EXCEPTION 'Applied journal must be posted or reversed'; END IF;
      IF NEW.status IN ('posted','reversed') AND NEW.posting_applied_at IS NULL THEN RAISE EXCEPTION 'Posted voucher requires a validated posting timestamp'; END IF;
      IF NEW.posting_applied_at IS NOT NULL AND (TG_OP='INSERT' OR OLD.posting_applied_at IS NULL) AND EXISTS(SELECT 1 FROM financial_periods p WHERE p.branch_id=NEW.branch_id AND NEW.journal_date BETWEEN p.start_date AND p.end_date AND p.status<>'open') THEN RAISE EXCEPTION 'Financial period is locked'; END IF;
      RETURN NEW; END; $$ LANGUAGE plpgsql""")
    op.execute('CREATE TRIGGER accounting_period_post_guard BEFORE INSERT OR UPDATE ON journal_entries FOR EACH ROW EXECUTE FUNCTION accounting_period_post_guard()')
    op.execute("""CREATE FUNCTION accounting_source_immutable() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'Financial configuration and audit history are append-only'; END; $$ LANGUAGE plpgsql""")
    for table in ['accounting_posting_keys','accounting_audit_logs','accounting_payment_adjustments']:
        op.execute(f'CREATE TRIGGER accounting_source_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION accounting_source_immutable()')
    op.execute("""CREATE FUNCTION accounting_policy_immutable() RETURNS trigger AS $$ BEGIN
      IF TG_OP='DELETE' OR OLD.approved_by IS NOT NULL OR (to_jsonb(NEW)-'approved_by'-'updated_by'-'updated_at') IS DISTINCT FROM (to_jsonb(OLD)-'approved_by'-'updated_by'-'updated_at') THEN RAISE EXCEPTION 'Accounting policy versions are immutable'; END IF;
      RETURN NEW; END; $$ LANGUAGE plpgsql""")
    op.execute('CREATE TRIGGER accounting_policy_immutable BEFORE UPDATE OR DELETE ON accounting_policies FOR EACH ROW EXECUTE FUNCTION accounting_policy_immutable()')
    op.execute("""CREATE FUNCTION accounting_account_code_guard() RETURNS trigger AS $$ BEGIN
      PERFORM id FROM branches WHERE id=NEW.branch_id FOR UPDATE;
      IF EXISTS(SELECT 1 FROM accounts WHERE branch_id IS NOT DISTINCT FROM NEW.branch_id AND account_code=NEW.account_code AND id<>NEW.id) THEN RAISE EXCEPTION 'Account code already exists in branch' USING ERRCODE='23505'; END IF;
      RETURN NEW; END; $$ LANGUAGE plpgsql""")
    op.execute('CREATE TRIGGER accounting_account_code_guard BEFORE INSERT OR UPDATE OF account_code,branch_id ON accounts FOR EACH ROW EXECUTE FUNCTION accounting_account_code_guard()')
    op.execute('CREATE TRIGGER accounting_header_lock BEFORE UPDATE OR DELETE ON journal_entries FOR EACH ROW EXECUTE FUNCTION accounting_header_immutable()')
    op.execute("""CREATE FUNCTION accounting_line_immutable() RETURNS trigger AS $$
      DECLARE identity uuid;
      BEGIN
        IF TG_OP='INSERT' THEN identity=NEW.journal_entry_id; ELSE identity=OLD.journal_entry_id; END IF;
        IF TG_OP<>'INSERT' AND EXISTS(SELECT 1 FROM journal_entries WHERE id=identity AND posting_applied_at IS NOT NULL) THEN RAISE EXCEPTION 'Posted accounting lines are immutable'; END IF;
        IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
      END; $$ LANGUAGE plpgsql""")
    op.execute('CREATE TRIGGER accounting_line_lock BEFORE UPDATE OR DELETE ON journal_entry_lines FOR EACH ROW EXECUTE FUNCTION accounting_line_immutable()')
    op.execute("""CREATE FUNCTION accounting_check_balance() RETURNS trigger AS $$
      DECLARE identity uuid; d numeric; c numeric; expected_d numeric; expected_c numeric; applied timestamp with time zone; n integer;
      BEGIN
        IF TG_TABLE_NAME='journal_entries' THEN identity=NEW.id; ELSIF TG_OP='DELETE' THEN identity=OLD.journal_entry_id; ELSE identity=NEW.journal_entry_id; END IF;
        SELECT total_debit,total_credit,posting_applied_at INTO expected_d,expected_c,applied FROM journal_entries WHERE id=identity;
        IF applied IS NOT NULL THEN
          SELECT COALESCE(sum(debit_amount),0),COALESCE(sum(credit_amount),0),count(*) INTO d,c,n FROM journal_entry_lines WHERE journal_entry_id=identity;
          IF n<2 OR d<=0 OR d<>c OR d<>expected_d OR c<>expected_c OR EXISTS(SELECT 1 FROM journal_entry_lines WHERE journal_entry_id=identity AND (debit_amount<0 OR credit_amount<0 OR (debit_amount>0)=(credit_amount>0))) THEN RAISE EXCEPTION 'Posted journal lines must balance'; END IF;
        END IF;
        RETURN NULL;
      END; $$ LANGUAGE plpgsql""")
    op.execute('CREATE CONSTRAINT TRIGGER accounting_balanced_header AFTER INSERT OR UPDATE ON journal_entries DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION accounting_check_balance()')
    op.execute('CREATE CONSTRAINT TRIGGER accounting_balanced_lines AFTER INSERT OR UPDATE OR DELETE ON journal_entry_lines DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION accounting_check_balance()')


def downgrade():
    op.drop_column('supplier_invoices','purchase_account_code')
    # Adjustment history remains intact until the explicitly requested schema downgrade.

    op.drop_column('supplier_invoices','pharmacy_purchase_id')
    op.drop_column('inventory_stock_transactions','cost_amount');op.drop_column('inventory_stock_transactions','unit_cost')
    op.execute('DROP TRIGGER accounting_account_code_guard ON accounts');op.execute('DROP FUNCTION accounting_account_code_guard()')
    op.execute('DROP TRIGGER accounting_policy_immutable ON accounting_policies');op.execute('DROP FUNCTION accounting_policy_immutable()')
    for table in ['accounting_posting_keys','accounting_audit_logs','accounting_payment_adjustments']:op.execute(f'DROP TRIGGER accounting_source_immutable ON {table}')
    op.execute('DROP FUNCTION accounting_source_immutable()')
    op.drop_table('accounting_payment_adjustments')
    op.execute('DROP TRIGGER accounting_period_post_guard ON journal_entries');op.execute('DROP FUNCTION accounting_period_post_guard()')
    for column in ['valuation_opening_journal_id','valuation_opening_value','inventory_value']:op.drop_column('pharmacy_medicines',column)
    for column in ['payment_provider','payment_method','paid_amount']:op.drop_column('pharmacy_sales',column)
    op.drop_column('pharmacy_sale_items','cost_amount')
    op.drop_column('billing_payments','advance_payment_id')
    op.drop_index('uq_bank_statement_key',table_name='bank_transactions')
    for column in ['matched_journal_id','statement_key','ledger_account_code']:op.drop_column('bank_transactions',column)
    op.drop_table('fixed_assets')
    op.drop_column('supplier_invoices','receiving_id')
    for column in ['cost_center','expense_account_code']:op.drop_column('expenses',column)
    for column in ['closed_at','opened_at','counter_name','cash_account_code']:op.drop_column('cash_closing',column)
    for trigger,table in [('accounting_balanced_lines','journal_entry_lines'),('accounting_balanced_header','journal_entries'),('accounting_line_lock','journal_entry_lines'),('accounting_header_lock','journal_entries')]:op.execute(f'DROP TRIGGER {trigger} ON {table}')
    for function in ['accounting_check_balance','accounting_line_immutable','accounting_header_immutable']:op.execute(f'DROP FUNCTION {function}()')
    op.drop_index('ix_accounting_audit_source',table_name='accounting_audit_logs')
    op.drop_index('ix_accounting_gl_account',table_name='journal_entry_lines');op.drop_index('ix_accounting_gl_scope_date',table_name='journal_entries')
    op.drop_table('accounting_posting_keys')
    for column in ['posting_applied_at','policy_snapshot','period_id','voucher_type']:op.drop_column('journal_entries',column)
    op.drop_table('financial_periods');op.drop_table('accounting_policies')
    for column in ['is_control','reporting_group','parent_id']:op.drop_column('accounts',column)
