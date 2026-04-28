from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin, metadata

user_roles = Table(
    "user_roles",
    metadata,
    Column("user_id", PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", PGUUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    metadata,
    Column("role_id", PGUUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", PGUUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True),
)

user_permissions = Table(
    "user_permissions",
    metadata,
    Column("user_id", PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("permission_id", PGUUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True),
)


class User(Base, BaseModelMixin):
    __tablename__ = "users"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"))
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    opd_consultation_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    opd_follow_up_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    opd_follow_up_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    opd_prescription_header_name: Mapped[str | None] = mapped_column(String(180))
    opd_prescription_header_degrees: Mapped[str | None] = mapped_column(String(300))
    opd_prescription_header_specialty: Mapped[str | None] = mapped_column(String(220))
    opd_prescription_header_workplace: Mapped[str | None] = mapped_column(String(220))
    opd_prescription_header_chamber: Mapped[str | None] = mapped_column(String(220))
    opd_prescription_header_phone: Mapped[str | None] = mapped_column(String(80))
    opd_prescription_header_address: Mapped[str | None] = mapped_column(String(300))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    branch = relationship("Branch", back_populates="users")
    department = relationship("Department", back_populates="users")
    patient = relationship("Patient")
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    direct_permissions = relationship("Permission", secondary=user_permissions, back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    billed_invoices = relationship(
        "BillingInvoice",
        foreign_keys="BillingInvoice.billed_by_user_id",
        back_populates="billed_by",
    )
    voided_invoices = relationship(
        "BillingInvoice",
        foreign_keys="BillingInvoice.voided_by_user_id",
        back_populates="voided_by",
    )
