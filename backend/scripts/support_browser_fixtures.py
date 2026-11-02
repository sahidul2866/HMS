"""Local-only isolated support-service branch and role accounts; operational writes are browser-owned."""
import json,os,secrets
from datetime import date
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.engine import make_url
import app.main
from app.core.database import SessionLocal
from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.branch import Branch
from app.models.department import Department
from app.models.hr import HRLeaveType
from app.models.user import User
from app.models.role import Role
from app.models.patient import Patient
parsed=make_url(get_settings().database_url)
assert parsed.host in {'localhost','127.0.0.1'} and parsed.database in {'hms_dev','hms_erp_test'}
db=SessionLocal();suffix=uuid4().hex[:9]
branch=Branch(code='SUPPORT-'+suffix,name='Synthetic support acceptance '+suffix);db.add(branch);db.flush()
dept=Department(branch_id=branch.id,code='SUP-'+suffix,name='Synthetic support');db.add(dept);db.flush()
roles={}
role_codes={'HR':'HR_MANAGER','Payroll':'PAYROLL_OFFICER','Head':'DEPARTMENT_HEAD','Employee':'EMPLOYEE','Transport':'TRANSPORT_MANAGER','Driver':'TRANSPORT_DRIVER','Dietitian':'DIETITIAN','Kitchen':'KITCHEN_STAFF','Catering':'CATERING_MANAGER'}
if os.getenv('HMS_E2E_POSTING_FIXTURES')=='1': role_codes.update({'Cashier':'BILLING_STAFF','Inventory':'INVENTORY_MANAGER','Accountant':'ACCOUNTANT','Doctor':'DOCTOR','Nurse':'NURSE'})
for label,code in role_codes.items():
 role=db.scalar(select(Role).where(Role.code==code));assert role,code
 password=secrets.token_urlsafe(20)+'1!';username='support_'+label.lower()+'_'+suffix
 u=User(branch_id=branch.id,department_id=dept.id if label in {'Head','Employee'} else None,username=username,email=username+'@example.test',full_name='Support '+label+' '+suffix,hashed_password=get_password_hash(password),roles=[role]);db.add(u);db.flush();roles[label]={'id':str(u.id),'username':username,'password':password}
patient=Patient(branch_id=branch.id,patient_number='SUP-'+suffix,first_name='Support',last_name='Synthetic'+suffix);db.add(patient)
db.flush()
extra={}
if os.getenv('HMS_E2E_POSTING_FIXTURES')=='1':
 from app.models.encounter import IPDBed
 bed=IPDBed(branch_id=branch.id,ward_name='Synthetic ward',bed_number='POST-'+suffix,daily_rate=0);db.add(bed);db.flush();extra['bed_id']=str(bed.id)
 role=db.scalar(select(Role).where(Role.code=='PATIENT'));password=secrets.token_urlsafe(20)+'1!';username='support_patient_'+suffix
 u=User(branch_id=branch.id,patient_id=patient.id,username=username,email=username+'@example.test',full_name='Support Patient '+suffix,hashed_password=get_password_hash(password),roles=[role]);db.add(u);db.flush();roles['Patient']={'id':str(u.id),'username':username,'password':password}
leave=HRLeaveType(branch_id=branch.id,code='SUP-UNPAID-'+suffix,name='Synthetic unpaid leave',is_paid=False);db.add(leave);db.commit()
out=Path('/tmp/hms-support-fixtures.json');fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
with os.fdopen(fd,'w') as file:json.dump({'roles':roles,'branch_id':str(branch.id),'department_id':str(dept.id),'patient_id':str(patient.id),'patient_number':patient.patient_number,'leave_type_id':str(leave.id),'suffix':suffix,**extra},file)
os.chmod(out,0o600);print('Support fixtures ready: dedicated synthetic branch, '+str(len(roles))+' role accounts, patient and leave policy')
