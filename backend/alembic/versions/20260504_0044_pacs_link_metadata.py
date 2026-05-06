"""add orthanc metadata fields to pacs links

Revision ID: 20260504_0044
Revises: 20260504_0043
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260504_0044"
down_revision = "20260504_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pacs_links", sa.Column("orthanc_study_id", sa.String(length=255), nullable=True))
    op.add_column("pacs_links", sa.Column("accession_number", sa.String(length=120), nullable=True))
    op.add_column("pacs_links", sa.Column("dicom_patient_id", sa.String(length=120), nullable=True))
    op.create_index("ix_pacs_links_orthanc_study_id", "pacs_links", ["orthanc_study_id"], unique=False)
    op.create_index("ix_pacs_links_accession_number", "pacs_links", ["accession_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pacs_links_accession_number", table_name="pacs_links")
    op.drop_index("ix_pacs_links_orthanc_study_id", table_name="pacs_links")
    op.drop_column("pacs_links", "dicom_patient_id")
    op.drop_column("pacs_links", "accession_number")
    op.drop_column("pacs_links", "orthanc_study_id")
