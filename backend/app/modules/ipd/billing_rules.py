from sqlalchemy import select
from app.models.encounter import IPDMedicationAdministration


def billable_order(db,order):
    if order.order_type not in {'medicine','lab','radiology','procedure'} or order.billing_status=='billed':return False
    if order.status not in {'cancelled','discontinued'}:return True
    # Stopping future treatment does not erase a medicine already administered.
    return order.order_type=='medicine' and db.scalar(select(IPDMedicationAdministration.id).where(IPDMedicationAdministration.order_id==order.id,IPDMedicationAdministration.status=='administered').limit(1)) is not None
