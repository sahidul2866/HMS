from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import ForeignKey, Integer, JSON, Numeric, String, Text, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, BaseModelMixin


class PrescriptionRevision(Base, BaseModelMixin):
    __tablename__ = 'prescription_revisions'
    __table_args__ = (UniqueConstraint('visit_id','version',name='uq_prescription_visit_version'),)
    visit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('opd_visits.id'),index=True)
    version: Mapped[int] = mapped_column(Integer,nullable=False)
    status: Mapped[str] = mapped_column(String(20),nullable=False)
    doctor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True),ForeignKey('users.id'))
    reason: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[dict] = mapped_column(JSON,nullable=False)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConfigurationProfileVersion(Base, BaseModelMixin):
    __tablename__ = 'configuration_profile_versions'
    __table_args__ = (UniqueConstraint('profile_id','version',name='uq_configuration_profile_version'),)
    profile_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('configuration_profiles.id'),index=True)
    version: Mapped[int] = mapped_column(Integer,nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON,nullable=False)


class OPDExternalPayment(Base, BaseModelMixin):
    __tablename__ = 'opd_external_payments'
    __table_args__ = (UniqueConstraint('visit_id','request_key',name='uq_opd_external_payment_request'),)
    visit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('opd_visits.id'),index=True)
    kind: Mapped[str] = mapped_column(String(30),nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2),nullable=False)
    request_key: Mapped[str] = mapped_column(String(100),nullable=False)
    reason: Mapped[str] = mapped_column(Text,nullable=False)
    settlement_snapshot: Mapped[dict] = mapped_column(JSON,nullable=False)


class PrescriptionShortcut(Base, BaseModelMixin):
    __tablename__ = 'prescription_shortcuts'
    owner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('users.id'),index=True)
    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True),ForeignKey('branches.id'))
    kind: Mapped[str] = mapped_column(String(30),nullable=False)
    name: Mapped[str] = mapped_column(String(150),nullable=False)
    content: Mapped[dict] = mapped_column(JSON,nullable=False)


class PrescriptionEvent(Base, BaseModelMixin):
    __tablename__ = 'prescription_events'
    visit_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('opd_visits.id'),index=True)
    actor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),ForeignKey('users.id'))
    kind: Mapped[str] = mapped_column(String(40),nullable=False)
    detail: Mapped[dict] = mapped_column(JSON,nullable=False)
