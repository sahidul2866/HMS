"""Real Angular/HTTP/PostgreSQL checks for paid, direct, pending and follow-up prescribing."""
import os
import socket
import threading
import subprocess
import time
import json
from pathlib import Path
from uuid import uuid4
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import pytest
from sqlalchemy import text,select,func
from sqlalchemy.orm import Session
from test_opd_workflow_integration import database,seed  # noqa:F401


@pytest.mark.skipif(os.getenv('HMS_RUN_BROWSER_TESTS')!='1',reason='Build frontend and set HMS_RUN_BROWSER_TESTS=1')
@pytest.mark.parametrize('flow',['hospital','doctor_direct','pending','follow_up'])
def test_prescription_application_workflow(database,tmp_path,flow):
    import uvicorn
    from fastapi import Request
    from app.main import app
    from app.core.database import get_db
    from app.dependencies.auth import get_current_user
    from app.models.base import Base
    from app.models.pharmacy import PharmacyMedicine,PharmacyMedicineType,PharmacyGeneric,PharmacyCompany,PharmacyInvestigationSetting
    from app.models.billing import BillingPayment
    from app.models.prescription import PrescriptionRevision,OPDExternalPayment,PrescriptionEvent
    from app.modules.configuration.service import ConfigurationService
    from app.schemas.configuration import ConfigurationProfileCreate
    from app.modules.opd.dashboard import hospital_today
    schema='rx_browser_'+uuid4().hex
    with database.engine.begin() as conn:conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine=database.engine.execution_options(schema_translate_map={None:schema});Base.metadata.create_all(engine)
    root=Path(__file__).resolve().parents[2];dist=root/'frontend/dist/mediprofit-frontend/browser'
    assert (dist/'index.html').exists()
    original=app.dependency_overrides.copy();seed_session=Session(engine,expire_on_commit=False)
    admin,doctors,_,_=seed(seed_session);doctor=doctors[0];doctor.opd_follow_up_fee=100;doctor.opd_bmdc_registration='TEST-BMDC-0'
    form=PharmacyMedicineType(name='Synthetic tablet');generic=PharmacyGeneric(name='Synthetic approved generic');company=PharmacyCompany(name='Synthetic manufacturer')
    seed_session.add_all([form,generic,company]);seed_session.flush()
    seed_session.add(PharmacyMedicine(branch_id=admin.branch_id,name='N Test Brand',strength='TEST-500',dosage_form='Tablet',medicine_type_id=form.id,generic_id=generic.id,company_id=company.id,search_aliases=['Synthetic generic mapping']))
    seed_session.add(PharmacyInvestigationSetting(branch_id=admin.branch_id,code='RX-CBC',test_name='Synthetic CBC',category_name='Pathology',service_area='laboratory',fee=100))
    seed_session.commit()
    ConfigurationService(seed_session).create_profile(ConfigurationProfileCreate(profile_type='prescription_layout',code='RX-BASE',name='Browser base clinical template',scope='doctor',target_type='doctor',target_id=doctor.id,payload={'paper_size':'A5','layout':'single_column','font_size':11,'sections':['complaint','history','vitals','examination','diagnosis','rx','investigation','advice','follow_up'],'fields':[{'key':'allergies','label':'Allergies / অ্যালার্জি','type':'textarea','required':True}]}),admin)
    ConfigurationService(seed_session).create_profile(ConfigurationProfileCreate(profile_type='doctor_share',code='RX-SHARE',name='Approved doctor fee share',scope='doctor',target_id=doctor.id,payload={'method':'percentage','doctor_share_percentage':70}),admin)
    for actor in [admin,doctor]:
        list(actor.roles);list(actor.direct_permissions)
        for role in actor.roles:list(role.permissions)
    def get_test_db():
        with Session(engine,expire_on_commit=False) as session:yield session
    def get_test_user(request:Request):return doctor if request.headers.get('authorization')=='Bearer doctor' else admin
    app.dependency_overrides[get_db]=get_test_db;app.dependency_overrides[get_current_user]=get_test_user
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error',lifespan='off'));thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    static=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(dist)));threading.Thread(target=static.serve_forever,daemon=True).start()
    try:
        for _ in range(100):
            if server.started:break
            time.sleep(.05)
        assert server.started
        result_file=tmp_path/'result.json'
        env={**os.environ,'HMS_RX_API':f'http://127.0.0.1:{port}','HMS_RX_UI':f'http://127.0.0.1:{static.server_port}','HMS_RX_FLOW':flow,'HMS_RX_DOCTOR':str(doctor.id),'HMS_RX_DATE':hospital_today().isoformat(),'HMS_RX_RESULT':str(result_file)}
        result=subprocess.run(['node',str(root/'frontend/e2e/prescription-workflow.cjs')],env=env,capture_output=True,text=True,timeout=100)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
        data=json.loads(result_file.read_text())
        with Session(engine) as session:
            from app.models.encounter import OPDVisit
            current=session.get(OPDVisit,data['visit_id'])
            assert current.prescription_status=='finalized'
            assert current.signed_prescription['prescription_data']['allergies']=='Patient-confirmed history / রোগীর ইতিহাস'
            cash=session.scalar(select(func.coalesce(func.sum(BillingPayment.amount),0)))
            assert cash==(500 if flow=='hospital' else 0)
            if flow=='doctor_direct':
                receipt=session.scalar(select(OPDExternalPayment));assert receipt.amount==500
                assert receipt.settlement_snapshot['hospital_cash_collected']=='0.00' and receipt.settlement_snapshot['hospital_share_due']=='150.00'
                review=session.scalar(select(PrescriptionEvent).where(PrescriptionEvent.visit_id==current.id,PrescriptionEvent.kind=='external_payment_review'));assert review.detail['decision']=='verified'
                from app.models.accounting import Account
                assert session.scalar(select(Account.current_balance).where(Account.branch_id==admin.branch_id,Account.account_code=='1001'))==150
                remittance=session.scalar(select(PrescriptionEvent).where(PrescriptionEvent.visit_id==current.id,PrescriptionEvent.kind=='external_remittance_link'));assert remittance.detail['remaining_hospital_share']=='0.00'
            assert len(list(session.scalars(select(PrescriptionRevision).where(PrescriptionRevision.visit_id==current.id))))==(2 if flow=='hospital' else 1)
            assert Path('/tmp/hms-rx-'+flow+'.pdf').stat().st_size>1000
    finally:
        server.should_exit=True;thread.join(timeout=5);static.shutdown();static.server_close();seed_session.close();app.dependency_overrides=original
        with database.engine.begin() as conn:conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
