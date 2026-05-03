from uuid import UUID

from sqlalchemy import ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class BillingItemLink(Base, BaseModelMixin):
    __tablename__ = "billing_item_links"

    invoice_item_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_invoice_items.id"), nullable=False
    )
    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    source_module: Mapped[str] = mapped_column(String(40), nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    invoice_item = relationship("BillingInvoiceItem", back_populates="item_links")
    branch = relationship("Branch")

    __table_args__ = (
        Index("ix_billing_item_links_invoice_item_id", "invoice_item_id"),
        Index("ix_billing_item_links_source", "source_entity_type", "source_entity_id"),
        Index("ix_billing_item_links_branch_module", "branch_id", "source_module"),
    )
