"""Local synthetic receipt -> batch return -> cashier credit -> supervisor custody -> patient review."""
import json,os,uuid
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path
import httpx
from sqlalchemy import select
import app.main
from app.core.database import SessionLocal
from app.core.security import create_access_token,get_password_hash
from app.models.user import User
from app.models.permission import Permission
from app.models.inventory import InventoryItem,InventoryStore,InventoryStoreItem,StockBatch
from app.models.patient_portal_account import PatientPortalAccount
from app.modules.auth.service import AuthService
BASE=os.getenv('HMS_ROLEFLOW_API','http://127.0.0.1:8000/api/v1')
assert BASE.startswith(('http://127.0.0.1:','http://localhost:'))
from sqlalchemy.engine import make_url
from app.core.config import get_settings
configured=make_url(get_settings().database_url)
assert configured.host in {'localhost','127.0.0.1'} and configured.database in {'hms_dev','hms_erp_test'}, 'Synthetic role workflow requires the local development/test database'
db=SessionLocal();client=httpx.Client(timeout=60);checks=[];suffix=uuid.uuid4().hex[:10]
def headers(user):return {'Authorization':'Bearer '+create_access_token(str(user.id),AuthService(db).get_effective_permissions(user))[0]}
def call(user,method,route,body=None,status=200):
 r=client.request(method,BASE+route,json=body,headers=headers(user));assert r.status_code==status,(route,r.status_code,r.text[:300]);return r.json()
def staff(username):return db.scalar(select(User).where(User.username==username))
reception=staff('reception_isha');pharmacist=staff('pharma_nadia');assert reception and pharmacist
patient=call(reception,'POST','/patients',{'first_name':'PhysicalReturn','last_name':'Synthetic'+suffix,'phone':'018'+''.join(str(int(c,16)%10) for c in suffix[:8])});checks.append('reception registration')
def test_user(label,codes):
 u=User(branch_id=reception.branch_id,username='return_'+label+'_'+suffix,email=label+suffix+'@example.test',full_name='Synthetic '+label,hashed_password=get_password_hash(uuid.uuid4().hex),direct_permissions=list(db.scalars(select(Permission).where(Permission.code.in_(codes)))))
 db.add(u);db.flush();return u
cashier=test_user('cashier',['billing.view','billing.invoice.create','billing.payment.collect','billing.payment.refund','billing.item.service','billing.item.medicine'])
supervisor=test_user('supervisor',['billing.view','billing.payment.collect','billing.service.manage'])
item=InventoryItem(branch_id=reception.branch_id,name='RoleReturn Medicine '+suffix,stock_quantity=10,item_type='medicine',created_by=reception.id,updated_by=reception.id)
store=InventoryStore(branch_id=reception.branch_id,code='RR-'+suffix,name='Synthetic return store',store_type='pharmacy',created_by=reception.id,updated_by=reception.id);db.add_all([item,store]);db.flush()
balance=InventoryStoreItem(item_id=item.id,store_id=store.id,quantity_on_hand=10,reserved_quantity=0,created_by=reception.id,updated_by=reception.id)
batch=StockBatch(item_id=item.id,store_id=store.id,batch_no='RR-BATCH-'+suffix,quantity=10,unit_cost=2,total_cost=20,expiry_date=date.today()+timedelta(days=60),created_by=reception.id,updated_by=reception.id);db.add_all([balance,batch]);db.commit()
dispense=call(pharmacist,'POST','/pharmacy/dispense',{'patient_id':patient['id'],'medicine_name':item.name,'quantity':5,'unit_price':10});checks.append('pharmacist actual issue')
issued=call(pharmacist,'GET','/pharmacy/dispenses')
assert not any(row['billing_invoice_item_id']==dispense['billing_invoice_item_id'] and row['status']=='pending' for row in issued), 'Walk-in issue left a duplicate pending work item'
invoice_id=dispense['billing_invoice_id'];line=dispense['billing_invoice_item_id'];assert invoice_id and line
call(cashier,'POST',f'/billing/invoices/{invoice_id}/payments',{'amount':50,'payment_method':'cash'});checks.append('cashier receipt')
call(cashier,'POST',f'/billing/invoices/{invoice_id}/return',{'reason':'Cannot credit before physical receipt','items':[{'invoice_item_id':line,'quantity':2}]},409);checks.append('unreceived credit rejected')
source=call(pharmacist,'GET',f'/pharmacy/dispenses/{dispense["id"]}/return-sources')[0]
body={'quantity':2,'source_issue_id':source['id'],'inspected':True,'restock':True,'note':'Sealed, inspected physical return','request_id':'RR-'+suffix}
call(pharmacist,'POST',f'/pharmacy/dispenses/{dispense["id"]}/return',body);call(pharmacist,'POST',f'/pharmacy/dispenses/{dispense["id"]}/return',body);db.expire_all()
assert db.get(StockBatch,batch.id).quantity==7 and db.get(InventoryStoreItem,balance.id).quantity_on_hand==7 and db.get(InventoryItem,item.id).stock_quantity==7;checks.append('original batch reconciled once on retry')
credit=call(cashier,'POST',f'/billing/invoices/{invoice_id}/return',{'reason':'Pharmacy physically received two sealed units','items':[{'invoice_item_id':line,'quantity':2}]})
assert Decimal(credit['paid_amount'])==30 and Decimal(credit['refunded_amount'])==20 and Decimal(credit['due_amount'])==0;checks.append('cashier linked credit and payout')
# Competing whole returns must not each restore the same two units.
from concurrent.futures import ThreadPoolExecutor
second=call(pharmacist,'POST','/pharmacy/dispense',{'patient_id':patient['id'],'medicine_name':item.name,'quantity':2,'unit_price':10})
second_source=call(pharmacist,'GET',f'/pharmacy/dispenses/{second["id"]}/return-sources')[0]
pharmacy_headers=headers(pharmacist)
def competing(label):
    return httpx.post(BASE+f'/pharmacy/dispenses/{second["id"]}/return',headers=pharmacy_headers,json={'quantity':2,'source_issue_id':second_source['id'],'inspected':True,'restock':True,'note':'Concurrent whole return accepted once','request_id':label+'-'+suffix},timeout=60).status_code
with ThreadPoolExecutor(max_workers=2) as pool: statuses=list(pool.map(competing,['race-A','race-B']))
assert sorted(statuses)==[200,409],statuses
db.expire_all();assert db.get(StockBatch,batch.id).quantity==7
checks.append('concurrent returns cannot restore the same units twice')
second_credit=call(cashier,'POST',f'/billing/invoices/{second["billing_invoice_id"]}/return',{'reason':'Whole unused second issue received back','items':[{'invoice_item_id':second['billing_invoice_item_id'],'quantity':2}]})
assert Decimal(second_credit['due_amount'])==0 and Decimal(second_credit['paid_amount'])==0
checks.append('unpaid physically received issue credited without payout')

ledger=call(cashier,'GET','/billing/cash/balance');assert Decimal(ledger['expected_amount'])==30
handover=call(cashier,'POST','/billing/cash/handovers',{'receiver_id':str(supervisor.id),'declared_amount':30,'note':'Synthetic receipt less physical return payout'})
call(cashier,'POST',f'/billing/cash/handovers/{handover["id"]}/accept',{'note':'Self acceptance forbidden'},403)
call(supervisor,'POST',f'/billing/cash/handovers/{handover["id"]}/accept',{'note':'Independent supervisor counted thirty'});checks.append('independent supervisor custody acceptance')
account=PatientPortalAccount(branch_id=reception.branch_id,patient_id=uuid.UUID(patient['id']),username='return_patient_'+suffix,email='patient'+suffix+'@example.test',full_name='Synthetic return patient',hashed_password=get_password_hash(uuid.uuid4().hex));db.add(account);db.commit()
token=create_access_token(str(account.id),['patient.portal.view'],principal_type='patient')[0]
r=client.get(BASE+'/portal/overview',headers={'Authorization':'Bearer '+token});assert r.status_code==200,r.text
assert r.json()['patient']['patient']['id']==patient['id'];checks.append('patient own record review')
r=client.post(BASE+f'/billing/invoices/{invoice_id}/refunds',json={'amount':1,'reason':'Patient forbidden'},headers={'Authorization':'Bearer '+token});assert r.status_code in (401,403);checks.append('patient cannot perform cashier action')
private=Path('/tmp/hms-physical-return-roles.json');private.write_text(json.dumps({'Cashier':{'username':cashier.username,'permissions':AuthService(db).get_effective_permissions(cashier),'token':headers(cashier)['Authorization'][7:]},'Supervisor':{'username':supervisor.username,'permissions':AuthService(db).get_effective_permissions(supervisor),'token':headers(supervisor)['Authorization'][7:]},'Patient':{'username':account.username,'permissions':['patient.portal.view'],'token':token}}));os.chmod(private,0o600)
Path('/tmp/hms-physical-return-roleflow.json').write_text(json.dumps({'checks':checks,'invoice_id':invoice_id,'dispense_id':dispense['id'],'batch_id':str(batch.id)},indent=2));print(f'{len(checks)} physical-return role workflow checks passed')
