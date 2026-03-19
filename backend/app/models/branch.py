from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class Branch(Base, BaseModelMixin):
    __tablename__ = "branches"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(255))

    departments = relationship("Department", back_populates="branch")
    users = relationship("User", back_populates="branch")
    patients = relationship("Patient", back_populates="branch")

