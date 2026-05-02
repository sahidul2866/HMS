"""add patient health assistant bot

Revision ID: 20260430_0037
Revises: 20260430_0036
Create Date: 2026-04-30 01:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260430_0037"
down_revision = "20260430_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_bot_conversations",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("current_intent", sa.String(length=80), nullable=True),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("intake", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_department", sa.String(length=120), nullable=True),
        sa.Column("recommended_doctor_type", sa.String(length=160), nullable=True),
        sa.Column("safety_level", sa.String(length=40), nullable=False),
        sa.Column("gemini_calls_today", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patient_bot_conversations_branch_id"), "patient_bot_conversations", ["branch_id"])
    op.create_index(op.f("ix_patient_bot_conversations_current_intent"), "patient_bot_conversations", ["current_intent"])
    op.create_index(op.f("ix_patient_bot_conversations_patient_id"), "patient_bot_conversations", ["patient_id"])
    op.create_index(op.f("ix_patient_bot_conversations_user_id"), "patient_bot_conversations", ["user_id"])

    op.create_table(
        "patient_bot_messages",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender", sa.String(length=20), nullable=False),
        sa.Column("message_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("gemini_used", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["patient_bot_conversations.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patient_bot_messages_conversation_id"), "patient_bot_messages", ["conversation_id"])
    op.create_index(op.f("ix_patient_bot_messages_patient_id"), "patient_bot_messages", ["patient_id"])

    for table_name, columns in {
        "patient_bot_intake_answers": [
            sa.Column("field_name", sa.String(length=80), nullable=False),
            sa.Column("answer", sa.Text(), nullable=False),
        ],
        "patient_bot_intents": [
            sa.Column("intent", sa.String(length=80), nullable=False),
            sa.Column("confidence", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=40), nullable=False),
        ],
        "patient_bot_recommendations": [
            sa.Column("intent", sa.String(length=80), nullable=False),
            sa.Column("department", sa.String(length=120), nullable=True),
            sa.Column("doctor_type", sa.String(length=160), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("safety_level", sa.String(length=40), nullable=False),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        ],
        "patient_bot_audit_logs": [
            sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("action", sa.String(length=120), nullable=False),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        ],
    }.items():
        base_columns = [
            sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
            *columns,
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(["conversation_id"], ["patient_bot_conversations.id"]),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.PrimaryKeyConstraint("id"),
        ]
        if table_name == "patient_bot_audit_logs":
            base_columns[0] = sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True)
            base_columns[1] = sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True)
            base_columns.insert(3, sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]))
        op.create_table(table_name, *base_columns)
        op.create_index(op.f(f"ix_{table_name}_conversation_id"), table_name, ["conversation_id"])
        op.create_index(op.f(f"ix_{table_name}_patient_id"), table_name, ["patient_id"])

    op.create_index(op.f("ix_patient_bot_intents_intent"), "patient_bot_intents", ["intent"])

    op.create_table(
        "symptom_department_rules",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symptom_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=False),
        sa.Column("doctor_type", sa.String(length=160), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("safety_level", sa.String(length=40), nullable=False),
        sa.Column("urgent_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_symptom_department_rules_branch_id"), "symptom_department_rules", ["branch_id"])

    op.create_table(
        "patient_bot_faqs",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("question", sa.String(length=255), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patient_bot_faqs_branch_id"), "patient_bot_faqs", ["branch_id"])

    op.create_table(
        "patient_bot_settings",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patient_bot_settings_branch_id"), "patient_bot_settings", ["branch_id"])
    op.create_index(op.f("ix_patient_bot_settings_key"), "patient_bot_settings", ["key"])

    op.create_table(
        "gemini_api_logs",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["patient_bot_conversations.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gemini_api_logs_branch_id"), "gemini_api_logs", ["branch_id"])
    op.create_index(op.f("ix_gemini_api_logs_conversation_id"), "gemini_api_logs", ["conversation_id"])
    op.create_index(op.f("ix_gemini_api_logs_patient_id"), "gemini_api_logs", ["patient_id"])


def downgrade() -> None:
    for table in [
        "gemini_api_logs",
        "patient_bot_settings",
        "patient_bot_faqs",
        "symptom_department_rules",
        "patient_bot_audit_logs",
        "patient_bot_recommendations",
        "patient_bot_intents",
        "patient_bot_intake_answers",
        "patient_bot_messages",
        "patient_bot_conversations",
    ]:
        op.drop_table(table)
