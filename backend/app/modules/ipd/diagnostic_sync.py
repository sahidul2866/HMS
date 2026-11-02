"""Keep inpatient task state aligned with the department's verified result."""
from datetime import UTC,datetime
from sqlalchemy import select
from app.models.encounter import IPDOrder,IPDAdmission,IPDNursingTask,OPDVisitOrder


def sync_diagnostic(db,domain,kind,actor):
    opd_field=OPDVisitOrder.lab_order_id if kind=='lab' else OPDVisitOrder.radiology_order_id
    records=domain.results if kind=='lab' else domain.reports
    findings=(records[0].overall_interpretation if kind=='lab' else records[0].overall_findings) if records else None
    for order in db.scalars(select(OPDVisitOrder).where(opd_field==domain.id)):
        if order.status=='cancelled':continue
        order.status=domain.status;order.result_text=findings;order.sample_note=domain.note
        order.sample_collected_at=domain.collected_at if kind=='lab' else domain.performed_at
        order.completed_at=domain.completed_at;order.verified_at=domain.verified_at;order.updated_by=actor.id
    field=IPDOrder.lab_order_id if kind=='lab' else IPDOrder.radiology_order_id
    for order in db.scalars(select(IPDOrder).where(field==domain.id)):
        if order.status in {'cancelled','discontinued'}:continue
        order.status='cancelled' if domain.status=='cancelled' else 'completed' if domain.status=='verified' else 'active'
        if domain.status=='cancelled':
            order.cancelled_at=datetime.now(UTC);order.cancelled_by_user_id=actor.id
            for task in order.nursing_tasks:
                if task.status in {'pending','in_progress'}:task.status='cancelled';task.updated_by=actor.id
        order.updated_by=actor.id
        if domain.status!='verified':
            admission=db.get(IPDAdmission,order.admission_id)
            setattr(admission,kind+'_clearance_status','pending')
        if kind=='lab' and domain.status in {'collected','in_progress','completed','verified'}:
            for task in db.scalars(select(IPDNursingTask).where(IPDNursingTask.order_id==order.id,IPDNursingTask.task_type=='sample_collection',IPDNursingTask.status.in_(['pending','in_progress']))):
                task.status='completed';task.completed_at=datetime.now(UTC);task.completed_by_user_id=actor.id;task.updated_by=actor.id
