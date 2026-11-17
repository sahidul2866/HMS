/* OPD dashboard: figures must agree with the visit list and the invoices, cards must open the matching list.
 * Posts synthetic records (one visit, one invoice, one part payment) to the LOCAL dev database. */
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const base=process.env.HMS_E2E_BASE_URL||'http://127.0.0.1:4200';
const output=process.env.HMS_E2E_ARTIFACTS||'/tmp/hms-opd-dashboard';
assert(['localhost','127.0.0.1'].includes(new URL(base).hostname));
(async()=>{
 await fs.mkdir(output,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.HMS_CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await (await browser.newContext({viewport:{width:1440,height:1100},timezoneId:'Asia/Dhaka'})).newPage();page.setDefaultTimeout(20000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400&&r.url().includes('/api/v1/'))errors.push(r.status()+' '+new URL(r.url()).pathname);});
 const stage=[];
 try{
  await page.goto(base,{waitUntil:'networkidle'});
  await page.locator('#login-identity').fill(process.env.HMS_E2E_USER||'superadmin');await page.locator('#login-password').fill(process.env.HMS_E2E_PASSWORD||'Admin123!');
  await page.getByRole('button',{name:'Sign In',exact:true}).click();await page.waitForURL('**/#/dashboard');
  const token=await page.evaluate(()=>localStorage.getItem('hms.accessToken'));
  const cfg=await(await page.request.get(base+'/assets/app-config.json')).json();assert(['localhost','127.0.0.1'].includes(new URL(cfg.apiBaseUrl).hostname));
  const call=async(method,route,data)=>{const r=await page.request.fetch(cfg.apiBaseUrl+route,{method,headers:{Authorization:'Bearer '+token},data});return {status:r.status(),body:await r.json().catch(()=>null)};};
  const today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Dhaka'});
  const before=(await call('GET','/opd/summary')).body;assert.equal(before.summary_date,today,'server day is the hospital day');
  stage.push('server-day');
  // Synthetic registration without a doctor (the billing-desk case), billed and part paid.
  const suffix=Date.now().toString(36).slice(-6);
  const patient=(await call('POST','/patients',{first_name:'DashBD',last_name:'Synthetic'+suffix,phone:'016'+String(Date.now()).slice(-8)})).body;assert(patient?.id);
  const visit=await call('POST','/opd/visits',{patient_id:patient.id,consulting_doctor_name:'Billing Desk',department_name:'General',visit_date:today});assert.equal(visit.status,200,JSON.stringify(visit.body));
  await call('GET','/billing/services');
  const draft=(await call('GET','/billing/drafts/opd-visit/'+visit.body.id)).body;
  const invoice=(await call('POST','/billing/invoices',{patient_id:draft.patient_id,source_opd_visit_id:draft.source_opd_visit_id,source_module:draft.source_module,billing_stage:draft.billing_stage,items:draft.items.map(i=>({billing_service_id:i.billing_service_id,quantity:i.quantity,source_module:i.source_module,source_label:i.source_label}))})).body;assert(invoice?.id,'invoice posted');
  const total=Number(invoice.total_amount);
  if(total>1)assert.equal((await call('POST','/billing/invoices/'+invoice.id+'/payments',{amount:Math.floor(total/2),payment_method:'cash'})).status,200);
  stage.push('seeded');
  const after=(await call('GET','/opd/summary')).body;
  assert.equal(after.total_visits,before.total_visits+1);
  assert.equal(after.unassigned_visits,before.unassigned_visits+1,'billing-desk visit is not a doctor');
  assert(!after.doctor_load.some(d=>/billing desk/i.test(d.doctor_name)),'Billing Desk is not listed as a doctor');
  assert.equal(Number((Number(after.billed_amount)-Number(before.billed_amount)).toFixed(2)),total,'billed amount follows the invoice');
  assert.equal(after.billed_amount,(Number(after.collected_amount)+Number(after.outstanding_amount)).toFixed(2),'billed = collected + outstanding');
  // The visit list for today agrees with the summary count.
  const list=(await call('GET','/opd/visits')).body.filter(v=>v.visit_date===today);
  assert.equal(list.length,after.total_visits,'summary count equals the visit list for the day');
  stage.push('api-agrees');
  await page.goto(base+'/?dash='+Date.now()+'#/opd',{waitUntil:'networkidle'});
  await page.getByRole('heading',{name:'Front Desk Snapshot'}).waitFor();
  const card=label=>page.locator('.kpi-card',{hasText:label}).first();
  assert((await card('Registered').locator('.kpi-value').innerText()).trim()===String(after.total_visits),'Registered card shows the summary count');
  const detail=await card('Registered').locator('.kpi-detail').innerText();
  assert(/paid/.test(detail)&&/not billed yet|with a balance/.test(detail),'Registered card explains its parts: '+detail);
  assert(/Last updated \d\d:\d\d:\d\d/.test(await page.locator('.dashboard-stamp').innerText()),'last-updated stamp');
  assert.equal(await page.locator('.mini-column__label').last().innerText(),'Today','last trend bar is Today');
  assert(await page.getByText(/without a doctor/).count()>=1,'billing-desk visits are explained apart from doctors');
  assert(await page.locator('.live-queue').count()===1,'live queue panel');
  await page.screenshot({path:output+'/dashboard.png',fullPage:true});
  stage.push('page-agrees');
  // A card opens the matching, filtered list.
  await card('Outstanding').click();await page.waitForURL(/opd\/visits.*payment=due/);
  await page.locator('select').filter({has:page.locator('option[value=due]')}).first().waitFor();
  assert.equal(await page.locator('select').filter({has:page.locator('option[value=due]')}).first().inputValue(),'due','Outstanding opens "Awaiting payment"');
  stage.push('card-opens-list');
  // Another day is empty for these synthetic records and says so.
  await page.goto(base+'/?dash='+Date.now()+'#/opd',{waitUntil:'networkidle'});
  await page.getByLabel('Dashboard day').fill('2020-01-01');
  await page.getByRole('heading',{name:/No OPD visits registered on/}).waitFor();
  assert((await page.getByRole('button',{name:'Back to today'}).count())===1);
  await page.getByRole('button',{name:'Back to today'}).click();await page.getByRole('heading',{name:'Front Desk Snapshot'}).waitFor();
  stage.push('other-day');
  // Mobile layout: nothing wider than the screen.
  await page.setViewportSize({width:390,height:900});await page.goto(base+'/?dash='+Date.now()+'#/opd',{waitUntil:'networkidle'});
  await page.getByRole('heading',{name:'Front Desk Snapshot'}).waitFor();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);assert(overflow<=4,'mobile overflow '+overflow);
  await page.screenshot({path:output+'/mobile.png',fullPage:true});
  stage.push('mobile');
  assert.deepEqual(errors,[]);
  console.log('OPD dashboard checks passed: '+stage.join(' > '));
 }catch(e){await page.screenshot({path:output+'/failure.png',fullPage:true}).catch(()=>{});console.error('FAILED after '+stage.join(' > ')+': '+e.message.slice(0,700));process.exitCode=1;}
 finally{await browser.close();}
})();
