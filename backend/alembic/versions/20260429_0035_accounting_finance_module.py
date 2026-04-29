"""Create accounting finance module tables.

Revision ID: 20260429_0035
Revises: 20260429_0034
Create Date: 2026-04-29 15:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.models.base import Base
import app.models.accounting  # noqa: F401

revision = "20260429_0035"
down_revision = "20260429_0034"
branch_labels = None
depends_on = None

TABLES = [
    "account_groups",
    "accounts",
    "journal_entries",
    "journal_entry_lines",
    "payment_methods",
    "advance_payments",
    "discounts",
    "refunds",
    "insurance_claims",
    "corporate_bills",
    "supplier_invoices",
    "supplier_payments",
    "expense_categories",
    "expenses",
    "doctor_commissions",
    "payroll_accounting",
    "cash_closing",
    "bank_accounts",
    "bank_transactions",
    "bank_reconciliations",
    "accounting_audit_logs",
]


def upgrade():
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    for table_name in TABLES:
        if table_name not in existing:
            Base.metadata.tables[table_name].create(bind, checkfirst=True)


def downgrade():
    bind = op.get_bind()
    for table_name in reversed(TABLES):
        Base.metadata.tables[table_name].drop(bind, checkfirst=True)
