"""Real browser -> Angular -> HTTP API -> isolated PostgreSQL policy administration."""
import os
import socket
import subprocess
import threading
import time
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from test_opd_workflow_integration import database, seed  # noqa: F401


@pytest.mark.skipif(os.getenv('HMS_RUN_BROWSER_TESTS') != '1', reason='Set HMS_RUN_BROWSER_TESTS=1 after building frontend')
def test_browser_policy_save_and_persisted_version(database, tmp_path):
    import uvicorn
    from app.main import app
    from app.core.database import get_db
    from app.dependencies.auth import get_current_user
    from app.models.base import Base
    from app.models.billing_policy import BillingPolicy
    from sqlalchemy import select
    root=Path(__file__).resolve().parents[2]
    dist=root/'frontend/dist/mediprofit-frontend/browser'
    assert (dist/'index.html').exists(), 'Build the frontend before running browser integration tests'
    schema='billing_browser_'+uuid4().hex
    with database.engine.begin() as conn:conn.execute(text(f'CREATE SCHEMA {schema}'))
    engine=database.engine.execution_options(schema_translate_map={None:schema})
    Base.metadata.create_all(engine)
    original=app.dependency_overrides.copy()
    seed_session=Session(engine,expire_on_commit=False)
    from test_billing_policies import setup_invoice
    from app.schemas.billing_policy import FinancialRules
    actor,billing,_,invoice,config,_=setup_invoice(seed_session,rules=FinancialRules(show_item_discounts=False),paid=1800)
    from app.schemas.billing import BillingInvoiceCreate,BillingInvoiceItemCreate
    from app.models.patient import Patient
    unpaid=billing.create_invoice(BillingInvoiceCreate(patient_id=invoice.patient_id,items=[BillingInvoiceItemCreate(billing_service_id=config['id'],quantity=1)]),actor,{})
    patient=seed_session.get(Patient,invoice.patient_id)
    seed_session.commit()
    list(actor.roles);list(actor.direct_permissions)
    def get_test_db():
        with Session(engine,expire_on_commit=False) as session:yield session
    app.dependency_overrides[get_db]=get_test_db
    app.dependency_overrides[get_current_user]=lambda:actor
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error',lifespan='off'))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    static=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(dist)))
    static_thread=threading.Thread(target=static.serve_forever,daemon=True);static_thread.start()
    script=tmp_path/'billing-browser.cjs'
    script.write_text(r'''
const {chromium}=require(process.env.HMS_PLAYWRIGHT_MODULE);
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 let page;try {
 const context=await browser.newContext({viewport:{width:1440,height:1100},timezoneId:'Asia/Dhaka'});
 await context.addInitScript(()=>localStorage.setItem('hms.accessToken','isolated-test-token'));
 await context.route(/http:\/\/(localhost|127\.0\.0\.1):8000\//,r=>r.continue({url:r.request().url().replace(/http:\/\/(localhost|127\.0\.0\.1):8000/,process.env.HMS_TEST_API)}));
 page=await context.newPage();page.setDefaultTimeout(20000);page.on('pageerror',e=>console.error('Browser page error:',e.message));
 await page.goto(process.env.HMS_TEST_UI+'/#/billing/settings');
 await page.getByRole('heading',{name:'Financial policies and settlements',exact:true}).waitFor();
 await page.getByLabel('Effective from',{exact:true}).fill('2026-11-19T09:00');
 await page.getByLabel('Policy reason',{exact:true}).fill('Browser verified hospital policy');
 await page.getByLabel('Financial rules',{exact:true}).fill(JSON.stringify({discount_sharing:{hospital:'70',doctor:'30'},doctor_key:'doctor',doctor_revenue_percentage:'70',show_item_discounts:false}));
 const [saved]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/billing/policies')&&r.request().method()==='POST'),page.getByRole('button',{name:'Save new policy version',exact:true}).click()]);
 assert.equal(saved.status(),200,await saved.text());
 await page.getByRole('cell',{name:'Browser verified hospital policy',exact:true}).waitFor();
 await page.screenshot({path:process.env.HMS_TEST_SCREENSHOT,fullPage:true});
 const summaryPage=await context.newPage();
 await summaryPage.goto(process.env.HMS_TEST_UI+'/#/billing/create');
 await summaryPage.getByPlaceholder('Search patient id, name, phone, or email').fill(process.env.HMS_TEST_PATIENT_NUMBER);
 await summaryPage.locator('.search-dropdown .result-card').filter({hasText:process.env.HMS_TEST_PATIENT_NUMBER}).first().click();
 await summaryPage.getByRole('heading',{name:'Patient history & credit dues',exact:true}).waitFor();
 const patientSummary=summaryPage.getByRole('region',{name:'Patient billing history'});
 await patientSummary.getByText(process.env.HMS_TEST_UNPAID_NUMBER,{exact:true}).first().waitFor();
 assert((await patientSummary.locator('.totals .due').innerText()).includes('1,000.00'),'actual unpaid invoice is included in credit dues');
 assert.equal(await summaryPage.getByRole('heading',{name:'Services and items',exact:true}).count(),0,'patient history appears before items');
 await summaryPage.screenshot({path:'/tmp/hms-billing-patient-summary.png',fullPage:true});
 await patientSummary.getByRole('link',{name:'View / collect dues',exact:true}).click();
 await summaryPage.getByRole('button',{name:'Print Invoice',exact:true}).waitFor();
 assert(summaryPage.url().includes('invoiceId='),'dues action opens the original invoice');
 await summaryPage.goto(process.env.HMS_TEST_UI+'/#/billing/create');
 await patientSummary.getByRole('button',{name:'New Billing',exact:true}).waitFor();
 await patientSummary.getByRole('button',{name:'New Billing',exact:true}).click();
 await summaryPage.getByRole('heading',{name:'Services and items',exact:true}).waitFor();
 assert((await summaryPage.locator('.top-patient-bar').innerText()).includes(process.env.HMS_TEST_PATIENT_NUMBER),'new billing retains selected patient');
 await summaryPage.close();
 await page.goto(process.env.HMS_TEST_UI+'/#/billing/list?invoiceId='+process.env.HMS_TEST_INVOICE);
 await page.getByRole('button',{name:'Print Invoice',exact:true}).waitFor();
 await page.getByRole('button',{name:'Print Invoice',exact:true}).click();
 const frame=page.frameLocator('.invoice-preview-frame');
 await frame.getByText('Net payable after credits',{exact:true}).first().waitFor();
 const html=await page.locator('.invoice-preview-frame').evaluate(el=>el.contentDocument.documentElement.outerHTML);
 assert(html.includes('Extra Discount'),'printed invoice discount is preserved');
 assert(html.includes('<td>—</td>'),'item discount hidden according to historical policy');
 const pdfPage=await context.newPage();await pdfPage.setContent(html);
 const pdf=await pdfPage.pdf({path:'/tmp/hms-billing-invoice.pdf',format:'A4',printBackground:true});
 assert.equal((pdf.toString('latin1').match(/\/Type\s*\/Page\b/g)||[]).length,2,'One page per invoice copy');await pdfPage.close();
 await page.locator('.invoice-preview-modal').getByRole('button',{name:'Close',exact:true}).click();
 await page.locator('.invoice-more-actions summary').click();
 page.on('dialog',d=>d.accept('Browser verified full cancellation'));
 const [cancelled]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/cancel')&&r.request().method()==='POST'),page.getByRole('button',{name:'Cancel and refund invoice',exact:true}).click()]);
 assert.equal(cancelled.status(),200,await cancelled.text());
 const result=await cancelled.json();assert.equal(result.status,'void');assert.equal(result.refunded_amount,'1800.00');
 console.log('Browser policy administration, historical invoice print/PDF and full cancellation passed');
 } catch(error){if(page){await page.screenshot({path:'/tmp/hms-patient-browser-failure.png',fullPage:true});console.error(await page.locator('body').innerText());}throw error;}finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
''')
    try:
        for _ in range(100):
            if server.started:break
            time.sleep(.05)
        assert server.started
        env={**os.environ,'HMS_PLAYWRIGHT_MODULE':str(root/'frontend/node_modules/playwright'),'HMS_TEST_API':f'http://127.0.0.1:{port}','HMS_TEST_UI':f'http://127.0.0.1:{static.server_port}','HMS_TEST_SCREENSHOT':'/tmp/hms-billing-policy-browser.png','HMS_TEST_INVOICE':str(invoice.id),'HMS_TEST_PATIENT_NUMBER':patient.patient_number,'HMS_TEST_UNPAID_NUMBER':unpaid.invoice_number}
        result=subprocess.run(['node',str(script)],env=env,text=True,capture_output=True,timeout=60)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
        with Session(engine) as session:
            saved=session.scalar(select(BillingPolicy).where(BillingPolicy.reason=='Browser verified hospital policy'))
            assert saved.reason=='Browser verified hospital policy'
            assert saved.rules['discount_sharing']=={'hospital':'70','doctor':'30'}
            from app.models.billing import BillingInvoice
            persisted=session.get(BillingInvoice,invoice.id)
            assert persisted.status=='void' and persisted.refunded_amount==1800 and persisted.paid_amount==0
            assert Path('/tmp/hms-billing-invoice.pdf').stat().st_size>1000
    finally:
        server.should_exit=True;thread.join(timeout=5)
        static.shutdown();static.server_close();seed_session.close()
        app.dependency_overrides=original
        with database.engine.begin() as conn:conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
