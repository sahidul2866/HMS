"""Compiled Angular/HTTP/PostgreSQL accounting acceptance, isolated from working data."""
import json,os,socket,subprocess,threading,time
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import select,text,func
from sqlalchemy.orm import Session
from test_opd_workflow_integration import database,seed


@pytest.mark.skipif(os.getenv('HMS_RUN_BROWSER_TESTS')!='1',reason='Build frontend and enable real browser tests')
def test_accounting_application_collection_closing_and_reports(database,tmp_path):
    import uvicorn
    from fastapi import Request
    from app.main import app
    from app.core.database import get_db
    from app.dependencies.auth import get_current_user
    from app.models.base import Base
    from app.models.user import User
    from app.models.accounting import Account,CashClosing,BankTransaction,JournalEntry
    from app.models.accounting_control import FinancialPeriod,AccountingPolicy
    from app.modules.opd.dashboard import hospital_today
    root=Path(__file__).resolve().parents[2];dist=root/'frontend/dist/mediprofit-frontend/browser'
    assert (dist/'index.html').exists()
    schema='accounting_browser_'+uuid4().hex
    with database.engine.begin() as conn:conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine=database.engine.execution_options(schema_translate_map={None:schema});Base.metadata.create_all(engine)
    session=Session(engine,expire_on_commit=False);original=app.dependency_overrides.copy()
    actor,doctors,_,_=seed(session)
    reviewer=User(branch_id=actor.branch_id,username='accounting-reviewer',email='accounting-reviewer@example.test',full_name='Finance Reviewer',hashed_password='unused',direct_permissions=actor.direct_permissions);session.add(reviewer);session.commit()
    for user in [actor,reviewer]:
        list(user.roles);list(user.direct_permissions)
        for role in user.roles:list(role.permissions)
    def test_db():
        with Session(engine,expire_on_commit=False) as db:yield db
    def test_user(request:Request):return reviewer if request.headers.get('authorization')=='Bearer reviewer' else actor
    app.dependency_overrides[get_db]=test_db;app.dependency_overrides[get_current_user]=test_user
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
        result_file=tmp_path/'accounting.json'
        env={**os.environ,'HMS_ACCT_API':f'http://127.0.0.1:{port}','HMS_ACCT_UI':f'http://127.0.0.1:{static.server_port}','HMS_ACCT_DATE':hospital_today().isoformat(),'HMS_ACCT_DOCTOR':str(doctors[0].id),'HMS_ACCT_RESULT':str(result_file)}
        result=subprocess.run(['node',str(root/'frontend/e2e/accounting-workflow.cjs')],capture_output=True,text=True,env=env,timeout=130)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
        data=json.loads(result_file.read_text())
        with Session(engine) as check:
            assert check.get(CashClosing,data['shift_id']).status=='approved'
            assert check.get(CashClosing,data['shift_id']).difference_amount==0
            assert check.scalar(select(Account.current_balance).where(Account.account_code=='1001'))==5500
            assert check.scalar(select(func.count(BankTransaction.id)).where(BankTransaction.reconciliation_status=='matched'))==1
            assert check.scalar(select(FinancialPeriod.status))=='closed'
            assert check.get(AccountingPolicy,data['policy_id']).approved_by==reviewer.id
            for entry in check.scalars(select(JournalEntry)):assert entry.total_debit==entry.total_credit
        from openpyxl import load_workbook
        workbook=load_workbook('/tmp/hms-accounting-statements.xlsx',data_only=True)
        assert workbook['Trial Balance'].cell(workbook['Trial Balance'].max_row,4).value==5600
        assert Path('/tmp/hms-accounting-statements.pdf').stat().st_size>1000
    finally:
        server.should_exit=True;thread.join(timeout=5);static.shutdown();static.server_close();session.close();app.dependency_overrides=original
        with database.engine.begin() as conn:conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
