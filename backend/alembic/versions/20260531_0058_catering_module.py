"""Add catering and dietary service module."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260531_0058"
down_revision = "20260531_0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catering_diet_types",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_npo", sa.Boolean(), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("default_restrictions", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "catering_meal_schedules",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meal_type", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("serving_time", sa.Time(), nullable=False),
        sa.Column("cutoff_minutes", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "catering_settings",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("setting_key", sa.String(length=120), nullable=False),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("setting_key"),
    )
    op.create_table(
        "catering_meal_plans",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("diet_type_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("meal_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ingredients", sa.Text(), nullable=True),
        sa.Column("allergens", sa.Text(), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("protein_grams", sa.Numeric(8, 2), nullable=True),
        sa.Column("billable_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("inventory_quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["diet_type_id"], ["catering_diet_types.id"]),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "catering_diet_orders",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ipd_admission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("er_visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("diet_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meal_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admission_number", sa.String(length=80), nullable=True),
        sa.Column("ward_name", sa.String(length=120), nullable=True),
        sa.Column("bed_number", sa.String(length=80), nullable=True),
        sa.Column("restrictions", sa.Text(), nullable=True),
        sa.Column("allergies", sa.Text(), nullable=True),
        sa.Column("special_instructions", sa.Text(), nullable=True),
        sa.Column("nutrition_notes", sa.Text(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("ordered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["diet_type_id"], ["catering_diet_types.id"]),
        sa.ForeignKeyConstraint(["er_visit_id"], ["er_visits.id"]),
        sa.ForeignKeyConstraint(["ipd_admission_id"], ["ipd_admissions.id"]),
        sa.ForeignKeyConstraint(["meal_plan_id"], ["catering_meal_plans.id"]),
        sa.ForeignKeyConstraint(["ordered_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_catering_diet_orders_patient_id", "catering_diet_orders", ["patient_id"])
    op.create_index("ix_catering_diet_orders_ward_name", "catering_diet_orders", ["ward_name"])
    op.create_index("ix_catering_diet_orders_bed_number", "catering_diet_orders", ["bed_number"])
    op.create_table(
        "catering_meal_tasks",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("diet_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meal_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meal_number", sa.String(length=80), nullable=False),
        sa.Column("meal_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=50), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ward_name", sa.String(length=120), nullable=True),
        sa.Column("bed_number", sa.String(length=80), nullable=True),
        sa.Column("diet_type_name", sa.String(length=140), nullable=False),
        sa.Column("restrictions", sa.Text(), nullable=True),
        sa.Column("allergies", sa.Text(), nullable=True),
        sa.Column("special_instructions", sa.Text(), nullable=True),
        sa.Column("preparation_status", sa.String(length=40), nullable=False),
        sa.Column("delivery_status", sa.String(length=40), nullable=False),
        sa.Column("safety_status", sa.String(length=40), nullable=False),
        sa.Column("safety_warnings", sa.JSON(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("prepared_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_by", sa.String(length=150), nullable=True),
        sa.Column("patient_response", sa.String(length=40), nullable=True),
        sa.Column("refusal_reason", sa.Text(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("billable_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("billing_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("inventory_status", sa.String(length=40), nullable=True),
        sa.Column("ticket_code", sa.String(length=120), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["billing_invoice_id"], ["billing_invoices.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["delivered_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["diet_order_id"], ["catering_diet_orders.id"]),
        sa.ForeignKeyConstraint(["meal_plan_id"], ["catering_meal_plans.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["prepared_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meal_number"),
        sa.UniqueConstraint("ticket_code"),
    )
    op.create_index("ix_catering_meal_tasks_patient_id", "catering_meal_tasks", ["patient_id"])
    op.create_index("ix_catering_meal_tasks_meal_date", "catering_meal_tasks", ["meal_date"])
    op.create_index("ix_catering_meal_tasks_ward_name", "catering_meal_tasks", ["ward_name"])
    op.create_index("ix_catering_meal_tasks_bed_number", "catering_meal_tasks", ["bed_number"])
    op.create_table(
        "catering_staff_meal_orders",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("staff_name", sa.String(length=160), nullable=False),
        sa.Column("staff_code", sa.String(length=80), nullable=True),
        sa.Column("meal_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=50), nullable=False),
        sa.Column("eligibility_type", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("token_code", sa.String(length=120), nullable=True),
        sa.Column("payroll_deductible", sa.Boolean(), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_code"),
    )
    op.create_table(
        "catering_inventory_usage",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meal_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_name", sa.String(length=160), nullable=False),
        sa.Column("quantity_used", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("stock_status", sa.String(length=40), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"]),
        sa.ForeignKeyConstraint(["meal_task_id"], ["catering_meal_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("catering_inventory_usage")
    op.drop_table("catering_staff_meal_orders")
    op.drop_index("ix_catering_meal_tasks_bed_number", table_name="catering_meal_tasks")
    op.drop_index("ix_catering_meal_tasks_ward_name", table_name="catering_meal_tasks")
    op.drop_index("ix_catering_meal_tasks_meal_date", table_name="catering_meal_tasks")
    op.drop_index("ix_catering_meal_tasks_patient_id", table_name="catering_meal_tasks")
    op.drop_table("catering_meal_tasks")
    op.drop_index("ix_catering_diet_orders_bed_number", table_name="catering_diet_orders")
    op.drop_index("ix_catering_diet_orders_ward_name", table_name="catering_diet_orders")
    op.drop_index("ix_catering_diet_orders_patient_id", table_name="catering_diet_orders")
    op.drop_table("catering_diet_orders")
    op.drop_table("catering_meal_plans")
    op.drop_table("catering_settings")
    op.drop_table("catering_meal_schedules")
    op.drop_table("catering_diet_types")
