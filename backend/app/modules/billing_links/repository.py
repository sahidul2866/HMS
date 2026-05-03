from uuid import UUID

from sqlalchemy.orm import Session

from app.models.billing_links import BillingItemLink


class BillingLinksRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_link(self, link: BillingItemLink) -> BillingItemLink:
        self.db.add(link)
        self.db.flush()
        return link

    def get_links_for_invoice_item(self, invoice_item_id: UUID) -> list[BillingItemLink]:
        return list(
            self.db.query(BillingItemLink)
            .filter(BillingItemLink.invoice_item_id == invoice_item_id)
            .all()
        )
