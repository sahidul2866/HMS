"""add opd consultation detail fields

Revision ID: 20260320_0014
Revises: 20260320_0013
Create Date: 2026-03-26 01:30:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260320_0014"
down_revision = "20260320_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("opd_visits", sa.Column("history_of_present_illness", sa.Text(), nullable=True))
    op.add_column("opd_visits", sa.Column("past_history", sa.Text(), nullable=True))
    op.add_column("opd_visits", sa.Column("vital_signs", sa.Text(), nullable=True))
    op.add_column("opd_visits", sa.Column("examination_note", sa.Text(), nullable=True))
    op.add_column("opd_visits", sa.Column("provisional_diagnosis", sa.Text(), nullable=True))
    op.add_column("opd_visits", sa.Column("final_diagnosis", sa.Text(), nullable=True))
    op.add_column("opd_visits", sa.Column("follow_up_date", sa.Date(), nullable=True))
    op.add_column("opd_visits", sa.Column("follow_up_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("opd_visits", "follow_up_note")
    op.drop_column("opd_visits", "follow_up_date")
    op.drop_column("opd_visits", "final_diagnosis")
    op.drop_column("opd_visits", "provisional_diagnosis")
    op.drop_column("opd_visits", "examination_note")
    op.drop_column("opd_visits", "vital_signs")
    op.drop_column("opd_visits", "past_history")
    op.drop_column("opd_visits", "history_of_present_illness")
