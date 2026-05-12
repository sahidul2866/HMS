"""Add hospital-grade blood bank module.

Revision ID: 20260511_0051
Revises: 20260511_0050
Create Date: 2026-05-11 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260511_0051"
down_revision = "20260511_0050"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _common_columns():
    return [
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade():
    if not _has_table("blood_bank_settings"):
        op.create_table(
            "blood_bank_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("setting_key", sa.String(120), nullable=False),
            sa.Column("setting_value", sa.JSON(), nullable=False),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("branch_id", "setting_key", name="uq_blood_bank_settings_branch_key"),
        )

    if not _has_table("blood_storage_locations"):
        op.create_table(
            "blood_storage_locations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("code", sa.String(60), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("location_type", sa.String(60), nullable=False, server_default="refrigerator"),
            sa.Column("parent_location_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("temperature_min", sa.Numeric(8, 2), nullable=True),
            sa.Column("temperature_max", sa.Numeric(8, 2), nullable=True),
            sa.Column("current_temperature", sa.Numeric(8, 2), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.ForeignKeyConstraint(["parent_location_id"], ["blood_storage_locations.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("branch_id", "code", name="uq_blood_storage_locations_branch_code"),
        )

    if not _has_table("blood_donors"):
        op.create_table(
            "blood_donors",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("donor_number", sa.String(60), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("date_of_birth", sa.Date(), nullable=True),
            sa.Column("age", sa.Integer(), nullable=True),
            sa.Column("gender", sa.String(30), nullable=True),
            sa.Column("blood_group", sa.String(10), nullable=True),
            sa.Column("phone", sa.String(30), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("last_donation_date", sa.Date(), nullable=True),
            sa.Column("eligibility_status", sa.String(40), nullable=False, server_default="unknown"),
            sa.Column("medical_screening_status", sa.String(40), nullable=False, server_default="pending"),
            sa.Column("remarks", sa.Text(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("donor_number"),
        )

    if not _has_table("blood_donor_screenings"):
        op.create_table(
            "blood_donor_screenings",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("donor_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("weight", sa.Numeric(8, 2), nullable=True),
            sa.Column("hemoglobin_level", sa.Numeric(8, 2), nullable=True),
            sa.Column("blood_pressure", sa.String(40), nullable=True),
            sa.Column("temperature", sa.Numeric(8, 2), nullable=True),
            sa.Column("pulse", sa.Integer(), nullable=True),
            sa.Column("medical_history", sa.JSON(), nullable=True),
            sa.Column("recent_illness", sa.Text(), nullable=True),
            sa.Column("medication_history", sa.Text(), nullable=True),
            sa.Column("travel_history", sa.Text(), nullable=True),
            sa.Column("previous_donation_date", sa.Date(), nullable=True),
            sa.Column("eligibility_result", sa.String(40), nullable=False),
            sa.Column("deferral_reason", sa.Text(), nullable=True),
            sa.Column("next_eligible_date", sa.Date(), nullable=True),
            sa.Column("screening_staff_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("screened_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("override_authorized_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["donor_id"], ["blood_donors.id"]),
            sa.ForeignKeyConstraint(["screening_staff_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["override_authorized_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("blood_collections"):
        op.create_table(
            "blood_collections",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("donor_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("screening_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("collection_number", sa.String(60), nullable=False),
            sa.Column("unit_number", sa.String(80), nullable=False),
            sa.Column("blood_group", sa.String(10), nullable=False),
            sa.Column("collection_volume_ml", sa.Integer(), nullable=True),
            sa.Column("bag_type", sa.String(80), nullable=True),
            sa.Column("anticoagulant_type", sa.String(80), nullable=True),
            sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("collection_staff_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("collection_location", sa.String(160), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["donor_id"], ["blood_donors.id"]),
            sa.ForeignKeyConstraint(["screening_id"], ["blood_donor_screenings.id"]),
            sa.ForeignKeyConstraint(["collection_staff_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("collection_number"),
            sa.UniqueConstraint("unit_number"),
        )

    if not _has_table("blood_units"):
        op.create_table(
            "blood_units",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("donor_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("source_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("unit_number", sa.String(80), nullable=False),
            sa.Column("blood_group", sa.String(10), nullable=False),
            sa.Column("rh_factor", sa.String(10), nullable=True),
            sa.Column("component_type", sa.String(80), nullable=False),
            sa.Column("collection_date", sa.Date(), nullable=True),
            sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expiry_date", sa.Date(), nullable=True),
            sa.Column("volume_ml", sa.Integer(), nullable=True),
            sa.Column("batch_number", sa.String(80), nullable=True),
            sa.Column("storage_location_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="testing_pending"),
            sa.Column("testing_status", sa.String(40), nullable=False, server_default="pending"),
            sa.Column("current_request_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("current_patient_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("prepared_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["collection_id"], ["blood_collections.id"]),
            sa.ForeignKeyConstraint(["donor_id"], ["blood_donors.id"]),
            sa.ForeignKeyConstraint(["source_unit_id"], ["blood_units.id"]),
            sa.ForeignKeyConstraint(["storage_location_id"], ["blood_storage_locations.id"]),
            sa.ForeignKeyConstraint(["current_patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["prepared_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("unit_number"),
        )

    if not _has_table("blood_test_results"):
        op.create_table(
            "blood_test_results",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("test_name", sa.String(120), nullable=False),
            sa.Column("test_code", sa.String(60), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
            sa.Column("result", sa.String(80), nullable=True),
            sa.Column("result_value", sa.String(160), nullable=True),
            sa.Column("lab_order_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("performed_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("performed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["unit_id"], ["blood_units.id"]),
            sa.ForeignKeyConstraint(["lab_order_id"], ["lab_orders.id"]),
            sa.ForeignKeyConstraint(["performed_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["verified_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("unit_id", "test_name", name="uq_blood_test_results_unit_test"),
        )

    if not _has_table("blood_requests"):
        op.create_table(
            "blood_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("request_number", sa.String(60), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("admission_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("er_visit_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("ot_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("requesting_doctor_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("department_name", sa.String(120), nullable=True),
            sa.Column("blood_group", sa.String(10), nullable=False),
            sa.Column("component_type", sa.String(80), nullable=False),
            sa.Column("quantity_units", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("urgency", sa.String(40), nullable=False, server_default="routine"),
            sa.Column("indication", sa.Text(), nullable=True),
            sa.Column("required_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("diagnosis", sa.Text(), nullable=True),
            sa.Column("status", sa.String(40), nullable=False, server_default="requested"),
            sa.Column("billing_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("payment_status", sa.String(40), nullable=True),
            sa.Column("emergency_override_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("override_reason", sa.Text(), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["admission_id"], ["ipd_admissions.id"]),
            sa.ForeignKeyConstraint(["er_visit_id"], ["er_visits.id"]),
            sa.ForeignKeyConstraint(["ot_booking_id"], ["ot_bookings.id"]),
            sa.ForeignKeyConstraint(["requesting_doctor_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
            sa.ForeignKeyConstraint(["billing_invoice_id"], ["billing_invoices.id"]),
            sa.ForeignKeyConstraint(["emergency_override_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("request_number"),
        )
        op.create_foreign_key("fk_blood_units_current_request_id_blood_requests", "blood_units", "blood_requests", ["current_request_id"], ["id"])

    if not _has_table("blood_crossmatches"):
        op.create_table(
            "blood_crossmatches",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("patient_blood_group", sa.String(10), nullable=False),
            sa.Column("unit_blood_group", sa.String(10), nullable=False),
            sa.Column("component_type", sa.String(80), nullable=False),
            sa.Column("result", sa.String(40), nullable=False),
            sa.Column("compatibility_status", sa.String(40), nullable=False),
            sa.Column("tested_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("emergency_override_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("override_reason", sa.Text(), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["request_id"], ["blood_requests.id"]),
            sa.ForeignKeyConstraint(["unit_id"], ["blood_units.id"]),
            sa.ForeignKeyConstraint(["tested_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["verified_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["emergency_override_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("request_id", "unit_id", name="uq_blood_crossmatches_request_unit"),
        )

    if not _has_table("blood_issues"):
        op.create_table(
            "blood_issues",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("issue_number", sa.String(60), nullable=False),
            sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("crossmatch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("issued_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("received_by", sa.String(160), nullable=True),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("destination", sa.String(160), nullable=True),
            sa.Column("transport_condition", sa.String(160), nullable=True),
            sa.Column("billing_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["request_id"], ["blood_requests.id"]),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["unit_id"], ["blood_units.id"]),
            sa.ForeignKeyConstraint(["crossmatch_id"], ["blood_crossmatches.id"]),
            sa.ForeignKeyConstraint(["issued_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["billing_invoice_id"], ["billing_invoices.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("issue_number"),
            sa.UniqueConstraint("unit_id", name="uq_blood_issues_unit_id"),
        )

    if not _has_table("blood_transfusions"):
        op.create_table(
            "blood_transfusions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="started"),
            sa.Column("started_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("vitals", sa.JSON(), nullable=True),
            sa.Column("reaction_observed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("reaction_details", sa.Text(), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
            *_common_columns(),
            sa.ForeignKeyConstraint(["issue_id"], ["blood_issues.id"]),
            sa.ForeignKeyConstraint(["unit_id"], ["blood_units.id"]),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["started_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["completed_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    for table_name, extra_cols in {
        "blood_returns": [
            sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("returned_by", sa.String(160), nullable=True),
            sa.Column("returned_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("condition_on_return", sa.String(160), nullable=True),
            sa.Column("minutes_outside_bank", sa.Integer(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("decision", sa.String(40), nullable=False),
            sa.Column("checked_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("remarks", sa.Text(), nullable=True),
        ],
        "blood_discards": [
            sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("reason", sa.String(120), nullable=False),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("discarded_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        ],
    }.items():
        if not _has_table(table_name):
            op.create_table(
                table_name,
                sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
                *extra_cols,
                *_common_columns(),
                sa.ForeignKeyConstraint(["unit_id"], ["blood_units.id"]),
                sa.PrimaryKeyConstraint("id"),
            )


def downgrade():
    for table_name in (
        "blood_discards",
        "blood_returns",
        "blood_transfusions",
        "blood_issues",
        "blood_crossmatches",
        "blood_test_results",
        "blood_requests",
        "blood_units",
        "blood_collections",
        "blood_donor_screenings",
        "blood_donors",
        "blood_storage_locations",
        "blood_bank_settings",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)

