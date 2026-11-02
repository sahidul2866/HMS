"""Create synthetic local accounts and stock for password-login browser acceptance."""
import json, os, secrets, sys
from datetime import UTC, datetime, timedelta, date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.engine import make_url
import app.main
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.patient import Patient
from app.models.encounter import DoctorOPDSchedule, IPDBed
from app.models.pharmacy import PharmacyDispense
from app.models.inventory import InventoryItem, InventoryStore, InventoryStoreItem, StockBatch, InventoryStockTransaction
parsed=make_url(get_settings().database_url)
assert parsed.host in {'localhost','127.0.0.1'} and parsed.database in {'hms_dev','hms_erp_test'}
output=Path('/tmp/hms-browser-role-fixtures.json');db=SessionLocal()
if len(sys.argv)>2 and sys.argv[1]=='--verify':
 data=json.loads(output.read_text());state=json.loads(Path(sys.argv[2]).read_text())
 batch=db.get(StockBatch,UUID(data['batch_id']));balance=db.scalar(select(InventoryStoreItem).where(InventoryStoreItem.item_id==batch.item_id,InventoryStoreItem.store_id==batch.store_id));item=db.get(InventoryItem,batch.item_id)
 assert batch.quantity==balance.quantity_on_hand==item.stock_quantity==17
 assert batch.total_cost==item.stock_value==34
 movements=list(db.scalars(select(InventoryStockTransaction).where(InventoryStockTransaction.batch_id==batch.id,InventoryStockTransaction.reference_type=='pharmacy_stock_review')))
 assert len(movements)==1 and movements[0].quantity_change==-1
 returned=db.get(PharmacyDispense,UUID(state['dispense']['id']));assert returned.returned_quantity==2 and len(returned.return_history)==2
 assert any(e.get('disposal_status')=='approved' for e in returned.return_history)
 from app.models.billing import BillingInvoice
 invoice=db.get(BillingInvoice,returned.billing_invoice_id);assert invoice.refunded_amount==20 and invoice.paid_amount==10
 from app.models.encounter import IPDAdmission
 assert db.get(IPDAdmission,UUID(state['admission']['id'])).status=='discharged'
 print('Persisted batch/store/item quantities and costs, single ledger correction, disposal, refund and discharge verified');sys.exit(0)
if len(sys.argv)>1:
 data=json.loads(output.read_text());patient=db.get(Patient,UUID(sys.argv[1]));assert patient and patient.first_name=='RoleBrowser'
 u=db.get(User,UUID(data['roles']['Patient']['id']));u.patient_id=patient.id;db.commit();print('Synthetic patient login linked');sys.exit(0)
suffix=uuid4().hex[:9];reception=db.scalar(select(User).where(User.username=='reception_isha'));branch=reception.branch_id
roles={};mapping={'Reception':'RECEPTIONIST','Doctor':'DOCTOR','Cashier':'BILLING_STAFF','Pharmacist':'PHARMACIST','Nurse':'NURSE','Patient':'PATIENT'}
for label,code in mapping.items():
 role=db.scalar(select(Role).where(Role.code==code));assert role,code
 password=secrets.token_urlsafe(20)+'1!';username='browser_'+label.lower()+'_'+suffix
 u=User(branch_id=branch,username=username,email=username+'@example.test',full_name='Browser '+label+' '+suffix,hashed_password=get_password_hash(password),roles=[role],opd_consultation_fee=Decimal('500') if label=='Doctor' else 0)
 db.add(u);db.flush();roles[label]={'id':str(u.id),'username':username,'password':password}
password=secrets.token_urlsafe(20)+'1!';username='browser_supervisor_'+suffix
u=User(branch_id=branch,username=username,email=username+'@example.test',full_name='Browser Supervisor '+suffix,hashed_password=get_password_hash(password),direct_permissions=list(db.scalars(select(Permission).where(Permission.code.in_(['billing.view','billing.payment.collect','billing.service.manage','pharmacy.view','pharmacy.stock.approve'])))))
db.add(u);db.flush();roles['Supervisor']={'id':str(u.id),'username':username,'password':password}
day=datetime.now(UTC).date()+timedelta(days=1)
db.add(DoctorOPDSchedule(branch_id=branch,doctor_user_id=UUID(roles['Doctor']['id']),weekday=day.weekday(),start_time='09:00',end_time='12:00',slot_duration_minutes=15,buffer_minutes=0))
store=InventoryStore(created_by=reception.id,updated_by=reception.id,branch_id=branch,code='BR-'+suffix,name='Browser pharmacy '+suffix,store_type='pharmacy')
item=InventoryItem(created_by=reception.id,updated_by=reception.id,branch_id=branch,name='Browser Medicine '+suffix,item_type='medicine',stock_quantity=20,stock_value=40)
db.add_all([store,item]);db.flush();batch=StockBatch(created_by=reception.id,updated_by=reception.id,item_id=item.id,store_id=store.id,batch_no='BR-'+suffix,quantity=20,unit_cost=2,total_cost=40,expiry_date=date.today()+timedelta(days=90));balance=InventoryStoreItem(created_by=reception.id,updated_by=reception.id,item_id=item.id,store_id=store.id,quantity_on_hand=20,reserved_quantity=0);db.add_all([batch,balance]);db.flush()
legacy=PharmacyDispense(branch_id=branch,medicine_name=item.name+' historical',quantity=2,returned_quantity=1,unit_price=10,total_price=20,status='partially_returned',dispensed_by_user_id=UUID(roles['Pharmacist']['id']))
db.add(legacy);db.flush();issue=InventoryStockTransaction(created_by=reception.id,updated_by=reception.id,item_id=item.id,store_id=store.id,batch_id=batch.id,transaction_type='dispense_out',reference_type='pharmacy_dispense',reference_id=legacy.id,quantity_change=-2,stock_before=22,stock_after=20);db.add(issue)
bed=IPDBed(branch_id=branch,ward_name='Browser Test Ward',bed_number='BR-'+suffix,bed_type='General',daily_rate=300,status='available');db.add(bed);db.commit()
data={'roles':roles,'date':day.isoformat(),'medicine':item.name,'batch_id':str(batch.id),'legacy_dispense_id':str(legacy.id),'bed_id':str(bed.id),'bed_number':bed.bed_number,'suffix':suffix}
fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
with os.fdopen(fd,'w') as file:json.dump(data,file)
os.chmod(output,0o600);print('Synthetic browser fixtures ready (7 role logins, dedicated stock and bed)')
