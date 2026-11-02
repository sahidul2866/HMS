"""One charge per Dhaka calendar day, at the highest occupied bed rate."""
from datetime import UTC,datetime,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from uuid import NAMESPACE_DNS,uuid5
from sqlalchemy import select
from app.models.encounter import IPDBedStay
from app.models.billing import BillingInvoice,BillingItemConfig

HOSPITAL_TZ=ZoneInfo('Asia/Dhaka')

def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def daily_charges(db,admission):
    end=aware(admission.discharged_at or datetime.now(UTC))
    stays=list(db.scalars(select(IPDBedStay).where(IPDBedStay.admission_id==admission.id).order_by(IPDBedStay.started_at)))
    if not stays:
        stays=[IPDBedStay(admission_id=admission.id,bed_id=admission.bed_id,ward_name=admission.ward_name,bed_number=admission.bed_number,daily_rate=admission.daily_charge,started_at=admission.admitted_at,ended_at=admission.discharged_at,estimated=True)]
    days={}
    for stay in stays:
        start=aware(stay.started_at);stop=min(aware(stay.ended_at) if stay.ended_at else end,end)
        if stop<start:continue
        day=start.astimezone(HOSPITAL_TZ).date()
        last=(stop-timedelta(microseconds=1) if stay.ended_at and stop>start else stop).astimezone(HOSPITAL_TZ).date()
        while day<=last:
            if day not in days or stay.daily_rate>days[day]['rate']:
                days[day]={'date':day,'rate':Decimal(stay.daily_rate),'bed_id':stay.bed_id,'ward_name':stay.ward_name,'bed_number':stay.bed_number,'estimated':stay.estimated}
            day+=timedelta(days=1)
    return [days[day] for day in sorted(days)]


def unbilled_charges(db,admission):
    days=daily_charges(db,admission);billed={};legacy=[]
    invoices=list(db.scalars(select(BillingInvoice).where(BillingInvoice.source_ipd_admission_id==admission.id,BillingInvoice.is_active.is_(True),BillingInvoice.status=='posted')))
    for invoice in invoices:
        for item in invoice.items:
            if item.source_module=='ipd_bed_charge' or (item.source_module=='ipd' and 'bed charge' in (item.source_label or '').lower()):
                if item.bed_charge_date:billed[item.bed_charge_date]=billed.get(item.bed_charge_date,Decimal(0))+item.quantity*item.unit_price
                else:legacy.append(item)
    # Old bed-day rows have no date. Allocate their original daily rates chronologically, without inventing rate history.
    legacy_index=0
    for item in legacy:
        for _ in range(int(item.quantity)):
            if legacy_index>=len(days):break
            day=days[legacy_index]['date'];billed[day]=billed.get(day,Decimal(0))+item.unit_price;legacy_index+=1
    return [{**day,'rate':day['rate']-billed.get(day['date'],Decimal(0))} for day in days if day['rate']>billed.get(day['date'],Decimal(0))]


def tariff(db,admission,day,actor):
    source_id=uuid5(NAMESPACE_DNS,f"ipd-bed-tariff:{admission.branch_id}:{day['bed_id']}:{day['ward_name']}:{day['bed_number']}:{day['rate']}")
    from sqlalchemy import text
    db.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'),{'key':'ipd-tariff:'+str(source_id)})
    config=db.scalar(select(BillingItemConfig).where(BillingItemConfig.source_module=='ipd',BillingItemConfig.source_entity_id==source_id))
    if not config:
        config=BillingItemConfig(branch_id=admission.branch_id,source_module='ipd',source_entity_id=source_id,service_code='BED-RATE-'+str(source_id)[:12],service_name=f"IPD Bed {day['ward_name']} / {day['bed_number']} @ {day['rate']}",unit_price=day['rate'],doctor_share_percentage=0,billing_instruction='Highest occupied daily rate · Dhaka calendar day',created_by=actor.id,updated_by=actor.id)
        db.add(config);db.flush()
    return config
