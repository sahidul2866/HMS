"""Add vehicle transport and ambulance module."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260706_0061"
down_revision = "20260621_0060"
branch_labels = None
depends_on = None


def base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "transport_drivers",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("driver_name", sa.String(160), nullable=False),
        sa.Column("contact_number", sa.String(60), nullable=True),
        sa.Column("license_number", sa.String(100), nullable=False),
        sa.Column("license_expiry_date", sa.Date(), nullable=True),
        sa.Column("assigned_vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shift", sa.String(80), nullable=True),
        sa.Column("availability_status", sa.String(40), nullable=False),
        sa.Column("emergency_contact", sa.String(120), nullable=True),
        sa.Column("qr_code", sa.String(160), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("license_number"),
        sa.UniqueConstraint("qr_code"),
    )
    op.create_index("ix_transport_drivers_driver_name", "transport_drivers", ["driver_name"])
    op.create_index("ix_transport_drivers_availability_status", "transport_drivers", ["availability_status"])

    op.create_table(
        "transport_vehicles",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_number", sa.String(80), nullable=False),
        sa.Column("registration_number", sa.String(100), nullable=True),
        sa.Column("vehicle_type", sa.String(80), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("equipment_available", sa.JSON(), nullable=True),
        sa.Column("assigned_driver_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("insurance_details", sa.Text(), nullable=True),
        sa.Column("insurance_expiry", sa.Date(), nullable=True),
        sa.Column("fitness_expiry", sa.Date(), nullable=True),
        sa.Column("registration_expiry", sa.Date(), nullable=True),
        sa.Column("fuel_type", sa.String(40), nullable=True),
        sa.Column("current_status", sa.String(40), nullable=False),
        sa.Column("current_latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("current_longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("location_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("readiness_status", sa.String(40), nullable=False),
        sa.Column("readiness_alerts", sa.JSON(), nullable=True),
        sa.Column("qr_code", sa.String(160), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["assigned_driver_id"], ["transport_drivers.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_number"),
        sa.UniqueConstraint("vehicle_number"),
        sa.UniqueConstraint("qr_code"),
    )
    op.create_index("ix_transport_vehicles_vehicle_number", "transport_vehicles", ["vehicle_number"])
    op.create_index("ix_transport_vehicles_vehicle_type", "transport_vehicles", ["vehicle_type"])
    op.create_index("ix_transport_vehicles_current_status", "transport_vehicles", ["current_status"])
    op.create_foreign_key("fk_transport_drivers_assigned_vehicle_id_transport_vehicles", "transport_drivers", "transport_vehicles", ["assigned_vehicle_id"], ["id"])

    op.create_table(
        "transport_requests",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_number", sa.String(80), nullable=False),
        sa.Column("request_type", sa.String(80), nullable=False),
        sa.Column("trip_type", sa.String(80), nullable=True),
        sa.Column("source_department", sa.String(100), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("staff_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("unknown_patient_name", sa.String(160), nullable=True),
        sa.Column("pickup_location", sa.String(255), nullable=False),
        sa.Column("dropoff_location", sa.String(255), nullable=False),
        sa.Column("required_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("urgency", sa.String(40), nullable=False),
        sa.Column("priority", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("required_vehicle_type", sa.String(80), nullable=True),
        sa.Column("required_equipment", sa.JSON(), nullable=True),
        sa.Column("attendant_required", sa.Boolean(), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transfer_reason", sa.Text(), nullable=True),
        sa.Column("patient_condition", sa.Text(), nullable=True),
        sa.Column("required_support", sa.Text(), nullable=True),
        sa.Column("transfer_notes", sa.Text(), nullable=True),
        sa.Column("receiving_facility", sa.String(180), nullable=True),
        sa.Column("responsible_doctor", sa.String(160), nullable=True),
        sa.Column("status", sa.String(60), nullable=False),
        sa.Column("assigned_vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_driver_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("billing_required", sa.Boolean(), nullable=False),
        sa.Column("billing_status", sa.String(40), nullable=False),
        sa.Column("billing_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("override_used", sa.Boolean(), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["assigned_driver_id"], ["transport_drivers.id"]),
        sa.ForeignKeyConstraint(["assigned_vehicle_id"], ["transport_vehicles.id"]),
        sa.ForeignKeyConstraint(["billing_invoice_id"], ["billing_invoices.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["staff_employee_id"], ["hr_employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_number"),
    )
    for column in ("request_number", "request_type", "trip_type", "source_department", "patient_id", "required_at", "urgency", "priority", "status"):
        op.create_index(f"ix_transport_requests_{column}", "transport_requests", [column])

    op.create_table(
        "transport_trips",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trip_number", sa.String(80), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("staff_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pickup_location", sa.String(255), nullable=False),
        sa.Column("dropoff_location", sa.String(255), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("distance_km", sa.Numeric(10, 2), nullable=False),
        sa.Column("waiting_minutes", sa.Integer(), nullable=False),
        sa.Column("trip_type", sa.String(80), nullable=True),
        sa.Column("priority", sa.String(40), nullable=False),
        sa.Column("status", sa.String(60), nullable=False),
        sa.Column("location_updates", sa.JSON(), nullable=True),
        sa.Column("charges", sa.JSON(), nullable=True),
        sa.Column("billing_status", sa.String(40), nullable=False),
        sa.Column("billing_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("qr_code", sa.String(160), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["billing_invoice_id"], ["billing_invoices.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["transport_drivers.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["transport_requests.id"]),
        sa.ForeignKeyConstraint(["staff_employee_id"], ["hr_employees.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["transport_vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_number"),
        sa.UniqueConstraint("qr_code"),
    )
    for column in ("request_id", "trip_number", "vehicle_id", "driver_id", "patient_id", "scheduled_at", "trip_type", "status"):
        op.create_index(f"ix_transport_trips_{column}", "transport_trips", [column])

    op.create_table(
        "transport_schedules",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("schedule_type", sa.String(60), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recurrence_rule", sa.String(160), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("purpose", sa.String(180), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["transport_drivers.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["transport_vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transport_schedules_start_at", "transport_schedules", ["start_at"])
    op.create_index("ix_transport_schedules_end_at", "transport_schedules", ["end_at"])

    op.create_table(
        "transport_maintenance",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("maintenance_type", sa.String(80), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("odometer_reading", sa.Numeric(12, 2), nullable=True),
        sa.Column("workshop_vendor", sa.String(180), nullable=True),
        sa.Column("cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("next_service_date", sa.Date(), nullable=True),
        sa.Column("parts_changed", sa.Text(), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["transport_vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transport_maintenance_vehicle_id", "transport_maintenance", ["vehicle_id"])
    op.create_index("ix_transport_maintenance_service_date", "transport_maintenance", ["service_date"])
    op.create_index("ix_transport_maintenance_next_service_date", "transport_maintenance", ["next_service_date"])

    op.create_table(
        "transport_fuel_logs",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fuel_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("fuel_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("odometer_reading", sa.Numeric(12, 2), nullable=True),
        sa.Column("filled_by", sa.String(160), nullable=True),
        sa.Column("receipt_attachment", sa.String(255), nullable=True),
        sa.Column("expense_category", sa.String(60), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["transport_vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transport_fuel_logs_vehicle_id", "transport_fuel_logs", ["vehicle_id"])
    op.create_index("ix_transport_fuel_logs_fuel_date", "transport_fuel_logs", ["fuel_date"])

    op.create_table(
        "transport_settings",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("setting_key", sa.String(120), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        *base_columns(),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("setting_key"),
    )


def downgrade() -> None:
    op.drop_table("transport_settings")
    op.drop_table("transport_fuel_logs")
    op.drop_table("transport_maintenance")
    op.drop_table("transport_schedules")
    op.drop_table("transport_trips")
    op.drop_table("transport_requests")
    op.drop_constraint("fk_transport_drivers_assigned_vehicle_id_transport_vehicles", "transport_drivers", type_="foreignkey")
    op.drop_table("transport_vehicles")
    op.drop_table("transport_drivers")
