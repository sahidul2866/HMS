from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class StaffBotConversation(Base, BaseModelMixin):
    __tablename__ = "staff_bot_conversations"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False, default="Staff Assistant")
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    user = relationship("User")
    messages = relationship("StaffBotMessage", back_populates="conversation", cascade="all, delete-orphan")


class StaffBotMessage(Base, BaseModelMixin):
    __tablename__ = "staff_bot_messages"

    conversation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("staff_bot_conversations.id"), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(20), nullable=False)  # user | bot
    message: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    conversation = relationship("StaffBotConversation", back_populates="messages")


class StaffBotAuditLog(Base, BaseModelMixin):
    __tablename__ = "staff_bot_audit_logs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"), nullable=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("staff_bot_conversations.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    source_module: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    used_database: Mapped[bool] = mapped_column(default=False, nullable=False)
    used_gemini: Mapped[bool] = mapped_column(default=False, nullable=False)
    response_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    user = relationship("User")
    conversation = relationship("StaffBotConversation")

