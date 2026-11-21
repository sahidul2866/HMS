/* Runs only against the isolated local API/schema created by test_prescription_browser.py. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fs = require('node:fs/promises');
const api = process.env.HMS_RX_API;
const ui = process.env.HMS_RX_UI;
const flow = process.env.HMS_RX_FLOW;
assert(api && ui && ['localhost','127.0.0.1'].includes(new URL(api).hostname));
assert(['localhost','127.0.0.1'].includes(new URL(ui).hostname));
(async () => {
 const browser = await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 let page;
 try {
  const context=await browser.newContext({viewport:{width:1500,height:1100},timezoneId:'Asia/Dhaka'});
  await context.addInitScript(()=>{if(!localStorage.getItem('hms.accessToken'))localStorage.setItem('hms.accessToken','admin');});
  await context.route(/http:\/\/(localhost|127\.0\.0\.1):8000\//,r=>r.continue({url:r.request().url().replace(/http:\/\/(localhost|127\.0\.0\.1):8000/,api)}));
  page=await context.newPage();page.setDefaultTimeout(20000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('dialog',d=>d.accept(d.message().includes('Amount received')?'500':'Browser-authorized clinical action'));
  async function call(method,path,body,role='admin') {const r=await page.request.fetch(api+'/api/v1'+path,{method,headers:{Authorization:'Bearer '+role},data:body});assert.equal(r.status(),200,await r.text());return r.json();}
  async function go(path) {await page.evaluate(()=>sessionStorage.removeItem('hms.tabs')).catch(()=>{});await page.goto(ui+'/#'+path,{waitUntil:'networkidle'});}
  await go('/opd/configuration');
  if(flow==='hospital') {
   await page.getByRole('button',{name:/^Prescription Builder/}).click();
   await page.getByLabel('Profile Name',{exact:true}).fill('Browser configured prescription');
   await page.getByLabel('Code',{exact:true}).fill('browser-rx-template');
   await page.getByLabel('Doctor / department UUID',{exact:true}).fill(process.env.HMS_RX_DOCTOR);
   await page.getByRole('button',{name:'Add clinical field',exact:true}).click();
   await page.getByLabel('Data key',{exact:true}).fill('allergies');
   await page.getByLabel('Label (English / Bangla)',{exact:true}).fill('Allergies / অ্যালার্জি');
   await page.getByLabel('Component',{exact:true}).selectOption('textarea');
   await page.getByLabel('Required',{exact:true}).check();
   const [saved]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/configuration/profiles')&&r.request().method()==='POST'),page.getByRole('button',{name:'Save Configuration',exact:true}).click()]);
   assert.equal(saved.status(),200,await saved.text());
   await page.screenshot({path:'/tmp/hms-rx-builder.png',fullPage:true});
  }
  let patient=await call('POST','/patients',{first_name:'Prescription',last_name:'Synthetic '+flow,phone:'017'+String(Date.now()).slice(-8)});
  const visitBody={patient_id:patient.id,doctor_user_id:process.env.HMS_RX_DOCTOR,consulting_doctor_name:'Doctor 0',department_name:'Medicine',visit_date:process.env.HMS_RX_DATE,visit_type:'new'};
  let prior;
  if(flow==='follow_up') {
   prior=await call('POST','/opd/visits',visitBody);
   await call('PUT',`/opd/visits/${prior.id}/status`,{status:'in_consultation'},'doctor');
   await call('POST',`/opd/visits/${prior.id}/finalize`,{final_diagnosis:'Prior clinical assessment',prescription_data:{allergies:'Previously recorded allergy history'}},'doctor');
  }
  const visit=await call('POST','/opd/visits',{...visitBody,visit_type:flow==='follow_up'?'follow_up':'new'});
  if(flow==='hospital')await call('PUT',`/opd/visits/${visit.id}/payment`,{amount:'500',discount:'0'});
  await page.evaluate(()=>localStorage.setItem('hms.accessToken','doctor'));
  await page.reload({waitUntil:'networkidle'});
  await go('/opd');
  await page.getByRole('heading',{name:'Outpatient Overview',exact:true}).waitFor();
  await go('/opd/visits?openVisit='+visit.id);
  await page.getByRole('heading',{name:visit.visit_number,exact:true}).waitFor();
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/status') && r.request().method()==='PUT'),page.getByRole('button',{name:'Start Visit',exact:true}).last().click()]);
  await page.getByRole('button',{name:'Finalize Prescription',exact:true}).waitFor();
  if(flow==='doctor_direct') {
   const [received]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/external-payment')&&r.request().method()==='POST'),page.getByRole('button',{name:'Record doctor-direct payment',exact:true}).click()]);
   assert.equal(received.status(),200,await received.text());
  }
  await page.getByLabel('Allergies / অ্যালার্জি',{exact:false}).fill('Patient-confirmed history / রোগীর ইতিহাস');
  await page.getByLabel('Chief complaints',{exact:true}).fill('Browser-recorded complaint');
  await page.getByPlaceholder('Final diagnosis',{exact:true}).fill('Clinician-entered test assessment');
  const name=page.getByPlaceholder('Medicine name',{exact:true});await name.fill('N');
  const selected=page.getByRole('button',{name:/^N Test Brand/}).first();await selected.waitFor();await selected.click();
  assert.equal(await page.getByLabel('Dose',{exact:true}).inputValue(),'','Catalog selection must not infer a dose');
  await page.getByLabel('Dose',{exact:true}).fill('Doctor-confirmed synthetic test dose');
  await page.getByLabel('Frequency',{exact:true}).fill('1+0+1');
  await page.getByPlaceholder('Duration',{exact:true}).fill('Explicit test duration');
  const [medicine]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/orders')&&r.request().method()==='POST'),page.getByRole('button',{name:'Add Medicine',exact:true}).click()]);
  assert.equal(medicine.status(),200,await medicine.text());
  await page.getByPlaceholder('Search lab or radiology test',{exact:true}).fill('CBC');
  const investigation=page.getByRole('button',{name:/^Synthetic CBC/}).first();await investigation.waitFor();
  const [ordered]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/orders')&&r.request().method()==='POST'),investigation.click()]);
  assert.equal(ordered.status(),200,await ordered.text());
  await page.getByLabel('Clinical advice',{exact:true}).fill('Recorded follow-up advice / ফলো-আপ');
  // Autosave is exercised through the real editor, API and database, then recovered after reload.
  await page.getByText('Draft saved',{exact:false}).first().waitFor();
  const savedDraft=await call('GET',`/opd/visits/${visit.id}`,undefined,'doctor');
  assert.equal(savedDraft.prescription_data.allergies,'Patient-confirmed history / রোগীর ইতিহাস');
  if(flow==='pending') {
   const longOrders=Array.from({length:90},(_,i)=>({order_type:'prescription',item_name:'Synthetic long entry '+String(i).padStart(3,'0'),instructions:'Explicit test-only clinical instructions. বাংলা নির্দেশনা।',quantity:1,request_key:'long-'+flow+'-'+String(i).padStart(8,'0')}));
   for(let i=0;i<longOrders.length;i+=45)await call('POST',`/opd/visits/${visit.id}/orders-batch`,longOrders.slice(i,i+45),'doctor');
  }
  await go('/opd/visits?openVisit='+visit.id);
  await page.getByLabel('Chief complaints',{exact:true}).waitFor();
  assert.equal(await page.getByLabel('Chief complaints',{exact:true}).inputValue(),'Browser-recorded complaint');
  const [signed]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/finalize')&&r.request().method()==='POST'),page.getByRole('button',{name:'Finalize Prescription',exact:true}).click()]);
  assert.equal(signed.status(),200,await signed.text());
  const signedVisit=await signed.json();assert.equal(signedVisit.prescription_status,'finalized');
  assert.equal(signedVisit.orders.filter(o=>o.order_type==='investigation').length,1);
  if(flow==='pending')assert.equal(signedVisit.consultation_payment_status,'unpaid');
  if(flow==='doctor_direct') {
   assert.equal(signedVisit.consultation_payment_status,'doctor_direct');
   const claims=await call('GET',`/opd/visits/${visit.id}/external-payments`,undefined,'admin');
   const review=await call('POST',`/opd/visits/${visit.id}/external-payments/${claims[0].id}/review`,{decision:'verified',evidence:'Synthetic finance evidence REF-001',request_key:'browser-direct-review'},'admin');
   assert.equal(review.detail.decision,'verified');assert.equal(review.detail.hospital_cash_collected,'0.00');
   const journal=await call('POST','/accounting/journal-entries',{journal_date:process.env.HMS_RX_DATE,source_module:'opd_external_remittance',source_reference:claims[0].id,narration:'Synthetic actual hospital remittance receipt',status:'posted',lines:[{account_code:'1001',account_name:'Cash / Bank',debit_amount:150,credit_amount:0},{account_code:'1160',account_name:'Doctor remittance clearing',debit_amount:0,credit_amount:150}]},'admin');
   const linked=await call('POST',`/opd/visits/${visit.id}/external-payments/${claims[0].id}/remittances`,{journal_id:journal.id,amount:150,evidence:'Synthetic finance remittance receipt',request_key:'browser-remit-link'},'admin');
   assert.equal(linked.detail.remaining_hospital_share,'0.00');
   const reconciled=await call('GET',`/opd/visits/${visit.id}/external-payments`,undefined,'admin');assert.equal(reconciled[0].hospital_share_remaining,'0.00');
  }
  if(flow==='hospital')assert.equal(signedVisit.consultation_payment_status,'paid');
  await page.getByRole('button',{name:'Print Prescription',exact:true}).last().click();
  const preview=page.frameLocator('.prescription-preview-frame');
  await preview.getByText('Browser-recorded complaint',{exact:false}).first().waitFor();
  const html=await page.locator('.prescription-preview-frame').evaluate(el=>el.contentDocument.documentElement.outerHTML);
  assert(html.includes('TEST-BMDC-0'));assert(html.includes('N Test Brand'));assert(html.includes('Patient-confirmed history'));
  assert(!html.includes('DRAFT — NOT SIGNED'));
  const pdfPage=await context.newPage();await pdfPage.setContent(html);
  const pdf=await pdfPage.pdf({path:'/tmp/hms-rx-'+flow+'.pdf',preferCSSPageSize:true,printBackground:true});
  const pages=(pdf.toString('latin1').match(/\/Type\s*\/Page\b/g)||[]).length;
  if(flow==='pending'){assert(pages>1);assert(html.includes('Synthetic long entry 089'));}
  await pdfPage.screenshot({path:'/tmp/hms-rx-print-'+flow+'.png',fullPage:true});await pdfPage.close();
  await page.getByRole('button',{name:'Close preview',exact:true}).click();
  if(flow==='hospital') {
   const original=await call('GET',`/opd/visits/${visit.id}/prescription-history`,undefined,'doctor');
   await page.getByRole('button',{name:'Amend signed prescription',exact:true}).click();
   await page.getByPlaceholder('Final diagnosis',{exact:true}).fill('Amended clinical assessment');
   const [revised]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/finalize')&&r.request().method()==='POST'),page.getByRole('button',{name:'Finalize Prescription',exact:true}).click()]);
   assert.equal(revised.status(),200,await revised.text());
   const versions=await call('GET',`/opd/visits/${visit.id}/prescription-history`,undefined,'doctor');
   assert.equal(versions.length,2);assert.deepEqual(versions[0].snapshot,original[0].snapshot);assert.equal(versions[1].snapshot.final_diagnosis,'Amended clinical assessment');
  }
  if(flow==='follow_up'){const old=await call('GET',`/opd/visits/${prior.id}/prescription-history`,undefined,'doctor');assert.equal(old[0].snapshot.final_diagnosis,'Prior clinical assessment');}
  await fs.writeFile(process.env.HMS_RX_RESULT,JSON.stringify({flow,visit_id:visit.id,patient_id:patient.id,pages,console_errors:errors},null,2));
  assert.deepEqual(errors,[]);console.log('Prescription workflow '+flow+' passed; PDF pages '+pages);
 } catch(error) {if(page){await page.screenshot({path:'/tmp/hms-rx-failure-'+flow+'.png',fullPage:true}).catch(()=>{});await fs.writeFile('/tmp/hms-rx-failure-'+flow+'.txt',await page.locator('body').innerText()).catch(()=>{});}throw error;} finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
