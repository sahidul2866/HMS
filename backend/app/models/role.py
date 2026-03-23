from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class Role(Base, BaseModelMixin):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_doctor_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_referral_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")
    users = relationship("User", secondary="user_roles", back_populates="roles")
