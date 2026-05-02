from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class PatientBotConversation(Base, BaseModelMixin):
    __tablename__ = "patient_bot_conversations"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180), default="Patient assistant chat", nullable=False)
    current_intent: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(40), default="collecting", nullable=False)
    intake: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    recommended_department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    recommended_doctor_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    safety_level: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    gemini_calls_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    messages = relationship("PatientBotMessage", back_populates="conversation", cascade="all, delete-orphan")


class PatientBotMessage(Base, BaseModelMixin):
    __tablename__ = "patient_bot_messages"

    conversation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient_bot_conversations.id"), nullable=False, index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(20), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    gemini_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    conversation = relationship("PatientBotConversation", back_populates="messages")


class PatientBotIntakeAnswer(Base, BaseModelMixin):
    __tablename__ = "patient_bot_intake_answers"

    conversation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient_bot_conversations.id"), nullable=False, index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)


class PatientBotIntent(Base, BaseModelMixin):
    __tablename__ = "patient_bot_intents"

    conversation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient_bot_conversations.id"), nullable=False, index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    intent: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="local", nullable=False)


class PatientBotRecommendation(Base, BaseModelMixin):
    __tablename__ = "patient_bot_recommendations"

    conversation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient_bot_conversations.id"), nullable=False, index=True)
    patient_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    intent: Mapped[str] = mapped_column(String(80), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    doctor_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_level: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class SymptomDepartmentRule(Base, BaseModelMixin):
    __tablename__ = "symptom_department_rules"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    symptom_keywords: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    doctor_type: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    safety_level: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    urgent_keywords: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)


class PatientBotFAQ(Base, BaseModelMixin):
    __tablename__ = "patient_bot_faqs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    question: Mapped[str] = mapped_column(String(255), nullable=False)
    keywords: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)


class PatientBotSetting(Base, BaseModelMixin):
    __tablename__ = "patient_bot_settings"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class GeminiAPILog(Base, BaseModelMixin):
    __tablename__ = "gemini_api_logs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=True, index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient_bot_conversations.id"), nullable=True, index=True)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="success", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PatientBotAuditLog(Base, BaseModelMixin):
    __tablename__ = "patient_bot_audit_logs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True, index=True)
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=True, index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patient_bot_conversations.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
