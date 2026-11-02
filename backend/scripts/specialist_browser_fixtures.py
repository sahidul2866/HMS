"""Local-only synthetic fixture accounts for specialist browser writes (no superadmin fallback)."""
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
from app.models.user import User
from app.models.role import Role
from app.models.patient import Patient
from app.models.billing import BillingItemConfig
parsed=make_url(get_settings().database_url);assert parsed.host in {'localhost','127.0.0.1'} and parsed.database in {'hms_dev','hms_erp_test'}
db=SessionLocal();suffix=uuid4().hex[:9];branch=db.scalar(select(User).where(User.username=='reception_isha')).branch_id
patient=Patient(branch_id=branch,patient_number='SP-'+suffix,first_name='SpecialistBrowser',last_name='Synthetic'+suffix,phone='019'+''.join(str(int(c,16)%10)for c in suffix[:8]));db.add(patient);db.flush()
roles={}
for label,code in {'Lab':'LAB_TECHNICIAN','Radiology':'RADIOLOGY_TECHNICIAN','Blood':'BLOOD_BANK_OFFICER','OTManager':'OT_MANAGER','Surgeon':'SURGEON','Anesthesia':'ANESTHETIST','OTNurse':'OT_NURSE','OTBilling':'OT_BILLING_OFFICER','Cashier':'BILLING_STAFF','Patient':'PATIENT'}.items():
 role=db.scalar(select(Role).where(Role.code==code));assert role,code
 password=secrets.token_urlsafe(20)+'1!';username='specialist_'+label.lower()+'_'+suffix
 u=User(branch_id=branch,username=username,email=username+'@example.test',full_name='Specialist '+label+' '+suffix,hashed_password=get_password_hash(password),roles=[role],patient_id=patient.id if label=='Patient' else None)
 db.add(u);db.flush();roles[label]={'id':str(u.id),'username':username,'password':password}
configs={}
for label,module in [('lab','laboratory'),('radiology','radiology')]:
 c=db.scalar(select(BillingItemConfig).where(BillingItemConfig.source_module==module,BillingItemConfig.is_active.is_(True),BillingItemConfig.unit_price>0,BillingItemConfig.branch_id==branch).order_by(BillingItemConfig.service_name));assert c,'Missing '+module+' billing catalog'
 configs[label]={'id':str(c.id),'name':c.service_name,'code':c.service_code,'price':str(c.unit_price)}
db.commit();out=Path('/tmp/hms-specialist-fixtures.json');fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
with os.fdopen(fd,'w') as file:json.dump({'roles':roles,'patient_id':str(patient.id),'patient_number':patient.patient_number,'suffix':suffix,'catalog':configs},file)
os.chmod(out,0o600);print('Specialist fixtures ready: 10 synthetic role logins and one dedicated patient')
